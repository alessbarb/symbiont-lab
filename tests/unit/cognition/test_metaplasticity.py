from __future__ import annotations

from symbiont.cognition.metaplasticity import LearningObjective, dominates


def _objective(
    prediction_error=0.5, representation_cost=0.5, instability=0.5, information_retained=0.5, calibration=0.5
) -> LearningObjective:
    return LearningObjective(
        prediction_error=prediction_error,
        representation_cost=representation_cost,
        instability=instability,
        information_retained=information_retained,
        calibration=calibration,
    )


def test_identical_objectives_never_dominate_each_other():
    a = _objective()
    b = _objective()
    assert not dominates(a, b)
    assert not dominates(b, a)


def test_strictly_better_on_all_dimensions_dominates():
    better = _objective(
        prediction_error=0.1, representation_cost=0.1, instability=0.1, information_retained=0.9, calibration=0.9
    )
    worse = _objective(
        prediction_error=0.5, representation_cost=0.5, instability=0.5, information_retained=0.5, calibration=0.5
    )
    assert dominates(better, worse)
    assert not dominates(worse, better)


def test_mixed_improvement_and_regression_dominates_neither_way():
    mixed = _objective(prediction_error=0.1, representation_cost=0.9)
    baseline = _objective(prediction_error=0.5, representation_cost=0.5)
    assert not dominates(mixed, baseline)
    assert not dominates(baseline, mixed)


def test_better_on_one_dimension_equal_on_rest_dominates():
    better = _objective(prediction_error=0.1)
    baseline = _objective(prediction_error=0.5)
    assert dominates(better, baseline)
