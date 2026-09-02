# OpenRecomp Assurance v0.2.0 — Release Notes Draft

`v0.2.0` expands the first bounded RV32I assurance release with two additional independently validated MIPS32 assurance milestones while preserving the same fail-closed, reproducible evidence model.

## Included bounded proofs

### RV32I Real V1

Retains the v0.1.0 bounded RV32I E07 assurance proof:

- byte-distinct equivalent baselines;
- exact observable equivalence;
- replay stability;
- deterministic generated AOT evidence;
- fail-closed evidence handling;
- **5/5** seeded semantic-divergence detection.

### MIPS32 Real V1

Adds a bounded little-endian MIPS32 Expansion V1 `logic-shift` assurance proof with:

- two byte-distinct but instruction-equivalent inputs;
- independent MIPS32 reference execution;
- complete GPR/HI/LO semantic state coverage;
- reference = Core V1 = GCC native AOT = Clang native AOT;
- exact replay and generated-artifact repeatability;
- **5/5** valid semantic mutations detected;
- preserved negative evidence from the original 4/5 neutral-seed discovery.

### MIPS32 ELF Real V1

Adds a bounded real ELF32 executable-ingestion assurance proof, pinned to merged OpenRecomp commit `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e`:

- real GNU-linked little-endian ELF32 `ET_EXEC` / `EM_MIPS` input;
- independent assurance-side ELF parser;
- byte-distinct equivalent ELF containers with identical semantic `.text`;
- exact full-ELF rebuild/replay stability;
- full ELF SHA-256 provenance across the normalized pipeline;
- reference = Core V1 = GCC native AOT = Clang native AOT;
- **5/5** full-ELF semantic mutations detected;
- fail-closed wrong-machine and missing-observation gates;
- zero-only linker-alignment padding validated rather than silently treated as semantics.

## Governance

Protected assurance `main` requires four strict status checks:

```text
schema-and-tests
rv32i-real-v1
mips32-real-v1
mips32-elf-real-v1
```

All four reproduced successfully on the merged pre-release baseline `f8c1aa32c57ad2fca64b6e011ab98f21e963047d` before release preparation.

## Classification

The included integrations are **PROVEN only at their explicitly bounded scopes**.

This release does **not** claim:

- arbitrary RV32I or MIPS32 binary equivalence;
- arbitrary MIPS32 ELF support;
- dynamic linking or relocation processing;
- general `.rodata`, `.data`, `.bss` or TLS loader semantics;
- big-endian MIPS32 ELF ingestion;
- full MIPS32 ISA coverage;
- proprietary binary compatibility.

## Next engineering milestone

After v0.2.0, the planned frontier is `OPENRECOMP_ASSURANCE_MIPS32_ELF_STATIC_MEMORY_V1`: a bounded static-memory ELF proof covering `.rodata`, initialized `.data`, zero-initialized `.bss`, deterministic loader layout, guest loads/stores, independent memory-layout evidence, replay stability, and seeded loader/semantic divergence testing.
