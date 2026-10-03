import pytest

from symbiont.cognition.generative import (
    GenerativeHypothesis,
    GenerativeReconciler,
    HypothesisStatus,
)


def test_hypothesis_requires_explicit_reconciliation_for_factual_status():
    hypothesis = GenerativeHypothesis(
        hypothesis_id="h0",
        source_episode_ids=("e0",),
        source_model_ids=("m0",),
        uncertainty=0.6,
    )
    hypothesis.mark_predicted()
    assert hypothesis.status is HypothesisStatus.PREDICTED
    assert hypothesis.factual_support_refs == ()

    GenerativeReconciler().reconcile(hypothesis, evidence_ref="obs-1", supported=True)
    assert hypothesis.status is HypothesisStatus.SUPPORTED
    assert hypothesis.factual_support_refs == ("obs-1",)

    with pytest.raises(ValueError, match="active hypotheses"):
        GenerativeReconciler().reconcile(hypothesis, evidence_ref="obs-2", supported=False)


def test_hypothesis_conflict_is_not_silent_support():
    hypothesis = GenerativeHypothesis("h1", ("e1",), ("m1",), 0.4)
    GenerativeReconciler().reconcile(hypothesis, evidence_ref="obs-conflict", supported=False)
    assert hypothesis.status is HypothesisStatus.CONTRADICTED
    assert hypothesis.factual_conflict_refs == ("obs-conflict",)
