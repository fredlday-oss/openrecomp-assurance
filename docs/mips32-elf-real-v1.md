# OpenRecomp Assurance MIPS32 ELF Real V1

## Purpose

`OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1` extends the proven bounded MIPS32 assurance method across a real ELF32 executable-ingestion boundary.

It is intentionally narrower than “MIPS32 ELF support.” The proof fixture is rights-safe, little-endian, statically linked, text-only and uses the already bounded MIPS32 Expansion V1 instruction semantics.

The merged assurance workflow pins merged OpenRecomp `main` commit `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e`. The assurance milestone is merged at `f8c1aa32c57ad2fca64b6e011ab98f21e963047d` and reproduced all required gates on that exact `main` commit.

## Independent ELF evidence

The assurance runner does not trust OpenRecomp's ELF parser as the sole source of container facts. It independently parses:

- ELF magic/class/data/version;
- `ET_EXEC` and `EM_MIPS`;
- section table bounds;
- `.text` location/flags/bytes;
- static symbol table function identity/address/size;
- ELF entry point;
- non-allocating `.assurance-note` content.

For the bounded fixture, `logic_shift_main` must begin at `.text` address `0x1000`, and its `STT_FUNC` size must match the exact intended semantic instruction image. GNU linker alignment bytes after the function are allowed only when fewer than 16 bytes and all zero.

## Equivalent baseline pair

Baseline A and baseline B are assembled and linked from identical instruction records. After linking, GNU MIPS `objcopy` adds a different non-allocating `.assurance-note` to each ELF.

The gate requires:

- full ELF SHA-256 values differ;
- independently parsed semantic `.text` bytes are exactly equal;
- note sections are non-allocating and contain the expected distinct provenance markers;
- reference/Core/GCC/Clang semantic observables are exactly equal.

This tests that irrelevant container-level provenance changes do not alter guest semantics while still preserving the distinct source artifact hashes through OpenRecomp provenance.

## Replay requirement

Each baseline is rebuilt independently from the same assembly and note marker. V1 requires:

- exact ELF byte repeatability;
- exact semantic observable repeatability;
- repeatable normalized IR, Module Image, portable C AOT and Native AOT ABI source for that exact ELF.

If GNU linking or section injection is nondeterministic on the hosted toolchain, the gate fails rather than silently weakening the replay claim.

## Execution paths

Every baseline, replay and seeded mutation runs through:

1. independent assurance ELF parsing;
2. OpenRecomp bounded MIPS32 ELF ingestion;
3. MIPS32 Expansion V1 normalized IR;
4. independent OpenRecomp MIPS32 reference interpreter;
5. Core V1;
6. portable C AOT + Native AOT ABI compiled with GCC;
7. the same generated AOT/ABI source compiled with Clang.

The gate requires reference = Core = GCC AOT = Clang AOT on the defined semantic observables for every variant.

## ELF provenance

For each variant, the independent full-ELF SHA-256 must match all OpenRecomp provenance surfaces:

- ELF metadata;
- normalized IR source hash;
- frontend report;
- Module Image IR/provenance records;
- independent reference result;
- Core result;
- GCC AOT result;
- Clang AOT result.

The normalized source adapter must be exactly:

```text
openrecomp.mips32-elf-expansion-v1
```

## Five semantic seeds

The five one-instruction mutations are the already proven MIPS32 Real V1 mutations, rebuilt as complete ELF executables:

1. `addiu` immediate `0x1234 -> 0x1235`;
2. `ori` immediate `0x00f0 -> 0x00f1`;
3. `sll` shift amount `4 -> 3`;
4. `andi` mask `0x00ff -> 0x00f0`;
5. final `addu -> subu`.

A seed counts only when:

- the independent ELF parser confirms the intended linked semantic bytes;
- OpenRecomp accepts the bounded ELF;
- reference/Core/GCC/Clang agree on the seeded semantics;
- at least one defined semantic observable differs from the baseline.

The hard gate is **5/5**.

## Negative gate

V1 also tampers a proven baseline ELF's `e_machine` from `EM_MIPS` to `EM_RISCV` and requires both the independent assurance parser and OpenRecomp bounded ELF frontend to reject it.

Missing semantic observation evidence must also fail closed.

## Bounded claim

A PASS proves only that, for this rights-safe little-endian ELF32 `ET_EXEC` / `EM_MIPS` fixture, two byte-distinct container variants with identical independently verified semantic `.text`, their exact rebuild/replays, and five specified valid semantic mutations, the bounded OpenRecomp ELF ingestion path preserves artifact provenance and agrees with independent reference/Core/GCC/Clang execution while detecting all five mutations.

It does **not** prove:

- arbitrary MIPS32 ELF executables;
- dynamic linking or relocations;
- general `.data`, `.rodata`, `.bss`, TLS or loader semantics;
- arbitrary startup/ABI conventions;
- big-endian ELF;
- full MIPS32 ISA coverage;
- `div` / `divu` outside an architecture-neutral normalized semantic contract;
- proprietary binary compatibility.

## Merged-main evidence

- Assurance `main`: `f8c1aa32c57ad2fca64b6e011ab98f21e963047d`
- OpenRecomp pin: `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e`
- Workflow run: `33670612738`
- Artifact ID: `9862381416`
- Artifact SHA-256: `f9baf9f0aa1929320b0a3ddb23560f2779ebd42236e64a2bd9c6d7750fe15687`

## Required markers

```text
OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1_SEEDS=5/5
OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1=PASS
```
