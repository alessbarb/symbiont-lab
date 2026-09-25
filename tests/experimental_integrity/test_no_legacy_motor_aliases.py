from __future__ import annotations

from pathlib import Path


def test_runtime_source_has_no_legacy_private_motor_aliases() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "self._actuator_proposer" not in source
    assert "self._sensorimotor_learner" not in source
