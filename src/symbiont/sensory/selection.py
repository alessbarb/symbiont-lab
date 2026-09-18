from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping


SELECTION_SCHEMA_VERSION = 1
MAX_SELECTION_PAIRS = 256
MIN_SELECTION_OBSERVATIONS = 8
_SELECTION_ALPHA = 0.15
_SELECTION_FORGETTING = 0.97


@dataclass(slots=True)
class PairwisePredictiveEvidence:
    """Bounded lag-1 predictive evidence between two organism percepts."""

    source_id: str
    target_id: str
    observations: int = 0
    effective_weight: float = 0.0
    sum_x: float = 0.0
    sum_y: float = 0.0
    sum_xx: float = 0.0
    sum_xy: float = 0.0
    gain_ewma: float = 0.0
    model_error_ewma: float = 0.0
    baseline_error_ewma: float = 0.0
    last_target: float | None = None

    def _predict(self, x: float) -> float | None:
        if self.observations < 4:
            return None
        if self.effective_weight < 2.0:
            return None
        n = self.effective_weight
        denominator = self.sum_xx - (self.sum_x * self.sum_x) / n
        if abs(denominator) <= 1e-12:
            return None
        slope = (self.sum_xy - (self.sum_x * self.sum_y) / n) / denominator
        intercept = (self.sum_y - slope * self.sum_x) / n
        prediction = intercept + slope * x
        return prediction if math.isfinite(prediction) else None

    def observe(self, x: float, y: float) -> None:
        if not math.isfinite(x) or not math.isfinite(y):
            return
        prediction = self._predict(x)
        mean_prediction = (
            self.sum_y / self.effective_weight
            if self.effective_weight > 0.0
            else None
        )
        if prediction is not None and self.last_target is not None and mean_prediction is not None:
            model_error = abs(y - prediction)
            persistence_error = abs(y - self.last_target)
            mean_error = abs(y - mean_prediction)
            baseline_error = min(persistence_error, mean_error)
            scale = max(abs(y), abs(self.last_target), abs(mean_prediction), 1e-6)
            denominator = baseline_error + 0.05 * scale
            instantaneous = (baseline_error - model_error) / denominator
            instantaneous = max(-1.0, min(1.0, instantaneous))
            alpha = 1.0 if self.observations == 4 else _SELECTION_ALPHA
            self.gain_ewma = (1.0 - alpha) * self.gain_ewma + alpha * instantaneous
            self.model_error_ewma = (1.0 - alpha) * self.model_error_ewma + alpha * model_error
            self.baseline_error_ewma = (
                (1.0 - alpha) * self.baseline_error_ewma + alpha * baseline_error
            )

        self.observations += 1
        self.effective_weight = _SELECTION_FORGETTING * self.effective_weight + 1.0
        self.sum_x = _SELECTION_FORGETTING * self.sum_x + x
        self.sum_y = _SELECTION_FORGETTING * self.sum_y + y
        self.sum_xx = _SELECTION_FORGETTING * self.sum_xx + x * x
        self.sum_xy = _SELECTION_FORGETTING * self.sum_xy + x * y
        self.last_target = y

    @property
    def positive_gain(self) -> float:
        if self.observations < max(16, MIN_SELECTION_OBSERVATIONS):
            return 0.0
        if self.baseline_error_ewma <= 1e-12:
            return 0.0
        relative_gain = (
            self.baseline_error_ewma - self.model_error_ewma
        ) / (self.baseline_error_ewma + 1e-12)
        # A weak positive fluctuation is not enough to become sensory fitness.
        if relative_gain <= 0.05:
            return 0.0
        return max(0.0, min(1.0, relative_gain))

    def checkpoint(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def restore(cls, payload: Mapping[str, Any]) -> "PairwisePredictiveEvidence":
        if not isinstance(payload, Mapping):
            raise ValueError("selection evidence must be an object")
        evidence = cls(
            source_id=payload.get("source_id"),
            target_id=payload.get("target_id"),
            observations=payload.get("observations", 0),
            effective_weight=payload.get(
                "effective_weight",
                min(float(payload.get("observations", 0)), 1.0 / (1.0 - _SELECTION_FORGETTING)),
            ),
            sum_x=payload.get("sum_x", 0.0),
            sum_y=payload.get("sum_y", 0.0),
            sum_xx=payload.get("sum_xx", 0.0),
            sum_xy=payload.get("sum_xy", 0.0),
            gain_ewma=payload.get("gain_ewma", 0.0),
            model_error_ewma=payload.get("model_error_ewma", 0.0),
            baseline_error_ewma=payload.get(
                "baseline_error_ewma",
                payload.get("persistence_error_ewma", 0.0),
            ),
            last_target=payload.get("last_target"),
        )
        if not isinstance(evidence.source_id, str) or not evidence.source_id:
            raise ValueError("selection source_id must be non-empty")
        if not isinstance(evidence.target_id, str) or not evidence.target_id:
            raise ValueError("selection target_id must be non-empty")
        if isinstance(evidence.observations, bool) or not isinstance(evidence.observations, int) or evidence.observations < 0:
            raise ValueError("selection observations must be non-negative integer")
        for name in (
            "effective_weight", "sum_x", "sum_y", "sum_xx", "sum_xy", "gain_ewma",
            "model_error_ewma", "baseline_error_ewma",
        ):
            value = getattr(evidence, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"selection {name} must be finite")
        if evidence.effective_weight < 0.0:
            raise ValueError("selection effective_weight must be non-negative")
        if evidence.last_target is not None and (
            isinstance(evidence.last_target, bool)
            or not isinstance(evidence.last_target, (int, float))
            or not math.isfinite(float(evidence.last_target))
        ):
            raise ValueError("selection last_target must be finite when present")
        return evidence


class SensorySelectionEngine:
    """Target-free organism-side competition based on lag-1 predictive utility.

    Every receptor may compete to predict every identity percept except itself.
    The engine never receives evaluator labels, expected roles or a chosen
    target.  It simply asks whether a receptor carries information that improves
    prediction of another directly experienced stream over persistence.
    """

    def __init__(self, *, max_pairs: int = MAX_SELECTION_PAIRS) -> None:
        if isinstance(max_pairs, bool) or not isinstance(max_pairs, int) or max_pairs <= 0:
            raise ValueError("max_pairs must be a positive integer")
        self.max_pairs = max_pairs
        self._pairs: dict[tuple[str, str], PairwisePredictiveEvidence] = {}
        self._previous: dict[str, float] = {}
        self._credits: dict[str, float] = {}

    @property
    def credits(self) -> dict[str, float]:
        return dict(self._credits)

    def observe(
        self,
        values: Mapping[str, float],
        *,
        identity_targets: set[str],
    ) -> dict[str, float]:
        current = {
            sensor_id: float(value)
            for sensor_id, value in values.items()
            if isinstance(sensor_id, str)
            and sensor_id
            and not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value))
        }
        targets = sorted(sensor_id for sensor_id in identity_targets if sensor_id in current)
        if self._previous:
            source_ids = sorted(self._previous)
            # Fair bounded admission: every active receptor gets a comparable
            # number of target opportunities instead of allowing early lexical
            # IDs to consume the global pair budget.
            per_source_cap = max(1, self.max_pairs // max(1, len(source_ids)))
            for source_id in source_ids:
                x = self._previous[source_id]
                admitted = 0
                for target_id in targets:
                    if source_id == target_id:
                        continue
                    key = (source_id, target_id)
                    evidence = self._pairs.get(key)
                    if evidence is None:
                        if admitted >= per_source_cap or len(self._pairs) >= self.max_pairs:
                            continue
                        evidence = PairwisePredictiveEvidence(source_id, target_id)
                        self._pairs[key] = evidence
                    evidence.observe(x, current[target_id])
                    admitted += 1

        credits: dict[str, float] = {}
        for evidence in self._pairs.values():
            if evidence.positive_gain <= 0.0:
                continue
            credits[evidence.source_id] = max(
                credits.get(evidence.source_id, 0.0),
                evidence.positive_gain,
            )
        self._credits = credits
        self._previous = current
        return dict(credits)

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": SELECTION_SCHEMA_VERSION,
            "max_pairs": self.max_pairs,
            "pairs": [
                self._pairs[key].checkpoint()
                for key in sorted(self._pairs)
            ],
            # Previous raw percept values are deliberately transient/private.
        }

    @classmethod
    def restore(cls, payload: Mapping[str, Any] | None) -> "SensorySelectionEngine":
        if payload is None:
            return cls()
        if not isinstance(payload, Mapping) or payload.get("schema_version") != SELECTION_SCHEMA_VERSION:
            raise ValueError("unsupported sensory selection checkpoint")
        engine = cls(max_pairs=payload.get("max_pairs", MAX_SELECTION_PAIRS))
        raw_pairs = payload.get("pairs", [])
        if not isinstance(raw_pairs, list) or len(raw_pairs) > engine.max_pairs:
            raise ValueError("invalid sensory selection pair list")
        for raw in raw_pairs:
            evidence = PairwisePredictiveEvidence.restore(raw)
            key = (evidence.source_id, evidence.target_id)
            if key in engine._pairs:
                raise ValueError("duplicate sensory selection pair")
            engine._pairs[key] = evidence
        engine._credits = {}
        return engine
