from __future__ import annotations

import ast
from pathlib import Path

_ALLOWED_COMMAND_AUTHORITY = {
    "src/symbiont/core/domains/action.py",
}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return func.attr
    return None


def test_production_has_single_motor_command_authority() -> None:
    root = Path(__file__).resolve().parents[2]
    src = root / "src" / "symbiont"
    violations: list[str] = []
    for path in src.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            is_command_construction = name in {
                "MotorCommand",
                "MotorCommand.from_mapping",
                "from_mapping",
            } and (
                name != "from_mapping"
                or isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "MotorCommand"
            )
            is_actuator_system = name == "ActuatorSystem"
            if (
                is_command_construction or is_actuator_system
            ) and rel not in _ALLOWED_COMMAND_AUTHORITY:
                violations.append(f"{rel}:{node.lineno}:{name}")
    assert violations == []


def test_runtime_does_not_cross_physical_actuator_boundary() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert ".execute_command(" not in runtime
    assert "ActuatorSystem(" not in runtime
    assert "MotorCommand.from_mapping(" not in runtime
