# OpenRecomp Assurance MIPS32 ELF Real V1

- OpenRecomp candidate commit: `225a3ed250e4d700cb9aaca1213ce584f9b00fe7`
- Byte-distinct equivalent ELF baselines: **PASS**
- Independently verified semantic `.text` equal: **PASS**
- Equivalent semantic observables: **PASS**
- Reference/Core/GCC/Clang agreement: **PASS**
- Exact ELF replay stability: **PASS**
- IR/Module/AOT repeatability: **PASS**
- Seeded semantic divergences: **5/5**
- Wrong-machine fail-closed: **PASS**
- Missing-observation fail-closed: **PASS**

**Verdict: PASS / PROVEN at the explicitly bounded candidate scope.**

This retained summary is not a substitute for the full generated CI evidence bundle. Final promotion requires OpenRecomp PR #25 to be human-merged, its real ELF gate to reproduce on the resulting OpenRecomp `main`, then the assurance pin to be updated to that merged commit and the complete assurance matrix rerun.
