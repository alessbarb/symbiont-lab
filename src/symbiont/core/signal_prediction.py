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


def baseline_predictions(history: list[float], *, scale_limit: float = 1e12) -> dict[str, float | None]:
    """Return fixed, non-adaptive references for one-step validation."""
    finite = [float(v) for v in history if math.isfinite(float(v))]
    if not finite:
        return {"zero": 0.0, "mean": None, "persistence": None}
    mean = sum(finite[-32:]) / min(32, len(finite))
    if abs(mean) > scale_limit:
        mean = math.copysign(scale_limit, mean)
    return {"zero": 0.0, "mean": mean, "persistence": finite[-1]}


__all__ = ["PredictionTrial", "BoundedPredictor", "absolute_loss", "baseline_predictions"]
