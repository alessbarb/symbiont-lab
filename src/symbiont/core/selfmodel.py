from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from statistics import median
from typing import Any, Collection, Iterable

from ..host.readings import CapabilitySamplingOutcome, ReadingQuality, SamplingOutcomeKind


class RecencyClass(IntEnum):
    """Coarse recency (design docs/design/cognicion-y-plasticidad.md
    §17) replacing SelfModel's one remaining exact durable field."""

    CURRENT = 0
    SHORT_IDLE = 1
    IDLE = 2
    LONG_IDLE = 3
    DORMANT = 4


_RECENCY_REPRESENTATIVE_IDLE_TICKS = {
    RecencyClass.CURRENT: 0,
    RecencyClass.SHORT_IDLE: 10,
    RecencyClass.IDLE: 40,
    RecencyClass.LONG_IDLE: 120,
    RecencyClass.DORMANT: 400,
}
_RECENCY_THRESHOLDS = (
    (10, RecencyClass.CURRENT),
    (40, RecencyClass.SHORT_IDLE),
    (120, RecencyClass.IDLE),
    (400, RecencyClass.LONG_IDLE),
)


def _recency_class(idle_ticks: int) -> RecencyClass:
    for threshold, recency in _RECENCY_THRESHOLDS:
        if idle_ticks < threshold:
            return recency
    return RecencyClass.DORMANT

SELF_MODEL_EWMA_ALPHA = 0.06
MIN_SELF_MODEL_ATTEMPTS = 5
LOW_HEALTH_INVESTIGATION_THRESHOLD = 0.15
IDLE_GRACE_TICKS = 20
_QUALITY_HEALTH: dict[ReadingQuality, float] = {
    ReadingQuality.NOMINAL: 1.0,
    ReadingQuality.DEGRADED: 0.6,
    ReadingQuality.STALE: 0.25,
    ReadingQuality.UNAVAILABLE: 0.0,
}
_OUTCOME_HEALTH: dict[SamplingOutcomeKind, float] = {
    SamplingOutcomeKind.MISSING: 0.0,
    SamplingOutcomeKind.PROVIDER_FAILED: 0.0,
}
_HEALTH_CLASSES = 16
_CONFIDENCE_CLASSES = 16
_MATURITY_CLASSES = 8
_COST_CLASSES = 16
_COST_REFERENCE_S = 1.0  # attributed cost at/above 1s quantizes to the top bin


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _ewma(previous: float, observation: float, alpha: float = SELF_MODEL_EWMA_ALPHA) -> float:
    return alpha * observation + (1 - alpha) * previous


def _idle_decayed(value: float, neutral: float, idle_ticks: int) -> float:
    steps = max(0, idle_ticks - IDLE_GRACE_TICKS)
    if steps == 0:
        return value
    return neutral + (value - neutral) * ((1 - SELF_MODEL_EWMA_ALPHA) ** steps)


@dataclass(slots=True)
class SenseSelfState:
    cost_ewma_s: float = 0.0
    health_ewma: float = 0.5
    quality_ewma: float = 0.5
    confidence_ewma: float = 0.0
    attempts: int = 0
    successes: int = 0
    last_observed_tick: int = 0

    @property
    def established(self) -> bool:
        return self.attempts >= MIN_SELF_MODEL_ATTEMPTS


def _maturity(successes: int) -> float:
    if successes <= 0:
        return 0.0
    return min(1.0, math.log1p(successes) / math.log1p(MIN_SELF_MODEL_ATTEMPTS))


