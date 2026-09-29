from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from governance.classify import ChangeClass, assess


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


from governance.publish import _active_work_conflicts


def test_active_work_conflict_is_detected() -> None:
    conflicts = _active_work_conflicts(
        ["src/symbiont_lab/studies/learning/visual_acquisition.py"],
        "HEAD",
    )
    assert any("visual-acquisition-d1-v2" in conflict for conflict in conflicts)



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


def test_roadmap_is_scientific_direction() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["docs/roadmap.md"],
        "diff --git a/docs/roadmap.md b/docs/roadmap.md\n+ new research phase",
    )
    assert result.classification == ChangeClass.SCIENTIFIC


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
