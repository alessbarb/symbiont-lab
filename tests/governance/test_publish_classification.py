from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from governance.classify import ChangeClass, assess
from governance.publish import _active_work_conflicts, _normalize_adr_ref


def test_private_model_promotion_is_scientific_by_semantics() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/physics3d/private_model_training.py"],
        "diff --git a/src/symbiont_lab/physics3d/private_model_training.py b/src/symbiont_lab/physics3d/private_model_training.py\n+ activate_private_model(... promotion_authorized=True)",
    )
    assert result.classification == ChangeClass.SCIENTIFIC
    assert "promotion-eligible" in result.equivalence_scenarios


def test_scientific_keywords_in_unclassified_docs_do_not_taint_classification() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["docs/notes.md"],
        "diff --git a/docs/notes.md b/docs/notes.md\n+ promotion training active shadow",
    )
    assert result.classification == ChangeClass.ORDINARY
    assert result.equivalence_scenarios == ()


def test_observatory_presentation_is_ordinary() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["observatory/ui/view.js"],
        "diff --git a/observatory/ui/view.js b/observatory/ui/view.js\n+ renderLabel()",
    )
    assert result.classification == ChangeClass.ORDINARY


def test_active_work_conflict_is_detected(monkeypatch) -> None:
    import governance.publish as publish_mod

    monkeypatch.setattr(
        publish_mod,
        "_active_work_at",
        lambda base: {
            "work": [
                {
                    "id": "synthetic-running-work",
                    "state": "RUNNING",
                    "protected_paths": ["src/symbiont_lab/studies/learning/**"],
                }
            ]
        },
    )
    conflicts = _active_work_conflicts(
        ["src/symbiont_lab/studies/learning/example.py"],
        "HEAD",
    )
    assert conflicts == ["synthetic-running-work: src/symbiont_lab/studies/learning/example.py"]


def test_equivalence_control_plane_is_constitutional() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/physics3d/equivalence_suite.py"],
        "diff --git a/src/symbiont_lab/physics3d/equivalence_suite.py b/src/symbiont_lab/physics3d/equivalence_suite.py\n+ # candidate tweak",
    )
    assert result.classification == ChangeClass.CONSTITUTIONAL


def test_equivalence_suite_manifest_is_constitutional() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["experiments/equivalence/suite-v1/suite.toml"],
        "diff --git a/experiments/equivalence/suite-v1/suite.toml b/experiments/equivalence/suite-v1/suite.toml\n+ ticks = 1",
    )
    assert result.classification == ChangeClass.CONSTITUTIONAL


def test_physics3d_runtime_is_scientific_even_without_keywords() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/physics3d/runtime.py"],
        "diff --git a/src/symbiont_lab/physics3d/runtime.py b/src/symbiont_lab/physics3d/runtime.py\n+ value = old_value + 1",
    )
    assert result.classification == ChangeClass.SCIENTIFIC
    assert "established-anthropomorphic" in result.equivalence_scenarios


def test_private_model_file_is_scientific_without_keyword_match() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/physics3d/private_model_training.py"],
        "diff --git a/src/symbiont_lab/physics3d/private_model_training.py b/src/symbiont_lab/physics3d/private_model_training.py\n+ # harmless-looking refactor",
    )
    assert result.classification == ChangeClass.SCIENTIFIC


def test_lab_run_controller_is_scientific() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/app/run_controller.py"],
        "diff --git a/src/symbiont_lab/app/run_controller.py b/src/symbiont_lab/app/run_controller.py\n+ return launch(spec)",
    )
    assert result.classification == ChangeClass.SCIENTIFIC


def test_workbench_web_presentation_stays_ordinary() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/workbench/web/views/body/viewer.js"],
        "diff --git a/src/symbiont_lab/workbench/web/views/body/viewer.js b/src/symbiont_lab/workbench/web/views/body/viewer.js\n+ renderPanel()",
    )
    assert result.classification == ChangeClass.ORDINARY


def test_governance_tests_are_constitutional() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["tests/governance/test_agent_governance.py"],
        "diff --git a/tests/governance/test_agent_governance.py b/tests/governance/test_agent_governance.py\n+ assert True",
    )
    assert result.classification == ChangeClass.CONSTITUTIONAL


def test_adr_is_constitutional() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["docs/adr/ADR-9999-example.md"],
        "diff --git a/docs/adr/ADR-9999-example.md b/docs/adr/ADR-9999-example.md\n+ - **Status:** Accepted",
    )
    assert result.classification == ChangeClass.CONSTITUTIONAL


def test_roadmap_classifies_as_ordinary_under_current_policy() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["docs/roadmap.md"],
        "diff --git a/docs/roadmap.md b/docs/roadmap.md\n+ update task status",
    )
    assert result.classification == ChangeClass.ORDINARY


def test_methodology_remains_scientific() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["docs/methodology/research-programme.md"],
        "diff --git a/docs/methodology/research-programme.md b/docs/methodology/research-programme.md\n+ new research phase",
    )
    assert result.classification == ChangeClass.SCIENTIFIC


def test_candidate_policy_classifies_roadmap_ordinary_and_methodology_scientific() -> None:
    policy = tomllib.loads((ROOT / "docs/governance/change-surfaces.toml").read_text())
    surfaces = {surface["id"]: surface for surface in policy["surface"]}
    assert surfaces["project-roadmap"]["classification"] == "ORDINARY"
    assert surfaces["project-roadmap"]["paths"] == ["docs/roadmap.md"]
    assert "docs/methodology/**" in surfaces["scientific-direction"]["paths"]
    assert surfaces["scientific-direction"]["classification"] == "SCIENTIFIC"


def test_experimental_integrity_tests_are_scientific() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["tests/experimental_integrity/test_boundary.py"],
        "diff --git a/tests/experimental_integrity/test_boundary.py b/tests/experimental_integrity/test_boundary.py\n+ assert invariant",
    )
    assert result.classification == ChangeClass.SCIENTIFIC


def test_study_code_is_scientific() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/studies/example.py"],
        "diff --git a/src/symbiont_lab/studies/example.py b/src/symbiont_lab/studies/example.py\n+ def run(): pass",
    )
    assert result.classification == ChangeClass.SCIENTIFIC


def test_adr_reference_cannot_escape_docs_adr() -> None:
    import pytest

    with pytest.raises(PermissionError, match="docs/adr"):
        _normalize_adr_ref("/tmp/ADR-9999.md")


def test_adr_reference_resolves_existing_accepted_adr() -> None:
    resolved = _normalize_adr_ref("ADR-0046")
    assert resolved.name.startswith("ADR-0046-")
    assert resolved.parent == (ROOT / "docs/adr").resolve()


def test_rebase_reprepares_final_diff_before_revalidation(monkeypatch) -> None:
    import subprocess

    import governance.publish as publish_mod

    normalized: list[str] = []
    rebases: list[list[str]] = []

    def fake_run(args, **kwargs):
        rebases.append(list(args))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(publish_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(
        publish_mod,
        "_normalize_local_commits",
        lambda remote: normalized.append(remote),
    )

    latest = "a" * 40
    publish_mod._rebase_and_reprepare(latest)

    assert rebases == [["git", "rebase", latest]]
    assert normalized == [latest]
