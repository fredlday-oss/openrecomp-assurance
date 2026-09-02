from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from harness.compare.mips32_observables import defined_mips32_observables, require_mips32_equal

OPENRECOMP_ELF_PIN = "225a3ed250e4d700cb9aaca1213ce584f9b00fe7"
CANONICAL_HEX = Path("examples/mips32-expansion-v1/logic-shift.hex")
CANONICAL_META = Path("examples/mips32-expansion-v1/logic-shift.json")
ADAPTER_ID = "openrecomp.mips32-elf-expansion-v1"

SEEDS = (
    ("seed-addiu-immediate", 0x24081234, 0x24081235, "change addiu immediate 0x1234 to 0x1235"),
    ("seed-ori-immediate", 0x340900F0, 0x340900F1, "change ori immediate 0x00f0 to 0x00f1"),
    ("seed-shift-amount", 0x00097100, 0x000970C0, "change valid sll shift amount 4 to 3"),
    ("seed-andi-mask", 0x311700FF, 0x311700F0, "change valid andi mask 0x00ff to 0x00f0"),
    ("seed-final-arithmetic", 0x01561021, 0x01561023, "change final valid addu into subu"),
)


class MIPS32ELFAssuranceError(RuntimeError):
    pass


@dataclass(frozen=True)
class IndependentELFView:
    source_sha256: str
    entry_point: int
    text_addr: int
    text_size: int
    text_sha256: str
    function_name: str
    function_address: int
    function_size: int
    semantic_bytes: bytes
    padding_bytes: bytes
    note_bytes: bytes


@dataclass(frozen=True)
class MIPS32ELFVariantResult:
    fixture_id: str
    elf_path: Path
    manifest_path: Path
    observation_path: Path
    independent: IndependentELFView
    reference_result: dict
    core_result: dict
    aot_gcc_result: dict
    aot_clang_result: dict
    artifacts: dict[str, Path]


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
        raise MIPS32ELFAssuranceError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout or ''}"
        )
    return proc.stdout or ""


def _git(repo: Path, *args: str) -> str:
    return _run(["git", *args], cwd=repo, capture=True).strip()


def verify_openrecomp(openrecomp: Path, expected_commit: str = OPENRECOMP_ELF_PIN) -> str:
    if not (openrecomp / ".git").exists():
        raise MIPS32ELFAssuranceError(f"not an OpenRecomp git checkout: {openrecomp}")
    head = _git(openrecomp, "rev-parse", "HEAD")
    if head != expected_commit:
        raise MIPS32ELFAssuranceError(f"OpenRecomp commit mismatch: expected {expected_commit}, got {head}")
    if _git(openrecomp, "status", "--porcelain"):
        raise MIPS32ELFAssuranceError("OpenRecomp working tree must be clean")
    return head


