#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import jsonschema

from harness.compare.observables import EvidenceError, compare_observables, defined_observables, require_equal
from harness.runner.openrecomp_rv32i import OPENRECOMP_PIN, SEEDS, OpenRecompRV32IRunner, baseline_source, seeded_source, verify_openrecomp


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
    parser = argparse.ArgumentParser(description="Run OpenRecomp Assurance RV32I v0.1 against real OpenRecomp.")
    parser.add_argument("--openrecomp", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("evidence/rv32i-v0.1-real-v1"))
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
        head = verify_openrecomp(args.openrecomp.resolve(), args.expected_openrecomp_commit)
        checks["real_openrecomp_commit"] = "PASS"

        canonical = (args.openrecomp.resolve() / "src" / "fixture_full.c").read_text(encoding="utf-8")
        runner = OpenRecompRV32IRunner(
            assurance_root=assurance_root,
            openrecomp=args.openrecomp,
            output_root=out / "runs",
            expected_commit=head,
        )
        runner.output_root.mkdir(parents=True, exist_ok=True)

        base_a = runner.run_variant("baseline-a", baseline_source(canonical, "A"))
        base_b = runner.run_variant("baseline-b", baseline_source(canonical, "B"))
        if base_a.elf_path.read_bytes() == base_b.elf_path.read_bytes():
            raise EvidenceError("equivalent baseline ELFs must be byte-distinct")
        checks["source_hashes_distinct"] = "PASS"

        require_equal(base_a.core_result, base_b.core_result)
        checks["baseline_observables_match"] = "PASS"

        replay_a = runner.run_variant("replay-a", base_a.source_path.read_text(encoding="utf-8"))
        replay_b = runner.run_variant("replay-b", base_b.source_path.read_text(encoding="utf-8"))
        require_equal(base_a.core_result, replay_a.core_result)
        require_equal(base_b.core_result, replay_b.core_result)
        checks["replay_stability"] = "PASS"

        if base_a.artifacts["aot-c"].read_bytes() != replay_a.artifacts["aot-c"].read_bytes():
            raise EvidenceError("baseline A AOT artifact is not repeatable")
        if base_b.artifacts["aot-c"].read_bytes() != replay_b.artifacts["aot-c"].read_bytes():
            raise EvidenceError("baseline B AOT artifact is not repeatable")
        checks["clean_artifact_repeatability"] = "PASS"

        seed_report = []
        for seed_id, old, new in SEEDS:
            seeded = runner.run_variant(seed_id, seeded_source(canonical, old, new))
            differences = compare_observables(base_a.core_result, seeded.core_result)
            is_detected = bool(differences)
            detected += int(is_detected)
            seed_report.append({
                "seed_id": seed_id,
                "detected": is_detected,
                "differences": differences,
            })
        (out / "seeded-divergences.json").write_text(
            json.dumps(seed_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        checks["seeded_divergences_5_of_5"] = "PASS" if detected == len(SEEDS) == 5 else "FAIL"

        malformed = dict(base_a.core_result)
        malformed.pop("checksum")
        try:
            defined_observables(malformed)
        except EvidenceError:
            checks["missing_evidence_fails_closed"] = "PASS"
        else:
            checks["missing_evidence_fails_closed"] = "FAIL"

        validate_generated(assurance_root, out)
        checks["generated_schema_validation"] = "PASS"

        all_pass = all(value == "PASS" for value in checks.values()) and detected == 5
        result = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-rv32i-v0.1-real-v1",
            "verdict": "PASS" if all_pass else "FAIL",
            "classification": "PROVEN" if all_pass else "BOUNDED",
            "bounded_claim": (
                "For the rights-safe E07 RV32I equivalent fixture pair and five deliberately seeded "
                "source variants, OpenRecomp at the pinned commit produces reproducible equivalent "
                "defined observables for the pair and detects every seeded semantic divergence."
            ),
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": len(SEEDS)},
        }
        result_path = out / "assurance-result.json"
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        jsonschema.validate(result, load_schema(assurance_root, "assurance-result.schema.json"))

        summary = [
            "# OpenRecomp Assurance RV32I V0.1 Real V1",
            "",
            f"- OpenRecomp commit: `{head}`",
            f"- Baseline ELF SHA-256 distinct: **{checks['source_hashes_distinct']}**",
            f"- Equivalent observables: **{checks['baseline_observables_match']}**",
            f"- Replay stability: **{checks['replay_stability']}**",
            f"- Clean AOT repeatability: **{checks['clean_artifact_repeatability']}**",
            f"- Seeded semantic divergences: **{detected}/5**",
            f"- Missing evidence fail-closed: **{checks['missing_evidence_fails_closed']}**",
            "",
            f"**Verdict: {result['verdict']} / {result['classification']}**",
            "",
        ]
        (out / "RESULT.md").write_text("\n".join(summary), encoding="utf-8")

        print(f"OPENRECOMP_ASSURANCE_RV32I_REAL_V1_SEEDS={detected}/5")
        print(f"OPENRECOMP_ASSURANCE_RV32I_REAL_V1={result['verdict']}")
        return 0 if all_pass else 2

    except Exception as exc:
        checks.setdefault("integration", "FAIL")
        failure = {
            "schema_version": "0.1",
            "fixture_id": "openrecomp-rv32i-v0.1-real-v1",
            "verdict": "FAIL",
            "classification": "FAIL",
            "bounded_claim": "The RV32I v0.1 assurance gate did not complete; no positive assurance claim is made.",
            "checks": checks,
            "seeded_divergences": {"detected": detected, "total": 5},
        }
        (out / "assurance-result.json").write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OPENRECOMP_ASSURANCE_RV32I_REAL_V1=FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
