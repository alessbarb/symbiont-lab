from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, PlasticNode
from symbiont.cognition.learning import PredictionError, compute_prediction_errors, huber_loss
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import NodeKind


def _target(node_id: str = "target") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.CONCEPT)


def _predictor(node_id: str = "p1", predicts: str = "target") -> PlasticNode:
    return PlasticNode(node_id=node_id, kind=NodeKind.PREDICTOR, predicts_node_id=predicts)


def test_huber_loss_is_quadratic_within_delta():
    assert huber_loss(0.5, delta=1.0) == pytest.approx(0.5 * 0.5 * 0.5)


def test_huber_loss_is_linear_beyond_delta():
    assert huber_loss(2.0, delta=1.0) == pytest.approx(1.0 * (2.0 - 0.5))


def test_huber_loss_is_zero_at_zero_error():
    assert huber_loss(0.0) == 0.0


def test_huber_loss_is_symmetric():
    assert huber_loss(1.5) == pytest.approx(huber_loss(-1.5))


def test_exact_prediction_yields_zero_error():
    graph = CognitiveGraph(nodes=(_target(), _predictor()), edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(graph, current={"target": 0.3, "p1": 0.1}, previous={"target": 0.0, "p1": 0.3})
    assert len(errors) == 1
    assert errors[0] == PredictionError(predictor_id="p1", target_id="target", error=0.0, loss=0.0)


def test_mismatched_prediction_yields_nonzero_error():
    graph = CognitiveGraph(nodes=(_target(), _predictor()), edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(graph, current={"target": 0.8, "p1": 0.1}, previous={"target": 0.0, "p1": 0.1})
    assert errors[0].error == pytest.approx(0.7)
    assert errors[0].loss > 0.0


def test_cold_start_predictor_missing_from_previous_is_skipped():
    graph = CognitiveGraph(nodes=(_target(), _predictor()), edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(graph, current={"target": 0.5}, previous={})
    assert errors == ()


def test_multiple_predictors_are_returned_sorted_by_predictor_id():
    nodes = (_target(), _predictor("p2"), _predictor("p1"))
    graph = CognitiveGraph(nodes=nodes, edges=(), kernel_limits=KernelLimits())
    errors = compute_prediction_errors(
        graph, current={"target": 0.5, "p1": 0.0, "p2": 0.0}, previous={"target": 0.0, "p1": 0.0, "p2": 0.0}
    )
    assert [error.predictor_id for error in errors] == ["p1", "p2"]
