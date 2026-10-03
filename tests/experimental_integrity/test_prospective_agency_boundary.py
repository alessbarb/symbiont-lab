from __future__ import annotations

import ast
from pathlib import Path


def _collect_attribute_accesses(node: ast.AST) -> list[ast.Attribute]:
    return [sub for sub in ast.walk(node) if isinstance(sub, ast.Attribute)]


def test_private_prospective_components_do_not_import_evaluator_telemetry():
    repo_root = Path(__file__).resolve().parents[2]
    private_files = [
        repo_root / "symbiont" / "src" / "symbiont" / "modeling" / "private_runtime.py",
        repo_root / "symbiont" / "src" / "symbiont" / "modeling" / "episodic.py",
    ]

    forbidden_tokens = {
        "lab.physics3d",
        "lab.world",
        "lab.observation",
        "evaluator",
        "ground_truth",
        "reward",
    }

    for path in private_files:
        content = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in content, (
                f"{path.relative_to(repo_root)} directly references forbidden evaluator token {token!r}"
            )


def test_private_prospective_decision_path_cannot_read_evaluator_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    modeling_root = repo_root / "symbiont" / "src" / "symbiont" / "modeling"
    forbidden_attributes = {
        "resource_distance",
        "resource_progress",
        "minimum_resource_distance",
        "target_position",
        "locomotion_progress",
        "absorbed_energy",
    }

    violations: list[str] = []
    for py_file in modeling_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in _collect_attribute_accesses(tree):
            if node.attr in forbidden_attributes:
                violations.append(f"{py_file.relative_to(repo_root)} references .{node.attr}")

    assert not violations, "Evaluator metric contamination:\n" + "\n".join(violations)


def test_private_prospective_selector_receives_no_evaluator_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = (
        repo_root / "symbiont" / "src" / "symbiont" / "modeling" / "private_runtime.py"
    )
    tree = ast.parse(private_runtime.read_text(encoding="utf-8"), filename=str(private_runtime))

    selector = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PrivateModelOrganismRuntime"
    )
    methods = [
        node
        for node in selector.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"_choose_acquired_action", "_deliberate_prospectively"}
    ]
    assert len(methods) >= 1
    forbidden = {
        "resource",
        "resource_distance",
        "resource_progress",
        "target",
        "coordinates",
        "evaluator",
    }

    for method in methods:
        parameter_names = {arg.arg for arg in method.args.args + method.args.kwonlyargs}
        assert parameter_names.isdisjoint(forbidden)


def test_prospective_choice_cannot_directly_train_outcome_value():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = (
        repo_root / "symbiont" / "src" / "symbiont" / "modeling" / "private_runtime.py"
    )
    source = private_runtime.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(private_runtime))

    runtime_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PrivateModelOrganismRuntime"
    )
    choosers = [
        node
        for node in runtime_class.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"_choose_acquired_action", "_deliberate_prospectively"}
    ]
    assert len(choosers) >= 1

    for chooser in choosers:
        chooser_source = ast.get_source_segment(source, chooser) or ""
        assert "_pending_outcome_value_credit" not in chooser_source
        assert "outcome_value_ledger.observe" not in chooser_source
        assert "decision.predicted_outcome" not in chooser_source


def test_outcome_value_credit_is_scheduled_only_from_observed_episode_path():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = (
        repo_root / "symbiont" / "src" / "symbiont" / "modeling" / "private_runtime.py"
    )
    source = private_runtime.read_text(encoding="utf-8")

    call = "self._schedule_observed_outcome_value_credit("
    assert source.count(call) == 1

    finalize_index = source.index("episode = self._finalize_private_transition")
    schedule_index = source.index(call)
    record_index = source.index("self.record_experience(", finalize_index)

    assert finalize_index < record_index < schedule_index


def test_private_prospective_selector_source_contains_no_evaluator_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = (
        repo_root / "symbiont" / "src" / "symbiont" / "modeling" / "private_runtime.py"
    )
    source = private_runtime.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(private_runtime))

    runtime_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PrivateModelOrganismRuntime"
    )
    choosers = [
        node
        for node in runtime_class.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"_choose_acquired_action", "_deliberate_prospectively"}
    ]
    assert len(choosers) >= 1

    for chooser in choosers:
        chooser_source = (ast.get_source_segment(source, chooser) or "").lower()
        for forbidden in (
            "resource_distance",
            "resource_progress",
            "minimum_resource_distance",
            "target_position",
            "locomotion",
            "absorbed_energy",
        ):
            assert forbidden not in chooser_source
