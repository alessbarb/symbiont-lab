from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _agentctl():
    spec = importlib.util.spec_from_file_location(
        "agentctl", ROOT / "scripts" / "agentctl.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_contract_uses_context_as_single_normal_read() -> None:
    contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "agentctl.py context" in contract
    assert "do not reread the governance corpus" in contract
    assert "Publish once" in contract


def test_context_is_compact_and_defers_classification(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    base = "a" * 40

    monkeypatch.setattr(ctl, "_trusted_origin_ref", lambda: base)

    def fake_governance(ref: str, name: str) -> dict:
        assert ref == base
        if name == "project-state.toml":
            return {"current_gate": "e8-label-invariance"}
        return {"work": []}

    def fake_git(*args: str, **kwargs) -> str:
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return "feature/example"
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        raise AssertionError(args)

    monkeypatch.setattr(ctl, "_trusted_governance_at", fake_governance)
    monkeypatch.setattr(ctl, "git", fake_git)
    monkeypatch.setattr(ctl, "changed_paths", lambda staged_only=False: [])

    assert ctl.context() == 0
    output = capsys.readouterr().out.splitlines()
    assert len(output) <= 10
    assert "worktree: clean (0 changed paths)" in output
    assert "classification: deferred-to-publish" in output


def test_context_json_reports_running_conflicts(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    base = "a" * 40

    monkeypatch.setattr(ctl, "_trusted_origin_ref", lambda: base)

    def fake_governance(ref: str, name: str) -> dict:
        assert ref == base
        if name == "project-state.toml":
            return {"current_gate": "gate"}
        return {
            "work": [
                {
                    "id": "study",
                    "state": "RUNNING",
                    "protected_paths": ["src/protected/**"],
                }
            ]
        }

    def fake_git(*args: str, **kwargs) -> str:
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return "feature/example"
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        raise AssertionError(args)

    monkeypatch.setattr(ctl, "_trusted_governance_at", fake_governance)
    monkeypatch.setattr(ctl, "git", fake_git)
    monkeypatch.setattr(
        ctl,
        "changed_paths",
        lambda staged_only=False: ["src/protected/a.py"],
    )

    assert ctl.context(as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["running_work"] == ["study"]
    assert payload["protected_conflicts"] == ["study:src/protected/a.py"]
    assert payload["classification"] == "deferred-to-publish"
