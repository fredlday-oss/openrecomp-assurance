#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import jsonschema

from harness.compare.mips32_observables import (
    MIPS32EvidenceError,
    compare_mips32_observables,
    defined_mips32_observables,
    require_mips32_equal,
)
from harness.runner.openrecomp_mips32_elf_static_memory import (
    OPENRECOMP_STATIC_MEMORY_PIN,
    SEEDS,
    MIPS32ELFStaticMemoryAssuranceError,
    OpenRecompMIPS32ELFStaticMemoryRunner,
    StaticVariantSpec,
    inspect_static_elf_independently,
    verify_openrecomp,
)


def load_schema(root: Path, name: str) -> dict:
    return json.loads((root / "schemas" / name).read_text(encoding="utf-8"))


def validate_generated(root: Path, generated: Path) -> None:
    schemas = {
        "artifact-manifest.json": load_schema(root, "artifact-manifest.schema.json"),
        "observation.json": load_schema(root, "observation.schema.json"),
    }
    for path in generated.rglob("*.json"):
        schema = schemas.get(path.name)
        if schema is not None:
            jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), schema)


def require_repeatable(original, replay, label: str) -> None:
    if original.elf_path.read_bytes() != replay.elf_path.read_bytes():
        raise MIPS32ELFStaticMemoryAssuranceError(f"{label}: full linked ELF is not byte-repeatable")
    require_mips32_equal(original.reference_result, replay.reference_result)
    for key in ("ir-v1", "module-v1", "aot-c", "native-abi-c"):
        if original.artifacts[key].read_bytes() != replay.artifacts[key].read_bytes():
            raise MIPS32ELFStaticMemoryAssuranceError(f"{label}: {key} is not byte-repeatable")


def _cstr(blob: bytes, offset: int) -> str:
    if offset < 0 or offset >= len(blob):
        return ""
    end = blob.find(b"\0", offset)
    if end < 0:
        end = len(blob)
    return blob[offset:end].decode("utf-8", "replace")


