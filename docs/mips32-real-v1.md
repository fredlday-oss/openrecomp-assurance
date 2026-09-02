# OpenRecomp Assurance MIPS32 Real V1

## Purpose

`OPENRECOMP_ASSURANCE_MIPS32_REAL_V1` extends the assurance method beyond the released RV32I gate without claiming general MIPS32 coverage.

The gate uses OpenRecomp's rights-safe `mips32-expansion-v1` `logic-shift` fixture and the independent MIPS32 reference interpreter already present in `openrecomp-e07`.

OpenRecomp is pinned to:

`53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`

## Execution paths

Every baseline, replay and seeded mutation is executed through all of the following paths:

1. MIPS32 expansion V1 frontend -> normalized IR V1 -> Module Image V1.
2. Independent MIPS32 reference interpreter.
3. OpenRecomp Core V1 reference executor.
4. Portable C AOT + Native AOT ABI V1 compiled with GCC.
5. The same generated AOT/ABI C compiled independently with Clang.

The gate fails if the reference, Core, GCC AOT and Clang AOT semantic observables disagree.

## Equivalent baseline pair

Two source files are created from the same canonical instruction records. They differ only by a comment-only assurance marker, which the MIPS32 fixture parser ignores.

The gate requires:

- source bytes / SHA-256 values are different;
- decoded `(address, instruction-word)` records are exactly equal;
- defined semantic observables are exactly equal;
- exact-source replay reproduces the same semantic observables;
- normalized IR, Module Image, portable C AOT and Native AOT ABI source are byte-repeatable for each replay.

## Defined semantic observables

The architecture-neutral observation schema remains unchanged. MIPS32 Real V1 stores scalar values:

- `architecture`
- `return_v0`
- `memory_word`
- `memory_bytes_hex`
- `checksum`
- `state_sha256`

`state_sha256` is the SHA-256 of the canonical JSON representation of the complete MIPS32 architectural state emitted by the reference path: GPR r1-r31 plus HI and LO. Core/AOT complete states must hash to the same value.

Operation counts are not part of the cross-reference semantic observation because the independent reference counts guest instructions while Core/AOT count normalized operations. Core, GCC AOT and Clang AOT operation counts must nevertheless agree exactly.

## Seeded semantic divergences

V1 requires 5/5 detection. Each seed changes exactly one valid instruction record:

1. `seed-addiu-immediate` — `addiu` immediate `0x1234 -> 0x1235`.
2. `seed-ori-immediate` — `ori` immediate `0x00f0 -> 0x00f1`.
3. `seed-shift-amount` — valid `sll` shift amount `4 -> 3`.
4. `seed-andi-mask` — `andi` mask `0x00ff -> 0x00fe`.
5. `seed-final-arithmetic` — final valid `addu -> subu`.

A seed counts as detected only when at least one defined semantic observable differs from baseline. The runner separately requires reference/Core/GCC/Clang agreement for the seeded result before the seed can contribute to a successful gate.

## Fail-closed conditions

The gate fails on any of the following:

- wrong or dirty OpenRecomp checkout;
- malformed or empty MIPS32 source records;
- non-equivalent decoded baseline records;
- missing semantic evidence;
- source provenance mismatch between frontend/reference/Core/AOT paths;
- incomplete normalized MIPS32 state slots;
- unexpected host-call requirements or host/function side effects;
- frontend/reference delay-slot disagreement;
- nondeterministic frontend, Module Image, AOT C or ABI C generation;
- reference/Core/GCC/Clang semantic mismatch;
- Core/GCC/Clang operation-count mismatch;
- fewer than 5/5 detected seeded semantic divergences;
- schema validation failure.

## Bounded claim

A successful V1 proves only that, for this rights-safe little-endian MIPS32 Expansion V1 fixture, its two instruction-equivalent source variants, exact replays and five specified valid semantic mutations, the independent reference path and the normalized Core/GCC/Clang AOT paths agree on the defined semantics and detect all five mutations.

It does **not** prove:

- arbitrary MIPS32 binaries;
- arbitrary ELF/executable ingestion;
- big-endian assurance;
- full MIPS32 ISA coverage;
- `div` / `divu` semantics outside the frozen normalized IR contract;
- general cross-architecture equivalence.

Those require separate evidence gates.

## Required terminal markers

```text
OPENRECOMP_ASSURANCE_MIPS32_REAL_V1_SEEDS=5/5
OPENRECOMP_ASSURANCE_MIPS32_REAL_V1=PASS
```

Until hosted CI produces those markers on the exact PR head, the milestone remains **CANDIDATE**.
