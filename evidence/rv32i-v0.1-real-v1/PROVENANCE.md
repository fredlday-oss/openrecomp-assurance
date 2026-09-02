# RV32I V0.1 Real V1 evidence provenance

This directory is a compact durable snapshot of the successful hosted evidence for `OPENRECOMP_ASSURANCE_RV32I_V0_1_REAL_V1`. The full generated bundle is intentionally not tracked because it is reproducible from the pinned source and contains 147 generated files.

## Source identity

- Assurance PR: `fredlday-oss/openrecomp-assurance#1`
- Assurance source head: `e4dc8348437cd12652271d7e48f2a9612c146b20`
- Pinned OpenRecomp commit: `53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`
- Hosted workflow run: `33647699060`
- Hosted job: `100306527281`
- Full evidence artifact ID: `9853501485`
- Full evidence artifact SHA-256: `9ef3db884aedec213c6f82cff5c6f7c83ebe69f42467e2b9aa6e43a42c328236`
- Full evidence file count: `147`

## Equivalent baseline evidence

- `baseline-a` ELF SHA-256: `e7222a209e540138842464b26a882479cb472a8fbbc9ecee5036b6428046e7c0`
- `baseline-b` ELF SHA-256: `f660f004079ed85ab6f0f708a8b59af1f71673f5d7423968acd77eb3b3c1b42c`
- Both baseline and replay observations agree on all ten defined observables:
  - `return_a0=48`
  - `tick_count=1`
  - `graphics_calls=1`
  - `audio_calls=1`
  - `input_calls=5`
  - `system_calls=1`
  - `checksum=122010428`
  - `operations=3866`
  - framebuffer SHA-256 `7f699a0e27f7b42dabc5f4c88d8efcab37d24b05fefb68c31d005e81caefbfe3`
  - audio-payload SHA-256 `9c6ff3c02eed3c7ee31a136812214774b069932abc9ca762c1c8691142ecb730`

The full hosted bundle contains nine `artifact-manifest.json` files and nine `observation.json` files: two baselines, two replays and five seeded variants. The runner validates those envelopes against the versioned schemas before returning PASS.

## Seed result

The hosted job emitted:

```text
OPENRECOMP_ASSURANCE_RV32I_REAL_V1_SEEDS=5/5
OPENRECOMP_ASSURANCE_RV32I_REAL_V1=PASS
```

The exact per-seed observable differences are preserved in `seeded-divergences.json`.

## Scope

`PROVEN` applies only to the bounded claim in `assurance-result.json`. It does not establish arbitrary RV32I binary equivalence, arbitrary compiler correctness or general cross-architecture assurance.
