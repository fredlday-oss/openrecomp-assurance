# OPENRECOMP_ASSURANCE_BOOTSTRAP_V1 — Implementation Handoff

## Mission

Bootstrap `openrecomp-assurance` as a genuinely reusable assurance repository, not a duplicate of OpenRecomp and not a grant-only shell.

## Hard rules

- Do not copy proprietary binaries/assets/firmware/keys/SDK content.
- Do not reimplement the OpenRecomp translator in this repo.
- Integrate the **real** OpenRecomp translation path for the RV32I reference test.
- Preserve machine-readable provenance and fail-closed schema validation.
- Never convert a BOUNDED/CANDIDATE result to PROVEN because one test run looks good.
- v0.1 requires **5/5** seeded semantic divergence detection.
- Every generated evidence artifact must be attributable to exact source/config/tool commits.

## Phase A — repository hygiene

1. Replace `LICENSE` placeholder with Apache-2.0 if confirmed.
2. Enable GitHub Issues, Actions and private vulnerability reporting if available.
3. Add branch protection after CI is green.
4. Add topics: `binary-translation`, `reproducible-builds`, `software-assurance`, `static-recompilation`, `provenance`, `riscv`.

## Phase B — import evidence, not implementation assumptions

Use the existing RV32I POC outputs as design evidence. Rebuild the assurance harness cleanly here rather than copying a monolithic experiment wholesale.

Extract/generalise:
- hashing/provenance capture;
- observation model;
- replay model;
- comparator;
- seeded defect/divergence runner;
- result classification.

Keep translation/lifting semantics in OpenRecomp.

## Phase C — diagnose the 3/5 divergence result

For each of the five prior seeded divergences:

1. describe the intended semantic change;
2. identify which observable should reveal it;
3. show why the old harness did or did not observe it;
4. modify the observation/comparison contract minimally;
5. add a regression test;
6. rerun all five seeds;
7. require 5/5 before v0.1.

Do not simply add seed-specific string matching or other test-only detection.

## Phase D — real RV32I reference flow

Implement one command that produces an output directory containing at minimum:

- `manifest_a.json`
- `manifest_b.json`
- `observation_a.json`
- `observation_b.json`
- replay evidence
- seeded divergence evidence
- `assurance-result.json`
- human-readable `RESULT.md`

Expected high-level gate:

```text
SOURCE_HASHES_DISTINCT=PASS
REAL_OPENRECOMP_TRANSLATION=PASS
DEFINED_OBSERVABLE_EQUIVALENCE=PASS
REPLAY_STABILITY=PASS
BASELINE_REPEATABILITY=PASS
SEEDED_DIVERGENCES=5/5
FAIL_CLOSED_NEGATIVE_TEST=PASS
VERDICT=PASS
CLASSIFICATION=PROVEN   # only for the exact bounded fixture claim
```

## Phase E — architecture-neutrality check

Before v0.2, inspect every shared schema and harness API for RV32I-specific assumptions. Guest-specific details belong under fixture/adapter namespaces.

## Human gate

Stop before:
- publishing a release;
- moving code out of another repo destructively;
- deleting old evidence;
- making a grant claim that exceeds machine evidence.

Prepare a summary showing changed files, tests, artifact hashes, divergence 5/5 evidence, limitations, and recommended next step.
