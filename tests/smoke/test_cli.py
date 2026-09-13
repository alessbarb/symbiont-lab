from __future__ import annotations

import json
import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "simulate" in result.stdout
    assert "experiment" in result.stdout
    assert "audit" in result.stdout
    assert "archive" in result.stdout
    assert "reproduce" in result.stdout


def test_cli_audit():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "audit", "verify"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "All experimental invariants verified successfully." in result.stdout


def test_cli_simulate():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "simulate", "--hosts", "10", "--steps", "20", "--seed", "1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "=== Symbiont Simulation Result ===" in result.stdout


def test_cli_study_run_prints_its_result():
    """A study's computed result must reach the user, not just a success banner."""
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.cli.main", "study", "run", "attention.replicated", "--seeds", "1,2"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Study completed successfully." in result.stdout
    banner_index = result.stdout.index("Study completed successfully.")
    payload = json.loads(result.stdout[banner_index + len("Study completed successfully.") :])
    assert payload["seeds"] == [1, 2]
    assert "summaries" in payload
