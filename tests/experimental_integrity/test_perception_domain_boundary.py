from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_perception_attention_phase() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._perception_domain.step(" in runtime
    assert "self._sensory_system.transduce(" not in runtime
    assert "attend_to_host(" not in runtime


def test_perception_domain_has_no_motor_execution_authority() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "domains" / "perception.py"
    ).read_text(encoding="utf-8")
    assert "MotorCommand" not in source
    assert "ActionCommitment" not in source
    assert "ActuatorSystem" not in source
    assert "ActionDomain" not in source
