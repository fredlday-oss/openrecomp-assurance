# Operator Runbook

## RV32I V0.1 real assurance gate

The v0.1 candidate uses a real, pinned OpenRecomp checkout. Keep the two repositories as sibling directories and do not modify the OpenRecomp working tree during the run.

### Prerequisites

- Git
- Python 3.12 or a compatible Python 3 release
- `jsonschema` and `pytest`
- Clang with `riscv32-unknown-elf` support
- GCC for the native shared-module build

A GitHub-hosted Ubuntu runner is the reference clean-machine environment in `.github/workflows/rv32i-real-v1.yml`.

### Clean checkout

```bash
git clone https://github.com/fredlday-oss/openrecomp-assurance.git
git clone https://github.com/fredlday-oss/openrecomp-e07.git

cd openrecomp-e07
git checkout 53d0bce144356f2b4ee7120c5f8c13cb82c4bf90
test -z "$(git status --porcelain)"
cd ../openrecomp-assurance

python -m pip install jsonschema pytest
python tools/public_safety_scan.py
pytest -q
```

For PR #1 before merge, check out `rv32i/v0.1-real-v1` in the assurance repository before running the commands above.

### Run the real gate

```bash
python RUN_RV32I_REAL_V1.py \
  --openrecomp ../openrecomp-e07 \
  --out evidence/rv32i-v0.1-real-v1-run \
  --expected-openrecomp-commit 53d0bce144356f2b4ee7120c5f8c13cb82c4bf90
```

Required terminal markers:

```text
OPENRECOMP_ASSURANCE_RV32I_REAL_V1_SEEDS=5/5
OPENRECOMP_ASSURANCE_RV32I_REAL_V1=PASS
```

Any lower seed count, missing observable, dirty/wrong OpenRecomp checkout, schema error, Core/AOT disagreement or command failure is a release-gate failure.

### Expected evidence

The output directory contains per-run artifact manifests and observations plus:

- `assurance-result.json`
- `seeded-divergences.json`
- `RESULT.md`

The equivalent baseline ELFs must have different SHA-256 values while matching all defined observables. Both baselines are replayed, and same-input AOT/Native-ABI generation is checked for byte repeatability where claimed.

## Release procedure

1. Require all PR checks to pass on the exact candidate head.
2. Review `docs/release-gate-v0.1.md` and the compact durable evidence snapshot.
3. Merge only after human review.
4. Require the same `schema-and-tests` and `rv32i-real-v1` workflows to pass on the resulting `main` commit.
5. Only then consider creating `v0.1.0`; never move/rewrite an existing release tag.
