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
