from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_constitutive_physiology_phase() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "self._physiology_domain.advance(" in runtime
    assert "self._metabolism.advance(retained_units=" not in runtime
    assert "self._developmental_tracker.observe(" not in runtime


def test_physiology_domain_has_no_action_domain_dependency() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont" / "core" / "domains" / "physiology.py").read_text(
        encoding="utf-8"
    )
    assert "ActionDomain" not in source
    assert "MotorCommand" not in source
    assert "ActionProposal" not in source
