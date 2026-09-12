from __future__ import annotations

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
