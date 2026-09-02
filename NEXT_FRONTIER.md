# Next Frontier

`OPENRECOMP_ASSURANCE_MIPS32_REAL_V1`

Current validation branch: `mips32/real-v1` into protected `main`.

Candidate success condition:

- existing `schema-and-tests` and `rv32i-real-v1` checks remain green;
- new `mips32-real-v1` hosted integration is green on the exact PR head;
- two byte-distinct but instruction-equivalent MIPS32 sources produce identical defined semantics;
- exact replays reproduce the baseline semantics and deterministic generated artifacts;
- independent MIPS32 reference = Core V1 = GCC native AOT = Clang native AOT;
- all **5/5** specified valid MIPS32 semantic mutations are detected;
- generated evidence validates against the existing assurance schemas.

Do not add `mips32-real-v1` to the protected required-check set, merge the candidate, or create a new assurance release until the hosted result is proven and reviewed.
