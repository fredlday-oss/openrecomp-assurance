from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from harness.compare.observables import defined_observables, require_equal

OPENRECOMP_PIN = "53d0bce144356f2b4ee7120c5f8c13cb82c4bf90"

SEEDS = (
    ("seed-fib-depth", "u32 recursive = fib(7u);", "u32 recursive = fib(6u);"),
    ("seed-state-rounds", "u32 looped = state_loop(5u);", "u32 looped = state_loop(4u);"),
    ("seed-rotate-count", "u32 mixed = rotate_mix(looped, 3u);", "u32 mixed = rotate_mix(looped, 2u);"),
    ("seed-graphics-x", "host_graphics(1u, 2u, pixel);", "host_graphics(2u, 2u, pixel);"),
    ("seed-audio-op", "u32 sample = (a ^ b) & 65535u;", "u32 sample = (a + b) & 65535u;"),
)


@dataclass(frozen=True)
class VariantResult:
    fixture_id: str
    source_path: Path
    elf_path: Path
    manifest_path: Path
    observation_path: Path
    core_result: dict
    aot_result: dict
    artifacts: dict[str, Path]


class IntegrationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, capture: bool = False) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        env=merged,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if proc.returncode != 0:
        output = proc.stdout or ""
        raise IntegrationError(f"command failed ({proc.returncode}): {' '.join(args)}\n{output}")
    return proc.stdout or ""


def _git(openrecomp: Path, *args: str) -> str:
    return _run(["git", *args], cwd=openrecomp, capture=True).strip()


def verify_openrecomp(openrecomp: Path, expected_commit: str = OPENRECOMP_PIN) -> str:
    if not (openrecomp / ".git").exists():
        raise IntegrationError(f"not an OpenRecomp git checkout: {openrecomp}")
    head = _git(openrecomp, "rev-parse", "HEAD")
    if head != expected_commit:
        raise IntegrationError(f"OpenRecomp commit mismatch: expected {expected_commit}, got {head}")
    if _git(openrecomp, "status", "--porcelain"):
        raise IntegrationError("OpenRecomp working tree must be clean")
    return head


def baseline_source(canonical: str, label: str) -> str:
    # Non-allocating ELF section: changes source/ELF provenance without changing
    # executable memory or the RV32I program's defined behavior.
    note = (
        '__asm__(".section .assurance_note,\\"\\",@progbits\\n"\n'
        f'        ".asciz \\"openrecomp-assurance:{label}\\\\0\\"\\n"\n'
        '        ".previous\\n");\n\n'
    )
    return note + canonical


def seeded_source(canonical: str, old: str, new: str) -> str:
    count = canonical.count(old)
    if count != 1:
        raise IntegrationError(f"seed anchor must occur exactly once: {old!r} (found {count})")
    return canonical.replace(old, new, 1)


