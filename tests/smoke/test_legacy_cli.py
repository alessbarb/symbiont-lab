from __future__ import annotations

import subprocess
import sys


def test_legacy_cli_sim():
    result = subprocess.run(
        [sys.executable, "-m", "symbiont_lab.compat.legacy_cli", "--hosts", "10", "--steps", "20", "--seed", "7", "--no-record"],
        capture_output=True,
        text=True,
    )
    # The module can be invoked or entry points can be tested via python -c
    res = subprocess.run(
        [sys.executable, "-c", "from symbiont_lab.compat.legacy_cli import sim_main; import sys; sys.argv=['symbiont-sim', '--hosts', '10', '--steps', '20', '--seed', '7', '--no-record']; sim_main()"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "SYMBIONT LAB — simulation complete" in res.stdout


def test_legacy_cli_budget():
    res = subprocess.run(
        [sys.executable, "-c", "from symbiont_lab.compat.legacy_cli import budget_main; import sys; sys.argv=['symbiont-budget', '--hosts', '10', '--steps', '20', '--seed', '7']; budget_main()"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "SYMBIONT LAB — equal-attention budget analysis" in res.stdout


def test_legacy_cli_causal_budget():
    res = subprocess.run(
        [sys.executable, "-c", "from symbiont_lab.compat.legacy_cli import causal_budget_main; import sys; sys.argv=['symbiont-causal-budget', '--hosts', '10', '--steps', '20', '--seed', '7', '--budget-per-1000', '15']; causal_budget_main()"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "SYMBIONT LAB — causal online attention budget" in res.stdout


def test_legacy_cli_generations():
    res = subprocess.run(
        [sys.executable, "-c", "from symbiont_lab.compat.legacy_cli import generations_main; import sys; sys.argv=['symbiont-generations', '--generations', '2', '--hosts', '8', '--steps', '20', '--seed', '7', '--threat-rate', '0']; generations_main()"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "SYMBIONT LAB — longitudinal species" in res.stdout
