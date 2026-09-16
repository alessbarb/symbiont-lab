"""Evaluator-only integrated gates for Milestone J."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.cognition.checkpoint import WEIGHT_DEADBAND, dequantize_weight, quantize_weight
from symbiont.core.attention import AttentionBudget, AttentionCandidate
from symbiont.host.hypotheses import HypothesisStatus, HypothesisTracker

from .prediction_promotion import run_prediction_promotion_study
from .runtime_prediction_longitudinal import run_runtime_prediction_longitudinal_study


@dataclass(frozen=True, slots=True)
class PredictiveDevelopmentGateStudy:
    codec_zero_exact: bool
    codec_deadband_preserved: bool
    codec_sign_preserved: bool
    attention_diminishing_returns: bool
    hypothesis_checkpoint_equal: bool
    shadow_gain_gate: bool
    shadow_noise_rejected: bool
    longitudinal_replay_equal: bool
    all_gates_pass: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_predictive_development_gate_study() -> PredictiveDevelopmentGateStudy:
    """Compose J contracts without feeding evaluator outcomes to cognition."""
    codec_zero_exact = dequantize_weight(quantize_weight(0.0)) == 0.0
    codec_deadband_preserved = all(
        dequantize_weight(quantize_weight(value)) == 0.0
        for value in (-WEIGHT_DEADBAND, 0.0, WEIGHT_DEADBAND)
    )
    codec_sign_preserved = all(
        (dequantize_weight(quantize_weight(value)) > 0.0) == (value > 0.0)
        for value in (-0.2, 0.2, -1.0, 1.0)
    )

    allocations = AttentionBudget(budget=1.0).allocate((
        AttentionCandidate(name="repeated", uncertainty=0.9, cost=1.0, observations=100),
        AttentionCandidate(name="fresh", uncertainty=0.8, cost=1.0, observations=0),
    ))
    attention_diminishing_returns = bool(allocations) and allocations[0].name == "fresh"

    tracker = HypothesisTracker()
    tracker.observe(("opaque-a", "opaque-b"), correlation=0.8, samples=6, min_samples=3, tick=1)
    restored = HypothesisTracker.restore(tracker.export())
    hypothesis_checkpoint_equal = restored.items == tracker.items and restored.items[0].status is HypothesisStatus.SUPPORTED

    promotion = run_prediction_promotion_study()
    longitudinal = run_runtime_prediction_longitudinal_study()
    shadow_gain_gate = promotion.signal_promotable
    shadow_noise_rejected = not promotion.noise_promotable
    longitudinal_replay_equal = longitudinal.continuation_replay_equal and longitudinal.signal_promoted
    all_gates_pass = all((
        codec_zero_exact,
        codec_deadband_preserved,
        codec_sign_preserved,
        bool(attention_diminishing_returns),
        hypothesis_checkpoint_equal,
        shadow_gain_gate,
        shadow_noise_rejected,
        longitudinal_replay_equal,
    ))
    return PredictiveDevelopmentGateStudy(
        codec_zero_exact=codec_zero_exact,
        codec_deadband_preserved=codec_deadband_preserved,
        codec_sign_preserved=codec_sign_preserved,
        attention_diminishing_returns=bool(attention_diminishing_returns),
        hypothesis_checkpoint_equal=hypothesis_checkpoint_equal,
        shadow_gain_gate=shadow_gain_gate,
        shadow_noise_rejected=shadow_noise_rejected,
        longitudinal_replay_equal=longitudinal_replay_equal,
        all_gates_pass=all_gates_pass,
    )


__all__ = ["PredictiveDevelopmentGateStudy", "run_predictive_development_gate_study"]
