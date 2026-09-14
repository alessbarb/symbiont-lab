from __future__ import annotations

import math
from dataclasses import dataclass

_EWMA_ALPHA = 0.06  # matches core/selfmodel.py's SELF_MODEL_EWMA_ALPHA convention
_VARIANCE_FLOOR = 1e-6


@dataclass(slots=True)
class SensoryNormalizer:
    """Converts a raw sensor reading into a bounded, graph-ready
    activation via a robust z-score against this sense's own running
    statistics, then a tanh squash (master doc §5.4). Independent per
    sense_id -- callers keep one instance per sense."""

    mean: float = 0.0
    variance: float = 0.0
    count: int = 0

    def normalize(self, raw_value: float, *, z_max: float = 4.0, softness: float = 2.0) -> float:
        stdev = math.sqrt(max(self.variance, _VARIANCE_FLOOR))
        z_score = (raw_value - self.mean) / stdev
        clipped = max(-z_max, min(z_max, z_score))
        activation = math.tanh(clipped / softness)

        self.count += 1
        if self.count == 1:
            self.mean = raw_value
            self.variance = 0.0
        else:
            delta = raw_value - self.mean
            self.mean += _EWMA_ALPHA * delta
            self.variance = (1.0 - _EWMA_ALPHA) * self.variance + _EWMA_ALPHA * delta * delta

        return activation
