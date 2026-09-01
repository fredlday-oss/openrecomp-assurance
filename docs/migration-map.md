# Migration Map from OpenRecomp

## Bring across / generalise

- public-safe RV32I synthetic fixture methodology;
- artifact hashing and provenance capture;
- deterministic observation capture;
- replay stability checks;
- clean baseline repeatability checks;
- seeded semantic divergence framework;
- PROVEN / BOUNDED / CANDIDATE evidence vocabulary;
- schema validation and fail-closed behaviour.

## Keep in the main OpenRecomp repo

- executable lifting semantics;
- guest ISA implementation;
- translation/code-generation logic;
- runtime implementation that is intrinsic to translated execution;
- project-specific game/platform research;
- proprietary or rights-sensitive evidence.

## Do not copy blindly

The earlier RV32I assurance POC detected only 3/5 seeded semantic divergences. Treat that as a regression target, not an accepted baseline. Diagnose each escaped seed, strengthen observations/comparison rules, and require 5/5 before v0.1.
