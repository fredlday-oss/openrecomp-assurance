# v0.1 Release Gate

All boxes are mandatory unless explicitly marked deferred in a reviewed issue.

- [ ] Apache-2.0 or other approved FOSS licence committed.
- [ ] Public-safe RV32I fixtures only.
- [ ] Schema versions pinned and validated fail-closed.
- [ ] Two independently built equivalent RV32I source artifacts have distinct SHA-256 hashes.
- [ ] Both pass real OpenRecomp lift/translation.
- [ ] Provenance manifests complete.
- [ ] Defined observable outputs match for the equivalent pair.
- [ ] Replay stability passes.
- [ ] Clean baseline artifact repeatability passes where claimed.
- [ ] Seeded semantic divergence detection is **5/5**.
- [ ] At least one malformed/missing evidence case fails closed.
- [ ] CI runs schema validation and unit tests on every PR.
- [ ] A clean-machine reproduction procedure is documented.
- [ ] `assurance-result.json` includes a bounded claim and classification.
- [ ] No proprietary game binaries/assets/firmware/keys/SDK material in repo or release artifacts.

## Tagging rule

Do not tag `v0.1.0` if seeded divergence detection is below 5/5. Use a pre-release tag only if the limitation is explicit and machine-visible.
