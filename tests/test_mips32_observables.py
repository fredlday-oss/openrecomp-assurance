import pytest

from harness.compare.mips32_observables import (
    MIPS32EvidenceError,
    compare_mips32_observables,
    defined_mips32_observables,
    require_mips32_equal,
)


def result(**overrides):
    base = {
        "architecture": "mips32-le",
        "return_v0": 7,
        "memory_word": 0,
        "memory_bytes_hex": "00000000",
        "checksum": 123,
        "state": {"gpr:r1": 1, "gpr:r2": 7, "special:hi": 0, "special:lo": 0},
    }
    base.update(overrides)
    return base


def test_defined_observables_are_scalar_and_hash_full_state():
    observed = defined_mips32_observables(result())
    assert observed["return_v0"] == 7
    assert len(observed["state_sha256"]) == 64
    assert "state" not in observed


def test_equal_results_pass():
    require_mips32_equal(result(), result())


def test_full_state_change_is_detected():
    changed = result(state={"gpr:r1": 2, "gpr:r2": 7, "special:hi": 0, "special:lo": 0})
    differences = compare_mips32_observables(result(), changed)
    assert set(differences) == {"state_sha256"}


def test_missing_evidence_fails_closed():
    malformed = result()
    malformed.pop("checksum")
    with pytest.raises(MIPS32EvidenceError):
        defined_mips32_observables(malformed)
