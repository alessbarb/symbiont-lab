from __future__ import annotations

from symbiont_lab.studies.common.statistics import (
    aggregate_metric,
    mean_delta,
    paired_deltas,
    safe_mean,
)


def test_safe_mean():
    assert safe_mean([1.0, 2.0, 3.0]) == 2.0
    assert safe_mean([1.0, None, 3.0]) == 2.0
    assert safe_mean([None, None]) is None


def test_paired_deltas():
    deltas = paired_deltas([0.8, 0.9, None], [0.5, 0.7, 0.6])
    assert len(deltas) == 2
    assert abs(deltas[0] - 0.3) < 1e-6
    assert abs(deltas[1] - 0.2) < 1e-6


def test_mean_delta():
    assert abs(mean_delta([0.8, 0.9], [0.5, 0.7]) - 0.25) < 1e-6


def test_aggregate_metric():
    agg = aggregate_metric([10.0, 20.0, 30.0])
    assert agg["mean"] == 20.0
    assert agg["median"] == 20.0
    assert agg["count"] == 3
