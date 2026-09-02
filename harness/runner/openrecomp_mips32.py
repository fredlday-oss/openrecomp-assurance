from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from harness.compare.mips32_observables import defined_mips32_observables, require_mips32_equal

OPENRECOMP_PIN = "53d0bce144356f2b4ee7120c5f8c13cb82c4bf90"
CANONICAL_HEX = Path("examples/mips32-expansion-v1/logic-shift.hex")
CANONICAL_META = Path("examples/mips32-expansion-v1/logic-shift.json")

SEEDS = (
    (
        "seed-addiu-immediate",
        "00001000 24081234",
        "00001000 24081235",
        "change the first addiu immediate from 0x1234 to 0x1235",
    ),
    (
        "seed-ori-immediate",
        "00001004 340900f0",
        "00001004 340900f1",
        "change the OR-immediate source value from 0x00f0 to 0x00f1",
    ),
    (
        "seed-shift-amount",
        "00001018 00097100",
        "00001018 000970c0",
        "change a valid sll shift amount from 4 to 3",
    ),
    (
        "seed-andi-mask",
        "0000103c 311700ff",
        "0000103c 311700fe",
        "change a valid andi mask from 0x00ff to 0x00fe",
    ),
    (
        "seed-final-arithmetic",
        "0000104c 01561021",
        "0000104c 01561023",
        "change the final valid addu into subu",
    ),
)


@dataclass(frozen=True)
class MIPS32VariantResult:
    fixture_id: str
    source_path: Path
    metadata_path: Path
    manifest_path: Path
    observation_path: Path
    reference_result: dict
    core_result: dict
    aot_gcc_result: dict
    aot_clang_result: dict
    artifacts: dict[str, Path]


class MIPS32IntegrationError(RuntimeError):
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
        raise MIPS32IntegrationError(f"command failed ({proc.returncode}): {' '.join(args)}\n{output}")
    return proc.stdout or ""


def _git(openrecomp: Path, *args: str) -> str:
    return _run(["git", *args], cwd=openrecomp, capture=True).strip()


def verify_openrecomp(openrecomp: Path, expected_commit: str = OPENRECOMP_PIN) -> str:
    if not (openrecomp / ".git").exists():
        raise MIPS32IntegrationError(f"not an OpenRecomp git checkout: {openrecomp}")
    head = _git(openrecomp, "rev-parse", "HEAD")
    if head != expected_commit:
        raise MIPS32IntegrationError(f"OpenRecomp commit mismatch: expected {expected_commit}, got {head}")
    if _git(openrecomp, "status", "--porcelain"):
        raise MIPS32IntegrationError("OpenRecomp working tree must be clean")
    return head


def baseline_hex(canonical: str, label: str) -> str:
    # MIPS32 expansion fixtures ignore comment-only lines. This deliberately
    # changes source provenance while preserving the decoded instruction image.
    return f"# openrecomp-assurance equivalent-baseline:{label}\n{canonical}"


def seeded_hex(canonical: str, old: str, new: str) -> str:
    count = canonical.count(old)
    if count != 1:
        raise MIPS32IntegrationError(f"seed anchor must occur exactly once: {old!r} (found {count})")
    return canonical.replace(old, new, 1)


