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

from observatory.schema_validate import validate as _validate

ROOT = Path(__file__).parent


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
