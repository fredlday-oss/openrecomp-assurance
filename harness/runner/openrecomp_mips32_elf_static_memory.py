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

from harness.compare.mips32_observables import require_mips32_equal

OPENRECOMP_STATIC_MEMORY_PIN = "832ca4133ce9ef71b3d5ada45bad643a65a8fa6c"
ADAPTER_ID = "openrecomp.mips32-elf-static-memory-v1"
BASE_RODATA_WORD = 0x11223344
BASE_DATA_WORD = 0x01020304
BASE_BSS_ADDR = 0x3010
OBSERVE_ADDR = 0x3000
OBSERVE_SIZE = 0x24

BASE_RECORDS = (
    0x24082000,
    0x8D090000,
    0x240A3000,
    0x8D4B0000,
    0x012B6021,
    0xAD4C0000,
    0x240D3010,
    0x8DAE0000,
    0x018E1021,
    0xADA20000,
    0x03E00008,
    0x00000000,
)


class MIPS32ELFStaticMemoryAssuranceError(RuntimeError):
    pass


@dataclass(frozen=True)
class StaticVariantSpec:
    fixture_id: str
    records: tuple[int, ...] = BASE_RECORDS
    rodata_word: int = BASE_RODATA_WORD
    data_word: int = BASE_DATA_WORD
    bss_addr: int = BASE_BSS_ADDR
    note_text: str = ""
    description: str = ""


SEEDS = (
    StaticVariantSpec(
        "seed-rodata-word", rodata_word=0x11223345,
        description="change the file-backed .rodata word 0x11223344 to 0x11223345",
    ),
    StaticVariantSpec(
        "seed-data-word", data_word=0x01020305,
        description="change the file-backed .data word 0x01020304 to 0x01020305",
    ),
    StaticVariantSpec(
        "seed-arithmetic-op",
        records=tuple(0x012B6023 if word == 0x012B6021 else word for word in BASE_RECORDS),
        description="change the valid addu combining .rodata/.data into subu",
    ),
    StaticVariantSpec(
        "seed-bss-read-from-data",
        records=tuple(0x8DAEFFF0 if word == 0x8DAE0000 else word for word in BASE_RECORDS),
        description="change the BSS load to read the updated .data word at -16 bytes",
    ),
    StaticVariantSpec(
        "seed-bss-layout-move",
        records=tuple(0x240D3020 if word == 0x240D3010 else word for word in BASE_RECORDS),
        bss_addr=0x3020,
        description="move .bss from 0x3010 to 0x3020 and update the guest address instruction",
    ),
)


@dataclass(frozen=True)
class SectionView:
    name: str
    address: int
    size: int
    data: bytes
    zero_fill: bool
    writable: bool
    executable: bool

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(frozen=True)
class IndependentStaticELFView:
    source_sha256: str
    entry_point: int
    semantic_text: bytes
    text_padding: bytes
    note_bytes: bytes
    sections: dict[str, SectionView]


@dataclass(frozen=True)
class StaticVariantResult:
    spec: StaticVariantSpec
    elf_path: Path
    independent: IndependentStaticELFView
    reference_result: dict
    core_result: dict
    aot_gcc_result: dict
    aot_clang_result: dict
    artifacts: dict[str, Path]
    manifest_path: Path
    observation_path: Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, capture: bool = False) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        args, cwd=str(cwd), env=merged, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if proc.returncode != 0:
        raise MIPS32ELFStaticMemoryAssuranceError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout or ''}"
        )
    return proc.stdout or ""


def _git(repo: Path, *args: str) -> str:
    return _run(["git", *args], cwd=repo, capture=True).strip()


def verify_openrecomp(openrecomp: Path, expected_commit: str = OPENRECOMP_STATIC_MEMORY_PIN) -> str:
    if not (openrecomp / ".git").exists():
        raise MIPS32ELFStaticMemoryAssuranceError(f"not an OpenRecomp git checkout: {openrecomp}")
    head = _git(openrecomp, "rev-parse", "HEAD")
    if head != expected_commit:
        raise MIPS32ELFStaticMemoryAssuranceError(
            f"OpenRecomp commit mismatch: expected {expected_commit}, got {head}"
        )
    if _git(openrecomp, "status", "--porcelain"):
        raise MIPS32ELFStaticMemoryAssuranceError("OpenRecomp working tree must be clean")
    return head