def static_permission_rejected(runner: OpenRecompMIPS32ELFStaticMemoryRunner, baseline, out: Path) -> bool:
    blob = bytearray(baseline.elf_path.read_bytes())
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", blob, 0)
    shoff, shentsize, shnum, shstrndx = header[6], header[11], header[12], header[13]
    sections = []
    for index in range(shnum):
        vals = struct.unpack_from("<IIIIIIIIII", blob, shoff + index * shentsize)
        sections.append({"index": index, "name_off": vals[0], "offset": vals[4], "size": vals[5]})
    names_sec = sections[shstrndx]
    names = blob[names_sec["offset"]:names_sec["offset"] + names_sec["size"]]
    target = next((item for item in sections if _cstr(names, item["name_off"]) == ".rodata"), None)
    if target is None:
        return False
    flags_off = shoff + target["index"] * shentsize + 8
    current_flags = struct.unpack_from("<I", blob, flags_off)[0]
    struct.pack_into("<I", blob, flags_off, current_flags | 0x1)
    bad = out / "bad-rodata-writable.elf"
    bad.write_bytes(blob)

    try:
        inspect_static_elf_independently(bad, baseline.spec, baseline.spec.note_text.encode("utf-8"))
    except MIPS32ELFStaticMemoryAssuranceError:
        independent_rejected = True
    else:
        independent_rejected = False

    bad_dir = out / "bad-rodata-upstream"
    bad_dir.mkdir(exist_ok=True)
    paths = [bad_dir / name for name in ("ir.json", "sidecar.json", "frontend.json", "elf.json")]
    proc = subprocess.run(
        [
            sys.executable,
            str(runner.openrecomp / "tools" / "mips32_elf_static_memory_frontend_v1.py"),
            str(bad), str(baseline.artifacts["fixture-meta"]), str(runner.host_contract), *map(str, paths),
        ],
        cwd=str(runner.openrecomp),
        env={**os.environ, **runner.env},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return independent_rejected and proc.returncode != 0 and ".rodata must be" in (proc.stdout or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded real MIPS32 ELF static-memory assurance against OpenRecomp.")
    parser.add_argument("--openrecomp", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("evidence/mips32-elf-static-memory-real-v1"))
    parser.add_argument("--expected-openrecomp-commit", default=OPENRECOMP_STATIC_MEMORY_PIN)
    args = parser.parse_args()

    assurance_root = Path(__file__).resolve().parent
    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    checks: dict[str, str] = {}
    detected = 0

    try:
        openrecomp = args.openrecomp.resolve()
        head = verify_openrecomp(openrecomp, args.expected_openrecomp_commit)
        checks["real_openrecomp_commit"] = "PASS"
        runner = OpenRecompMIPS32ELFStaticMemoryRunner(
            assurance_root=assurance_root,
            openrecomp=openrecomp,
            output_root=out / "runs",
            expected_commit=head,
        )
        runner.output_root.mkdir(parents=True, exist_ok=True)

        base_a_spec = StaticVariantSpec("baseline-a", note_text="equivalent-static-memory:A")
        base_b_spec = StaticVariantSpec("baseline-b", note_text="equivalent-static-memory:B")
        base_a = runner.run_variant(base_a_spec)
        base_b = runner.run_variant(base_b_spec)
        if base_a.independent.source_sha256 == base_b.independent.source_sha256:
            raise MIPS32ELFStaticMemoryAssuranceError("equivalent baseline ELF hashes must differ")
        checks["baseline_elf_hashes_distinct"] = "PASS"
        if base_a.independent.semantic_text != base_b.independent.semantic_text:
            raise MIPS32ELFStaticMemoryAssuranceError("equivalent baseline semantic .text differs")
        for name in (".rodata", ".data", ".bss"):
            a = base_a.independent.sections[name]
            b = base_b.independent.sections[name]
            if (a.address, a.data, a.zero_fill) != (b.address, b.data, b.zero_fill):
                raise MIPS32ELFStaticMemoryAssuranceError(f"equivalent baseline {name} differs")
        checks["independent_static_image_equal"] = "PASS"
        require_mips32_equal(base_a.reference_result, base_b.reference_result)
        checks["baseline_observables_match"] = "PASS"
        checks["reference_core_gcc_clang_agreement"] = "PASS"

        replay_a = runner.run_variant(replace(base_a_spec, fixture_id="replay-a"))
        replay_b = runner.run_variant(replace(base_b_spec, fixture_id="replay-b"))
        require_repeatable(base_a, replay_a, "baseline A")
        require_repeatable(base_b, replay_b, "baseline B")
        checks["elf_replay_stability"] = "PASS"
        checks["generated_artifact_repeatability"] = "PASS"

        seed_report = []
        for seed in SEEDS:
            seeded = runner.run_variant(replace(seed, note_text=seed.fixture_id))
            differences = compare_mips32_observables(base_a.reference_result, seeded.reference_result)
            is_detected = bool(differences)
            detected += int(is_detected)
            seed_report.append({
                "seed_id": seed.fixture_id,
                "description": seed.description,
                "detected": is_detected,
                "elf_sha256": seeded.independent.source_sha256,
                "static_layout": {
                    name: {
                        "address": section.address,
                        "size": section.size,
                        "sha256": section.sha256,
                        "zero_fill": section.zero_fill,
                    }
                    for name, section in seeded.independent.sections.items()
                },
                "differences": differences,
            })
        (out / "seeded-divergences.json").write_text(
            json.dumps(seed_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checks["seeded_loader_semantic_divergences_5_of_5"] = "PASS" if detected == len(SEEDS) == 5 else "FAIL"

        malformed = dict(base_a.reference_result)
        malformed.pop("checksum")
        try:
            defined_mips32_observables(malformed)
        except MIPS32EvidenceError:
            checks["missing_observation_fails_closed"] = "PASS"
        else:
            checks["missing_observation_fails_closed"] = "FAIL"

        checks["invalid_static_permission_fails_closed"] = (
            "PASS" if static_permission_rejected(runner, base_a, out) else "FAIL"
        )
        validate_generated(assurance_root, out)
        checks["generated_schema_validation"] = "PASS"

        all_pass = all(value == "PASS" for value in checks.values()) and detected == len(SEEDS) == 5
        result = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-mips32-elf-static-memory-real-v1",
            "verdict": "PASS" if all_pass else "FAIL",
            "classification": "PROVEN" if all_pass else "BOUNDED",
            "bounded_claim": (
                "For a rights-safe little-endian ELF32 ET_EXEC/EM_MIPS fixture with independently verified .rodata, "
                "file-backed .data including bounded GNU MIPS linker padding, and zero-filled .bss, two byte-distinct "
                "but semantically equivalent ELF containers, their exact rebuild/replays, and five specified static-loader "
                "or guest-semantic variants, OpenRecomp preserves full-ELF provenance and the independent reference, Core V1, "
                "GCC native AOT and Clang native AOT agree on defined state and memory semantics; all five variants are detected. "
                "This does not prove arbitrary MIPS32 ELF loading, relocations, dynamic linking, TLS, big-endian ELF, runtime "
                "section-permission enforcement or full ISA coverage."
            ),
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        (out / "assurance-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        jsonschema.validate(result, load_schema(assurance_root, "assurance-result.schema.json"))

        summary = [
            "# OpenRecomp Assurance MIPS32 ELF Static Memory Real V1", "",
            f"- OpenRecomp commit: `{head}`",
            f"- Byte-distinct equivalent ELF baselines: **{checks['baseline_elf_hashes_distinct']}**",
            f"- Independently verified static image equal: **{checks['independent_static_image_equal']}**",
            f"- Equivalent defined observables: **{checks['baseline_observables_match']}**",
            f"- Reference/Core/GCC/Clang agreement: **{checks['reference_core_gcc_clang_agreement']}**",
            f"- Exact ELF replay stability: **{checks['elf_replay_stability']}**",
            f"- Generated IR/Module/AOT repeatability: **{checks['generated_artifact_repeatability']}**",
            f"- Seeded loader/semantic divergences: **{detected}/{len(SEEDS)}**",
            f"- Invalid static permission fail-closed: **{checks['invalid_static_permission_fails_closed']}**",
            f"- Missing observation fail-closed: **{checks['missing_observation_fails_closed']}**", "",
            f"**Verdict: {result['verdict']} / {result['classification']}**", "",
        ]
        (out / "RESULT.md").write_text("\n".join(summary), encoding="utf-8")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_ELF_STATIC_MEMORY_REAL_V1_SEEDS={detected}/{len(SEEDS)}")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_ELF_STATIC_MEMORY_REAL_V1={result['verdict']}")
        return 0 if all_pass else 2

    except Exception as exc:
        checks.setdefault("integration", "FAIL")
        failure = {
            "schema_version": "0.1", "fixture_id": "openrecomp-mips32-elf-static-memory-real-v1",
            "verdict": "FAIL", "classification": "FAIL",
            "bounded_claim": "The MIPS32 ELF Static Memory Real V1 gate did not complete; no positive static-memory assurance claim is made.",
            "checks": checks, "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        (out / "assurance-result.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_ELF_STATIC_MEMORY_REAL_V1=FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
