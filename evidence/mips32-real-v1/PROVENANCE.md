# MIPS32 Real V1 Provenance

## Successful validation

- Assurance repository: `fredlday-oss/openrecomp-assurance`
- PR: `#2` — `assurance: add real MIPS32 V1 gate`
- Validated source head: `ffbe4ec76671e3c61120854710ceff4e19ed8d0f`
- OpenRecomp pin: `53d0bce144356f2b4ee7120c5f8c13cb82c4bf90`
- GitHub Actions workflow: `mips32-real-assurance-v1`
- Workflow run: `33654146696`
- Job: `mips32-real-v1` / `100328356220`
- Machine evidence artifact ID: `9856020089`
- Artifact files: `201`
- Artifact ZIP SHA-256: `a00337de4558b041db6e326f51284a3fdfb16fa42ac5b8e130e50c69be918b56`
- Terminal markers:
  - `OPENRECOMP_ASSURANCE_MIPS32_REAL_V1_SEEDS=5/5`
  - `OPENRECOMP_ASSURANCE_MIPS32_REAL_V1=PASS`

The compact files in this directory are retained from that successful machine-evidence bundle. The full generated bundle remains a reproducible GitHub Actions artifact rather than being committed to the repository.

## Negative validation retained

The first hosted attempt correctly stopped at `4/5` rather than promoting incomplete evidence:

- Workflow run: `33653531988`
- Artifact ID: `9855770726`
- Artifact ZIP SHA-256: `b1dbad61b9d11d2941601d32c0ba6ba2548083a3edf20d64194dfff7d93a993d`
- Result: `OPENRECOMP_ASSURANCE_MIPS32_REAL_V1_SEEDS=4/5` / `FAIL`

That run showed `seed-andi-mask` (`0x00ff -> 0x00fe`) was semantically neutral for the canonical `r8=0x1234` state. The gate was not weakened. The seed was corrected to the valid and observable `0x00ff -> 0x00f0` mutation, after which the same strict gate reached `5/5`.

## Claim boundary

`PROVEN` applies only to the bounded little-endian MIPS32 Expansion V1 `logic-shift` assurance scope described in `docs/mips32-real-v1.md`. It does not imply arbitrary MIPS32 binary, ISA, endianness, or executable-ingestion equivalence.
