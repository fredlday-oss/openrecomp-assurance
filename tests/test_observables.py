import pytest

from harness.compare.observables import DEFINED_OBSERVABLES, EvidenceError, compare_observables, defined_observables, require_equal


def sample():
    out = {key: 1 for key in DEFINED_OBSERVABLES}
    out["framebuffer_sha256"] = "a" * 64
    out["audio_payload_sha256"] = "b" * 64
    return out


def test_equal_observables_pass():
    require_equal(sample(), dict(sample()))


def test_difference_is_reported():
    other = sample()
    other["checksum"] = 2
    diff = compare_observables(sample(), other)
    assert list(diff) == ["checksum"]


def test_missing_observable_fails_closed():
    value = sample()
    del value["checksum"]
    with pytest.raises(EvidenceError):
        defined_observables(value)
