from __future__ import annotations

from pathlib import Path

import symbiont.actuation.sensorimotor as sensorimotor_module


def test_legacy_sensorimotor_learner_symbol_is_removed() -> None:
    assert not hasattr(sensorimotor_module, "SensorimotorLearner")


def test_action_domain_owns_canonical_competence_engine() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "src" / "symbiont" / "core" / "domains" / "action.py"
    source = path.read_text(encoding="utf-8")
    assert "CompetenceDevelopmentEngine" in source
    assert "SensorimotorLearner" not in source
