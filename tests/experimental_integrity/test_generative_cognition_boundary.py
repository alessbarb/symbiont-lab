from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            values.append(node.module or "")
    return tuple(values)


def test_resident_generative_cognition_has_no_lab_world_or_actuator_dependency() -> None:
    path = ROOT / "symbiont" / "src" / "symbiont" / "cognition" / "generative" / "resident.py"
    imports = _imports(path)
    forbidden = (
        "lab",
        "physics3d",
        "actuation.system",
        "actuation.surface",
        "modeling.ledger",
        "modeling.experience",
    )
    for value in imports:
        assert not any(token in value for token in forbidden), value


def test_runtime_remains_orchestrator_not_generative_algorithm_owner() -> None:
    source = (
        ROOT / "symbiont" / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "RolloutEngine(",
        "BranchEngine(",
        "GenerativeWorkspace(",
        "GenerativeAgenda(",
        "GenerativeHypothesis(",
        "ExperienceRecombiner(",
    )
    for token in forbidden:
        assert token not in source


def test_generative_cognition_never_imports_observatory_or_lab() -> None:
    directory = ROOT / "symbiont" / "src" / "symbiont" / "cognition" / "generative"
    for path in directory.glob("*.py"):
        imports = _imports(path)
        for value in imports:
            assert "lab" not in value
            assert "observatory" not in value
