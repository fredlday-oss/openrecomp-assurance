# MIPS32 ELF Real V1 Candidate Provenance

This compact record refers to the first successful hosted candidate run of `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1`.

- Assurance PR: #3
- Assurance candidate head: `c75d9f5af430e1c95472d1b2f4dd14bb384db9ba`
- OpenRecomp PR: #25
- OpenRecomp candidate commit: `225a3ed250e4d700cb9aaca1213ce584f9b00fe7`
- Assurance workflow run: `33662599263`
- Evidence artifact ID: `9859297566`
- Evidence artifact SHA-256: `20b96121741420cabc8714ed6ac71a28690e753024c5b23d4b358a279fee9c42`
- Full generated bundle file count: 256
- Hosted result: `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1_SEEDS=5/5`
- Hosted verdict: `OPENRECOMP_ASSURANCE_MIPS32_ELF_REAL_V1=PASS`

The bundle is generated evidence and is intentionally not committed wholesale because it contains linked ELF and native build artifacts. The repository retains only compact machine-result/provenance summaries. The complete bundle remains reproducible through the hosted workflow.

This is candidate provenance, not final merged-main provenance. Before the assurance milestone is merged/promoted, replace the OpenRecomp candidate pin with the resulting OpenRecomp `main` merge commit and rerun all assurance workflows.
