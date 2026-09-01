# Assurance Model

## Claim structure

Every verdict must identify:

- what artifacts were compared;
- what translator/toolchain/configuration produced them;
- what inputs were controlled;
- which observables were compared;
- which divergence tests were exercised;
- what replay/reproducibility checks completed;
- the exact bounded claim being made.

## Example bounded claim

> For fixture `rv32i-equivalent-pair-001`, under assurance contract version 0.1, both translated executions produced identical defined observables across N deterministic replays, and all required seeded semantic divergences were detected.

This does **not** imply universal equivalence of the original programs.

## Minimum v0.1 properties

- provenance completeness;
- source artifact distinction where required;
- deterministic observation inputs;
- stable replay;
- clean baseline repeatability;
- 5/5 seeded divergence detection;
- explicit bounded claim text;
- machine-readable result.
