#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FORBIDDEN_SUFFIXES = {
    ".7z", ".apk", ".bin", ".bios", ".dll", ".dmg", ".dol", ".elf",
    ".exe", ".fw", ".img", ".ipa", ".iso", ".key", ".n64", ".p12",
    ".pem", ".pfx", ".pkg", ".rar", ".rom", ".sdk", ".so", ".v64",
    ".wad", ".xbe", ".xiso", ".z64", ".zip",
}
FORBIDDEN_NAME_FRAGMENTS = {
    "bios_dump", "firmware_dump", "game_dump", "private_key", "rom_dump", "sdk_dump",
}
MAX_TRACKED_BYTES = 2 * 1024 * 1024


def tracked_files(root: Path) -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    return [root / item.decode("utf-8") for item in raw.split(b"\0") if item]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    files = tracked_files(root)

    for path in files:
        rel = path.relative_to(root).as_posix()
        name = path.name.lower()
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            violations.append(f"forbidden tracked binary/archive/key suffix: {rel}")
        if any(fragment in name for fragment in FORBIDDEN_NAME_FRAGMENTS):
            violations.append(f"forbidden sensitive/proprietary filename pattern: {rel}")
        if path.is_file() and path.stat().st_size > MAX_TRACKED_BYTES:
            violations.append(f"tracked file exceeds {MAX_TRACKED_BYTES} bytes: {rel}")

    if violations:
        for violation in violations:
            print(f"PUBLIC_SAFETY_FAIL: {violation}", file=sys.stderr)
        return 2

    print(f"OPENRECOMP_ASSURANCE_PUBLIC_SAFETY=PASS tracked_files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