def _cstr(blob: bytes, offset: int) -> str:
    if offset < 0 or offset >= len(blob):
        return ""
    end = blob.find(b"\0", offset)
    if end < 0:
        end = len(blob)
    return blob[offset:end].decode("utf-8", "replace")


def _section_bytes(blob: bytes, section: dict) -> bytes:
    if section["type"] == 8:
        return bytes(section["size"])
    offset, size = section["offset"], section["size"]
    if offset > len(blob) or size > len(blob) - offset:
        raise MIPS32ELFStaticMemoryAssuranceError(
            f"independent parser: section out of bounds: {section['name']}"
        )
    return blob[offset:offset + size]


def assembly_for(spec: StaticVariantSpec) -> str:
    lines = [
        ".set noreorder",
        ".set noat",
        '.section .text,"ax",@progbits',
        ".globl static_memory_main",
        ".type static_memory_main, @function",
        "static_memory_main:",
    ]
    lines.extend(f"    .word 0x{word:08x}" for word in spec.records)
    lines.extend([
        ".size static_memory_main, .-static_memory_main",
        '',
        '.section .openrecomp_rodata,"a",@progbits',
        '.align 2',
        f"    .word 0x{spec.rodata_word:08x}",
        '',
        '.section .openrecomp_data,"aw",@progbits',
        '.align 2',
        f"    .word 0x{spec.data_word:08x}",
        '',
        '.section .openrecomp_bss,"aw",@nobits',
        '.align 2',
        '    .space 4',
    ])
    return "\n".join(lines) + "\n"


def linker_script_for(spec: StaticVariantSpec) -> str:
    return f"""ENTRY(static_memory_main)
SECTIONS
{{
  . = 0x00001000;
  .text : ALIGN(4) {{ *(.text*) }}
  . = 0x00002000;
  .rodata : ALIGN(4) {{ *(.openrecomp_rodata) }}
  . = 0x00003000;
  .data : ALIGN(4) {{ *(.openrecomp_data) }}
  . = 0x{spec.bss_addr:08x};
  .bss (NOLOAD) : ALIGN(4) {{ *(.openrecomp_bss) }}
  /DISCARD/ : {{ *(.MIPS.abiflags) *(.reginfo) *(.gnu.attributes) *(.pdr) }}
}}
"""


