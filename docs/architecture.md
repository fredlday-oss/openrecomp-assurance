# Architecture

## Boundary

OpenRecomp Assurance sits **after or around** a binary translation system. Translators integrate using explicit inputs and outputs rather than by embedding assurance-specific behaviour into translation semantics.

### Logical components

1. **Adapter** — invokes a translator/lifter and normalises its artifact metadata.
2. **Manifest recorder** — hashes sources, generated IR/code, host artifacts, toolchain and configuration.
3. **Controlled runner** — executes translated artifacts under defined deterministic inputs.
4. **Observation recorder** — captures agreed observables such as return state, memory digest, framebuffer digest, audio digest, trace digest, or domain-specific outputs.
5. **Replay engine** — repeats the same observation under the same declared inputs.
6. **Comparator** — evaluates explicit equivalence rules.
7. **Verdict engine** — emits PASS/FAIL and classification metadata without overstating scope.

## Architecture-neutral rule

Guest-architecture semantics belong in translator adapters or guest-specific fixture definitions. Shared assurance schemas must not encode RV32I assumptions unless explicitly namespaced.

## Fail-closed rule

Unknown schema versions, missing required hashes, missing observations, unsupported equivalence rules, or non-reproducible inputs must not silently degrade to PASS.
