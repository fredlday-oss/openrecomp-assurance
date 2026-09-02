# OpenRecomp Assurance

Open infrastructure for deterministic binary translation assurance, reproducible execution, provenance, and observable-equivalence validation.

## Purpose

`openrecomp-assurance` is the architecture-neutral assurance layer for binary translation systems. It does **not** replace a lifter or translator. It verifies what a translation pipeline produced and records enough evidence for another developer to reproduce, replay, compare, and challenge that result.

The initial reference integration is OpenRecomp RV32I. Additional translation systems and guest architectures should be able to integrate through the same contracts.

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

## v0.1 reference objective

Two independently built RV32I inputs that are expected to be semantically equivalent must:

1. have distinct source artifact hashes;
2. pass validated OpenRecomp intake and translation;
3. produce machine-readable provenance manifests;
4. execute under controlled deterministic inputs;
5. produce matching defined observables;
6. replay stably;
7. reproduce clean baseline artifacts where reproducibility is claimed;
8. detect **5/5** deliberately seeded semantic divergences;
9. emit a machine-readable assurance verdict;
10. fail closed when evidence is missing or inconsistent.

A result must never be promoted from `CANDIDATE` or `BOUNDED` to `PROVEN` merely because one run succeeds.

## Current v0.1 candidate

`OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1` is implemented on PR #1 and pins OpenRecomp commit `53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`. Hosted CI has produced a bounded `PASS / PROVEN` result with two byte-distinct equivalent RV32I ELFs, exact baseline observable agreement, replay stability, repeatable generated AOT evidence, fail-closed missing evidence and **5/5** seeded semantic divergence detection.

The compact machine result is retained under `evidence/rv32i-v0.1-real-v1/`. This is a release candidate, not a `v0.1.0` release: the PR must pass final CI, be human-reviewed/merged, and pass the same real gate on `main` before a tag is considered.

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

## First release gate

`v0.1.0` must not be tagged until `docs/release-gate-v0.1.md` is fully satisfied on the candidate and the same workflows pass after merge on `main`.

## Licence

Code and repository documentation are distributed under Apache License 2.0; see `LICENSE`.
