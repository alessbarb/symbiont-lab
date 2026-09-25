from __future__ import annotations

from pathlib import Path


def test_runtime_has_explicit_memory_phase() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    cognition = (root / "src" / "symbiont" / "core" / "domains" / "cognition.py").read_text(
        encoding="utf-8"
    )
    assert "self._memory_domain.observe(" in runtime
    assert "MemoryConsolidator" not in cognition
    assert "consolidator.observe(" not in cognition


def test_memory_domain_has_no_action_authority() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont" / "core" / "domains" / "memory.py").read_text(
        encoding="utf-8"
    )
    assert "MotorCommand" not in source
    assert "ActionProposal" not in source
    assert "ActuatorSystem" not in source
