from __future__ import annotations

import hashlib
import json

MIPS32_DEFINED_OBSERVABLES = (
    "architecture",
    "return_v0",
    "memory_word",
    "memory_bytes_hex",
    "checksum",
    "state_sha256",
)


class MIPS32EvidenceError(ValueError):
    """Raised when MIPS32 semantic evidence is incomplete or inconsistent."""


def _state_sha256(state: dict) -> str:
    if not isinstance(state, dict):
        raise MIPS32EvidenceError("state must be an object")
    payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def defined_mips32_observables(result: dict) -> dict:
    required = ("architecture", "return_v0", "memory_word", "memory_bytes_hex", "checksum", "state")
    missing = [key for key in required if key not in result]
    if missing:
        raise MIPS32EvidenceError("missing defined MIPS32 evidence: " + ", ".join(missing))
    return {
        "architecture": result["architecture"],
        "return_v0": result["return_v0"],
        "memory_word": result["memory_word"],
        "memory_bytes_hex": result["memory_bytes_hex"],
        "checksum": result["checksum"],
        "state_sha256": _state_sha256(result["state"]),
    }


def compare_mips32_observables(expected: dict, observed: dict) -> dict:
    left = defined_mips32_observables(expected)
    right = defined_mips32_observables(observed)
    return {
        key: {"expected": left[key], "observed": right[key]}
        for key in MIPS32_DEFINED_OBSERVABLES
        if left[key] != right[key]
    }


def require_mips32_equal(expected: dict, observed: dict) -> None:
    differences = compare_mips32_observables(expected, observed)
    if differences:
        formatted = ", ".join(
            f"{key}={value['expected']!r}->{value['observed']!r}"
            for key, value in differences.items()
        )
        raise MIPS32EvidenceError("MIPS32 observable mismatch: " + formatted)
