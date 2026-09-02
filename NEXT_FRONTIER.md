# Next Frontier

`OPENRECOMP_ASSURANCE_V0_2_RELEASE_CANDIDATE`

The MIPS32 ELF assurance milestone is merged and promoted. The release candidate is based on assurance `main` commit:

```text
f8c1aa32c57ad2fca64b6e011ab98f21e963047d
```

and pins merged OpenRecomp `main` commit:

```text
fa9f9b75aa421728de7f0ff1a0d068ef6f40201e
```

## Proven bounded scope on merged `main`

- RV32I real assurance V1: **PASS / PROVEN_BOUNDED**;
- MIPS32 real assurance V1: **PASS / PROVEN_BOUNDED**;
- MIPS32 real ELF ingestion assurance V1: **PASS / PROVEN_BOUNDED**;
- all three real gates reproduce on merged assurance `main`;
- `schema-and-tests` also reproduces on merged assurance `main`;
- `Protect main` requires all four stable contexts with strict required-status-check policy enabled.

## v0.2.0 promotion sequence

1. Merge the release-prep PR only if its exact head passes all four protected contexts.
2. Verify all four contexts reproduce on the resulting assurance `main` commit.
3. Confirm the release tag `v0.2.0` does not already exist.
4. Create `v0.2.0` on that exact post-merge assurance `main` commit as a separate explicit release action.
5. Preserve the bounded claim language from `docs/release-gate-v0.2.md` and `docs/release-notes-v0.2.0.md`.

Do not claim arbitrary RV32I equivalence, arbitrary MIPS32 equivalence, arbitrary MIPS32 ELF loading, dynamic linking, relocation/data-section semantics, big-endian ELF, or full ISA coverage from v0.2.0.

## Engineering frontier after v0.2.0

`OPENRECOMP_ASSURANCE_MIPS32_ELF_STATIC_MEMORY_V1`

The next technical milestone should extend the currently text-only MIPS32 ELF proof to a bounded static-memory executable with `.rodata`, initialized `.data`, zero-initialized `.bss`, deterministic loader layout, guest loads/stores, independent memory-layout evidence, replay stability, and seeded loader/semantic divergence tests.
