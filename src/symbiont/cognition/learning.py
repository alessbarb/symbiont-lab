from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .graph import CognitiveGraph, PlasticEdge
from .types import WEIGHT_RANGE, NodeKind

ELIGIBILITY_BOUND = 10.0  # generous relative to a_i, a_j in (-1, 1); prevents unbounded growth when decay==1.0


def huber_loss(error: float, delta: float = 1.0) -> float:
    magnitude = abs(error)
    if magnitude <= delta:
        return 0.5 * error * error
    return delta * (magnitude - 0.5 * delta)


@dataclass(slots=True, frozen=True)
class PredictionError:
    predictor_id: str
    target_id: str
    error: float
    loss: float


def compute_prediction_errors(
    graph: CognitiveGraph, *, current: Mapping[str, float], previous: Mapping[str, float]
) -> tuple[PredictionError, ...]:
    predictors = sorted(
        (node for node in graph.nodes if node.kind is NodeKind.PREDICTOR), key=lambda node: node.node_id
    )
    errors: list[PredictionError] = []
    for predictor in predictors:
        if predictor.node_id not in previous:
            continue  # cold start: no prediction was made last tick
        target_id = predictor.predicts_node_id
        assert target_id is not None  # guaranteed by CognitiveGraph construction validation
        target_value = current.get(target_id, 0.0)
        predicted_value = previous[predictor.node_id]
        error = target_value - predicted_value
        errors.append(
            PredictionError(predictor_id=predictor.node_id, target_id=target_id, error=error, loss=huber_loss(error))
        )
    return tuple(errors)


def update_eligibility(edge: PlasticEdge, *, source_previous: float, target_current: float, decay: float) -> None:
    updated = decay * edge.eligibility + source_previous * target_current
    edge.eligibility = max(-ELIGIBILITY_BOUND, min(ELIGIBILITY_BOUND, updated))


def apply_oja_update(
    edge: PlasticEdge,
    *,
    source_activation: float,
    target_activation: float,
    learning_rate: float,
    modulation: float,
    eligible: bool,
    frozen: bool = False,
) -> None:
    if frozen or not eligible or modulation == 0.0:
        return
    delta = learning_rate * modulation * (
        source_activation * target_activation - target_activation * target_activation * edge.weight
    )
    new_weight = edge.weight + delta
    edge.weight = max(WEIGHT_RANGE[0], min(WEIGHT_RANGE[1], new_weight))
