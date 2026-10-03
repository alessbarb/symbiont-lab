from symbiont.cognition.generative import (
    GenerativeHypothesis,
    GenerativeReconciler,
)


def test_hypothesis_checkpoint_preserves_non_authoritative_lifecycle():
    hypothesis = GenerativeHypothesis(
        hypothesis_id="h0",
        source_episode_ids=("e0",),
        source_model_ids=("m0",),
        uncertainty=0.6,
    )
    GenerativeReconciler().reconcile(hypothesis, evidence_ref="obs-0", supported=True)

    restored = GenerativeHypothesis.from_checkpoint(hypothesis.checkpoint())

    assert restored.checkpoint() == hypothesis.checkpoint()
