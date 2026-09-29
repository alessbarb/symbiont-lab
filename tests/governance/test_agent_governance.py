from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "docs" / "governance"


def _agentctl():
    spec = importlib.util.spec_from_file_location("agentctl", ROOT / "scripts" / "agentctl.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract(path: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    start = "<!-- BEGIN CANONICAL AGENT CONTRACT -->"
    end = "<!-- END CANONICAL AGENT CONTRACT -->"
    return text[text.index(start) : text.index(end) + len(end)]


def test_agent_contract_is_identical() -> None:
    assert _contract("AGENTS.md") == _contract("CLAUDE.md")


def test_constitution_is_single_invariant_source() -> None:
    constitution = (GOV / "constitution.md").read_text(encoding="utf-8")
    assert "## Architectural invariants" in constitution
    assert "## Normative architectural invariants" not in (ROOT / "AGENTS.md").read_text()
    assert "## Normative architectural invariants" not in (ROOT / "CLAUDE.md").read_text()


def test_governance_toml_is_parseable() -> None:
    for name in (
        "project-state.toml",
        "frozen-artifacts.toml",
        "active-work.toml",
        "validation-matrix.toml",
        "authority-grants.toml",
        "resource-policy.toml",
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


def test_control_plane_is_l4() -> None:
    ctl = _agentctl()
    for path in (
        "AGENTS.md",
        "docs/governance/project-state.toml",
        "scripts/agentctl.py",
        "tests/governance/test_agent_governance.py",
        ".github/workflows/ci.yml",
        ".pre-commit-config.yaml",
    ):
        assert ctl.required_authority(path, "HEAD") == "L4"


def test_completed_protocol_is_automatically_frozen() -> None:
    ctl = _agentctl()
    path = "experiments/embodiment/yoked-external-causation/experiment.toml"
    assert ctl.required_authority(path, "HEAD") == "L4"


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
