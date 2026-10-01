from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _agentctl():
    spec = importlib.util.spec_from_file_location(
        "agentctl",
        ROOT / "scripts" / "agentctl.py",
    )
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args: str, **kwargs) -> str:
    if args == ("rev-parse", "--abbrev-ref", "HEAD"):
        return "feature/example"
    if args == ("rev-parse", "HEAD"):
        return "b" * 40
    raise AssertionError(args)


def test_contract_uses_context() -> None:
    contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "agentctl.py context" in contract
    assert "Publish once" in contract


def test_context_output(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    base = "a" * 40

    def governance(ref: str, name: str) -> dict:
        assert ref == base
        if name == "project-state.toml":
            return {"current_gate": "gate"}
        return {"work": []}

    monkeypatch.setattr(ctl, "_trusted_origin_ref", lambda: base)
    monkeypatch.setattr(ctl, "_trusted_governance_at", governance)
    monkeypatch.setattr(ctl, "git", _git)
    monkeypatch.setattr(ctl, "changed_paths", lambda staged_only=False: [])

    assert ctl.context() == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) <= 10
    assert "classification: deferred-to-publish" in lines


def test_context_json_conflict(monkeypatch, capsys) -> None:
    ctl = _agentctl()
    base = "a" * 40

    def governance(ref: str, name: str) -> dict:
        assert ref == base
        if name == "project-state.toml":
            return {"current_gate": "gate"}
        return {
            "work": [
                {
                    "id": "study",
                    "state": "RUNNING",
                    "protected_paths": ["src/protected/**"],
                },
            ],
        }

    monkeypatch.setattr(ctl, "_trusted_origin_ref", lambda: base)
    monkeypatch.setattr(ctl, "_trusted_governance_at", governance)
    monkeypatch.setattr(ctl, "git", _git)
    monkeypatch.setattr(
        ctl,
        "changed_paths",
        lambda staged_only=False: ["src/protected/a.py"],
    )

    assert ctl.context(as_json=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["running_work"] == ["study"]
    assert payload["protected_conflicts"] == ["study:src/protected/a.py"]
