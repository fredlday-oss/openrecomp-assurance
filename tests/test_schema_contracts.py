from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMA_NAMES = (
    "artifact-manifest.schema.json",
    "observation.schema.json",
    "assurance-result.schema.json",
)
SHA = "0" * 64


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def samples() -> dict[str, dict]:
    return {
        "artifact-manifest.schema.json": {
            "schema_version": "0.1",
            "run_id": "test:manifest",
            "source": {"kind": "rv32i-elf", "sha256": SHA},
            "translator": {"name": "OpenRecomp", "commit": "53d0bce"},
            "artifacts": [{"kind": "ir-v1", "sha256": SHA}],
        },
        "observation.schema.json": {
            "schema_version": "0.1",
            "run_id": "test:observation",
            "fixture_id": "fixture",
            "observables": {"checksum": 1},
        },
        "assurance-result.schema.json": {
            "schema_version": "0.1",
            "fixture_id": "fixture",
            "verdict": "PASS",
            "classification": "BOUNDED",
            "bounded_claim": "bounded test claim",
            "checks": {"example": "PASS"},
            "seeded_divergences": {"detected": 0, "total": 0},
        },
    }


def test_schema_versions_are_pinned_to_v0_1():
    for name in SCHEMA_NAMES:
        schema = load_schema(name)
        assert schema["properties"]["schema_version"]["const"] == "0.1"


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_minimal_valid_instances_are_accepted(name: str):
    jsonschema.validate(samples()[name], load_schema(name))


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_wrong_schema_version_is_rejected(name: str):
    value = deepcopy(samples()[name])
    value["schema_version"] = "9.9"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, load_schema(name))


@pytest.mark.parametrize(
    ("name", "required_key"),
    (
        ("artifact-manifest.schema.json", "source"),
        ("observation.schema.json", "observables"),
        ("assurance-result.schema.json", "bounded_claim"),
    ),
)
def test_missing_required_evidence_is_rejected(name: str, required_key: str):
    value = deepcopy(samples()[name])
    del value[required_key]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, load_schema(name))
