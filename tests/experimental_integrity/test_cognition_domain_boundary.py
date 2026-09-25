from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_cognition_and_memory_learning() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._cognition_domain.step(" in runtime
    assert "self._cognitive_bridge.tick(" not in runtime
    assert "self._memory_consolidator.observe(" not in runtime
    assert "self._sensory_system.plastic_step(" not in runtime


def test_cognition_domain_has_no_physical_execution_authority() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "domains" / "cognition.py"
    ).read_text(encoding="utf-8")
    assert "MotorCommand" not in source
    assert "ActuatorSystem" not in source
    assert "ActionCommitment" not in source