class OpenRecompRV32IRunner:
    def __init__(self, assurance_root: Path, openrecomp: Path, output_root: Path, expected_commit: str = OPENRECOMP_PIN):
        self.assurance_root = assurance_root.resolve()
        self.openrecomp = openrecomp.resolve()
        self.output_root = output_root.resolve()
        self.expected_commit = expected_commit
        self.python = sys.executable
        self.host_contract = self.openrecomp / "contracts" / "host_contract.json"
        self.linker = self.openrecomp / "link.ld"
        self.include = self.openrecomp / "include"
        self.env = {"PYTHONPATH": str(self.openrecomp)}

    def _compile_elf(self, source: Path, elf: Path) -> None:
        _run(
            [
                "clang",
                "--target=riscv32-unknown-elf",
                "-march=rv32i",
                "-mabi=ilp32",
                "-O0",
                "-ffreestanding",
                "-fno-builtin",
                "-fno-stack-protector",
                "-fno-pic",
                "-nostdlib",
                f"-Wl,-T,{self.linker}",
                "-Wl,--build-id=none",
                str(source),
                "-o",
                str(elf),
            ],
            cwd=self.output_root,
        )

    def _tool(self, name: str, *args: Path | str) -> None:
        _run(
            [self.python, str(self.openrecomp / "tools" / name), *map(str, args)],
            cwd=self.openrecomp,
            env=self.env,
        )

    def _write_manifest(self, fixture_id: str, paths: dict[str, Path], manifest_path: Path) -> None:
        source = paths["elf"]
        artifact_kinds = (
            "legacy-ir",
            "ir-v1",
            "module-v1",
            "core-result",
            "aot-c",
            "native-abi-c",
            "native-module",
            "aot-result",
        )
        manifest = {
            "schema_version": "0.1",
            "run_id": f"rv32i-v0.1-real-v1:{fixture_id}",
            "source": {"kind": "rv32i-elf", "path": str(source), "sha256": _sha256(source)},
            "translator": {
                "name": "OpenRecomp",
                "commit": self.expected_commit,
                "config_sha256": _sha256(self.host_contract),
            },
            "artifacts": [
                {"kind": kind, "path": str(paths[kind]), "sha256": _sha256(paths[kind])}
                for kind in artifact_kinds
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_observation(self, fixture_id: str, result: dict, path: Path) -> None:
        observation = {
            "schema_version": "0.1",
            "run_id": f"rv32i-v0.1-real-v1:{fixture_id}",
            "fixture_id": fixture_id,
            "observables": defined_observables(result),
        }
        path.write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def run_variant(self, fixture_id: str, source_text: str) -> VariantResult:
        work = self.output_root / fixture_id
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        source = work / "fixture.c"
        elf = work / "fixture.elf"
        legacy = work / "legacy-ir.json"
        metadata = work / "elf-metadata.json"
        ir = work / "ir-v1.json"
        sidecar = work / "sidecar.json"
        module = work / "module-v1.json"
        core = work / "core-result.json"
        aot_a = work / "aot.a.c"
        aot_b = work / "aot.b.c"
        abi_a = work / "native-abi.a.c"
        abi_b = work / "native-abi.b.c"
        native = work / "module.so"
        aot_result = work / "aot-result.json"
        manifest = work / "artifact-manifest.json"
        observation = work / "observation.json"

        source.write_text(source_text, encoding="utf-8", newline="\n")
        self._compile_elf(source, elf)
        self._tool("make_ir.py", elf, legacy, metadata)
        self._tool("bridge_rv32i_ir_v1.py", legacy, self.host_contract, ir, sidecar)
        self._tool("validate_ir_v1.py", ir)
        self._tool("package_ir_v1_module.py", ir, sidecar, self.host_contract, module)
        self._tool("validate_module_v1.py", module, ir, self.host_contract)
        self._tool("run_core_api_v1.py", module, ir, self.host_contract, core)

        self._tool("aot_c_backend_v1.py", module, ir, self.host_contract, aot_a)
        self._tool("aot_c_backend_v1.py", module, ir, self.host_contract, aot_b)
        if aot_a.read_bytes() != aot_b.read_bytes():
            raise IntegrationError(f"{fixture_id}: AOT C generation is not byte-repeatable")
        self._tool("native_aot_abi_v1.py", module, ir, self.host_contract, abi_a)
        self._tool("native_aot_abi_v1.py", module, ir, self.host_contract, abi_b)
        if abi_a.read_bytes() != abi_b.read_bytes():
            raise IntegrationError(f"{fixture_id}: Native ABI generation is not byte-repeatable")

        _run(
            [
                "gcc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fPIC",
                "-fvisibility=hidden",
                "-shared",
                f"-I{self.include}",
                str(aot_a),
                str(abi_a),
                "-o",
                str(native),
            ],
            cwd=self.output_root,
        )
        self._tool("test_native_aot_abi_v1.py", native, module, ir, self.host_contract)
        self._tool("run_aot_e07_v1.py", native, self.host_contract, aot_result)

        core_json = json.loads(core.read_text(encoding="utf-8"))
        aot_json = json.loads(aot_result.read_text(encoding="utf-8"))
        require_equal(core_json, aot_json)

        paths = {
            "elf": elf,
            "legacy-ir": legacy,
            "ir-v1": ir,
            "module-v1": module,
            "core-result": core,
            "aot-c": aot_a,
            "native-abi-c": abi_a,
            "native-module": native,
            "aot-result": aot_result,
        }
        self._write_manifest(fixture_id, paths, manifest)
        self._write_observation(fixture_id, core_json, observation)
        return VariantResult(
            fixture_id=fixture_id,
            source_path=source,
            elf_path=elf,
            manifest_path=manifest,
            observation_path=observation,
            core_result=core_json,
            aot_result=aot_json,
            artifacts=paths,
        )
