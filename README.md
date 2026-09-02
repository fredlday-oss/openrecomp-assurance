# OpenRecomp Assurance

Open infrastructure for deterministic binary translation assurance, reproducible execution, provenance, and observable-equivalence validation.

## Purpose

`openrecomp-assurance` is the architecture-neutral assurance layer for binary translation systems. It does **not** replace a lifter or translator. It verifies what a translation pipeline produced and records enough evidence for another developer to reproduce, replay, compare, and challenge that result.

The released reference integration is OpenRecomp RV32I. MIPS32 Real V1 is the next bounded guest-architecture integration under validation. Additional translation systems and guest architectures should be able to integrate through the same contracts.

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

## Current MIPS32 candidate

`OPENRECOMP_ASSURANCE_MIPS32_REAL_V1` extends the same assurance discipline to the rights-safe little-endian MIPS32 Expansion V1 `logic-shift` fixture. It adds an independent MIPS32 reference oracle and requires agreement across:

- independent MIPS32 reference execution;
- normalized Core V1;
- GCC-compiled native AOT;
- Clang-compiled native AOT.

The candidate uses two byte-distinct but instruction-equivalent source records, exact replays, deterministic generated artifacts, complete GPR/HI/LO state hashing, and **5/5** specified valid semantic mutations. The claim remains fixture-bounded; it is not general MIPS32 equivalence.

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
