from __future__ import annotations

from symbiont.cognition.metaplasticity import LearningObjective
from symbiont_lab.evolution.evaluation import EvaluationResult, select_archive


def _result(genome_id: str, **objective_kwargs) -> EvaluationResult:
    defaults = dict(prediction_error=0.5, representation_cost=0.5, instability=0.5, information_retained=0.5, calibration=0.5)
    defaults.update(objective_kwargs)
    return EvaluationResult(
        genome_id=genome_id, objective=LearningObjective(**defaults), regime_label="regime-a", seed_pair_id="seed-1"
    )


def test_empty_batch_returns_empty_archive():
    assert select_archive((), max_archive_size=10) == ()


def test_dominated_result_is_excluded():
    better = _result("better", prediction_error=0.1)
    worse = _result("worse", prediction_error=0.5)
    archive = select_archive((better, worse), max_archive_size=10)
    assert better in archive
    assert worse not in archive


def test_mutually_non_dominated_results_both_survive():
    a = _result("a", prediction_error=0.1, representation_cost=0.9)
    b = _result("b", prediction_error=0.9, representation_cost=0.1)
    archive = select_archive((a, b), max_archive_size=10)
    assert a in archive
    assert b in archive


def test_archive_never_exceeds_max_size():
    results = tuple(
        _result(f"g{i}", prediction_error=0.1 * i, representation_cost=1.0 - 0.1 * i) for i in range(10)
    )
    archive = select_archive(results, max_archive_size=3)
    assert len(archive) <= 3


def test_identical_results_all_survive_since_none_dominates_another():
    a = _result("a")
    b = _result("b")
    archive = select_archive((a, b), max_archive_size=10)
    assert a in archive
    assert b in archive
