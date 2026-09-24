from __future__ import annotations

import ast
from pathlib import Path


REGULATION = Path("src/symbiont/core/regulation")


def test_regulation_imports_no_lab_world_or_evaluator_modules() -> None:
    forbidden = ("symbiont_lab", "symbiont_world")
    for path in sorted(REGULATION.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names = (node.module or "",)
            else:
                continue
            assert not any(
                name == token or name.startswith(token + ".")
                for name in names
                for token in forbidden
            )


def test_regulation_contains_no_anatomical_motor_mapping() -> None:
    forbidden_identifiers = {
        "head", "arm", "leg", "hand", "foot",
        "left_arm", "right_arm", "joint_name", "body_kind",
    }
    for path in sorted(REGULATION.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = {
            node.id.lower()
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        assert not names.intersection(forbidden_identifiers)


def test_runtime_fast_path_still_activates_through_sensorimotor_learner() -> None:
    source = Path(
        "src/symbiont/core/orchestration/runtime.py"
    ).read_text(encoding="utf-8")
    assert '"primitive_reactive"' in source
    assert "self._sensorimotor_learner.activate_primitive(" in source
    assert "self._action_arbitrator.choose_reactive(" in source
