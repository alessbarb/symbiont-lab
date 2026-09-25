from __future__ import annotations

from pathlib import Path


def test_lab_studies_do_not_reach_legacy_sensorimotor_private_state() -> None:
    root = Path(__file__).resolve().parents[2]
    study = (
        root / "src" / "symbiont_lab" / "studies" / "learning" / "prospective_agency_embodied.py"
    ).read_text(encoding="utf-8")
    assert "_sensorimotor_learner" not in study
    assert "available_motor_competence_ids" in study
