from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_agentctl_publish_never_pushes_directly_to_main() -> None:
    source = (ROOT / "scripts/governance/publish.py").read_text(encoding="utf-8")

    assert "HEAD:main" not in source
    assert "HEAD:refs/heads/{candidate}" in source
    assert "awaiting GitHub Actions validation and promotion" in source
    assert "_validate_staged" not in source


def test_promotion_requires_green_current_candidate_and_protects_control_plane() -> None:
    workflow = (ROOT / ".github/workflows/promote.yml").read_text(encoding="utf-8")

    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "startsWith(github.event.workflow_run.head_branch, 'agentctl/')" in workflow
    assert 'PARENT="$(git rev-parse "$HEAD_SHA^")"' in workflow
    assert '"$PARENT" != "$CURRENT_MAIN"' in workflow
    assert "CONSTITUTIONAL candidates are never auto-promoted" not in workflow
    assert 'CLASS" = "CONSTITUTIONAL"' in workflow
    assert "candidate changes the trusted validation/governance control plane" in workflow
    assert 'git push origin "$HEAD_SHA:refs/heads/main"' in workflow


def test_validation_matrix_routes_ci_without_local_test_commands() -> None:
    with (ROOT / "docs/governance/validation-matrix.toml").open("rb") as handle:
        matrix = tomllib.load(handle)

    sections = [value for value in matrix.values() if isinstance(value, dict)]
    assert sections
    assert all("commands" not in section for section in sections)
    assert any(section.get("ci_lanes") for section in sections)


def test_precommit_is_feedback_not_governance_validation() -> None:
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "agentctl.py verify" not in precommit
    assert "ruff check --fix" in precommit
    assert "ruff format" in precommit
