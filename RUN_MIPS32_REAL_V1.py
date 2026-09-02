#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import jsonschema

from harness.compare.mips32_observables import (
    MIPS32EvidenceError,
    compare_mips32_observables,
    defined_mips32_observables,
    require_mips32_equal,
)
from harness.runner.openrecomp_mips32 import (
    OPENRECOMP_PIN,
    SEEDS,
    OpenRecompMIPS32Runner,
    baseline_hex,
    decoded_records,
    seeded_hex,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpenRecomp Assurance MIPS32 Real V1 against real OpenRecomp.")
    parser.add_argument("--openrecomp", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("evidence/mips32-real-v1"))
    parser.add_argument("--expected-openrecomp-commit", default=OPENRECOMP_PIN)
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

        runner = OpenRecompMIPS32Runner(
            assurance_root=assurance_root,
            openrecomp=openrecomp,
            output_root=out / "runs",
            expected_commit=head,
        )
        runner.output_root.mkdir(parents=True, exist_ok=True)
        canonical = runner.canonical_hex.read_text(encoding="utf-8")

        base_a_text = baseline_hex(canonical, "A")
        base_b_text = baseline_hex(canonical, "B")
        if decoded_records(base_a_text) != decoded_records(base_b_text):
            raise MIPS32EvidenceError("equivalent baseline sources decode to different instruction records")
        checks["baseline_decoded_records_equal"] = "PASS"

        base_a = runner.run_variant("baseline-a", base_a_text)
        base_b = runner.run_variant("baseline-b", base_b_text)
        if base_a.source_path.read_bytes() == base_b.source_path.read_bytes():
            raise MIPS32EvidenceError("equivalent baseline MIPS32 source bytes must be distinct")
        checks["source_hashes_distinct"] = "PASS"

        require_mips32_equal(base_a.reference_result, base_b.reference_result)
        checks["baseline_observables_match"] = "PASS"
        checks["reference_core_gcc_clang_agreement"] = "PASS"

        replay_a = runner.run_variant("replay-a", base_a.source_path.read_text(encoding="utf-8"))
        replay_b = runner.run_variant("replay-b", base_b.source_path.read_text(encoding="utf-8"))
        require_mips32_equal(base_a.reference_result, replay_a.reference_result)
        require_mips32_equal(base_b.reference_result, replay_b.reference_result)
        if base_a.source_path.read_bytes() != replay_a.source_path.read_bytes():
            raise MIPS32EvidenceError("baseline A replay source bytes changed")
        if base_b.source_path.read_bytes() != replay_b.source_path.read_bytes():
            raise MIPS32EvidenceError("baseline B replay source bytes changed")
        checks["replay_stability"] = "PASS"

        for original, replay, label in ((base_a, replay_a, "A"), (base_b, replay_b, "B")):
            for key in ("ir-v1", "module-v1", "aot-c", "native-abi-c"):
                if original.artifacts[key].read_bytes() != replay.artifacts[key].read_bytes():
                    raise MIPS32EvidenceError(f"baseline {label} {key} artifact is not repeatable")
        checks["clean_artifact_repeatability"] = "PASS"

        seed_report = []
        for seed_id, old, new, description in SEEDS:
            seeded = runner.run_variant(seed_id, seeded_hex(canonical, old, new))
            differences = compare_mips32_observables(base_a.reference_result, seeded.reference_result)
            is_detected = bool(differences)
            detected += int(is_detected)
            seed_report.append(
                {
                    "seed_id": seed_id,
                    "description": description,
                    "detected": is_detected,
                    "differences": differences,
                }
            )
        (out / "seeded-divergences.json").write_text(
            json.dumps(seed_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checks["seeded_divergences_5_of_5"] = "PASS" if detected == len(SEEDS) == 5 else "FAIL"

        malformed = dict(base_a.reference_result)
        malformed.pop("checksum")
        try:
            defined_mips32_observables(malformed)
        except MIPS32EvidenceError:
            checks["missing_evidence_fails_closed"] = "PASS"
        else:
            checks["missing_evidence_fails_closed"] = "FAIL"

        validate_generated(assurance_root, out)
        checks["generated_schema_validation"] = "PASS"

        all_pass = all(value == "PASS" for value in checks.values()) and detected == len(SEEDS) == 5
        result = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-mips32-real-v1",
            "verdict": "PASS" if all_pass else "FAIL",
            "classification": "PROVEN" if all_pass else "BOUNDED",
            "bounded_claim": (
                "For the rights-safe OpenRecomp MIPS32 expansion-v1 logic-shift fixture, two byte-distinct "
                "but instruction-equivalent source records, their exact replays, and five specified valid "
                "semantic mutations, the independent MIPS32 reference interpreter, normalized Core V1, "
                "GCC native AOT and Clang native AOT agree on the defined semantic observables; every seeded "
                "mutation is detected. This does not prove arbitrary MIPS32 binaries, arbitrary endianness, "
                "or general MIPS32 ISA coverage."
            ),
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        result_path = out / "assurance-result.json"
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        jsonschema.validate(result, load_schema(assurance_root, "assurance-result.schema.json"))

        summary = [
            "# OpenRecomp Assurance MIPS32 Real V1",
            "",
            f"- OpenRecomp commit: `{head}`",
            f"- Baseline source SHA-256 distinct: **{checks['source_hashes_distinct']}**",
            f"- Baseline decoded instruction records equal: **{checks['baseline_decoded_records_equal']}**",
            f"- Equivalent semantic observables: **{checks['baseline_observables_match']}**",
            f"- Reference/Core/GCC/Clang agreement: **{checks['reference_core_gcc_clang_agreement']}**",
            f"- Replay stability: **{checks['replay_stability']}**",
            f"- Clean IR/Module/AOT repeatability: **{checks['clean_artifact_repeatability']}**",
            f"- Seeded semantic divergences: **{detected}/{len(SEEDS)}**",
            f"- Missing evidence fail-closed: **{checks['missing_evidence_fails_closed']}**",
            "",
            f"**Verdict: {result['verdict']} / {result['classification']}**",
            "",
        ]
        (out / "RESULT.md").write_text("\n".join(summary), encoding="utf-8")

        print(f"OPENRECOMP_ASSURANCE_MIPS32_REAL_V1_SEEDS={detected}/{len(SEEDS)}")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_REAL_V1={result['verdict']}")
        return 0 if all_pass else 2

    except Exception as exc:
        checks.setdefault("integration", "FAIL")
        failure = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-mips32-real-v1",
            "verdict": "FAIL",
            "classification": "FAIL",
            "bounded_claim": "The MIPS32 Real V1 assurance gate did not complete; no positive MIPS32 assurance claim is made.",
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        (out / "assurance-result.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OPENRECOMP_ASSURANCE_MIPS32_REAL_V1=FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
