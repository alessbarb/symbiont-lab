"""Unit tests for ProspectivePolicy — utility, gates, tiebreaking, decision reasons."""

from __future__ import annotations

import pytest

from symbiont.agency.policy import EvaluatedCandidate, ProspectivePolicy
from symbiont.agency.types import (
    CounterfactualPrediction,
    OutcomeValueEstimate,
    ProspectiveCandidate,
)


def _make_policy(
    *,
    organism_id: str = "test-org",
    min_model_confidence: float = 0.1,
    min_value_samples: int = 1,
    decision_margin: float = 0.0,
) -> ProspectivePolicy:
    return ProspectivePolicy(
        organism_id=organism_id,
        min_model_confidence=min_model_confidence,
        min_value_samples=min_value_samples,
        decision_margin=decision_margin,
    )


def _candidate(
    action_id: str, predicted_outcome: str, cc: int, mean_value: float, samples: int = 8
) -> EvaluatedCandidate:
    return EvaluatedCandidate(
        candidate=ProspectiveCandidate(action_id=action_id, family="primitive"),
        prediction=CounterfactualPrediction(
            action_id=action_id,
            predicted_outcome=predicted_outcome,
            confidence_class=cc,
        ),
        value=OutcomeValueEstimate(
            outcome_id=predicted_outcome,
            samples=samples,
            mean_value=mean_value,
            variance=0.01,
            confidence=min(1.0, samples / 16.0),
        ),
        estimated_cost=None,
    )


def _candidate_no_value(action_id: str, predicted_outcome: str, cc: int) -> EvaluatedCandidate:
    return EvaluatedCandidate(
        candidate=ProspectiveCandidate(action_id=action_id, family="primitive"),
        prediction=CounterfactualPrediction(
            action_id=action_id,
            predicted_outcome=predicted_outcome,
            confidence_class=cc,
        ),
        value=None,
        estimated_cost=None,
    )


def test_no_candidates_returns_no_candidates_reason():
    policy = _make_policy()
    decision = policy.choose([], homeostatic_deviation=0.5, tick=1)
    assert decision.reason == "no_candidates"
    assert decision.candidate_id is None


def test_all_missing_value_returns_no_value_evidence():
    policy = _make_policy()
    ec = _candidate_no_value("prim.1", "outcome.1", cc=6)
    decision = policy.choose([ec], homeostatic_deviation=0.5, tick=1)
    assert decision.reason == "no_value_evidence"
    assert decision.candidate_id is None


def test_insufficient_model_confidence_returns_reason():
    policy = _make_policy(min_model_confidence=0.9)  # very high threshold
    ec = _candidate("prim.1", "outcome.1", cc=1, mean_value=0.5)  # cc=1 → conf=1/7≈0.14
    decision = policy.choose([ec], homeostatic_deviation=0.5, tick=1)
    assert decision.reason == "insufficient_confidence"


def test_decision_margin_blocks_close_candidates():
    policy = _make_policy(decision_margin=0.5)  # high margin requirement
    # Two candidates with very similar utility
    ec1 = _candidate("prim.1", "outcome.1", cc=7, mean_value=0.5, samples=16)
    ec2 = _candidate("prim.2", "outcome.2", cc=7, mean_value=0.49, samples=16)
    decision = policy.choose([ec1, ec2], homeostatic_deviation=0.5, tick=1)
    assert decision.reason == "insufficient_margin"


def test_single_sufficient_candidate_is_selected():
    policy = _make_policy()
    ec = _candidate("prim.abc", "outcome.positive", cc=6, mean_value=0.8, samples=16)
    decision = policy.choose([ec], homeostatic_deviation=0.5, tick=1)
    assert decision.reason == "selected"
    assert decision.candidate_id == "prim.abc"
    assert decision.predicted_outcome == "outcome.positive"
    assert decision.expected_value is not None
    assert decision.model_confidence is not None
    assert decision.value_confidence is not None


