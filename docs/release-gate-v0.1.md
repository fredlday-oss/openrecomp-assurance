# v0.1 Release Gate

All boxes are mandatory. The checks below were audited against `OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1`; completing the checklist does **not** by itself authorize a merge or tag. The exact candidate head must have green PR CI, then the merged `main` commit must pass the same gates before `v0.1.0` is considered.

## Candidate checklist

- [x] Apache-2.0 or other approved FOSS licence committed. — `LICENSE` is Apache-2.0.
- [x] Public-safe RV32I fixtures only. — the real gate consumes OpenRecomp's synthetic E07 fixture; `fixtures/rv32i/` contains no proprietary binary material.
- [x] Schema versions pinned and validated fail-closed. — all three JSON schemas pin `schema_version: 0.1`; `tests/test_schema_contracts.py` exercises valid, wrong-version and missing-required-field cases.
- [x] Two independently built equivalent RV32I source artifacts have distinct SHA-256 hashes. — baseline ELF hashes are recorded in `evidence/rv32i-v0.1-real-v1/PROVENANCE.md`.
- [x] Both pass real OpenRecomp lift/translation. — each variant crosses ELF intake, legacy IR, IR V1, Module Image V1, Core API V1, portable C AOT and Native AOT ABI V1 at the pinned OpenRecomp commit.
- [x] Provenance manifests complete. — the hosted evidence contains nine validated `artifact-manifest.json` files, one for each baseline/replay/seed run.
- [x] Defined observable outputs match for the equivalent pair. — all ten declared observables match exactly for baseline A/B and their replays.
- [x] Replay stability passes. — `replay_stability: PASS` in `assurance-result.json`.
- [x] Clean baseline artifact repeatability passes where claimed. — `clean_artifact_repeatability: PASS`; same normalized input regenerates byte-identical AOT/Native-ABI source where claimed.
- [x] Seeded semantic divergence detection is **5/5**. — `seeded-divergences.json` records a defined-observable difference for every seed.
- [x] At least one malformed/missing evidence case fails closed. — the runner removes required `checksum` evidence and requires comparator rejection; schema negative tests also reject missing required fields.
- [x] CI runs schema validation and unit tests on every PR. — `.github/workflows/ci.yml` runs schema syntax checks, public safety and pytest; `.github/workflows/rv32i-real-v1.yml` executes the real integration.
- [x] A clean-machine reproduction procedure is documented. — see `RUNBOOK.md` and `docs/rv32i-v0.1-real-v1.md`.
- [x] `assurance-result.json` includes a bounded claim and classification. — durable snapshot records `verdict: PASS`, `classification: PROVEN` and the exact bounded claim.
- [x] No proprietary game binaries/assets/firmware/keys/SDK material in repo or release artifacts. — only rights-safe synthetic source is used; `tools/public_safety_scan.py` rejects tracked binary/archive/key classes and suspicious dump/key names.

## Audited hosted evidence

- Assurance source head that produced the durable result: `e4dc8348437cd12652271d7e48f2a9612c146b20`
- Pinned OpenRecomp: `53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`
- Workflow run: `33647699060`
- Job: `100306527281`
- Full evidence artifact: `9853501485`
- Artifact SHA-256: `9ef3db884aedec213c6f82cff5c6f7c83ebe69f42467e2b9aa6e43a42c328236`
- Full artifact file count: `147`

## Tagging rule

Do not tag `v0.1.0` if seeded divergence detection is below 5/5, if any required gate is not green, or if the post-merge `main` run has not reproduced the release-candidate result. A tag is a separate explicit human release action.
