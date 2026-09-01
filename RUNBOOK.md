# Operator Runbook

## Local bootstrap

```bash
python -m pip install jsonschema pytest
python -m py_compile tools/validate_json.py
pytest -q
```

At bootstrap time there may be no Python tests yet; the implementation agent should add them before claiming the CI gate is complete.

## Recommended implementation sequence

1. Add sample valid/invalid JSON instances and schema tests.
2. Implement content hashing utility.
3. Implement manifest builder.
4. Implement observation writer.
5. Implement comparator with explicit observable declarations.
6. Implement replay command.
7. Implement OpenRecomp adapter.
8. Reproduce old RV32I baseline.
9. Port seeded divergences and reach 5/5.
10. Add clean-machine reproduction script.
