from __future__ import annotations

import ast
from pathlib import Path


def test_prospective_agency_has_no_lab_or_world_dependency():
    repo_root = Path(__file__).resolve().parents[2]
    agency_src = repo_root / "src" / "symbiont" / "agency"
    assert agency_src.is_dir()

    violations: list[str] = []
    for py_file in agency_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in {"symbiont_lab", "symbiont_world"}:
                        violations.append(
                            f"{py_file.relative_to(repo_root)} imports {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in {"symbiont_lab", "symbiont_world"}:
                    violations.append(
                        f"{py_file.relative_to(repo_root)} imports from {node.module}"
                    )

    assert not violations, "Prospective agency boundary violation(s):\n" + "\n".join(violations)


def test_prospective_agency_never_reads_evaluator_task_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    agency_src = repo_root / "src" / "symbiont" / "agency"

    forbidden = {
        "resource_distance",
        "resource_progress",
        "target_position",
        "target_coordinate",
        "locomotion_score",
        "minimum_resource_distance",
    }
    violations: list[str] = []
    for py_file in agency_src.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                violations.append(
                    f"{py_file.relative_to(repo_root)} references {node.id}"
                )
            elif isinstance(node, ast.Attribute) and node.attr in forbidden:
                violations.append(
                    f"{py_file.relative_to(repo_root)} references .{node.attr}"
                )

    assert not violations, "Evaluator metric contamination:\n" + "\n".join(violations)


def test_private_prospective_selector_receives_no_evaluator_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = repo_root / "src" / "symbiont" / "modeling" / "private_runtime.py"
    tree = ast.parse(private_runtime.read_text(encoding="utf-8"), filename=str(private_runtime))

    selector = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PrivateModelOrganismRuntime"
    )
    method = next(
        node
        for node in selector.body
        if isinstance(node, ast.FunctionDef) and node.name == "_choose_acquired_primitive"
    )
    parameter_names = {arg.arg for arg in method.args.args + method.args.kwonlyargs}
    forbidden = {
        "resource",
        "resource_distance",
        "resource_progress",
        "target",
        "coordinates",
        "evaluator",
    }

    assert parameter_names.isdisjoint(forbidden)


def test_prospective_choice_cannot_directly_train_outcome_value():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = repo_root / "src" / "symbiont" / "modeling" / "private_runtime.py"
    source = private_runtime.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(private_runtime))

    runtime_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PrivateModelOrganismRuntime"
    )
    chooser = next(
        node
        for node in runtime_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "_choose_acquired_primitive"
    )
    chooser_source = ast.get_source_segment(source, chooser) or ""

    assert "_pending_outcome_value_credit" not in chooser_source
    assert "outcome_value_ledger.observe" not in chooser_source
    assert "decision.predicted_outcome" not in chooser_source


def test_outcome_value_credit_is_scheduled_only_from_observed_episode_path():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = repo_root / "src" / "symbiont" / "modeling" / "private_runtime.py"
    source = private_runtime.read_text(encoding="utf-8")

    call = "self._schedule_observed_outcome_value_credit("
    assert source.count(call) == 1

    finalize_index = source.index("episode = self._finalize_private_transition")
    schedule_index = source.index(call)
    record_index = source.index("self.record_experience(episode)", finalize_index)

    assert finalize_index < record_index < schedule_index


def test_private_prospective_selector_source_contains_no_evaluator_metrics():
    repo_root = Path(__file__).resolve().parents[2]
    private_runtime = repo_root / "src" / "symbiont" / "modeling" / "private_runtime.py"
    source = private_runtime.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(private_runtime))

    runtime_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PrivateModelOrganismRuntime"
    )
    chooser = next(
        node
        for node in runtime_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "_choose_acquired_primitive"
    )
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