class SelfModel:
    """Bounded, per-sense self-model of cost, health and confidence.

    Composes signals already available from sampling outcomes; never
    duplicates ``AdaptiveSenseModel.SenseState.utility`` (worth watching)
    or ``MetacognitionEngine`` (collective epistemic confidence) — see
    git history for the v0.53 self-model design rationale.
    """

    MAX_SENSES = 256

    def __init__(self) -> None:
        self._states: dict[str, SenseSelfState] = {}

    def _state(self, sense_id: str) -> SenseSelfState | None:
        return self._states.get(sense_id)

    def observe(self, *, outcome: CapabilitySamplingOutcome, tick: int) -> None:
        state = self._states.setdefault(outcome.capability_id, SenseSelfState())
        state.attempts += 1
        state.last_observed_tick = tick
        state.cost_ewma_s = (
            _ewma(state.cost_ewma_s, outcome.attributed_elapsed_s) if state.attempts > 1 else outcome.attributed_elapsed_s
        )

        if outcome.kind is SamplingOutcomeKind.SUCCEEDED:
            state.successes += 1
            health_obs = _QUALITY_HEALTH.get(outcome.quality, 1.0) if outcome.quality else 1.0
        elif outcome.kind is SamplingOutcomeKind.UNAVAILABLE:
            health_obs = 0.0
        else:
            health_obs = _OUTCOME_HEALTH.get(outcome.kind, 0.0)

        state.health_ewma = _clip(_ewma(state.health_ewma, health_obs))
        state.quality_ewma = _clip(_ewma(state.quality_ewma, health_obs))

        maturity = _maturity(state.successes)
        confidence_target = _clip(0.70 * state.health_ewma + 0.30 * state.quality_ewma) * maturity
        state.confidence_ewma = _clip(_ewma(state.confidence_ewma, confidence_target))

    def health(self, sense_id: str, current_tick: int | None = None) -> float:
        state = self._state(sense_id)
        if state is None:
            return 0.5
        if current_tick is None:
            return state.health_ewma
        idle_ticks = max(0, current_tick - state.last_observed_tick)
        return _idle_decayed(state.health_ewma, 0.5, idle_ticks)

    def confidence(self, sense_id: str, current_tick: int | None = None) -> float:
        state = self._state(sense_id)
        if state is None:
            return 0.0
        if current_tick is None:
            return state.confidence_ewma
        idle_ticks = max(0, current_tick - state.last_observed_tick)
        return _idle_decayed(state.confidence_ewma, 0.0, idle_ticks)

    def is_established(self, sense_id: str) -> bool:
        state = self._state(sense_id)
        return state.established if state is not None else False

    def relative_cost(self, sense_id: str, *, reference_ids: Iterable[str]) -> float:
        established_costs = [
            self._states[ref_id].cost_ewma_s
            for ref_id in reference_ids
            if ref_id in self._states and self._states[ref_id].established
        ]
        if not established_costs:
            return 1.0
        reference_median = median(established_costs)
        state = self._state(sense_id)
        if state is None or reference_median <= 0.0:
            return 1.0
        return _clip(state.cost_ewma_s / reference_median, 0.25, 4.0)

    def reconcile(self, allowed_sense_ids: Collection[str]) -> None:
        allowed = set(allowed_sense_ids)
        for sense_id in list(self._states):
            if sense_id not in allowed:
                del self._states[sense_id]

    def export(self, *, current_tick: int) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for sense_id, state in self._states.items():
            if not state.established:
                continue
            idle_ticks = max(0, current_tick - state.last_observed_tick)
            payload[sense_id] = {
                "cost_class": _quantize_cost(state.cost_ewma_s),
                "health_class": _quantize(state.health_ewma, _HEALTH_CLASSES),
                "confidence_class": _quantize(state.confidence_ewma, _CONFIDENCE_CLASSES),
                "maturity_class": _quantize(_maturity(state.successes), _MATURITY_CLASSES),
                "recency_class": _recency_class(idle_ticks).value,
            }
        return payload

    @classmethod
    def restore(
        cls, payload: dict[str, Any] | None, *, allowed_sense_ids: Collection[str], current_tick: int
    ) -> "SelfModel":
        model = cls()
        if not payload:
            return model
        if not isinstance(payload, dict):
            raise ValueError("self_model payload must be a JSON object")
        if len(payload) > cls.MAX_SENSES:
            raise ValueError(f"self_model payload exceeds MAX_SENSES ({cls.MAX_SENSES})")
        allowed = set(allowed_sense_ids)
        for sense_id, entry in payload.items():
            if sense_id not in allowed:
                continue
            if not isinstance(entry, dict):
                raise ValueError(f"self_model entry for {sense_id!r} must be a JSON object")
            cost_class = entry["cost_class"]
            health_class = entry["health_class"]
            confidence_class = entry["confidence_class"]
            maturity_class = entry["maturity_class"]
            recency_class_raw = entry["recency_class"]
            _require_class_range(cost_class, _COST_CLASSES, "cost_class")
            _require_class_range(health_class, _HEALTH_CLASSES, "health_class")
            _require_class_range(confidence_class, _CONFIDENCE_CLASSES, "confidence_class")
            _require_class_range(maturity_class, _MATURITY_CLASSES, "maturity_class")
            _require_class_range(recency_class_raw, len(RecencyClass), "recency_class")
            representative_idle = _RECENCY_REPRESENTATIVE_IDLE_TICKS[RecencyClass(recency_class_raw)]
            last_observed_tick = max(0, current_tick - representative_idle)
            maturity = maturity_class / (_MATURITY_CLASSES - 1)
            successes = int(round(math.expm1(maturity * math.log1p(MIN_SELF_MODEL_ATTEMPTS))))
            state = SenseSelfState(
                cost_ewma_s=_dequantize_cost(cost_class),
                health_ewma=_dequantize(health_class, _HEALTH_CLASSES),
                quality_ewma=_dequantize(health_class, _HEALTH_CLASSES),
                confidence_ewma=_dequantize(confidence_class, _CONFIDENCE_CLASSES),
                attempts=max(successes, MIN_SELF_MODEL_ATTEMPTS),
                successes=successes,
                last_observed_tick=last_observed_tick,
            )
            model._states[sense_id] = state
        return model


def _require_class_range(value: Any, num_classes: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an int")
    if not (0 <= value < num_classes):
        raise ValueError(f"{field_name} out of range [0, {num_classes})")


def _quantize(value: float, num_classes: int) -> int:
    return round(_clip(value) * (num_classes - 1))


def _dequantize(class_id: int, num_classes: int) -> float:
    return class_id / (num_classes - 1)


def _quantize_cost(cost_s: float) -> int:
    ratio = min(1.0, math.log1p(max(0.0, cost_s)) / math.log1p(_COST_REFERENCE_S))
    return round(ratio * (_COST_CLASSES - 1))


def _dequantize_cost(class_id: int) -> float:
    ratio = class_id / (_COST_CLASSES - 1)
    return math.expm1(ratio * math.log1p(_COST_REFERENCE_S))