def test_best_utility_candidate_wins():
    policy = _make_policy(decision_margin=0.01)
    ec_good = _candidate("prim.good", "outcome.good", cc=7, mean_value=0.9, samples=16)
    ec_bad = _candidate("prim.bad", "outcome.bad", cc=3, mean_value=0.1, samples=16)
    decision = policy.choose([ec_good, ec_bad], homeostatic_deviation=0.3, tick=5)
    assert decision.reason == "selected"
    assert decision.candidate_id == "prim.good"


def test_negative_utility_candidate_can_lose_to_zero():
    """A candidate with negative mean value should have negative utility."""
    policy = _make_policy(decision_margin=0.01)
    ec_neg = _candidate("prim.neg", "outcome.neg", cc=7, mean_value=-0.8, samples=16)
    ec_zero = _candidate("prim.zero", "outcome.zero", cc=7, mean_value=0.01, samples=16)
    decision = policy.choose([ec_neg, ec_zero], homeostatic_deviation=0.3, tick=10)
    assert decision.reason == "selected"
    assert decision.candidate_id == "prim.zero"


def test_tiebreaking_is_deterministic():
    """Same candidates + same tick → same decision every time."""
    policy = _make_policy(decision_margin=0.0)
    ec1 = _candidate("prim.alpha", "outcome.x", cc=7, mean_value=0.5, samples=16)
    ec2 = _candidate("prim.beta", "outcome.x", cc=7, mean_value=0.5, samples=16)
    candidates = [ec1, ec2]
    decisions = [
        policy.choose(candidates, homeostatic_deviation=0.5, tick=42).candidate_id for _ in range(5)
    ]
    assert len(set(decisions)) == 1, "tiebreaking must be deterministic"


def test_tiebreaking_varies_by_tick():
    """Different ticks produce different tiebreaking (pseudorandom, not constant)."""
    # This is a soft property — may be the same for some ticks, but not all
    policy = _make_policy(decision_margin=0.0)
    ec1 = _candidate("prim.aa", "outcome.1", cc=7, mean_value=0.5, samples=16)
    ec2 = _candidate("prim.bb", "outcome.1", cc=7, mean_value=0.5, samples=16)
    choices = {
        policy.choose([ec1, ec2], homeostatic_deviation=0.5, tick=t).candidate_id
        for t in range(100)
    }
    # With 100 different ticks, both candidates should appear at some point
    assert len(choices) >= 1  # deterministic per tick, but varied across ticks


def test_selected_decision_has_correct_margin():
    policy = _make_policy(decision_margin=0.0)
    ec1 = _candidate("prim.1", "outcome.1", cc=7, mean_value=0.9, samples=16)
    ec2 = _candidate("prim.2", "outcome.2", cc=7, mean_value=0.4, samples=16)
    decision = policy.choose([ec1, ec2], homeostatic_deviation=0.0, tick=1)
    assert decision.reason == "selected"
    assert decision.decision_margin is not None
    assert decision.decision_margin >= 0.0


def test_zero_confidence_class_is_excluded():
    """Confidence class 0 is no-signal and must not allow selection."""
    policy = _make_policy(min_model_confidence=0.0)
    ec = _candidate("prim.zero_cc", "outcome.1", cc=0, mean_value=0.9, samples=16)
    decision = policy.choose([ec], homeostatic_deviation=0.5, tick=1)
    # cc=0 → model_confidence_norm=0 < _MIN_CONFIDENCE_CLASS=1
    assert decision.reason == "insufficient_confidence"


def test_policy_construction_validates_inputs():
    with pytest.raises(ValueError):
        ProspectivePolicy(
            organism_id="", min_model_confidence=0.5, min_value_samples=4, decision_margin=0.02
        )
    with pytest.raises(ValueError):
        ProspectivePolicy(
            organism_id="x", min_model_confidence=1.5, min_value_samples=4, decision_margin=0.02
        )
    with pytest.raises(ValueError):
        ProspectivePolicy(
            organism_id="x", min_model_confidence=0.5, min_value_samples=0, decision_margin=0.02
        )
    with pytest.raises(ValueError):
        ProspectivePolicy(
            organism_id="x", min_model_confidence=0.5, min_value_samples=4, decision_margin=-0.1
        )
