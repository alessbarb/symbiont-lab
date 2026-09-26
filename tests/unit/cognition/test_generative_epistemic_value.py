import pytest

from symbiont.cognition.generative import EpistemicValueEstimator


def test_epistemic_value_is_comparison_signal_not_action_authority():
    value = EpistemicValueEstimator.estimate(
        candidate_ref="candidate-1",
        current_uncertainty=0.8,
        expected_uncertainty=0.3,
        expected_hypothesis_discrimination=0.7,
        model_disagreement=0.4,
    )
    assert value.expected_uncertainty_reduction == 0.5
    assert value.comparison_score == pytest.approx((0.5 + 0.7 + 0.4) / 3.0)
    assert not hasattr(value, "action_id")


def test_pairwise_discrimination_uses_only_internal_forecast_disagreement():
    assert EpistemicValueEstimator.pairwise_discrimination(()) == 0.0
    assert EpistemicValueEstimator.pairwise_discrimination((("x",),)) == 0.0
    assert EpistemicValueEstimator.pairwise_discrimination((("x",), ("x",))) == 0.0
    assert EpistemicValueEstimator.pairwise_discrimination((("x",), ("y",))) == 1.0
    assert EpistemicValueEstimator.pairwise_discrimination(
        (("x",), ("y",), ("y",))
    ) == pytest.approx(2 / 3)
