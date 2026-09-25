from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_regulation_and_delayed_credit() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._development_domain.update_gene_expression(" in runtime
    assert "self._regulation_domain.schedule_homeostatic_action_credit(" in runtime
    assert "self._regulation_domain.resolve_homeostatic_action_credit(" in runtime
    assert "self._regulation_domain.update_gene_expression(" not in runtime


def test_regulation_domain_does_not_execute_motor_commands() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "domains" / "regulation.py"
    ).read_text(encoding="utf-8")
    assert "MotorCommand" not in source
    assert "ActuatorSystem" not in source
    assert "ActionProposal" not in source