def inspect_static_elf_independently(path: Path, spec: StaticVariantSpec, note: bytes) -> IndependentStaticELFView:
    blob = path.read_bytes()
    if len(blob) < 52 or blob[:4] != b"\x7fELF" or blob[4:7] != bytes((1, 1, 1)):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: expected current little-endian ELF32")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", blob, 0)
    _, etype, machine, version, entry, _, shoff, _, ehsize, _, _, shentsize, shnum, shstrndx = header
    if (etype, machine, version) != (2, 8, 1) or ehsize < 52:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: wrong type/machine/version")
    if not shoff or not shnum or shentsize < 40 or shstrndx >= shnum:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: invalid section table")
    if shoff > len(blob) or shnum > (len(blob) - shoff) // shentsize:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: section table out of bounds")

    raw = []
    for index in range(shnum):
        vals = struct.unpack_from("<IIIIIIIIII", blob, shoff + index * shentsize)
        raw.append({
            "index": index, "name_off": vals[0], "type": vals[1], "flags": vals[2], "addr": vals[3],
            "offset": vals[4], "size": vals[5], "link": vals[6], "info": vals[7],
            "addralign": vals[8], "entsize": vals[9],
        })
    name_sec = raw[shstrndx]
    if name_sec["offset"] > len(blob) or name_sec["size"] > len(blob) - name_sec["offset"]:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: shstrtab out of bounds")
    names = blob[name_sec["offset"]:name_sec["offset"] + name_sec["size"]]
    sections = []
    for item in raw:
        section = dict(item)
        section["name"] = _cstr(names, item["name_off"])
        if section["type"] in {4, 9} and section["size"]:
            raise MIPS32ELFStaticMemoryAssuranceError("independent parser: relocation section present")
        _section_bytes(blob, section)
        sections.append(section)
    by_name = {item["name"]: item for item in sections}
    required = {".text", ".rodata", ".data", ".bss", ".assurance-note"}
    if not required.issubset(by_name):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: required section missing")

    text = by_name[".text"]
    rodata = by_name[".rodata"]
    data = by_name[".data"]
    bss = by_name[".bss"]
    note_sec = by_name[".assurance-note"]
    if text["type"] == 8 or (text["flags"] & 0x6) != 0x6:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: invalid executable .text")
    if rodata["type"] == 8 or (rodata["flags"] & 0x2) != 0x2 or rodata["flags"] & (0x1 | 0x4):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: invalid .rodata attributes")
    if data["type"] == 8 or (data["flags"] & 0x3) != 0x3 or data["flags"] & 0x4:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: invalid .data attributes")
    if bss["type"] != 8 or (bss["flags"] & 0x3) != 0x3 or bss["flags"] & 0x4:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: invalid .bss attributes")
    if note_sec["flags"] & 0x2:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: assurance note must be non-allocatable")

    note_actual = _section_bytes(blob, note_sec)
    if note_actual != note:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: assurance note mismatch")

    function = None
    for section in sections:
        if section["type"] != 2 or not section["entsize"] or section["link"] >= len(sections):
            continue
        strings_sec = sections[section["link"]]
        strings = _section_bytes(blob, strings_sec)
        for index in range(section["size"] // section["entsize"]):
            off = section["offset"] + index * section["entsize"]
            name_off, value, size, info, _, shndx = struct.unpack_from("<IIIBBH", blob, off)
            if (info & 0xF) == 2 and shndx == text["index"] and _cstr(strings, name_off) == "static_memory_main":
                function = (value, size)
    expected_text = b"".join(word.to_bytes(4, "little") for word in spec.records)
    if function is None or function != (0x1000, len(expected_text)) or entry != 0x1000 or text["addr"] != 0x1000:
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: entry/function layout mismatch")
    text_bytes = _section_bytes(blob, text)
    semantic = text_bytes[:len(expected_text)]
    padding = text_bytes[len(expected_text):]
    if semantic != expected_text or len(padding) >= 16 or any(padding):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: .text semantics/padding mismatch")

    ro_bytes = _section_bytes(blob, rodata)
    data_bytes = _section_bytes(blob, data)
    bss_bytes = _section_bytes(blob, bss)
    if (rodata["addr"], rodata["size"], ro_bytes) != (0x2000, 4, spec.rodata_word.to_bytes(4, "little")):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: .rodata layout/content mismatch")
    expected_data = spec.data_word.to_bytes(4, "little") + bytes(12)
    if (data["addr"], data["size"], data_bytes) != (0x3000, 16, expected_data):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: .data layout/content mismatch")
    if (bss["addr"], bss["size"], bss_bytes) != (spec.bss_addr, 4, bytes(4)):
        raise MIPS32ELFStaticMemoryAssuranceError("independent parser: .bss layout/zero-fill mismatch")
    ranges = [(0x2000, 0x2004, ".rodata"), (0x3000, 0x3010, ".data"), (spec.bss_addr, spec.bss_addr + 4, ".bss")]
    for i, (a0, a1, an) in enumerate(ranges):
        for b0, b1, bn in ranges[i + 1:]:
            if max(a0, b0) < min(a1, b1):
                raise MIPS32ELFStaticMemoryAssuranceError(f"independent parser: overlap {an}/{bn}")

    static = {
        ".rodata": SectionView(".rodata", rodata["addr"], rodata["size"], ro_bytes, False, False, False),
        ".data": SectionView(".data", data["addr"], data["size"], data_bytes, False, True, False),
        ".bss": SectionView(".bss", bss["addr"], bss["size"], bss_bytes, True, True, False),
    }
    return IndependentStaticELFView(
        source_sha256=hashlib.sha256(blob).hexdigest(), entry_point=entry,
        semantic_text=semantic, text_padding=padding, note_bytes=note_actual, sections=static,
    )


class OpenRecompMIPS32ELFStaticMemoryRunner:
    def __init__(self, assurance_root: Path, openrecomp: Path, output_root: Path, expected_commit: str):
        self.assurance_root = assurance_root.resolve()
        self.openrecomp = openrecomp.resolve()
        self.output_root = output_root.resolve()
        self.expected_commit = expected_commit
        self.python = sys.executable
        self.host_contract = self.openrecomp / "contracts" / "host_contract.json"
        self.include = self.openrecomp / "include"
        self.env = {"PYTHONPATH": str(self.openrecomp)}

    def _tool(self, name: str, *args: Path | str) -> None:
        _run([self.python, str(self.openrecomp / "tools" / name), *map(str, args)], cwd=self.openrecomp, env=self.env)

    def _compile_native(self, compiler: str, aot_c: Path, abi_c: Path, out: Path) -> None:
        _run([
            compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-fPIC", "-fvisibility=hidden",
            "-shared", f"-I{self.include}", str(aot_c), str(abi_c), "-o", str(out),
        ], cwd=self.output_root)

    def _runtime(self, spec: StaticVariantSpec) -> dict:
        return {
            "fixture_version": "1.0.0", "profile": "expansion-v1", "fixture_id": spec.fixture_id,
            "architecture": "mips32-le", "entry_address": 0x1000,
            "functions": [{"id": "static_memory_main", "address": 0x1000}],
            "memory_size_bytes": 262144,
            "initial_state": {"gpr:r29": 196608, "gpr:r31": 0},
            "observe_state_slot": "gpr:r2",
            "observable_memory": {"address": OBSERVE_ADDR, "size_bytes": OBSERVE_SIZE},
            "max_operations": 20000, "max_reference_steps": 2000,
        }

    def _build_elf(self, work: Path, spec: StaticVariantSpec) -> tuple[Path, IndependentStaticELFView]:
        source = work / "fixture.S"
        linker = work / "fixture.ld"
        obj = work / "fixture.o"
        linked = work / "fixture.linked.elf"
        note_path = work / "assurance-note.bin"
        final = work / "fixture.elf"
        note = spec.note_text.encode("utf-8")
        source.write_text(assembly_for(spec), encoding="utf-8", newline="\n")
        linker.write_text(linker_script_for(spec), encoding="utf-8", newline="\n")
        note_path.write_bytes(note)
        _run(["mipsel-linux-gnu-as", "-32", "-G0", str(source), "-o", str(obj)], cwd=work)
        _run([
            "mipsel-linux-gnu-ld", "-m", "elf32ltsmip", "--build-id=none", "-T", str(linker),
            str(obj), "-o", str(linked),
        ], cwd=work)
        _run([
            "mipsel-linux-gnu-objcopy", "--add-section", f".assurance-note={note_path}",
            "--set-section-flags", ".assurance-note=readonly", str(linked), str(final),
        ], cwd=work)
        return final, inspect_static_elf_independently(final, spec, note)

    def _write_manifest(self, spec: StaticVariantSpec, source: Path, artifacts: dict[str, Path], path: Path) -> None:
        kinds = (
            "fixture-assembly", "fixture-linker", "fixture-meta", "elf-metadata", "frontend-report", "ir-v1",
            "sidecar", "module-v1", "reference-result", "core-result", "aot-c", "native-abi-c",
            "native-module-gcc", "native-module-clang", "aot-result-gcc", "aot-result-clang",
        )
        payload = {
            "schema_version": "0.1", "run_id": f"mips32-elf-static-memory-real-v1:{spec.fixture_id}",
            "source": {"kind": "mips32-elf-static-memory", "path": str(source), "sha256": _sha256(source)},
            "translator": {"name": "OpenRecomp", "commit": self.expected_commit, "config_sha256": _sha256(self.host_contract)},
            "artifacts": [
                {"kind": kind, "path": str(artifacts[kind]), "sha256": _sha256(artifacts[kind])} for kind in kinds
            ],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _write_observation(self, spec: StaticVariantSpec, reference: dict, path: Path) -> None:
        from harness.compare.mips32_observables import defined_mips32_observables
        payload = {
            "schema_version": "0.1", "run_id": f"mips32-elf-static-memory-real-v1:{spec.fixture_id}",
            "fixture_id": spec.fixture_id, "observables": defined_mips32_observables(reference),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def run_variant(self, spec: StaticVariantSpec) -> StaticVariantResult:
        work = self.output_root / spec.fixture_id
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        elf, independent = self._build_elf(work, spec)
        metadata = work / "fixture.json"
        metadata.write_text(json.dumps(self._runtime(spec), indent=2, sort_keys=True) + "\n", encoding="utf-8")

        ir_a, ir_b = work / "ir.a.json", work / "ir.b.json"
        side_a, side_b = work / "sidecar.a.json", work / "sidecar.b.json"
        front_a, front_b = work / "frontend.a.json", work / "frontend.b.json"
        elf_a, elf_b = work / "elf.a.json", work / "elf.b.json"
        reference = work / "reference.json"
        module_a, module_b = work / "module.a.json", work / "module.b.json"
        core = work / "core.json"
        aot_a, aot_b = work / "aot.a.c", work / "aot.b.c"
        abi_a, abi_b = work / "native-abi.a.c", work / "native-abi.b.c"
        native_gcc, native_clang = work / "module.gcc.so", work / "module.clang.so"
        aot_gcc, aot_clang = work / "aot.gcc.json", work / "aot.clang.json"
        manifest, observation = work / "artifact-manifest.json", work / "observation.json"

        for ir, side, front, elf_meta in ((ir_a, side_a, front_a, elf_a), (ir_b, side_b, front_b, elf_b)):
            self._tool(
                "mips32_elf_static_memory_frontend_v1.py", elf, metadata, self.host_contract,
                ir, side, front, elf_meta,
            )
        for first, second, label in (
            (ir_a, ir_b, "IR"), (side_a, side_b, "sidecar"), (front_a, front_b, "frontend"), (elf_a, elf_b, "ELF metadata"),
        ):
            if first.read_bytes() != second.read_bytes():
                raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: {label} is not byte-repeatable")
        self._tool("validate_ir_v1.py", ir_a)
        self._tool("run_mips32_elf_static_memory_reference_v1.py", elf, metadata, reference)
        self._tool("package_ir_v1_module.py", ir_a, side_a, self.host_contract, module_a)
        self._tool("package_ir_v1_module.py", ir_a, side_a, self.host_contract, module_b)
        if module_a.read_bytes() != module_b.read_bytes():
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: Module is not byte-repeatable")
        self._tool("validate_module_v1.py", module_a, ir_a, self.host_contract)
        self._tool("run_mips32_expansion_core_v1.py", module_a, ir_a, self.host_contract, metadata, core)
        self._tool("aot_c_backend_v1.py", module_a, ir_a, self.host_contract, aot_a)
        self._tool("aot_c_backend_v1.py", module_a, ir_a, self.host_contract, aot_b)
        if aot_a.read_bytes() != aot_b.read_bytes():
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: AOT C is not byte-repeatable")
        self._tool("native_aot_abi_v1.py", module_a, ir_a, self.host_contract, abi_a)
        self._tool("native_aot_abi_v1.py", module_a, ir_a, self.host_contract, abi_b)
        if abi_a.read_bytes() != abi_b.read_bytes():
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: Native ABI is not byte-repeatable")
        self._compile_native("gcc", aot_a, abi_a, native_gcc)
        self._compile_native("clang", aot_a, abi_a, native_clang)
        self._tool("test_native_aot_abi_v1.py", native_gcc, module_a, ir_a, self.host_contract)
        self._tool("test_native_aot_abi_v1.py", native_clang, module_a, ir_a, self.host_contract)
        self._tool("run_aot_mips32_expansion_v1.py", native_gcc, ir_a, metadata, aot_gcc)
        self._tool("run_aot_mips32_expansion_v1.py", native_clang, ir_a, metadata, aot_clang)

        ir_json = json.loads(ir_a.read_text(encoding="utf-8"))
        front_json = json.loads(front_a.read_text(encoding="utf-8"))
        elf_json = json.loads(elf_a.read_text(encoding="utf-8"))
        module_json = json.loads(module_a.read_text(encoding="utf-8"))
        ref_json = json.loads(reference.read_text(encoding="utf-8"))
        core_json = json.loads(core.read_text(encoding="utf-8"))
        gcc_json = json.loads(aot_gcc.read_text(encoding="utf-8"))
        clang_json = json.loads(aot_clang.read_text(encoding="utf-8"))

        if ir_json["source"].get("adapter") != ADAPTER_ID or ir_json["source"]["architecture"] != "mips32-le":
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: normalized adapter identity mismatch")
        if elf_json["input_sha256"] != independent.source_sha256:
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: upstream/independent full-ELF hash mismatch")
        if front_json.get("static_memory_segment_count") != 3:
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: frontend lost static segment count")
        upstream_segments = {item["name"]: item for item in elf_json["static_memory_segments"]}
        module_segments = {item["name"]: item for item in module_json["memory"]["segments"]}
        for name, section in independent.sections.items():
            up = upstream_segments.get(name)
            mod = module_segments.get(name)
            if up is None or mod is None:
                raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: {name} missing from upstream/module evidence")
            if (up["guest_address"], up["size_bytes"], up["data_sha256"], up["zero_fill"]) != (
                section.address, section.size, section.sha256, section.zero_fill,
            ):
                raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: {name} upstream layout disagrees with independent parser")
            if (mod["guest_address"], mod["data_sha256"]) != (section.address, section.sha256):
                raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: {name} Module Image differs from independent bytes")

        source_hashes = {
            independent.source_sha256, ir_json["source"]["input_sha256"], front_json["source_input_sha256"],
            module_json["ir"]["source_input_sha256"], module_json["provenance"]["source_input_sha256"],
            ref_json["source_input_sha256"], core_json["source_input_sha256"],
            gcc_json["source_input_sha256"], clang_json["source_input_sha256"],
        }
        if len(source_hashes) != 1:
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: full ELF provenance diverged")
        require_mips32_equal(ref_json, core_json)
        require_mips32_equal(ref_json, gcc_json)
        require_mips32_equal(ref_json, clang_json)
        if not (core_json["operations"] == gcc_json["operations"] == clang_json["operations"]):
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: Core/GCC/Clang operation count differs")
        if front_json["delay_slots_lowered"] != ref_json["delay_slots_executed"]:
            raise MIPS32ELFStaticMemoryAssuranceError(f"{spec.fixture_id}: delay-slot evidence differs")

        artifacts = {
            "fixture-assembly": work / "fixture.S", "fixture-linker": work / "fixture.ld", "fixture-meta": metadata,
            "elf-metadata": elf_a, "frontend-report": front_a, "ir-v1": ir_a, "sidecar": side_a,
            "module-v1": module_a, "reference-result": reference, "core-result": core, "aot-c": aot_a,
            "native-abi-c": abi_a, "native-module-gcc": native_gcc, "native-module-clang": native_clang,
            "aot-result-gcc": aot_gcc, "aot-result-clang": aot_clang,
        }
        self._write_manifest(spec, elf, artifacts, manifest)
        self._write_observation(spec, ref_json, observation)
        return StaticVariantResult(
            spec=spec, elf_path=elf, independent=independent, reference_result=ref_json,
            core_result=core_json, aot_gcc_result=gcc_json, aot_clang_result=clang_json,
            artifacts={**artifacts, "elf": elf}, manifest_path=manifest, observation_path=observation,
        )
