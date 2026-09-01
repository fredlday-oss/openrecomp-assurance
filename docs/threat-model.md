# Threat Model

OpenRecomp Assurance is designed to catch evidence and translation failures that could otherwise create false confidence.

## In scope

- stale or substituted source artifacts;
- mismatched generated artifacts;
- nondeterministic execution presented as deterministic;
- missing or mutated provenance;
- comparator bugs that ignore meaningful output changes;
- seeded semantic divergences that escape detection;
- unsupported schema versions;
- accidental architecture-specific assumptions in shared contracts;
- replay drift;
- baseline artifacts that are not reproducible when claimed.

## Out of scope for v0.1

- malicious host kernel/hypervisor;
- compromised compiler toolchain;
- formal proof of arbitrary program equivalence;
- side-channel equivalence;
- full undefined-behaviour equivalence across toolchains.
