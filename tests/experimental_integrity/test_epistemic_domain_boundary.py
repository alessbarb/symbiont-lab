from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_second_look_and_narrative() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._epistemic_domain.investigate(" in runtime
    assert "SecondLookSession(" not in runtime
    assert "narrate_host(" not in runtime


def test_epistemic_domain_cannot_execute_actions() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "domains" / "epistemic.py"
    ).read_text(encoding="utf-8")
    assert "MotorCommand" not in source
    assert "ActionDomain" not in source
    assert "ActuatorSystem" not in source
