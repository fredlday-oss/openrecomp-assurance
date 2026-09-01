#!/usr/bin/env python3
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    raise SystemExit("Install dependency: python -m pip install jsonschema")

if len(sys.argv) != 3:
    raise SystemExit("usage: validate_json.py SCHEMA.json INSTANCE.json")

schema_path = Path(sys.argv[1])
instance_path = Path(sys.argv[2])
schema = json.loads(schema_path.read_text(encoding="utf-8"))
instance = json.loads(instance_path.read_text(encoding="utf-8"))
jsonschema.Draft202012Validator(schema).validate(instance)
print(f"PASS: {instance_path} validates against {schema_path}")
