# OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1

Status: IN PROGRESS
Branch: `feature/rv32i-v0.1-real-v1`
Target release: `v0.1.0`

## Goal

Turn the existing RV32I assurance proof into a clean, reusable reference implementation inside `openrecomp-assurance`.

The assurance repository is not the translator. It consumes a real OpenRecomp translation result and produces independently checkable evidence about provenance, replay stability, observable agreement, reproducibility, and seeded semantic divergence detection.

## Scope

1. Use only synthetic/open RV32I fixtures.
2. Invoke a real OpenRecomp RV32I lift/translation path; mock mode is not sufficient for release.
3. Produce machine-readable artifact, observation, and assurance-result records conforming to the repository schemas.
4. Record source ELF, generated C/IR, host executable, metadata, toolchain, OpenRecomp commit, and observation hashes.
5. Run clean baseline A/B builds from intentionally different ELF artifacts with equivalent expected behavior.
6. Replay each baseline and prove stable observations.
7. Seed five semantically meaningful divergences and require all five to be detected by the assurance layer.
8. Re-run a clean baseline after seeded tests to prove no state contamination.

## Non-goals

- No proprietary game binaries, firmware, SDKs, keys, or assets.
- No MIPS32 implementation in v0.1.
- No claim of complete semantic equivalence.
- No seed-specific hard-coded detector logic.
- No release tag while any mandatory gate is incomplete.

## Required outputs

Each run must emit an `out/` evidence tree containing, at minimum:

- `result.json`
- `RESULT.md`
- `provenance/artifact-manifest.json`
- `observations/baseline_a.json`
- `observations/baseline_b.json`
- `observations/replay_a.json`
- `observations/replay_b.json`
- `divergence/seed_01.json` through `seed_05.json`
- `hashes/sha256.txt`
- `logs/` with bounded build/run transcripts

## Acceptance gate for v0.1.0

All are mandatory:

- [ ] Real OpenRecomp lift/translation invocation: PASS
- [ ] Synthetic RV32I provenance: PASS
- [ ] Baseline A/B ELF hashes differ: PASS
- [ ] Baseline observable outputs agree: PASS
- [ ] Baseline replay stability: PASS
- [ ] Clean baseline artifact repeatability: PASS
- [ ] Schema validation: PASS
- [ ] Seeded semantic divergences detected: 5/5
- [ ] No seed-specific detector special-casing: PASS
- [ ] Post-seed clean baseline: PASS
- [ ] CI reproduces the bounded assurance suite: PASS
- [ ] Limitations documented: PASS

If any gate fails, verdict MUST be `V0_1_NO_GO` and the failed evidence must remain visible.

A successful bounded run may emit `V0_1_GO`, but this means only that the RV32I reference assurance contract passed the documented tests. It is not a claim of universal binary equivalence or cross-architecture assurance.

## Divergence classes

The five seeded defects should cover distinct semantic failure classes rather than five variations of the same mutation. Preferred classes:

1. Return/register-state divergence.
2. Guest-memory write divergence.
3. Control-flow/path divergence.
4. Deterministic host-observable divergence (for example frame/audio/checksum output in the synthetic fixture).
5. Metadata/provenance or deterministic-input contract divergence that changes the effective execution claim.

Each seed must include:

- mutation identifier;
- expected affected observable;
- observed affected observable;
- detector that fired;
- reproducibility result;
- evidence hashes.

## Implementation order

### Phase A — adapter boundary

Create a narrow adapter from OpenRecomp output into the assurance harness. The adapter must expose inputs/outputs explicitly and must not reach into undocumented private state when a versioned artifact can be consumed instead.

### Phase B — baseline evidence

Port the clean RV32I A/B baseline workflow and normalize results into the versioned schemas.

### Phase C — replay and repeatability

Run repeated observations from the same source and repeated clean builds. Separate deterministic observable equality from binary byte-for-byte artifact equality where toolchain metadata makes those different claims.

### Phase D — seeded divergence suite

Implement the five semantic seeds. Fix the assurance coverage until all five are detected for principled reasons.

### Phase E — CI and independent reproduction

Make the bounded suite runnable from a fresh checkout with documented dependencies and no private local paths.

## Evidence discipline

Use the following vocabulary consistently:

- **PROVEN** — directly demonstrated by captured evidence within the stated bounded test.
- **BOUNDED** — supported only within explicitly stated conditions.
- **CANDIDATE** — design or capability not yet demonstrated end-to-end.
- **FAILED** — required evidence contradicts or does not support the claim.

The v0.1 RV32I assurance implementation must preserve failed results rather than rewriting them into a pass narrative.

## Human gate

Do not tag `v0.1.0`, merge to `main`, publish a release, or make a funding/application claim based on this work until a human reviews:

- final `RESULT.md`;
- `result.json`;
- all five seed reports;
- hashes;
- CI result;
- limitations;
- comparison with the earlier 3/5 bounded result.

## Next frontier after GO

`OPENRECOMP_ASSURANCE_ARCH_NEUTRAL_V0_2_V1`

The next phase should prove that the assurance contract is not accidentally RV32I-specific before adding a full second architecture implementation.
