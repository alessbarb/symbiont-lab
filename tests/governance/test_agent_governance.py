from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "docs" / "governance"


def _contract(path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    start = "<!-- BEGIN CANONICAL AGENT CONTRACT -->"
    end = "<!-- END CANONICAL AGENT CONTRACT -->"
    return text[text.index(start) : text.index(end) + len(end)]


def test_agent_contract_is_identical() -> None:
    assert _contract("AGENTS.md") == _contract("CLAUDE.md")


def test_governance_toml_is_parseable() -> None:
    for name in (
        "project-state.toml",
        "frozen-artifacts.toml",
        "active-work.toml",
        "validation-matrix.toml",
    ):
        with (GOV / name).open("rb") as handle:
            assert tomllib.load(handle)


def test_project_state_locks_current_direction() -> None:
    with (GOV / "project-state.toml").open("rb") as handle:
        state = tomllib.load(handle)
    assert state["current_gate"] == "visual-acquisition-d1-v2"
    assert state["programmes"]["world"]["state"] == "maintenance-only"
    assert state["programmes"]["population-expansion"]["state"] == "blocked"
    assert state["programmes"]["e8-label-invariance"]["state"] == "p0-open"


def test_agentctl_verifies_repository_governance() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/agentctl.py", "verify"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout
