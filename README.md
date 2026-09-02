# OpenRecomp Assurance

Open infrastructure for deterministic binary translation assurance, reproducible execution, provenance, and observable-equivalence validation.

## Purpose

`openrecomp-assurance` is the architecture-neutral assurance layer for binary translation systems. It does **not** replace a lifter or translator. It verifies what a translation pipeline produced and records enough evidence for another developer to reproduce, replay, compare, and challenge that result.

The released v0.1 reference is RV32I. Current protected `main` also contains bounded real MIPS32 assurance and bounded real MIPS32 ELF-ingestion assurance, all reproduced under independent reference/Core/native-AOT comparison gates. Additional translation systems and guest architectures should be able to integrate through the same contracts.

## Assurance pipeline

```text
source artifact(s)
      |
      v
translator/lifter adapter
      |
      +--> artifact manifest + provenance
      |
      v
translated host artifact(s)
      |
      v
controlled execution
      |
      +--> observation.json
      |
      v
replay + comparison
      |
      v
assurance-result.json
      |
      +--> PASS / FAIL / BOUNDED / CANDIDATE
```

## Released v0.1 reference

`v0.1.0` is the first bounded OpenRecomp Assurance release. It contains `OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1`, pins OpenRecomp commit `53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`, and is tagged at assurance commit `fc1030303281e0adb82bb3e45b552edf23f006db`.

The release proves only its stated RV32I E07 scope: byte-distinct equivalent inputs, exact observable agreement, replay stability, repeatable generated AOT evidence, fail-closed missing evidence, and **5/5** seeded semantic-divergence detection. Compact machine evidence is retained under `evidence/rv32i-v0.1-real-v1/`.

## Current protected main / v0.2 candidate scope

The v0.2 release candidate is based on assurance `main` commit `f8c1aa32c57ad2fca64b6e011ab98f21e963047d` and includes three bounded real assurance integrations:

### RV32I Real V1

The released RV32I E07 proof remains green and protected.

### MIPS32 Real V1

`OPENRECOMP_ASSURANCE_MIPS32_REAL_V1` applies the same assurance discipline to the rights-safe little-endian MIPS32 Expansion V1 `logic-shift` fixture. It requires agreement across:

- independent MIPS32 reference execution;
- normalized Core V1;
- GCC-compiled native AOT;
- Clang-compiled native AOT.

The gate uses two byte-distinct but instruction-equivalent inputs, exact replays, deterministic generated artifacts, complete GPR/HI/LO state hashing, and **5/5** specified valid semantic mutations. The claim remains fixture-bounded; it is not general MIPS32 equivalence.

### MIPS32 ELF Real V1

`OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1` extends that bounded method across a real GNU-linked little-endian ELF32 `ET_EXEC` / `EM_MIPS` ingestion boundary. The assurance runner independently parses the ELF container, verifies entry/function/semantic `.text` facts, preserves full-ELF provenance, requires exact rebuild/replay stability, and runs every baseline/replay/seed through reference, Core, GCC AOT and Clang AOT.

This gate pins merged OpenRecomp `main` commit `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e` and detects **5/5** full-ELF semantic mutations. It remains intentionally text-only and does not claim arbitrary ELF loading, dynamic linking, relocation/data-section semantics, big-endian ELF or full MIPS32 ISA coverage.

## Protected checks

The active `Protect main` ruleset requires these four stable contexts with strict required-status-check policy enabled:

- `schema-and-tests`
- `rv32i-real-v1`
- `mips32-real-v1`
- `mips32-elf-real-v1`

## Non-goals

- Universal proof of arbitrary binary equivalence.
- Emulation of unsupported architectures.
- Distribution of proprietary binaries, firmware, keys, SDKs, or copyrighted game assets.
- Hiding unsupported behaviour behind permissive fallbacks.
- Treating identical output from a single fixture as proof of general semantic equivalence.

## Repository layout

- `docs/` — architecture, assurance model, threat model, provenance, migration guidance.
- `schemas/` — versioned JSON contracts.
- `harness/` — runner, replay and comparison implementation seams.
- `fixtures/rv32i/` — rights-safe synthetic/reference fixtures only.
- `tests/` — baseline, seeded-divergence, schema and reproducibility gates.
- `tools/` — validation and public-safety tooling.
- `evidence/` — compact durable machine-result snapshots; full generated bundles remain reproducible CI artifacts.
- `.github/workflows/` — CI assurance gates.

## Status vocabulary

- **PROVEN** — the stated bounded claim is directly supported by reproducible machine evidence.
- **BOUNDED** — useful evidence exists, but coverage is insufficient for the broader claim.
- **CANDIDATE** — interface/design exists but required validation has not completed.
- **FAIL** — an asserted contract or gate was violated.

A result must never be promoted from `CANDIDATE` or `BOUNDED` to `PROVEN` merely because one run succeeds. Each claim must remain explicitly bounded to the evidence actually produced.

## Licence

Code and repository documentation are distributed under Apache License 2.0; see `LICENSE`.
