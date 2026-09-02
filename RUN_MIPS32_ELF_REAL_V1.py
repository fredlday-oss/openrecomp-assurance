#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import jsonschema

from harness.compare.mips32_observables import (
    MIPS32EvidenceError,
    compare_mips32_observables,
    defined_mips32_observables,
    require_mips32_equal,
)
from harness.runner.openrecomp_mips32_elf import (
    OPENRECOMP_ELF_PIN,
    SEEDS,
    MIPS32ELFAssuranceError,
    OpenRecompMIPS32ELFRunner,
    canonical_records,
    inspect_elf_independently,
    mutate_records,
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
        raise MIPS32ELFAssuranceError(f"{label}: linked ELF container is not byte-repeatable")
    require_mips32_equal(original.reference_result, replay.reference_result)
    for key in ("ir-v1", "module-v1", "aot-c", "native-abi-c"):
        if original.artifacts[key].read_bytes() != replay.artifacts[key].read_bytes():
            raise MIPS32ELFAssuranceError(f"{label}: {key} artifact is not byte-repeatable")


def openrecomp_rejects_wrong_machine(runner: OpenRecompMIPS32ELFRunner, source_elf: Path, out: Path) -> bool:
    blob = bytearray(source_elf.read_bytes())
    struct.pack_into("<H", blob, 18, 243)
    bad = out / "wrong-machine.elf"
    bad.write_bytes(blob)
    # The independent assurance parser must reject the tampered container too.
    try:
        inspect_elf_independently(bad, canonical_records(runner.canonical_hex.read_text(encoding="utf-8")), b"equivalent-baseline:A")
    except MIPS32ELFAssuranceError:
        independent_rejected = True
    else:
        independent_rejected = False

    paths = [out / f"wrong-machine-{name}" for name in ("ir.json", "sidecar.json", "frontend.json", "elf.json")]
    proc = subprocess.run(
        [
            sys.executable,
            str(runner.openrecomp / "tools" / "mips32_elf_frontend_v1.py"),
            str(bad), str(runner.runtime_meta), str(runner.host_contract), *map(str, paths),
        ],
        cwd=str(runner.openrecomp),
        env={**__import__("os").environ, **runner.env},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return independent_rejected and proc.returncode != 0 and "expected EM_MIPS" in (proc.stdout or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded real MIPS32 ELF ingestion assurance against OpenRecomp.")
    parser.add_argument("--openrecomp", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("evidence/mips32-elf-real-v1"))
    parser.add_argument("--expected-openrecomp-commit", default=OPENRECOMP_ELF_PIN)
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
        runner = OpenRecompMIPS32ELFRunner(
            assurance_root=assurance_root,
            openrecomp=openrecomp,
            output_root=out / "runs",
            expected_commit=head,
        )
        runner.output_root.mkdir(parents=True, exist_ok=True)
        records = canonical_records(runner.canonical_hex.read_text(encoding="utf-8"))

        base_a = runner.run_variant("baseline-a", records, "equivalent-baseline:A")
        base_b = runner.run_variant("baseline-b", records, "equivalent-baseline:B")
        if base_a.independent.source_sha256 == base_b.independent.source_sha256:
            raise MIPS32ELFAssuranceError("equivalent baseline ELF hashes must be distinct")
        checks["baseline_elf_hashes_distinct"] = "PASS"
        if base_a.independent.semantic_bytes != base_b.independent.semantic_bytes:
            raise MIPS32ELFAssuranceError("equivalent baseline ELF semantic .text differs")
        if base_a.independent.padding_bytes != base_b.independent.padding_bytes:
            raise MIPS32ELFAssuranceError("equivalent baseline ELF padding differs")
        checks["independent_elf_semantic_image_equal"] = "PASS"
        require_mips32_equal(base_a.reference_result, base_b.reference_result)
        checks["baseline_observables_match"] = "PASS"
        checks["reference_core_gcc_clang_agreement"] = "PASS"

        replay_a = runner.run_variant("replay-a", records, "equivalent-baseline:A")
        replay_b = runner.run_variant("replay-b", records, "equivalent-baseline:B")
        require_repeatable(base_a, replay_a, "baseline A")
        require_repeatable(base_b, replay_b, "baseline B")
        checks["elf_replay_stability"] = "PASS"
        checks["clean_artifact_repeatability"] = "PASS"

        seed_report = []
        for seed_id, old, new, description in SEEDS:
            seeded_records = mutate_records(records, old, new)
            seeded = runner.run_variant(seed_id, seeded_records, seed_id)
            differences = compare_mips32_observables(base_a.reference_result, seeded.reference_result)
            is_detected = bool(differences)
            detected += int(is_detected)
            seed_report.append({
                "seed_id": seed_id,
                "description": description,
                "detected": is_detected,
                "elf_sha256": seeded.independent.source_sha256,
                "semantic_text_sha256": __import__("hashlib").sha256(seeded.independent.semantic_bytes).hexdigest(),
                "differences": differences,
            })
        (out / "seeded-divergences.json").write_text(
            json.dumps(seed_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checks["seeded_divergences_5_of_5"] = "PASS" if detected == len(SEEDS) == 5 else "FAIL"

        malformed = dict(base_a.reference_result)
        malformed.pop("checksum")
        try:
            defined_mips32_observables(malformed)
        except MIPS32EvidenceError:
            checks["missing_observation_fails_closed"] = "PASS"
        else:
            checks["missing_observation_fails_closed"] = "FAIL"

        checks["wrong_machine_fails_closed"] = (
            "PASS" if openrecomp_rejects_wrong_machine(runner, base_a.elf_path, out) else "FAIL"
        )
        validate_generated(assurance_root, out)
        checks["generated_schema_validation"] = "PASS"

        all_pass = all(value == "PASS" for value in checks.values()) and detected == len(SEEDS) == 5
        result = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-mips32-elf-real-v1",
            "verdict": "PASS" if all_pass else "FAIL",
            "classification": "PROVEN" if all_pass else "BOUNDED",
            "bounded_claim": (
                "For a rights-safe little-endian ELF32 ET_EXEC/EM_MIPS logic-shift executable, two ELF containers "
                "with byte-distinct non-allocating assurance-note provenance but identical independently verified semantic .text, "
                "their exact rebuild/replays, and five specified valid one-instruction semantic mutations, OpenRecomp bounded "
                "ELF ingestion preserves ELF provenance and the independent MIPS32 reference, Core V1, GCC native AOT and "
                "Clang native AOT agree on defined semantics; all five mutations are detected. This does not prove arbitrary "
                "MIPS32 ELF loading, dynamic linking, relocation/data-section semantics, big-endian ELF or full ISA coverage."
            ),
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        (out / "assurance-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        jsonschema.validate(result, load_schema(assurance_root, "assurance-result.schema.json"))

        summary = [
            "# OpenRecomp Assurance MIPS32 ELF Real V1",
            "",
            f"- OpenRecomp commit: `{head}`",
            f"- Byte-distinct equivalent ELF baselines: **{checks['baseline_elf_hashes_distinct']}**",
            f"- Independently verified semantic .text equal: **{checks['independent_elf_semantic_image_equal']}**",
            f"- Equivalent semantic observables: **{checks['baseline_observables_match']}**",
            f"- Reference/Core/GCC/Clang agreement: **{checks['reference_core_gcc_clang_agreement']}**",
            f"- Exact ELF replay stability: **{checks['elf_replay_stability']}**",
            f"- IR/Module/AOT repeatability: **{checks['clean_artifact_repeatability']}**",
            f"- Seeded semantic divergences: **{detected}/{len(SEEDS)}**",
            f"- Wrong-machine fail-closed: **{checks['wrong_machine_fails_closed']}**",
            f"- Missing-observation fail-closed: **{checks['missing_observation_fails_closed']}**",
            "",
            f"**Verdict: {result['verdict']} / {result['classification']}**",
            "",
        ]
        (out / "RESULT.md").write_text("\n".join(summary), encoding="utf-8")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1_SEEDS={detected}/{len(SEEDS)}")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1={result['verdict']}")
        return 0 if all_pass else 2

    except Exception as exc:
        checks.setdefault("integration", "FAIL")
        failure = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-mips32-elf-real-v1",
            "verdict": "FAIL",
            "classification": "FAIL",
            "bounded_claim": "The MIPS32 ELF Real V1 assurance gate did not complete; no positive ELF ingestion assurance claim is made.",
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        (out / "assurance-result.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1=FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