def canonical_records(source: str) -> tuple[tuple[int, int], ...]:
    records: list[tuple[int, int]] = []
    for line_number, raw in enumerate(source.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise MIPS32ELFAssuranceError(f"line {line_number}: malformed canonical record")
        records.append((int(parts[0], 16), int(parts[1], 16)))
    if not records:
        raise MIPS32ELFAssuranceError("canonical MIPS32 source has no records")
    addresses = [address for address, _ in records]
    if addresses != list(range(addresses[0], addresses[0] + 4 * len(addresses), 4)):
        raise MIPS32ELFAssuranceError("canonical instruction records are not contiguous")
    return tuple(records)


def mutate_records(records: tuple[tuple[int, int], ...], old: int, new: int) -> tuple[tuple[int, int], ...]:
    count = sum(word == old for _, word in records)
    if count != 1:
        raise MIPS32ELFAssuranceError(f"seed word 0x{old:08x} must occur exactly once; found {count}")
    return tuple((address, new if word == old else word) for address, word in records)


def assembly_for(records: tuple[tuple[int, int], ...]) -> str:
    if records[0][0] != 0x1000:
        raise MIPS32ELFAssuranceError("bounded ELF V1 fixture must start at 0x1000")
    lines = [
        "    .set noreorder",
        "    .set nomacro",
        "    .text",
        "    .balign 4",
        "    .globl logic_shift_main",
        "    .type logic_shift_main, @function",
        "logic_shift_main:",
    ]
    lines.extend(f"    .word 0x{word:08x}" for _, word in records)
    lines.append("    .size logic_shift_main, .-logic_shift_main")
    return "\n".join(lines) + "\n"


def _cstr(blob: bytes, offset: int) -> str:
    if offset >= len(blob):
        return ""
    end = blob.find(b"\0", offset)
    if end < 0:
        end = len(blob)
    return blob[offset:end].decode("utf-8", "replace")


def inspect_elf_independently(path: Path, expected_records: tuple[tuple[int, int], ...], note: bytes) -> IndependentELFView:
    blob = path.read_bytes()
    if len(blob) < 52 or blob[:4] != b"\x7fELF":
        raise MIPS32ELFAssuranceError("independent parser: not ELF")
    if blob[4] != 1 or blob[5] != 1 or blob[6] != 1:
        raise MIPS32ELFAssuranceError("independent parser: expected ELF32 little-endian current version")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", blob, 0)
    _, etype, machine, version, entry, _, shoff, _, ehsize, _, _, shentsize, shnum, shstrndx = header
    if (etype, machine, version) != (2, 8, 1) or ehsize < 52:
        raise MIPS32ELFAssuranceError("independent parser: wrong type/machine/version")
    if not shoff or not shnum or shentsize < 40 or shstrndx >= shnum:
        raise MIPS32ELFAssuranceError("independent parser: invalid section table")
    if shoff > len(blob) or shnum > (len(blob) - shoff) // shentsize:
        raise MIPS32ELFAssuranceError("independent parser: section table out of bounds")

    raw = []
    for index in range(shnum):
        vals = struct.unpack_from("<IIIIIIIIII", blob, shoff + index * shentsize)
        raw.append({
            "index": index, "name_off": vals[0], "type": vals[1], "flags": vals[2], "addr": vals[3],
            "offset": vals[4], "size": vals[5], "link": vals[6], "info": vals[7],
            "addralign": vals[8], "entsize": vals[9],
        })
    names_section = raw[shstrndx]
    if names_section["offset"] > len(blob) or names_section["size"] > len(blob) - names_section["offset"]:
        raise MIPS32ELFAssuranceError("independent parser: shstrtab out of bounds")
    names = blob[names_section["offset"] : names_section["offset"] + names_section["size"]]
    sections = []
    for item in raw:
        section = dict(item)
        section["name"] = _cstr(names, item["name_off"])
        if item["type"] != 8 and (item["offset"] > len(blob) or item["size"] > len(blob) - item["offset"]):
            raise MIPS32ELFAssuranceError(f"independent parser: section out of bounds: {section['name']}")
        sections.append(section)

    text = next((item for item in sections if item["name"] == ".text"), None)
    note_section = next((item for item in sections if item["name"] == ".assurance-note"), None)
    if text is None or note_section is None:
        raise MIPS32ELFAssuranceError("independent parser: missing .text or .assurance-note")
    if text["type"] == 8 or not (text["flags"] & 0x2) or not (text["flags"] & 0x4):
        raise MIPS32ELFAssuranceError("independent parser: invalid executable .text")
    if note_section["flags"] & 0x2:
        raise MIPS32ELFAssuranceError("independent parser: assurance note must be non-allocatable")
    note_actual = blob[note_section["offset"] : note_section["offset"] + note_section["size"]]
    if note_actual != note:
        raise MIPS32ELFAssuranceError("independent parser: assurance note content mismatch")

    function = None
    for section in sections:
        if section["type"] != 2 or not section["entsize"] or section["link"] >= len(sections):
            continue
        strings_section = sections[section["link"]]
        strings = blob[strings_section["offset"] : strings_section["offset"] + strings_section["size"]]
        count = section["size"] // section["entsize"]
        for index in range(count):
            off = section["offset"] + index * section["entsize"]
            name_off, value, size, info, _, shndx = struct.unpack_from("<IIIBBH", blob, off)
            if (info & 0xF) == 2 and shndx == text["index"] and _cstr(strings, name_off) == "logic_shift_main":
                function = (value, size)
    if function is None:
        raise MIPS32ELFAssuranceError("independent parser: logic_shift_main STT_FUNC missing")
    function_address, function_size = function
    expected_bytes = b"".join(word.to_bytes(4, "little") for _, word in expected_records)
    if function_address != expected_records[0][0] or function_size != len(expected_bytes) or entry != function_address:
        raise MIPS32ELFAssuranceError("independent parser: function/entry layout mismatch")
    if text["addr"] != function_address:
        raise MIPS32ELFAssuranceError("independent parser: semantic function must begin at .text start")
    text_bytes = blob[text["offset"] : text["offset"] + text["size"]]
    semantic = text_bytes[:function_size]
    padding = text_bytes[function_size:]
    if semantic != expected_bytes:
        raise MIPS32ELFAssuranceError("independent parser: linked semantic .text differs from intended records")
    if len(padding) >= 16 or any(padding):
        raise MIPS32ELFAssuranceError("independent parser: non-zero/excessive linker padding")

    return IndependentELFView(
        source_sha256=hashlib.sha256(blob).hexdigest(),
        entry_point=entry,
        text_addr=text["addr"],
        text_size=text["size"],
        text_sha256=hashlib.sha256(text_bytes).hexdigest(),
        function_name="logic_shift_main",
        function_address=function_address,
        function_size=function_size,
        semantic_bytes=semantic,
        padding_bytes=padding,
        note_bytes=note_actual,
    )


class OpenRecompMIPS32ELFRunner:
    def __init__(self, assurance_root: Path, openrecomp: Path, output_root: Path, expected_commit: str = OPENRECOMP_ELF_PIN):
        self.assurance_root = assurance_root.resolve()
        self.openrecomp = openrecomp.resolve()
        self.output_root = output_root.resolve()
        self.expected_commit = expected_commit
        self.python = sys.executable
        self.host_contract = self.openrecomp / "contracts" / "host_contract.json"
        self.runtime_meta = self.openrecomp / CANONICAL_META
        self.canonical_hex = self.openrecomp / CANONICAL_HEX
        self.include = self.openrecomp / "include"
        self.env = {"PYTHONPATH": str(self.openrecomp)}

    def _tool(self, name: str, *args: Path | str) -> None:
        _run([self.python, str(self.openrecomp / "tools" / name), *map(str, args)], cwd=self.openrecomp, env=self.env)

    def _compile_native(self, compiler: str, aot_c: Path, abi_c: Path, out: Path) -> None:
        _run([
            compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-fvisibility=hidden",
            "-shared", f"-I{self.include}", str(aot_c), str(abi_c), "-o", str(out),
        ], cwd=self.output_root)

    def _build_elf(self, work: Path, records: tuple[tuple[int, int], ...], note: bytes) -> tuple[Path, IndependentELFView]:
        source = work / "fixture.S"
        obj = work / "fixture.o"
        linked = work / "fixture.linked.elf"
        note_path = work / "assurance-note.bin"
        final = work / "fixture.elf"
        source.write_text(assembly_for(records), encoding="utf-8", newline="\n")
        note_path.write_bytes(note)
        _run(["mipsel-linux-gnu-as", "-32", str(source), "-o", str(obj)], cwd=work)
        _run([
            "mipsel-linux-gnu-ld", "-m", "elf32ltsmip", "-Ttext", "0x1000", "-e", "logic_shift_main",
            "--build-id=none", str(obj), "-o", str(linked),
        ], cwd=work)
        _run([
            "mipsel-linux-gnu-objcopy", "--add-section", f".assurance-note={note_path}",
            "--set-section-flags", ".assurance-note=readonly", str(linked), str(final),
        ], cwd=work)
        return final, inspect_elf_independently(final, records, note)

    def _write_manifest(self, fixture_id: str, source: Path, artifacts: dict[str, Path], path: Path) -> None:
        kinds = (
            "fixture-assembly", "fixture-meta", "elf-metadata", "frontend-report", "ir-v1", "sidecar", "module-v1",
            "reference-result", "core-result", "aot-c", "native-abi-c", "native-module-gcc", "native-module-clang",
            "aot-result-gcc", "aot-result-clang",
        )
        payload = {
            "schema_version": "0.1",
            "run_id": f"mips32-elf-real-v1:{fixture_id}",
            "source": {"kind": "mips32-elf", "path": str(source), "sha256": _sha256(source)},
            "translator": {"name": "OpenRecomp", "commit": self.expected_commit, "config_sha256": _sha256(self.host_contract)},
            "artifacts": [
                {"kind": kind, "path": str(artifacts[kind]), "sha256": _sha256(artifacts[kind])}
                for kind in kinds
            ],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_observation(self, fixture_id: str, reference: dict, path: Path) -> None:
        payload = {
            "schema_version": "0.1",
            "run_id": f"mips32-elf-real-v1:{fixture_id}",
            "fixture_id": fixture_id,
            "observables": defined_mips32_observables(reference),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def run_variant(self, fixture_id: str, records: tuple[tuple[int, int], ...], note_text: str) -> MIPS32ELFVariantResult:
        work = self.output_root / fixture_id
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        note = note_text.encode("utf-8")
        elf, independent = self._build_elf(work, records, note)

        metadata = work / "fixture.json"
        shutil.copyfile(self.runtime_meta, metadata)
        ir_a, ir_b = work / "ir.a.json", work / "ir.b.json"
        sidecar_a, sidecar_b = work / "sidecar.a.json", work / "sidecar.b.json"
        frontend_a, frontend_b = work / "frontend.a.json", work / "frontend.b.json"
        elf_meta_a, elf_meta_b = work / "elf.a.json", work / "elf.b.json"
        reference = work / "reference.json"
        module_a, module_b = work / "module.a.json", work / "module.b.json"
        core = work / "core.json"
        aot_a, aot_b = work / "aot.a.c", work / "aot.b.c"
        abi_a, abi_b = work / "native-abi.a.c", work / "native-abi.b.c"
        native_gcc, native_clang = work / "module.gcc.so", work / "module.clang.so"
        aot_gcc, aot_clang = work / "aot.gcc.json", work / "aot.clang.json"
        manifest, observation = work / "artifact-manifest.json", work / "observation.json"

        for ir, sidecar, frontend, elf_meta in (
            (ir_a, sidecar_a, frontend_a, elf_meta_a),
            (ir_b, sidecar_b, frontend_b, elf_meta_b),
        ):
            self._tool("mips32_elf_frontend_v1.py", elf, metadata, self.host_contract, ir, sidecar, frontend, elf_meta)
        for first, second, label in (
            (ir_a, ir_b, "IR V1"), (sidecar_a, sidecar_b, "sidecar"),
            (frontend_a, frontend_b, "frontend report"), (elf_meta_a, elf_meta_b, "ELF metadata"),
        ):
            if first.read_bytes() != second.read_bytes():
                raise MIPS32ELFAssuranceError(f"{fixture_id}: {label} generation is not byte-repeatable")
        self._tool("validate_ir_v1.py", ir_a)
        self._tool("run_mips32_elf_reference_v1.py", elf, metadata, reference)
        self._tool("package_ir_v1_module.py", ir_a, sidecar_a, self.host_contract, module_a)
        self._tool("package_ir_v1_module.py", ir_a, sidecar_a, self.host_contract, module_b)
        if module_a.read_bytes() != module_b.read_bytes():
            raise MIPS32ELFAssuranceError(f"{fixture_id}: Module generation is not byte-repeatable")
        self._tool("validate_module_v1.py", module_a, ir_a, self.host_contract)
        self._tool("run_mips32_expansion_core_v1.py", module_a, ir_a, self.host_contract, metadata, core)
        self._tool("aot_c_backend_v1.py", module_a, ir_a, self.host_contract, aot_a)
        self._tool("aot_c_backend_v1.py", module_a, ir_a, self.host_contract, aot_b)
        if aot_a.read_bytes() != aot_b.read_bytes():
            raise MIPS32ELFAssuranceError(f"{fixture_id}: AOT C generation is not byte-repeatable")
        self._tool("native_aot_abi_v1.py", module_a, ir_a, self.host_contract, abi_a)
        self._tool("native_aot_abi_v1.py", module_a, ir_a, self.host_contract, abi_b)
        if abi_a.read_bytes() != abi_b.read_bytes():
            raise MIPS32ELFAssuranceError(f"{fixture_id}: Native ABI generation is not byte-repeatable")
        self._compile_native("gcc", aot_a, abi_a, native_gcc)
        self._compile_native("clang", aot_a, abi_a, native_clang)
        self._tool("test_native_aot_abi_v1.py", native_gcc, module_a, ir_a, self.host_contract)
        self._tool("test_native_aot_abi_v1.py", native_clang, module_a, ir_a, self.host_contract)
        self._tool("run_aot_mips32_expansion_v1.py", native_gcc, ir_a, metadata, aot_gcc)
        self._tool("run_aot_mips32_expansion_v1.py", native_clang, ir_a, metadata, aot_clang)

        ir_json = json.loads(ir_a.read_text(encoding="utf-8"))
        frontend_json = json.loads(frontend_a.read_text(encoding="utf-8"))
        elf_meta_json = json.loads(elf_meta_a.read_text(encoding="utf-8"))
        module_json = json.loads(module_a.read_text(encoding="utf-8"))
        reference_json = json.loads(reference.read_text(encoding="utf-8"))
        core_json = json.loads(core.read_text(encoding="utf-8"))
        aot_gcc_json = json.loads(aot_gcc.read_text(encoding="utf-8"))
        aot_clang_json = json.loads(aot_clang.read_text(encoding="utf-8"))

        if ir_json["source"]["architecture"] != "mips32-le" or ir_json["source"]["adapter"] != ADAPTER_ID:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: normalized ELF source identity mismatch")
        if not ir_json["module_id"].startswith("openrecomp.mips32.elf.expansion-v1."):
            raise MIPS32ELFAssuranceError(f"{fixture_id}: ELF module namespace mismatch")
        if ir_json["required_host_symbols"] != []:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: unexpected host symbols")
        if elf_meta_json["machine"] != 8 or elf_meta_json["entry_point"] != independent.entry_point:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: OpenRecomp ELF identity disagrees with independent parser")
        if elf_meta_json["input_sha256"] != independent.source_sha256:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: OpenRecomp ELF hash disagrees with independent parser")
        if elf_meta_json["text"]["sha256"] != independent.text_sha256:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: OpenRecomp .text hash disagrees with independent parser")
        if frontend_json["elf_text_sha256"] != independent.text_sha256:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: frontend report .text hash mismatch")

        source_hashes = {
            independent.source_sha256,
            ir_json["source"]["input_sha256"],
            frontend_json["source_input_sha256"],
            module_json["ir"]["source_input_sha256"],
            module_json["provenance"]["source_input_sha256"],
            reference_json["source_input_sha256"], core_json["source_input_sha256"],
            aot_gcc_json["source_input_sha256"], aot_clang_json["source_input_sha256"],
        }
        if len(source_hashes) != 1:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: ELF provenance diverged across paths")
        if frontend_json["delay_slots_lowered"] != reference_json["delay_slots_executed"]:
            raise MIPS32ELFAssuranceError(f"{fixture_id}: delay-slot evidence mismatch")

        require_mips32_equal(reference_json, core_json)
        require_mips32_equal(reference_json, aot_gcc_json)
        require_mips32_equal(reference_json, aot_clang_json)
        if not (core_json["operations"] == aot_gcc_json["operations"] == aot_clang_json["operations"]):
            raise MIPS32ELFAssuranceError(f"{fixture_id}: Core/GCC/Clang operation counts disagree")

        artifacts = {
            "fixture-assembly": work / "fixture.S", "fixture-meta": metadata, "elf-metadata": elf_meta_a,
            "frontend-report": frontend_a, "ir-v1": ir_a, "sidecar": sidecar_a, "module-v1": module_a,
            "reference-result": reference, "core-result": core, "aot-c": aot_a, "native-abi-c": abi_a,
            "native-module-gcc": native_gcc, "native-module-clang": native_clang,
            "aot-result-gcc": aot_gcc, "aot-result-clang": aot_clang,
        }
        self._write_manifest(fixture_id, elf, artifacts, manifest)
        self._write_observation(fixture_id, reference_json, observation)
        return MIPS32ELFVariantResult(
            fixture_id=fixture_id, elf_path=elf, manifest_path=manifest, observation_path=observation,
            independent=independent, reference_result=reference_json, core_result=core_json,
            aot_gcc_result=aot_gcc_json, aot_clang_result=aot_clang_json,
            artifacts={**artifacts, "elf": elf},
        )
