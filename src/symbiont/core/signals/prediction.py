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


class RidgePredictor:
    """Tiny bounded online ridge regressor kept entirely in volatile memory.

    Rows are supplied only after their target is known.  The intercept is
    added internally and the normal equations are solved afresh, keeping the
    implementation deterministic and avoiding an unbounded optimizer state.
    """

    def __init__(self, *, history_limit: int = 64, regularization: float = 1e-6) -> None:
        if history_limit < 2 or history_limit > 64:
            raise ValueError("history_limit must be between 2 and 64")
        if not math.isfinite(regularization) or regularization <= 0:
            raise ValueError("regularization must be positive and finite")
        self._rows: deque[tuple[tuple[float, ...], float]] = deque(maxlen=history_limit)
        self.regularization = float(regularization)

    def observe(self, features: tuple[float, ...], target: float) -> None:
        if not features or any(isinstance(x, bool) or not math.isfinite(float(x)) for x in features):
            raise ValueError("features must be finite numeric values")
        if isinstance(target, bool) or not math.isfinite(float(target)):
            raise ValueError("target must be finite")
        row = tuple(float(x) for x in features)
        if self._rows and len(row) != len(self._rows[0][0]):
            raise ValueError("feature width changed")
        self._rows.append((row, float(target)))

    def predict(self, features: tuple[float, ...]) -> float | None:
        if not self._rows or len(features) != len(self._rows[0][0]):
            return None
        x = [1.0, *(float(v) for v in features)]
        if any(not math.isfinite(v) for v in x):
            return None
        width = len(x)
        matrix = [[0.0] * (width + 1) for _ in range(width)]
        for row, target in self._rows:
            z = [1.0, *row]
            for i in range(width):
                for j in range(width): matrix[i][j] += z[i] * z[j]
                matrix[i][-1] += z[i] * target
        for i in range(1, width): matrix[i][i] += self.regularization
        # Gaussian elimination with pivoting; singular rows simply censor
        # this trial instead of emitting a non-finite prediction.
        for col in range(width):
            pivot = max(range(col, width), key=lambda r: abs(matrix[r][col]))
            if abs(matrix[pivot][col]) < 1e-12: return None
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            divisor = matrix[col][col]
            matrix[col] = [v / divisor for v in matrix[col]]
            for r in range(width):
                if r == col: continue
                factor = matrix[r][col]
                matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[col])]
        value = sum(matrix[i][-1] * x[i] for i in range(width))
        return value if math.isfinite(value) else None

    @property
    def count(self) -> int:
        return len(self._rows)


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


__all__ = ["PredictionTrial", "BoundedPredictor", "RidgePredictor", "absolute_loss", "scaled_squared_loss", "improvement_class", "baseline_predictions"]
