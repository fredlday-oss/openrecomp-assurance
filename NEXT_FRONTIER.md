# Next Frontier

`OPENRECOMP_ASSURANCE_RV32I_V0_1_RELEASE_CANDIDATE`

Current protected-review target: PR #1 from `rv32i/v0.1-real-v1` into `main`.

Candidate success condition:

- schema/unit/public-safety CI green on the exact PR head;
- real pinned OpenRecomp RV32I assurance gate green with **5/5** seeded semantic divergences;
- `docs/release-gate-v0.1.md` evidence audit complete.

After human merge, require the same gates to pass on the resulting `main` commit. Only after that post-merge proof should `v0.1.0` be considered as a separate explicit release action.
