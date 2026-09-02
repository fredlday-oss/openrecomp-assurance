# OpenRecomp Assurance MIPS32 Real V1

- OpenRecomp commit: `53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`
- Baseline source SHA-256 distinct: **PASS**
- Baseline decoded instruction records equal: **PASS**
- Equivalent semantic observables: **PASS**
- Reference/Core/GCC/Clang agreement: **PASS**
- Replay stability: **PASS**
- Clean IR/Module/AOT repeatability: **PASS**
- Seeded semantic divergences: **5/5**
- Missing evidence fail-closed: **PASS**

**Verdict: PASS / PROVEN**

This result is bounded to the rights-safe little-endian MIPS32 Expansion V1 `logic-shift` fixture, its two instruction-equivalent source variants, exact replays, and five specified valid semantic mutations. It is not a claim of general MIPS32 binary or ISA equivalence.
