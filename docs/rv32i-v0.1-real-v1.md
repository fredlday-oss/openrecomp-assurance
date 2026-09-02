# OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1

This gate is the first real OpenRecomp integration for `openrecomp-assurance`.

## Boundaries

The integration is pinned to OpenRecomp commit:

`53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`

It uses only OpenRecomp's public-safe E07 synthetic RV32I source and host contract. No commercial game binary, firmware, key, SDK or proprietary asset is required.

The assurance claim is intentionally bounded. A PASS does not prove arbitrary RV32I equivalence or arbitrary binary-translation correctness.

## Real pipeline

Every baseline and seeded variant crosses the real OpenRecomp path:

1. compile original/synthetic C to an RV32I ELF with Clang;
2. validated ELF intake and legacy IR generation (`tools/make_ir.py`);
3. normalized IR V1 bridge;
4. IR V1 validation and Module Image V1 packaging;
5. Core API V1 execution;
6. portable C AOT generation;
7. Native AOT ABI V1 generation;
8. warning-clean native shared-module compilation;
9. Native AOT ABI validation;
10. native AOT execution through the same deterministic E07 host contract.

Core and AOT defined observables must agree for every run.

## Equivalent baseline pair

`baseline-a` and `baseline-b` are separately compiled. Each prepends a different non-allocating `.assurance_note` ELF section to the same rights-safe fixture body. The note changes source/ELF provenance and therefore the source SHA-256 without changing executable memory or defined guest behavior.

Required gate:

- source ELF SHA-256 values differ;
- all defined observables match exactly.

Defined observables are:

- `return_a0`;
- `tick_count`;
- graphics/audio/input/system call counts;
- semantic checksum;
- operation count;
- framebuffer SHA-256;
- audio-payload SHA-256.

## Five semantic seeds

The five defects are source-level behavior changes that remain valid inputs to the real pipeline. Detection means at least one defined observable differs from the equivalent baseline.

| Seed | Mutation | Intended assurance surface |
| --- | --- | --- |
| `seed-fib-depth` | `fib(7)` -> `fib(6)` | computation/result |
| `seed-state-rounds` | state loop `5` -> `4` | state + host-input behavior |
| `seed-rotate-count` | rotate/mix count `3` -> `2` | computation/result |
| `seed-graphics-x` | graphics x `1` -> `2` | framebuffer observable |
| `seed-audio-op` | sample XOR -> addition | audio observable |

`5/5` is mandatory. `4/5` is not a release PASS.

## Replay and repeatability

Both equivalent baselines are rebuilt and rerun from source. Defined observables must remain identical. Portable AOT C generated from the same normalized evidence must be byte-repeatable; the gate does not infer arbitrary compiler-binary reproducibility.

## Fail-closed evidence

The comparator deliberately receives one observation with a required field removed. Acceptance of that incomplete evidence is a hard failure.

## Outputs

`RUN_RV32I_REAL_V1.py` emits under the selected output directory:

- per-run `artifact-manifest.json`;
- per-run `observation.json`;
- Core/AOT results and intermediate hashes/artifacts;
- `seeded-divergences.json`;
- `assurance-result.json`;
- `RESULT.md`.

All assurance JSON envelopes are validated against the repository's versioned schemas.

## Run

From an environment containing a clean checkout of both repositories:

```bash
python RUN_RV32I_REAL_V1.py \
  --openrecomp ../openrecomp-e07 \
  --out evidence/rv32i-v0.1-real-v1
```

The OpenRecomp checkout must be exactly the pinned commit and have a clean tracked working tree. The hosted workflow performs that checkout automatically.

## Release rule

Do not tag `v0.1.0` until this real integration returns PASS with `5/5` seeded semantic divergence detection and the remaining `docs/release-gate-v0.1.md` items have been audited.
