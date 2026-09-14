"""Roadmap safety finding A09: the resident stream's actual output must
validate against the published, closed (`additionalProperties: false`)
snapshot schema — not just be checked for the presence of certain keys."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def _validate(value, schema, path="$"):
    """A small, dependency-free structural validator covering the subset of
    JSON Schema this project's own schemas actually use: type,
    additionalProperties, required, properties, items, enum, const,
    minimum/maximum, minItems/maxItems. Raises AssertionError with the
    failing path on the first violation."""
    if "const" in schema:
        assert value == schema["const"], f"{path}: expected const {schema['const']!r}, got {value!r}"
        return

    schema_type = schema.get("type")
    if schema_type is not None:
        types = schema_type if isinstance(schema_type, list) else [schema_type]
        type_map = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float), "null": type(None)}
        ok = False
        for candidate in types:
            py_type = type_map[candidate]
            if candidate == "integer":
                ok = ok or (isinstance(value, int) and not isinstance(value, bool))
            elif candidate == "number":
                ok = ok or (isinstance(value, (int, float)) and not isinstance(value, bool))
            else:
                ok = ok or isinstance(value, py_type)
        assert ok, f"{path}: expected type {schema_type!r}, got {type(value).__name__} ({value!r})"

    if "enum" in schema:
        assert value in schema["enum"], f"{path}: {value!r} not in enum {schema['enum']!r}"

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            assert value >= schema["minimum"], f"{path}: {value} < minimum {schema['minimum']}"
        if "maximum" in schema:
            assert value <= schema["maximum"], f"{path}: {value} > maximum {schema['maximum']}"

    if isinstance(value, str) and "maxLength" in schema:
        assert len(value) <= schema["maxLength"], f"{path}: length {len(value)} exceeds maxLength {schema['maxLength']}"

    if isinstance(value, dict):
        for key in schema.get("required", []):
            assert key in value, f"{path}: missing required property {key!r}"
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unexpected = set(value) - set(properties)
            assert not unexpected, f"{path}: unexpected propert{'y' if len(unexpected) == 1 else 'ies'} {sorted(unexpected)}"
        for key, subvalue in value.items():
            if key in properties:
                _validate(subvalue, properties[key], f"{path}.{key}")

    if isinstance(value, list):
        if "maxItems" in schema:
            assert len(value) <= schema["maxItems"], f"{path}: {len(value)} items exceeds maxItems {schema['maxItems']}"
        if "minItems" in schema:
            assert len(value) >= schema["minItems"], f"{path}: {len(value)} items is fewer than minItems {schema['minItems']}"
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]")


class ResidentContractTests(unittest.TestCase):
    def test_a_real_resident_tick_validates_against_the_published_schema(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            result = subprocess.run(
                [
                    sys.executable, "resident.py",
                    "--state-file", str(state_file),
                    "--max-ticks", "1",
                    "--interval", "0.01",
                    "--checkpoint-every", "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, msg=f"expected exactly one envelope, got: {result.stdout!r}")

        envelope = json.loads(lines[0])
        self.assertEqual(envelope["type"], "symbiont-observatory-snapshot")
        snapshot = envelope["snapshot"]

        # These are exactly the fields A09 found undeclared in the schema.
        organism = snapshot["organism"]
        self.assertIn("sensory_development", organism)
        self.assertIn("sensory_relations", organism)
        self.assertIn("sampling", organism)

        _validate(snapshot, schema)


if __name__ == "__main__":
    unittest.main()
