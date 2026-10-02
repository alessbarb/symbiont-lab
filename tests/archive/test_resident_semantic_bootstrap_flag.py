"""Resident output must validate against the closed Observatory contracts."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent


class ResidentSemanticBootstrapFlag(unittest.TestCase):
    @pytest.mark.superseded(
        by="tests/experimental_integrity/test_canonical_organism_profile.py::test_no_launcher_deviates_without_declaring_it",
        reason="The --semantic-bootstrap launcher flag was removed: launchers cannot deviate from the canonical profile (ADR-0062).",
    )
    def test_semantic_bootstrap_flag_is_accepted_and_does_not_break_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            observatory_dir = Path(tmp) / "observatory-state"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "symbiont_lab.cli.observed_resident",
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
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
