"""Roadmap safety/architecture check: Fleet must genuinely distinguish
independent resident processes, not merely render two rows from hand-typed
fixtures. This launches two real residents and verifies discovery end to
end."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from observatory.registry import read_registry

ROOT = Path(__file__).parent


def _run_resident(state_file: Path, observatory_dir: Path, display_id: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, "resident.py",
            "--state-file", str(state_file),
            "--observatory-dir", str(observatory_dir),
            "--display-id", display_id,
            "--max-ticks", "1",
            "--interval", "0.01",
            "--checkpoint-every", "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


class ObservatoryIntegrationTests(unittest.TestCase):
    def test_two_residents_register_as_two_distinct_instances_with_distinct_run_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            observatory_dir = Path(tmp) / "observatory-state"
            state_file_a = Path(tmp) / "organism-a.json"
            state_file_b = Path(tmp) / "organism-b.json"

            result_a = _run_resident(state_file_a, observatory_dir, "symbiont-a")
            result_b = _run_resident(state_file_b, observatory_dir, "symbiont-b")
            self.assertEqual(result_a.returncode, 0, msg=result_a.stderr)
            self.assertEqual(result_b.returncode, 0, msg=result_b.stderr)

            records = read_registry(observatory_dir)
            self.assertEqual(len(records), 2)
            instance_ids = {record["instance_id"] for record in records}
            run_ids = {record["run_id"] for record in records}
            self.assertEqual(len(instance_ids), 2)
            self.assertEqual(len(run_ids), 2)

    def test_restarting_the_same_state_file_keeps_instance_id_but_changes_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            observatory_dir = Path(tmp) / "observatory-state"
            state_file = Path(tmp) / "organism.json"

            first = _run_resident(state_file, observatory_dir, "symbiont-a")
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            first_records = read_registry(observatory_dir)
            self.assertEqual(len(first_records), 1)
            first_instance_id = first_records[0]["instance_id"]
            first_run_id = first_records[0]["run_id"]

            second = _run_resident(state_file, observatory_dir, "symbiont-a")
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            second_records = read_registry(observatory_dir)
            self.assertEqual(len(second_records), 1)
            self.assertEqual(second_records[0]["instance_id"], first_instance_id)
            self.assertNotEqual(second_records[0]["run_id"], first_run_id)


if __name__ == "__main__":
    unittest.main()
