"""Resident output must validate against the closed Observatory contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from observatory.schema_validate import validate as _validate

ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent


class ResidentContractTests(unittest.TestCase):
    def test_a_real_resident_tick_validates_against_the_published_schema(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "resident.py",
                    "--state-file",
                    str(state_file),
                    "--max-ticks",
                    "1",
                    "--interval",
                    "0.01",
                    "--checkpoint-every",
                    "1",
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
        organism = snapshot["organism"]
        self.assertEqual(snapshot["schema_version"], 2)
        self.assertIn("cognition", organism)
        self.assertIn("sensory_development", organism)
        self.assertIn("sensory_relations", organism)
        self.assertIn("sampling", organism)
        _validate(snapshot, schema, schema_root=ROOT)

    def test_resident_publishes_registry_journal_and_canonical_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            observatory_dir = Path(tmp) / "observatory-state"
            result = subprocess.run(
                [
                    sys.executable,
                    "resident.py",
                    "--state-file",
                    str(state_file),
                    "--observatory-dir",
                    str(observatory_dir),
                    "--max-ticks",
                    "1",
                    "--interval",
                    "0.01",
                    "--checkpoint-every",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            registry_files = [
                path
                for path in (observatory_dir / "instances").glob("*.json")
                if not path.name.endswith(".topology.json")
            ]
            self.assertEqual(len(registry_files), 1)
            record = json.loads(registry_files[0].read_text(encoding="utf-8"))
            self.assertRegex(record["instance_id"], r"^[0-9a-f]{16}$")
            self.assertNotIn(str(state_file), json.dumps(record))

            topology_files = list((observatory_dir / "instances").glob("*.topology.json"))
            self.assertEqual(len(topology_files), 1)
            topology = json.loads(topology_files[0].read_text(encoding="utf-8"))
            self.assertEqual(topology["genome_id"], "genome_symbiont_base_v1")
            self.assertEqual(topology["topology_revision"], 0)
            self.assertEqual(topology["nodes"], [])
            self.assertEqual(topology["edges"], [])

            journal_segments = list((observatory_dir / "journal").glob("*.ndjson"))
            self.assertEqual(len(journal_segments), 1)

    def test_cognitive_first_launch_publishes_revision_zero_topology(self) -> None:
        genome_file = REPO_ROOT / "examples" / "cognition" / "genome.json"
        graph_file = REPO_ROOT / "examples" / "cognition" / "graph.json"
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            observatory_dir = Path(tmp) / "observatory-state"
            result = subprocess.run(
                [
                    sys.executable,
                    "resident.py",
                    "--state-file",
                    str(state_file),
                    "--observatory-dir",
                    str(observatory_dir),
                    "--genome-file",
                    str(genome_file),
                    "--graph-file",
                    str(graph_file),
                    "--semantic-bootstrap",
                    "--max-ticks",
                    "1",
                    "--interval",
                    "0.01",
                    "--checkpoint-every",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            topology_files = list((observatory_dir / "instances").glob("*.topology.json"))
            self.assertEqual(len(topology_files), 1)
            topology = json.loads(topology_files[0].read_text(encoding="utf-8"))
            self.assertEqual(topology["topology_revision"], 0)
            self.assertTrue(topology["nodes"])

    def test_semantic_bootstrap_flag_is_accepted_and_does_not_break_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            observatory_dir = Path(tmp) / "observatory-state"
            result = subprocess.run(
                [
                    sys.executable,
                    "resident.py",
                    "--state-file",
                    str(state_file),
                    "--observatory-dir",
                    str(observatory_dir),
                    "--semantic-bootstrap",
                    "--max-ticks",
                    "1",
                    "--interval",
                    "0.01",
                    "--checkpoint-every",
                    "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
