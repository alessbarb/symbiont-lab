from __future__ import annotations

import pytest

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
from symbiont.cognition.learning import (
    PredictionError,
    apply_oja_update,
    compute_prediction_errors,
    huber_loss,
    update_eligibility,
)
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind, WEIGHT_RANGE


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


# --- eligibility trace and bounded Oja update ---


def _edge(weight: float = 0.5) -> PlasticEdge:
    return PlasticEdge(
        source_id="a", target_id="b", kind=EdgeKind.EXCITATORY, weight=weight, plasticity=0.5, delay_ticks=1
    )


def test_eligibility_grows_with_sustained_coactivation():
    edge = _edge()
    for _ in range(20):
        update_eligibility(edge, source_previous=0.8, target_current=0.8, decay=0.9)
    assert edge.eligibility > 0.5


def test_eligibility_decays_toward_zero_without_coactivation():
    edge = _edge()
    edge.eligibility = 1.0
    for _ in range(50):
        update_eligibility(edge, source_previous=0.0, target_current=0.0, decay=0.9)
    assert abs(edge.eligibility) < 0.01


def test_eligibility_stays_finite_and_bounded_under_repeated_extremes():
    import math

    edge = _edge()
    for _ in range(1000):
        update_eligibility(edge, source_previous=1.0, target_current=1.0, decay=0.99)
    assert math.isfinite(edge.eligibility)
    assert abs(edge.eligibility) <= 1.0 / (1.0 - 0.99) + 1e-6


def test_oja_update_is_a_noop_when_not_eligible():
    edge = _edge(weight=0.5)
    apply_oja_update(edge, source_activation=1.0, target_activation=1.0, learning_rate=0.5, modulation=1.0, eligible=False)
    assert edge.weight == 0.5


def test_oja_update_is_a_noop_when_modulation_is_zero():
    edge = _edge(weight=0.5)
    apply_oja_update(edge, source_activation=1.0, target_activation=1.0, learning_rate=0.5, modulation=0.0, eligible=True)
    assert edge.weight == 0.5


def test_oja_update_moves_weight_toward_correlated_activity():
    edge = _edge(weight=0.1)
    for _ in range(50):
        apply_oja_update(
            edge, source_activation=0.9, target_activation=0.9, learning_rate=0.1, modulation=1.0, eligible=True
        )
    assert edge.weight > 0.1


def test_oja_update_never_leaves_weight_range_under_repeated_extremes():
    edge = _edge(weight=0.0)
    for _ in range(2000):
        apply_oja_update(
            edge, source_activation=1.0, target_activation=1.0, learning_rate=0.9, modulation=1.0, eligible=True
        )
    assert WEIGHT_RANGE[0] <= edge.weight <= WEIGHT_RANGE[1]


# --- end-to-end demonstration ---


def test_a_predictor_measurably_learns_a_periodic_signal_over_many_ticks():
    from symbiont.cognition.graph import TickContext

    sense = PlasticNode(node_id="s", kind=NodeKind.SENSE)
    predictor = PlasticNode(node_id="p", kind=NodeKind.PREDICTOR, predicts_node_id="s", bias=0.0, tau=1.0)
    feed = PlasticEdge(
        source_id="s", target_id="p", kind=EdgeKind.PREDICTIVE, weight=0.05, plasticity=0.5, delay_ticks=0
    )
    graph = CognitiveGraph(nodes=(sense, predictor), edges=(feed,), kernel_limits=KernelLimits())

    previous_frame: dict[str, float] = {}
    losses: list[float] = []
    for tick in range(1, 201):
        signal = 0.8 if tick % 2 == 0 else -0.8
        frame = graph.activate(inputs={"s": signal}, context=TickContext(tick=tick), previous=previous_frame)

        errors = compute_prediction_errors(graph, current=frame.activations, previous=previous_frame)
        for error in errors:
            update_eligibility(
                feed, source_previous=previous_frame.get("s", 0.0), target_current=frame.activations["p"], decay=0.9
            )
            apply_oja_update(
                feed,
                source_activation=previous_frame.get("s", 0.0),
                target_activation=frame.activations["p"],
                learning_rate=0.05,
                modulation=1.0,
                eligible=True,
            )
            losses.append(error.loss)

        previous_frame = dict(frame.activations)

    early_average = sum(losses[:20]) / 20
    late_average = sum(losses[-20:]) / 20
    assert late_average < early_average
