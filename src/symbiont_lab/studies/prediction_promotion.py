"""Longitudinal shadow-prediction promotion gate (evaluator-only)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.cognition.learning import ShadowPrediction


@dataclass(frozen=True, slots=True)
class PredictionPromotionStudy:
    signal_trials: int
    signal_gain: float
    signal_promotable: bool
    noise_trials: int
    noise_gain: float
    noise_promotable: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_prediction_promotion_study(*, trials: int = 32) -> PredictionPromotionStudy:
    if trials < 8:
        raise ValueError("trials must be at least 8")
    signal = ShadowPrediction("source", "target")
    noise = ShadowPrediction("source", "noise")
    for index in range(trials):
        previous = float(index % 2)
        # The source predicts the next target exactly; persistence does not.
        target = 1.0 - previous
        signal.observe(previous, target, previous - 0.5)
        # The noise candidate is no better than persistence.
        noise.observe(previous - 0.5, previous, previous)
    return PredictionPromotionStudy(signal.samples, signal.predictive_gain,
                                    signal.promotable, noise.samples,
                                    noise.predictive_gain, noise.promotable)


__all__ = ["PredictionPromotionStudy", "run_prediction_promotion_study"]
