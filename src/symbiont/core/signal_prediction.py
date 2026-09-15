"""Small, in-memory prediction primitives for opaque signal knowledge.

The predictor intentionally exposes only quantized losses to callers.  It is
not persisted: restoring a runtime must warm up a fresh predictor.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import math


@dataclass(frozen=True, slots=True)
class PredictionTrial:
    subject_id: str
    object_id: str
    horizon: int
    issued_tick: int
    prediction: float
    target_tick: int


class BoundedPredictor:
    """Deterministic past-scale predictor with bounded training history."""

    def __init__(self, *, history_limit: int = 64) -> None:
        if history_limit < 2:
            raise ValueError("history_limit must be at least 2")
        self._history: deque[float] = deque(maxlen=history_limit)

    def predict(self) -> float | None:
        return self._history[-1] if self._history else None

    def observe(self, value: float) -> None:
        if isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError("value must be finite")
        self._history.append(float(value))

    @property
    def count(self) -> int:
        return len(self._history)


def absolute_loss(prediction: float | None, target: float | None) -> float | None:
    if prediction is None or target is None:
        return None
    if not math.isfinite(float(prediction)) or not math.isfinite(float(target)):
        return None
    return abs(float(prediction) - float(target))


def scaled_squared_loss(prediction: float | None, target: float | None,
                        scale: float | None) -> float | None:
    """Protocol loss: bounded squared error in units of past target scale."""
    if prediction is None or target is None or scale is None:
        return None
    try:
        p, t, s = float(prediction), float(target), float(scale)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (p, t, s)) or s < 1e-12:
        return None
    return min(4.0, abs((p - t) / s)) ** 2


def improvement_class(candidate_loss: float | None, baseline_loss: float | None) -> str | None:
    """Classify material improvement only when both losses are comparable."""
    if candidate_loss is None or baseline_loss is None or not all(math.isfinite(v) for v in (candidate_loss, baseline_loss)):
        return None
    if baseline_loss <= 0:
        return "none"
    ratio = (baseline_loss - candidate_loss) / baseline_loss
    if ratio < 0.15 or baseline_loss - candidate_loss < 0.01:
        return "none"
    return "substantial" if ratio >= 0.30 else "material"


def baseline_predictions(history: list[float], *, scale_limit: float = 1e12) -> dict[str, float | None]:
    """Return fixed, non-adaptive references for one-step validation."""
    finite = [float(v) for v in history if math.isfinite(float(v))]
    if not finite:
        return {"zero": 0.0, "mean": None, "persistence": None}
    # The protocol fixes a recent, bounded 64-reading reference window;
    # callers may provide a longer history but the baseline never grows.
    mean = sum(finite[-64:]) / min(64, len(finite))
    if abs(mean) > scale_limit:
        mean = math.copysign(scale_limit, mean)
    return {"zero": 0.0, "mean": mean, "persistence": finite[-1]}


__all__ = ["PredictionTrial", "BoundedPredictor", "absolute_loss", "scaled_squared_loss", "improvement_class", "baseline_predictions"]
