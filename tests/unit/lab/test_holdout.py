from __future__ import annotations

import json

import pytest

from symbiont_lab.evaluation.holdout import DevelopmentPhase, FrozenEvaluationPhase, SeedLedger


def test_development_phase_rejects_empty_or_duplicate_seeds() -> None:
    with pytest.raises(ValueError):
        DevelopmentPhase(study_id="s", seeds=())
    with pytest.raises(ValueError):
        DevelopmentPhase(study_id="s", seeds=(1, 1))
    with pytest.raises(ValueError):
        DevelopmentPhase(study_id="s", seeds=(True,))
    with pytest.raises(ValueError):
        DevelopmentPhase(study_id="", seeds=(1,))


def test_ledger_starts_empty_and_persists_after_recording(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    assert ledger.development_history("study.a") == set()
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1, 2, 3)))
    assert ledger.development_history("study.a") == {1, 2, 3}

    reopened = SeedLedger(tmp_path / "ledger.json")
    assert reopened.development_history("study.a") == {1, 2, 3}


def test_ledger_is_append_only_and_never_shrinks(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1, 2)))
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(3,)))
    assert ledger.development_history("study.a") == {1, 2, 3}
    # A later call that only repeats old seeds must not drop anything.
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1,)))
    assert ledger.development_history("study.a") == {1, 2, 3}


def test_ledger_keeps_separate_history_per_study(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1,)))
    ledger.record_development(DevelopmentPhase(study_id="study.b", seeds=(1,)))
    assert ledger.development_history("study.a") == {1}
    assert ledger.development_history("study.b") == {1}


def test_frozen_evaluation_phase_rejects_seeds_already_used_for_development(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1, 2, 3)))
    evaluation = FrozenEvaluationPhase(study_id="study.a", seeds=(3, 4))
    with pytest.raises(ValueError, match="overlap"):
        evaluation.validate_disjoint(ledger)


def test_frozen_evaluation_phase_accepts_seeds_never_used_for_development(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1, 2, 3)))
    evaluation = FrozenEvaluationPhase(study_id="study.a", seeds=(4, 5))
    evaluation.validate_disjoint(ledger)  # must not raise


def test_disjointness_check_is_scoped_per_study(tmp_path) -> None:
    ledger = SeedLedger(tmp_path / "ledger.json")
    ledger.record_development(DevelopmentPhase(study_id="study.a", seeds=(1,)))
    # Same seed under a different study_id is not a conflict.
    FrozenEvaluationPhase(study_id="study.b", seeds=(1,)).validate_disjoint(ledger)


def test_ledger_rejects_corrupt_payload(tmp_path) -> None:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps({"study.a": ["not-an-int"]}), encoding="utf-8")
    ledger = SeedLedger(path)
    with pytest.raises(ValueError):
        ledger.development_history("study.a")
