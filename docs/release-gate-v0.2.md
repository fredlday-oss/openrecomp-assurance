# v0.2 Release Gate

All checks below are mandatory. This document prepares `v0.2.0`; it does **not** authorize a tag by itself. The release-prep PR must pass the protected checks on its exact head, then those checks must reproduce on the resulting merged `main` commit before `v0.2.0` is created.

## Release scope

`v0.2.0` may claim only these bounded integrations:

- `OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1` — **PROVEN_BOUNDED**;
- `OPENRECOMP_ASSURANCE_MIPS32_REAL_V1` — **PROVEN_BOUNDED**;
- `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1` — **PROVEN_BOUNDED**.

The MIPS32 ELF gate pins merged OpenRecomp `main` commit:

```text
fa9f9b75aa421728de7f0ff1a0d068ef6f40201e
```

The pre-release assurance baseline inspected for this package is:

```text
f8c1aa32c57ad2fca64b6e011ab98f21e963047d
```

## Mandatory checklist

- [x] Apache-2.0 licence remains committed.
- [x] Repository public-safety gate is green on merged `main`.
- [x] Schema/unit tests are green on merged `main`.
- [x] RV32I real assurance reproduces on merged `main`.
- [x] MIPS32 real assurance reproduces on merged `main`.
- [x] MIPS32 ELF real assurance reproduces on merged `main` against the merged OpenRecomp pin.
- [x] RV32I seeded semantic divergence detection remains **5/5**.
- [x] MIPS32 seeded semantic divergence detection remains **5/5**.
- [x] MIPS32 ELF seeded semantic divergence detection remains **5/5**.
- [x] Fail-closed missing/malformed evidence checks remain enabled.
- [x] MIPS32 ELF wrong-machine rejection remains enabled.
- [x] `Protect main` requires all four stable contexts with strict required-status checks.
- [x] No bypass actors are configured in the active `Protect main` ruleset.
- [x] MIPS32 ELF provenance is bound to merged OpenRecomp and assurance `main` SHAs.
- [x] Release notes explicitly preserve bounded claims and exclusions.
- [x] No proprietary binary/assets/firmware/keys/SDK material is required or added.

## Protected contexts

The active `Protect main` ruleset requires:

```text
schema-and-tests
rv32i-real-v1
mips32-real-v1
mips32-elf-real-v1
```

Strict required-status-check policy is enabled.

## Audited merged-main runs before release prep

All four runs below target assurance `main` SHA `f8c1aa32c57ad2fca64b6e011ab98f21e963047d` and completed successfully.

### Schema and tests

- Workflow: `assurance-ci`
- Required context: `schema-and-tests`
- Run: `33670612728`
- Conclusion: `success`

### RV32I real assurance

- Workflow: `rv32i-real-assurance-v1`
- Required context: `rv32i-real-v1`
- Run: `33670612791`
- Conclusion: `success`
- Artifact ID: `9862379447`
- Artifact SHA-256: `ebadb7526ca420776259149c02a86b301a55d34657446b5deeb11e32283b154a`

### MIPS32 real assurance

- Workflow: `mips32-real-assurance-v1`
- Required context: `mips32-real-v1`
- Run: `33670612885`
- Conclusion: `success`
- Artifact ID: `9862358170`
- Artifact SHA-256: `6976765b334bd101692e5407cf3dba62151ec68d8fb2d5f75f0a936b570fc2c9`

### MIPS32 ELF real assurance

- Workflow: `mips32-elf-real-assurance-v1`
- Required context: `mips32-elf-real-v1`
- Run: `33670612738`
- Conclusion: `success`
- OpenRecomp pin: `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e`
- Artifact ID: `9862381416`
- Artifact SHA-256: `f9baf9f0aa1929320b0a3ddb23560f2779ebd42236e64a2bd9c6d7750fe15687`

## Claims explicitly excluded from v0.2.0

Do not claim any of the following from this release:

- arbitrary RV32I equivalence;
- arbitrary MIPS32 equivalence;
- arbitrary MIPS32 ELF executables;
- dynamic linking;
- relocation processing;
- general `.rodata`, `.data`, `.bss` or TLS loader semantics;
- arbitrary startup/ABI conventions;
- big-endian MIPS32 ELF ingestion;
- full MIPS32 ISA coverage;
- `div` / `divu` beyond a future architecture-neutral semantic contract;
- proprietary binary compatibility.

## Final release sequence

1. Require all four protected contexts to pass on the exact release-prep PR head.
2. Merge the release-prep PR.
3. Require all four contexts to pass again on the resulting `main` SHA.
4. Verify `v0.2.0` does not already exist.
5. Create `v0.2.0` on that exact post-merge `main` SHA.
6. Publish the bounded release notes from `docs/release-notes-v0.2.0.md`.

A tag/release is a separate explicit action and must not be created from a pre-merge candidate SHA.
