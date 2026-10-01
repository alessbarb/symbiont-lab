from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "docs" / "governance"


def _agentctl():
    spec = importlib.util.spec_from_file_location(
        "agentctl", ROOT / "scripts" / "agentctl.py"
    )
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


def test_governance_toml_is_parseable() -> None:
    for name in (
        "project-state.toml",
        "frozen-artifacts.toml",
        "active-work.toml",
        "validation-matrix.toml",
        "resource-policy.toml",
        "owner-root.toml",
        "bootstrap-exceptions.toml",
        "change-surfaces.toml",
        "publication-policy.toml",
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
    source = (ROOT / "scripts" / "agentctl.py").read_text(encoding="utf-8")
    for token in (
        "GRANT_FILE",
        "required_authority(",
        "_grant_from_base",
        "Authority-Grant",
        "owner_approved",
        ".agent-session.toml",
    ):
        assert token not in source


def test_redundant_merge_requires_a_parent_with_identical_tree(monkeypatch) -> None:
    ctl = _agentctl()
    trees = {"merge": "tree-a", "parent-a": "tree-a", "parent-b": "tree-b"}

    def fake_git(*args: str, **kwargs) -> str:
        if args[:3] == ("show", "-s", "--format=%P"):
            return "parent-a parent-b"
        if args[:3] == ("show", "-s", "--format=%T"):
            return trees[args[3]]
        raise AssertionError(args)

    monkeypatch.setattr(ctl, "git", fake_git)
    assert ctl._is_redundant_merge_commit("merge")
    trees["merge"] = "tree-merge-resolution"
    assert not ctl._is_redundant_merge_commit("merge")


def test_ci_check_skips_redundant_merge_without_skipping_source(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    merge, ordinary = "a" * 40, "b" * 40
    audited: list[str] = []

    monkeypatch.setattr(ctl, "commit_exists", lambda _ref: True)
    monkeypatch.setattr(
        ctl,
        "git",
        lambda *args, **kwargs: f"{ordinary}\n{merge}",
    )
    monkeypatch.setattr(
        ctl,
        "git_result",
        lambda *args: type("Result", (), {"returncode": 0})(),
    )
    monkeypatch.setattr(ctl, "_publication_cutoff", lambda _head: None)
    monkeypatch.setattr(
        ctl,
        "_is_redundant_merge_commit",
        lambda commit: commit == merge,
    )
    monkeypatch.setattr(ctl, "_is_legacy_commit", lambda _commit, _cutoff: False)
    monkeypatch.setattr(
        ctl,
        "_audit_commit",
        lambda commit: audited.append(commit) or [],
    )

    assert ctl.ci_check("base", "head") == 0
    assert audited == [ordinary]
    assert "1 redundant merge commits skipped" in capsys.readouterr().out


def test_agentctl_verifies_repository_governance() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/agentctl.py", "verify"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_active_run_path_is_blocked(monkeypatch) -> None:
    ctl = _agentctl()
    monkeypatch.setattr(
        ctl,
        "_active_work_at",
        lambda ref: [
            {
                "id": "running",
                "state": "RUNNING",
                "protected_paths": ["src/x/**"],
            }
        ],
    )
    assert ctl._path_blocked_by_active("src/x/a.py", "HEAD") == "running"


def test_agent_contract_uses_context_as_single_normal_read() -> None:
    contract = _contract("AGENTS.md")
    assert "agentctl.py context" in contract
    assert "do not reread the governance corpus" in contract
    assert "Publish once" in contract


def test_context_is_compact_and_defers_classification(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    base = "a" * 40

    monkeypatch.setattr(ctl, "_trusted_origin_ref", lambda: base)
    monkeypatch.setattr(
        ctl,
        "_trusted_governance_at",
        lambda ref, name: (
            {"current_gate": "e8-label-invariance"}
            if name == "project-state.toml"
            else {"work": []}
        ),
    )

    def fake_git(*args: str, **kwargs) -> str:
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return "feature/example"
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        raise AssertionError(args)

    monkeypatch.setattr(ctl, "git", fake_git)
    monkeypatch.setattr(ctl, "changed_paths", lambda staged_only=False: [])

    assert ctl.context() == 0
    output = capsys.readouterr().out.splitlines()
    assert len(output) <= 10
    assert "worktree: clean (0 changed paths)" in output
    assert "classification: deferred-to-publish" in output
    assert any(line.startswith("next: ") for line in output)


def test_context_json_reports_running_conflicts(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    base = "a" * 40

    monkeypatch.setattr(ctl, "_trusted_origin_ref", lambda: base)
    monkeypatch.setattr(
        ctl,
        "_trusted_governance_at",
        lambda ref, name: (
            {"current_gate": "gate"}
            if name == "project-state.toml"
            else {
                "work": [
                    {
                        "id": "study",
                        "state": "RUNNING",
                        "protected_paths": ["src/protected/**"],
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        ctl,
        "git",
        lambda *args, **kwargs: (
            "feature/example"
            if args == ("rev-parse", "--abbrev-ref", "HEAD")
            else "b" * 40
        ),
    )
    monkeypatch.setattr(
        ctl,
        "changed_paths",
        lambda staged_only=False: ["src/protected/a.py"],
    )

    assert ctl.context(as_json=True) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["running_work"] == ["study"]
    assert payload["protected_conflicts"] == ["study:src/protected/a.py"]
    assert payload["classification"] == "deferred-to-publish"

