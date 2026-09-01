# Provenance

Each assurance run should record immutable identifiers for:

- source artifact SHA-256;
- translator repository + commit;
- assurance repository + commit;
- configuration hash;
- generated IR/code hash;
- host executable/module hash;
- toolchain identity/version;
- fixture identity/version;
- observation artifact hash;
- timestamps only as metadata, never as semantic inputs unless explicitly declared.

Where two source artifacts are expected to differ but behave equivalently, their hashes must be distinct and the equivalence expectation must be declared in the fixture metadata.
