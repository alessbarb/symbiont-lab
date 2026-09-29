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
    return text[text.index(start): text.index(end) + len(end)]


def test_agent_contract_is_identical() -> None:
    assert _contract("AGENTS.md") == _contract("CLAUDE.md")


def test_governance_toml_is_parseable() -> None:
    for name in (
        "project-state.toml", "frozen-artifacts.toml", "active-work.toml",
        "validation-matrix.toml", "authority-grants.toml", "resource-policy.toml",
        "owner-root.toml",
        "bootstrap-exceptions.toml",
    ):
        with (GOV / name).open("rb") as handle:
            assert tomllib.load(handle)


def test_control_plane_is_l4() -> None:
    ctl = _agentctl()
    for path in (
        "AGENTS.md", "docs/governance/project-state.toml", "scripts/agentctl.py",
        "tests/governance/test_agent_governance.py", ".github/workflows/ci.yml",
        ".github/CODEOWNERS", ".pre-commit-config.yaml", ".claude/settings.json",
        ".codex/hooks.json", ".agents/rules/graphify.md", "pyproject.toml",
        "pyrightconfig.json", ".gitignore",
    ):
        assert ctl.required_authority(path, "HEAD") == "L4"


def test_completed_experiment_freezes_entire_directory() -> None:
    ctl = _agentctl()
    base = "experiments/embodiment/yoked-external-causation"
    for path in (f"{base}/experiment.toml", f"{base}/README.md", f"{base}/results.json"):
        assert ctl.required_authority(path, "HEAD") == "L4"


def test_integrity_and_protocol_surfaces_are_not_l1() -> None:
    ctl = _agentctl()
    assert ctl.required_authority("tests/experimental_integrity/test_example.py", "HEAD") == "L2"
    assert ctl.required_authority("tests/experiments/test_example.py", "HEAD") == "L3"
    assert ctl.required_authority("docs/design/example.md", "HEAD") == "L3"
    assert ctl.required_authority("research/example.md", "HEAD") == "L3"


def test_commit_exists_uses_return_code() -> None:
    ctl = _agentctl()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()
    assert ctl.commit_exists(head)
    assert not ctl.commit_exists("0" * 40)


def test_git_common_dir_exists() -> None:
    assert _agentctl().git_common_dir().exists()


def test_agentctl_verifies_repository_governance() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/agentctl.py", "verify"], cwd=ROOT,
        check=False, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_bootstrap_exceptions_are_exact() -> None:
    with (GOV / "bootstrap-exceptions.toml").open("rb") as handle:
        entries = tomllib.load(handle)["commit"]
    assert entries
    for entry in entries:
        assert entry["status"] == "accepted"
        assert len(entry["sha"]) == 40
        int(entry["sha"], 16)
        assert entry["reason"]
