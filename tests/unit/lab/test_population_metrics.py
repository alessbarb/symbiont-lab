import pytest

from symbiont_lab.studies.population_metrics import PopulationMetrics


def test_population_metrics_are_bounded_and_evaluator_side() -> None:
    metrics = PopulationMetrics(3)
    metrics.record(tick=1, population=2, births=1, resource_use=0.5, cooperation=1)
    metrics.record(tick=2, population=0, deaths=2)
    assert metrics.extinct
    assert len(metrics.snapshots()) == 2


def test_population_capacity_is_hard() -> None:
    metrics = PopulationMetrics(2)
    with pytest.raises(ValueError):
        metrics.record(tick=0, population=3)
