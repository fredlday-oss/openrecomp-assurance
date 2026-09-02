# OpenRecomp Assurance MIPS32 ELF Real V1

- Assurance merged `main`: `f8c1aa32c57ad2fca64b6e011ab98f21e963047d`
- OpenRecomp merged `main` pin: `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e`
- Byte-distinct equivalent ELF baselines: **PASS**
- Independently verified semantic `.text` equal: **PASS**
- Equivalent semantic observables: **PASS**
- Reference/Core/GCC/Clang agreement: **PASS**
- Exact ELF replay stability: **PASS**
- IR/Module/AOT repeatability: **PASS**
- Seeded semantic divergences: **5/5**
- Wrong-machine fail-closed: **PASS**
- Missing-observation fail-closed: **PASS**
- Merged-main workflow run: `33670612738`
- Merged-main evidence artifact: `9862381416`
- Merged-main artifact SHA-256: `f9baf9f0aa1929320b0a3ddb23560f2779ebd42236e64a2bd9c6d7750fe15687`

**Verdict: PASS / PROVEN at the explicitly bounded merged-main scope.**

This retained summary is not a substitute for the full generated CI evidence bundle. It records the final merged-main promotion state used by the v0.2 release candidate.
