from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_governance_label_descriptions_fit_github_limit() -> None:
    from governance.publish import _GOVERNANCE_LABELS

    assert all(len(description) <= 100 for _, description in _GOVERNANCE_LABELS.values())


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
    monkeypatch.setattr(
        publish_mod,
        "_git",
        lambda *args: {
            ("show", "-s", "--format=%s", "commit-sha"): "Fix candidate PR creation",
            ("show", "-s", "--format=%b", "commit-sha"): "Explicit commit body",
        }[args],
    )
    url = publish_mod._create_candidate_pr("agentctl/123-abcd", "commit-sha", ChangeClass.ORDINARY)

    assert url == "https://github.com/example/repo/pull/1"
    assert calls[0] == ["gh", "label", "list", "--json", "name"]
    assert calls[1][:3] == ["gh", "pr", "create"]
    assert calls[1][calls[1].index("--head") + 1] == "agentctl/123-abcd"
    assert calls[1][calls[1].index("--title") + 1] == "Fix candidate PR creation"
    assert calls[1][calls[1].index("--body") + 1] == "Explicit commit body"
    assert "--fill" not in calls[1]
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
    monkeypatch.setattr(
        publish_mod,
        "_git",
        lambda *args: {
            ("show", "-s", "--format=%s", "commit-sha"): "Scientific candidate",
            ("show", "-s", "--format=%b", "commit-sha"): "",
        }[args],
    )
    publish_mod._create_candidate_pr("agentctl/456-efgh", "commit-sha", ChangeClass.SCIENTIFIC)

    assert calls[1][:3] == ["gh", "label", "create"]
    assert calls[1][3] == "SCIENTIFIC"
    assert calls[-1][-2:] == ["--label", "SCIENTIFIC"]
    assert calls[-1][calls[-1].index("--body") + 1] == (
        "Governed candidate `agentctl/456-efgh` created by agentctl."
    )


def test_ci_exposes_one_stable_governed_required_gate() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "governed-ci-gate:" in workflow
    assert "name: governed-ci-gate" in workflow
    assert "if: always()" in workflow
    assert 'require_success "validation-plan" "$PLAN_RESULT"' in workflow
    assert 'require_success "code-quality-and-governance" "$QUALITY_RESULT"' in workflow
    assert "\\${{" not in workflow

    for job in (
        "governance-docs",
        "software-core",
        "physics3d-tests",
        "modeling-tests",
        "world-tests",
        "observatory-tests",
        "architecture-integrity",
        "runtime-contracts",
        "experiment-mechanics",
        "canonical-full",
        "python-compatibility",
        "host-portability",
        "host-constrained",
        "protocol-mechanics",
    ):
        assert f"      - {job}" in workflow

    gate = workflow.split("  governed-ci-gate:", 1)[1].split("\n  performance-report:", 1)[0]
    assert "performance-report" not in gate
    assert 'require_lane "host-portability"' in gate
    assert 'require_lane "python-compatibility"' in gate


def test_push_ci_uses_main_as_candidate_baseline_and_falls_back_for_missing_sha() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert workflow.count('git merge-base --is-ancestor origin/main "$HEAD"') == 2
    assert workflow.count('BASE="$(git merge-base origin/main "$HEAD")"') == 2
    assert workflow.count('! git cat-file -e "$BASE^{commit}" 2>/dev/null') == 2
