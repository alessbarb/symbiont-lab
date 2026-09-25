from __future__ import annotations

import ast
from pathlib import Path


def _calls_named(path: Path, name: str) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == name:
            lines.append(node.lineno)
        elif isinstance(fn, ast.Attribute) and fn.attr == name:
            lines.append(node.lineno)
    return lines


def test_production_does_not_instantiate_legacy_sensorimotor_learner() -> None:
    root = Path(__file__).resolve().parents[2]
    production = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py",
        root / "src" / "symbiont" / "core" / "domains" / "action.py",
        root / "src" / "symbiont_lab" / "physics3d" / "runtime.py",
    )
    for path in production:
        assert _calls_named(path, "SensorimotorLearner") == []


def test_action_domain_owns_canonical_competence_engine() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "src" / "symbiont" / "core" / "domains" / "action.py"
    text = path.read_text(encoding="utf-8")
    assert "CompetenceDevelopmentEngine" in text
    assert "_legacy_learner" not in text
