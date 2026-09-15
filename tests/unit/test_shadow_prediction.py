from symbiont.cognition.learning import ShadowPrediction

def test_shadow_prediction_requires_out_of_sample_gain():
    candidate = ShadowPrediction("a", "b")
    for _ in range(8):
        candidate.observe(1.0, 1.0, 0.0)
    assert candidate.samples == 8
    assert candidate.predictive_gain > 0
    assert candidate.promotable

def test_shadow_prediction_does_not_promote_without_gain():
    candidate = ShadowPrediction("a", "b")
    for _ in range(8):
        candidate.observe(0.0, 1.0, 0.0)
    assert not candidate.promotable
