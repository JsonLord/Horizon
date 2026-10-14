"""Offline schema, profile, source and generated-schedule consistency checks."""

import json
from pathlib import Path

import jsonschema

from src.control.schedules import synchronize
from src.research.profiles import load_profiles
from src.research.registry import load_registry


def main():
    for instance, schema in [
        ("sources/registry.json", "schemas/source-registry.schema.json"),
        ("schedules/registry.json", "schemas/schedule-registry.schema.json"),
    ]:
        jsonschema.validate(
            json.loads(Path(instance).read_text()), json.loads(Path(schema).read_text())
        )
    for path in Path("profiles").rglob("*.json"):
        jsonschema.validate(
            json.loads(path.read_text()),
            json.loads(Path("schemas/profile.schema.json").read_text()),
        )
    load_registry()
    profiles = load_profiles()
    result = synchronize(check=True)
    print(json.dumps({**result, "profiles": len(profiles), "schemas_valid": True}))


if __name__ == "__main__":
    main()
