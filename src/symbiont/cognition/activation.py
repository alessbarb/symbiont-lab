from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.foundation.epistemic import DEFAULT_EPISTEMIC_CONVENTIONS

_EWMA_ALPHA = DEFAULT_EPISTEMIC_CONVENTIONS.ewma_alpha
_VARIANCE_FLOOR = 1e-6
MIN_NORMALIZER_SAMPLES = DEFAULT_EPISTEMIC_CONVENTIONS.established_signal_min_samples


@dataclass(slots=True)
class SensoryNormalizer:
    """Converts a raw sensor reading into a bounded, graph-ready
    activation via a robust z-score against this sense's own running
    statistics, then a tanh squash (master doc §5.4). Independent per
    sense_id -- callers keep one instance per sense."""

    mean: float = 0.0
    variance: float = 0.0
    count: int = 0

    @property
    def is_established(self) -> bool:
        """Below MIN_NORMALIZER_SAMPLES, ``mean`` is not yet an aggregate
        statistic -- after the first observation it is literally equal to
        that raw reading (see ``normalize``'s cold-start branch). A
        caller persisting this state (e.g. a future checkpoint) must gate
        export on this, the same discipline every other stat tracker in
        this codebase already follows (``AdaptiveSenseModel``,
        ``SelfModel``) -- exporting an unestablished normalizer would
        persist a value indistinguishable from a single raw telemetry
        sample, which CLAUDE.md prohibits."""
        return self.count >= MIN_NORMALIZER_SAMPLES

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
