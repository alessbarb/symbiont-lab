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
