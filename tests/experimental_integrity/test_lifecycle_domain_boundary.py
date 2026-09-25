from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_lifecycle_event_state() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._lifecycle_domain.events(" in runtime
    assert "runtime_events.append(" not in runtime
    assert "update_interoception_metrics(" in runtime


def test_lifecycle_domain_has_no_action_selection_logic() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "domains" / "lifecycle.py"
    ).read_text(encoding="utf-8")
    assert "ActionProposal" not in source
    assert "MotorCommand" not in source
    assert "ActionArbitrator" not in source
