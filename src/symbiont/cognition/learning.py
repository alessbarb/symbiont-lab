from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Mapping

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

@dataclass(slots=True)
class ShadowPrediction:
    """Out-of-sample predictor candidate; never mutates the cognitive graph."""
    source_id: str
    target_id: str
    samples: int = 0
    model_loss: float = 0.0
    persistence_loss: float = 0.0
    status: str = "candidate"

    def observe(self, source_previous: float, target_current: float, target_previous: float) -> None:
        # The source value is the one-step model prediction in shadow mode.
        self.samples += 1
        self.model_loss += huber_loss(target_current - source_previous)
        self.persistence_loss += huber_loss(target_current - target_previous)
        if self.samples >= 8 and self.status != "retired":
            self.status = "supported" if self.predictive_gain > 0.0 else "contradicted"
            if self.samples >= 16 and self.status == "contradicted":
                self.status = "retired"

    @property
    def predictive_gain(self) -> float:
        if self.samples == 0:
            return 0.0
        return (self.persistence_loss - self.model_loss) / self.samples

    @property
    def promotable(self) -> bool:
        return self.status == "supported" and self.samples >= 8 and self.predictive_gain > 0.0


@dataclass(slots=True)
class LaggedShadowPrediction:
    """Bounded out-of-graph candidate for a fixed multi-step relation.

    This is deliberately not a causal claim and never mutates a
    ``CognitiveGraph``.  It only asks whether a source value observed a fixed
    number of ticks ago predicts a target better than target persistence.
    Keeping this experiment in shadow mode lets us measure temporal memory
    without silently expanding the canonical graph's one-step semantics.
    """

    source_id: str
    target_id: str
    lag_ticks: int
    samples: int = 0
    model_loss: float = 0.0
    persistence_loss: float = 0.0
    status: str = "candidate"
    _source_history: Deque[float] = field(init=False, repr=False)
    _target_history: Deque[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.lag_ticks <= 16:
            raise ValueError("lag_ticks must be within [1, 16]")
        self._source_history: Deque[float] = deque(maxlen=self.lag_ticks + 1)
        self._target_history: Deque[float] = deque(maxlen=2)

    def observe(self, source_current: float, target_current: float) -> None:
        self._source_history.append(float(source_current))
        self._target_history.append(float(target_current))
        if len(self._source_history) <= self.lag_ticks or len(self._target_history) < 2:
            return

        source_value = self._source_history[0]
        target_previous = self._target_history[-2]
        self.samples += 1
        self.model_loss += huber_loss(target_current - source_value)
        self.persistence_loss += huber_loss(target_current - target_previous)
        if self.samples >= 8 and self.status != "retired":
            self.status = "supported" if self.predictive_gain > 0.0 else "contradicted"
            if self.samples >= 16 and self.status == "contradicted":
                self.status = "retired"

    @property
    def predictive_gain(self) -> float:
        if self.samples == 0:
            return 0.0
        return (self.persistence_loss - self.model_loss) / self.samples

    @property
    def promotable(self) -> bool:
        return self.status == "supported" and self.samples >= 8 and self.predictive_gain > 0.0


@dataclass(slots=True)
class ComposedShadowPrediction:
    """Experimental composition of two learned one-step relations.

    The candidate is deliberately limited to a three-channel chain.  It
    estimates ``m[t] ~= a*x[t-1]`` and ``y[t] ~= b*m[t-1]`` from observations,
    then evaluates the composed prediction ``a*b*x[t-2]`` against target
    persistence.  Rolling evidence makes the second relation revisable after
    a change in dynamics.  The candidate remains outside the graph.
    """

    source_id: str
    intermediate_id: str
    target_id: str
    window_ticks: int = 32
    samples: int = 0
    model_loss: float = 0.0
    persistence_loss: float = 0.0
    status: str = "candidate"
    _source_history: Deque[float] = field(init=False, repr=False)
    _intermediate_history: Deque[float] = field(init=False, repr=False)
    _target_history: Deque[float] = field(init=False, repr=False)
    _first_pairs: Deque[tuple[float, float]] = field(init=False, repr=False)
    _second_pairs: Deque[tuple[float, float]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 8 <= self.window_ticks <= 256:
            raise ValueError("window_ticks must be within [8, 256]")
        self._source_history = deque(maxlen=3)
        self._intermediate_history = deque(maxlen=2)
        self._target_history = deque(maxlen=2)
        self._first_pairs = deque(maxlen=self.window_ticks)
        self._second_pairs = deque(maxlen=self.window_ticks)

    @staticmethod
    def _slope(pairs: Deque[tuple[float, float]]) -> float:
        denominator = sum(source * source for source, _ in pairs)
        if denominator <= 1e-12:
            return 0.0
        return sum(source * target for source, target in pairs) / denominator

    @property
    def first_relation_slope(self) -> float:
        return self._slope(self._first_pairs)

    @property
    def second_relation_slope(self) -> float:
        return self._slope(self._second_pairs)

    def observe(self, source_current: float, intermediate_current: float, target_current: float) -> None:
        source_current = float(source_current)
        intermediate_current = float(intermediate_current)
        target_current = float(target_current)
        if self._source_history:
            self._first_pairs.append((self._source_history[-1], intermediate_current))
        if self._intermediate_history:
            self._second_pairs.append((self._intermediate_history[-1], target_current))

        self._source_history.append(source_current)
        self._intermediate_history.append(intermediate_current)
        self._target_history.append(target_current)
        if len(self._source_history) < 3 or len(self._target_history) < 2:
            return

        predicted = self.first_relation_slope * self.second_relation_slope * self._source_history[0]
        target_previous = self._target_history[-2]
        self.samples += 1
        self.model_loss += huber_loss(target_current - predicted)
        self.persistence_loss += huber_loss(target_current - target_previous)
        if self.samples >= 8 and self.status != "retired":
            self.status = "supported" if self.predictive_gain > 0.0 else "contradicted"
            if self.samples >= 16 and self.status == "contradicted":
                self.status = "retired"

    @property
    def predictive_gain(self) -> float:
        if self.samples == 0:
            return 0.0
        return (self.persistence_loss - self.model_loss) / self.samples

    @property
    def promotable(self) -> bool:
        return self.status == "supported" and self.samples >= 8 and self.predictive_gain > 0.0
