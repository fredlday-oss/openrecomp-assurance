# MIPS32 ELF Real V1 Provenance

## Final merged-main validation

`OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1` is merged to assurance `main` and pinned to the merged OpenRecomp MIPS32 ELF ingestion implementation.

- Assurance repository: `fredlday-oss/openrecomp-assurance`
- Assurance merged `main`: `f8c1aa32c57ad2fca64b6e011ab98f21e963047d`
- Assurance PR: `#3` — `assurance: add real MIPS32 ELF ingestion V1 gate`
- OpenRecomp repository: `fredlday-oss/openrecomp-e07`
- OpenRecomp merged `main` pin: `fa9f9b75aa421728de7f0ff1a0d068ef6f40201e`
- OpenRecomp PR: `#25` — bounded MIPS32 ELF ingestion V1
- Assurance workflow: `mips32-elf-real-assurance-v1`
- Merged-main workflow run: `33670612738`
- Evidence artifact ID: `9862381416`
- Evidence artifact SHA-256: `f9baf9f0aa1929320b0a3ddb23560f2779ebd42236e64a2bd9c6d7750fe15687`
- Evidence artifact size: `283876` bytes
- Hosted result: `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1_SEEDS=5/5`
- Hosted verdict: `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1=PASS`

The merged-main workflow re-ran the real GNU-linked ELF matrix against the exact merged OpenRecomp pin and uploaded fresh machine evidence. The bundle is generated evidence and is intentionally not committed wholesale because it contains linked ELF and native build artifacts. The repository retains compact machine-result/provenance summaries while the complete bundle remains reproducible through the hosted workflow.

## Historical candidate validation

Before upstream and assurance merge, the first successful hosted candidate run was:

- Assurance candidate head: `c75d9f5af430e1c95472d1b2f4dd14bb384db9ba`
- OpenRecomp candidate commit: `225a3ed250e4d700cb9aaca1213ce584f9b00fe7`
- Assurance workflow run: `33662599263`
- Evidence artifact ID: `9859297566`
- Evidence artifact SHA-256: `20b96121741420cabc8714ed6ac71a28690e753024c5b23d4b358a279fee9c42`
- Full generated bundle file count: `256`
- Hosted result: `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1_SEEDS=5/5`
- Hosted verdict: `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1=PASS`

This historical candidate record is retained to preserve the validation trail. Final promotion is based on the merged-main validation above, not on the candidate commit.

## Claim boundary

`PROVEN` applies only to the bounded rights-safe little-endian, text-only ELF32 `ET_EXEC` / `EM_MIPS` assurance scope described in `docs/mips32-elf-real-v1.md`. It does not imply arbitrary MIPS32 ELF executables, dynamic linking, relocations, general data/BSS/TLS loader semantics, arbitrary startup/ABI conventions, big-endian ELF, full MIPS32 ISA coverage, or proprietary binary compatibility.
