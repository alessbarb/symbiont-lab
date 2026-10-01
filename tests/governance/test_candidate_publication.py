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
