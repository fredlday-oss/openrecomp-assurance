# MIPS32 ELF Static Memory Real V1

`OPENRECOMP_ASSURANCE_MIPS32_ELF_STATIC_MEMORY_V1` extends the bounded real MIPS32 ELF assurance path to static memory initialization and guest memory effects.

## Merged upstream pin

The validation branch is pinned to the merged OpenRecomp `main` commit that introduced bounded MIPS32 ELF static-memory V1:

`832ca4133ce9ef71b3d5ada45bad643a65a8fa6c`

OpenRecomp PR #26 was first rebased onto the current IR V1.1/divrem-enabled main line, passed the complete 18-workflow PR matrix, was squash-merged, and its static-memory workflow reproduced successfully on the resulting `main` commit before this assurance repin.

## Independent assurance evidence

The assurance runner does not trust OpenRecomp's ELF parser as its oracle. It independently parses ELF32 section headers, symbol tables and section bytes and verifies:

- little-endian ELF32 `ET_EXEC` / `EM_MIPS`;
- entry and `STT_FUNC` layout for `static_memory_main`;
- intended semantic `.text` bytes plus only bounded zero text padding;
- `.rodata` at `0x2000`, read-only/non-executable, with exact file-backed bytes;
- `.data` at `0x3000`, writable/non-executable, including the real GNU MIPS linker's 12 zero pad bytes in the 16-byte file-backed section;
- `.bss` as writable/non-executable `SHT_NOBITS`, four zero-filled bytes;
- no relocation sections;
- a non-allocating `.assurance-note` used to make equivalent baseline ELF containers byte-distinct.

The independent section image must agree with OpenRecomp ELF metadata and Module Image V1 memory segments.

## Execution agreement

Every baseline, replay and seed must run through:

1. the real static-memory ELF frontend;
2. normalized IR V1 validation;
3. Module Image V1 packaging and validation;
4. the independent MIPS32 reference machine initialized from the real ELF static sections;
5. Core V1;
6. portable C AOT;
7. Native AOT ABI V1;
8. GCC native AOT execution;
9. Clang native AOT execution.

The independent reference, Core, GCC AOT and Clang AOT must agree on complete bounded state and observable memory semantics.

## Equivalent baselines and replay

Baseline A and B have identical independently verified `.text`, `.rodata`, `.data` and `.bss` semantics, but different non-allocating assurance-note bytes. Therefore their full ELF SHA-256 hashes must differ while their defined observables remain identical.

Each baseline is rebuilt independently. The complete ELF container and static image must reproduce exactly. Per-variant IR, Module Image, portable C AOT and Native ABI generation is independently checked for byte repeatability within each variant; replay fixtures use distinct fixture identities and therefore do not require identity-bearing generated JSON to be byte-identical across differently named runs.

## Five seeded divergences

The gate requires **5/5** detection without relaxing the comparator:

1. change the `.rodata` word;
2. change the initialized `.data` word;
3. change the valid `addu` combining the loaded values to `subu`;
4. redirect the BSS load to the updated `.data` word;
5. move `.bss` from `0x3010` to `0x3020` and update the guest address instruction to the new loader layout.

Every seed must still pass independent ELF validation and reference = Core = GCC = Clang before it can count as detected.

## Fail-closed gates

- missing required observation evidence must fail closed;
- a tampered writable `.rodata` must be rejected by both the independent assurance parser and OpenRecomp's static-memory frontend;
- generated evidence envelopes must satisfy the repository schemas.

## Bounded classification

A PASS proves only the explicit rights-safe fixture/mutation scope above. It does **not** prove arbitrary MIPS32 ELF support, arbitrary binary equivalence, relocation or dynamic-linking semantics, TLS, GOT/PLT behavior, big-endian ELF, runtime section-permission enforcement, full MIPS32 ISA coverage or proprietary-binary compatibility.
