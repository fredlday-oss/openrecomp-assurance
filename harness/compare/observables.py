from __future__ import annotations

DEFINED_OBSERVABLES = (
    "return_a0",
    "tick_count",
    "graphics_calls",
    "audio_calls",
    "input_calls",
    "system_calls",
    "checksum",
    "operations",
    "framebuffer_sha256",
    "audio_payload_sha256",
)


class EvidenceError(ValueError):
    """Raised when evidence is incomplete or structurally inconsistent."""


def defined_observables(result: dict) -> dict:
    missing = [key for key in DEFINED_OBSERVABLES if key not in result]
    if missing:
        raise EvidenceError("missing defined observables: " + ", ".join(missing))
    return {key: result[key] for key in DEFINED_OBSERVABLES}


def compare_observables(expected: dict, observed: dict) -> dict:
    left = defined_observables(expected)
    right = defined_observables(observed)
    return {
        key: {"expected": left[key], "observed": right[key]}
        for key in DEFINED_OBSERVABLES
        if left[key] != right[key]
    }


def require_equal(expected: dict, observed: dict) -> None:
    differences = compare_observables(expected, observed)
    if differences:
        formatted = ", ".join(
            f"{key}={value['expected']!r}->{value['observed']!r}"
            for key, value in differences.items()
        )
        raise EvidenceError("observable mismatch: " + formatted)
