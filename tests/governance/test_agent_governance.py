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
    return text[text.index(start):text.index(end) + len(end)]


def test_agent_contract_is_identical() -> None:
    assert _contract("AGENTS.md") == _contract("CLAUDE.md")


def test_governance_toml_is_parseable() -> None:
    for name in (
        "project-state.toml", "frozen-artifacts.toml", "active-work.toml",
        "validation-matrix.toml", "resource-policy.toml", "owner-root.toml",
        "bootstrap-exceptions.toml", "change-surfaces.toml", "publication-policy.toml",
    ):
        with (GOV / name).open("rb") as handle:
            assert tomllib.load(handle)


def test_control_plane_requires_external_review() -> None:
    ctl = _agentctl()
    with (GOV / "frozen-artifacts.toml").open("rb") as handle:
        artifacts = tomllib.load(handle)["artifact"]
    by_path = {item["path_glob"]: item for item in artifacts}
    for pattern in ctl.CONTROL_PLANE:
        assert by_path[pattern]["rule"] == "external-review-required"


def test_active_grant_machinery_is_absent() -> None:
    source = (ROOT / "scripts/agentctl.py").read_text(encoding="utf-8")
    for token in ("GRANT_FILE", "required_authority(", "_grant_from_base", "Authority-Grant", "owner_approved", ".agent-session.toml"):
        assert token not in source


def test_agentctl_verifies_repository_governance() -> None:
    result = subprocess.run([sys.executable, "scripts/agentctl.py", "verify"], cwd=ROOT, check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_active_run_path_is_blocked(monkeypatch) -> None:
    ctl = _agentctl()
    monkeypatch.setattr(ctl, "_active_work_at", lambda ref: [{"id": "running", "state": "RUNNING", "protected_paths": ["src/x/**"]}])
    assert ctl._path_blocked_by_active("src/x/a.py", "HEAD") == "running"