def decoded_records(source_text: str) -> tuple[tuple[int, int], ...]:
    records: list[tuple[int, int]] = []
    for line_number, raw in enumerate(source_text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise MIPS32IntegrationError(f"line {line_number}: malformed MIPS32 record")
        try:
            address = int(parts[0], 16)
            word = int(parts[1], 16)
        except ValueError as exc:
            raise MIPS32IntegrationError(f"line {line_number}: invalid MIPS32 hexadecimal record") from exc
        records.append((address, word))
    if not records:
        raise MIPS32IntegrationError("MIPS32 source has no decoded records")
    return tuple(records)


class OpenRecompMIPS32Runner:
    def __init__(self, assurance_root: Path, openrecomp: Path, output_root: Path, expected_commit: str = OPENRECOMP_PIN):
        self.assurance_root = assurance_root.resolve()
        self.openrecomp = openrecomp.resolve()
        self.output_root = output_root.resolve()
        self.expected_commit = expected_commit
        self.python = sys.executable
        self.host_contract = self.openrecomp / "contracts" / "host_contract.json"
        self.include = self.openrecomp / "include"
        self.canonical_hex = self.openrecomp / CANONICAL_HEX
        self.canonical_meta = self.openrecomp / CANONICAL_META
        self.env = {"PYTHONPATH": str(self.openrecomp)}

    def _tool(self, name: str, *args: Path | str) -> None:
        _run(
            [self.python, str(self.openrecomp / "tools" / name), *map(str, args)],
            cwd=self.openrecomp,
            env=self.env,
        )

    def _compile_native(self, compiler: str, aot_c: Path, abi_c: Path, out: Path) -> None:
        _run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fPIC",
                "-fvisibility=hidden",
                "-shared",
                f"-I{self.include}",
                str(aot_c),
                str(abi_c),
                "-o",
                str(out),
            ],
            cwd=self.output_root,
        )

    def _write_manifest(self, fixture_id: str, paths: dict[str, Path], manifest_path: Path) -> None:
        artifact_kinds = (
            "fixture-meta",
            "frontend-report",
            "ir-v1",
            "sidecar",
            "module-v1",
            "reference-result",
            "core-result",
            "aot-c",
            "native-abi-c",
            "native-module-gcc",
            "native-module-clang",
            "aot-result-gcc",
            "aot-result-clang",
        )
        manifest = {
            "schema_version": "0.1",
            "run_id": f"mips32-real-v1:{fixture_id}",
            "source": {"kind": "mips32-hex", "path": str(paths["source"]), "sha256": _sha256(paths["source"])},
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

    def _write_observation(self, fixture_id: str, reference_result: dict, path: Path) -> None:
        observation = {
            "schema_version": "0.1",
            "run_id": f"mips32-real-v1:{fixture_id}",
            "fixture_id": fixture_id,
            "observables": defined_mips32_observables(reference_result),
        }
        path.write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def run_variant(self, fixture_id: str, source_text: str) -> MIPS32VariantResult:
        work = self.output_root / fixture_id
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)

        source = work / "fixture.hex"
        metadata = work / "fixture.json"
        ir_a = work / "ir.a.json"
        ir_b = work / "ir.b.json"
        sidecar_a = work / "sidecar.a.json"
        sidecar_b = work / "sidecar.b.json"
        frontend_a = work / "frontend.a.json"
        frontend_b = work / "frontend.b.json"
        reference = work / "reference.json"
        module_a = work / "module.a.json"
        module_b = work / "module.b.json"
        core = work / "core.json"
        aot_a = work / "aot.a.c"
        aot_b = work / "aot.b.c"
        abi_a = work / "native-abi.a.c"
        abi_b = work / "native-abi.b.c"
        native_gcc = work / "module.gcc.so"
        native_clang = work / "module.clang.so"
        aot_gcc = work / "aot.gcc.json"
        aot_clang = work / "aot.clang.json"
        manifest = work / "artifact-manifest.json"
        observation = work / "observation.json"

        source.write_text(source_text, encoding="utf-8", newline="\n")
        shutil.copyfile(self.canonical_meta, metadata)

        self._tool("mips32_expansion_frontend_v1.py", source, metadata, self.host_contract, ir_a, sidecar_a, frontend_a)
        self._tool("mips32_expansion_frontend_v1.py", source, metadata, self.host_contract, ir_b, sidecar_b, frontend_b)
        for first, second, label in (
            (ir_a, ir_b, "IR V1"),
            (sidecar_a, sidecar_b, "sidecar"),
            (frontend_a, frontend_b, "frontend report"),
        ):
            if first.read_bytes() != second.read_bytes():
                raise MIPS32IntegrationError(f"{fixture_id}: {label} generation is not byte-repeatable")
        self._tool("validate_ir_v1.py", ir_a)

        self._tool("run_mips32_expansion_reference.py", source, metadata, reference)
        self._tool("package_ir_v1_module.py", ir_a, sidecar_a, self.host_contract, module_a)
        self._tool("package_ir_v1_module.py", ir_a, sidecar_a, self.host_contract, module_b)
        if module_a.read_bytes() != module_b.read_bytes():
            raise MIPS32IntegrationError(f"{fixture_id}: Module Image generation is not byte-repeatable")
        self._tool("validate_module_v1.py", module_a, ir_a, self.host_contract)
        self._tool("run_mips32_expansion_core_v1.py", module_a, ir_a, self.host_contract, metadata, core)

        self._tool("aot_c_backend_v1.py", module_a, ir_a, self.host_contract, aot_a)
        self._tool("aot_c_backend_v1.py", module_a, ir_a, self.host_contract, aot_b)
        if aot_a.read_bytes() != aot_b.read_bytes():
            raise MIPS32IntegrationError(f"{fixture_id}: AOT C generation is not byte-repeatable")

        self._tool("native_aot_abi_v1.py", module_a, ir_a, self.host_contract, abi_a)
        self._tool("native_aot_abi_v1.py", module_a, ir_a, self.host_contract, abi_b)
        if abi_a.read_bytes() != abi_b.read_bytes():
            raise MIPS32IntegrationError(f"{fixture_id}: Native ABI generation is not byte-repeatable")

        self._compile_native("gcc", aot_a, abi_a, native_gcc)
        self._compile_native("clang", aot_a, abi_a, native_clang)
        self._tool("test_native_aot_abi_v1.py", native_gcc, module_a, ir_a, self.host_contract)
        self._tool("test_native_aot_abi_v1.py", native_clang, module_a, ir_a, self.host_contract)
        self._tool("run_aot_mips32_expansion_v1.py", native_gcc, ir_a, metadata, aot_gcc)
        self._tool("run_aot_mips32_expansion_v1.py", native_clang, ir_a, metadata, aot_clang)

        reference_json = json.loads(reference.read_text(encoding="utf-8"))
        core_json = json.loads(core.read_text(encoding="utf-8"))
        aot_gcc_json = json.loads(aot_gcc.read_text(encoding="utf-8"))
        aot_clang_json = json.loads(aot_clang.read_text(encoding="utf-8"))
        ir_json = json.loads(ir_a.read_text(encoding="utf-8"))
        frontend_json = json.loads(frontend_a.read_text(encoding="utf-8"))

        if ir_json["source"]["architecture"] != "mips32-le":
            raise MIPS32IntegrationError(f"{fixture_id}: expected mips32-le normalized source")
        if ir_json["source"]["adapter"] != "openrecomp.mips32-expansion-v1":
            raise MIPS32IntegrationError(f"{fixture_id}: unexpected MIPS32 adapter identity")
        if ir_json["required_host_symbols"] != []:
            raise MIPS32IntegrationError(f"{fixture_id}: MIPS32 assurance variant unexpectedly requires host symbols")

        expected_slots = {f"gpr:r{i}" for i in range(1, 32)} | {"special:hi", "special:lo"}
        if {item["id"] for item in ir_json["state_slots"]} != expected_slots:
            raise MIPS32IntegrationError(f"{fixture_id}: normalized MIPS32 state slots are incomplete")

        source_hash = _sha256(source)
        provenance_hashes = {
            source_hash,
            ir_json["source"]["input_sha256"],
            frontend_json["source_input_sha256"],
            reference_json["source_input_sha256"],
            core_json["source_input_sha256"],
            aot_gcc_json["source_input_sha256"],
            aot_clang_json["source_input_sha256"],
        }
        if len(provenance_hashes) != 1:
            raise MIPS32IntegrationError(f"{fixture_id}: source provenance diverged across MIPS32 paths")

        if frontend_json["delay_slots_lowered"] != reference_json["delay_slots_executed"]:
            raise MIPS32IntegrationError(f"{fixture_id}: frontend/reference delay-slot count mismatch")

        require_mips32_equal(reference_json, core_json)
        require_mips32_equal(reference_json, aot_gcc_json)
        require_mips32_equal(reference_json, aot_clang_json)
        if not (core_json["operations"] == aot_gcc_json["operations"] == aot_clang_json["operations"]):
            raise MIPS32IntegrationError(f"{fixture_id}: Core/GCC/Clang operation counts disagree")
        for name, result in (("core", core_json), ("aot-gcc", aot_gcc_json), ("aot-clang", aot_clang_json)):
            if result["function_return"] is not None or result["host"] != {}:
                raise MIPS32IntegrationError(f"{fixture_id}: {name} has unexpected host/function side effects")

        paths = {
            "source": source,
            "fixture-meta": metadata,
            "frontend-report": frontend_a,
            "ir-v1": ir_a,
            "sidecar": sidecar_a,
            "module-v1": module_a,
            "reference-result": reference,
            "core-result": core,
            "aot-c": aot_a,
            "native-abi-c": abi_a,
            "native-module-gcc": native_gcc,
            "native-module-clang": native_clang,
            "aot-result-gcc": aot_gcc,
            "aot-result-clang": aot_clang,
        }
        self._write_manifest(fixture_id, paths, manifest)
        self._write_observation(fixture_id, reference_json, observation)

        return MIPS32VariantResult(
            fixture_id=fixture_id,
            source_path=source,
            metadata_path=metadata,
            manifest_path=manifest,
            observation_path=observation,
            reference_result=reference_json,
            core_result=core_json,
            aot_gcc_result=aot_gcc_json,
            aot_clang_result=aot_clang_json,
            artifacts=paths,
        )
