from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_agentctl_publish_never_pushes_directly_to_main() -> None:
    source = (ROOT / "scripts/governance/publish.py").read_text(encoding="utf-8")
    assert "HEAD:main" not in source
    assert "HEAD:refs/heads/{candidate}" in source
    assert "owner_approved" not in source
    assert "Owner-Approval:" not in source


def test_promotion_only_auto_promotes_ordinary_candidates() -> None:
    workflow = (ROOT / ".github/workflows/promote.yml").read_text(encoding="utf-8")
    assert 'CLASS" = "SCIENTIFIC"' in workflow
    assert 'CLASS" = "CONSTITUTIONAL"' in workflow
    assert "only ORDINARY candidates are auto-promoted" in workflow
    assert "Owner-Approval:" not in workflow
    assert "candidate changes the trusted validation/governance control plane" in workflow


def test_validation_matrix_routes_ci_without_local_test_commands() -> None:
    with (ROOT / "docs/governance/validation-matrix.toml").open("rb") as handle:
        matrix = tomllib.load(handle)
    sections = [value for value in matrix.values() if isinstance(value, dict)]
    assert sections
    assert all("commands" not in section for section in sections)


def test_precommit_is_feedback_not_governance_validation() -> None:
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "agentctl.py verify" not in precommit


def test_candidate_pr_gets_its_computed_governance_label(monkeypatch) -> None:
    import governance.publish as publish_mod
    from governance.classify import ChangeClass

    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = '[{"name":"ORDINARY"}]'
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["gh", "pr", "create"]:
            result = Result()
            result.stdout = "https://github.com/example/repo/pull/1\n"
            return result
        return Result()

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    url = publish_mod._create_candidate_pr("agentctl/123-abcd", ChangeClass.ORDINARY)

    assert url == "https://github.com/example/repo/pull/1"
    assert calls[0] == ["gh", "label", "list", "--json", "name"]
    assert calls[1][:3] == ["gh", "pr", "create"]
    assert calls[1][-2:] == ["--label", "ORDINARY"]


def test_candidate_pr_creates_missing_class_label(monkeypatch) -> None:
    import governance.publish as publish_mod
    from governance.classify import ChangeClass

    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = "[]"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["gh", "pr", "create"]:
            result = Result()
            result.stdout = "https://github.com/example/repo/pull/2\n"
            return result
        return Result()

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    publish_mod._create_candidate_pr("agentctl/456-efgh", ChangeClass.SCIENTIFIC)

    assert calls[1][:3] == ["gh", "label", "create"]
    assert calls[1][3] == "SCIENTIFIC"
    assert calls[-1][-2:] == ["--label", "SCIENTIFIC"]
