import pytest

from symbiont.core.agent import Agent
from symbiont.core.beliefs import BeliefModel
from symbiont.core.collective import CollectiveMemory
from symbiont.core.model import Observation


def test_belief_strengthens_without_ground_truth():
    beliefs = BeliefModel()
    revisions = [
        beliefs.revise(
            fingerprint="H-H-H-M-H",
            probability=0.82,
            confidence=0.70,
            step=step,
        )
        for step in range(8)
    ]

    probability, certainty = beliefs.belief("H-H-H-M-H")

    assert probability == pytest.approx(0.82)
    assert certainty > revisions[0].certainty
    assert beliefs.states["H-H-H-M-H"].revisions == 8


def test_conflicting_evidence_reduces_certainty_and_can_reverse_belief():
    beliefs = BeliefModel()
    for step in range(4):
        beliefs.revise(
            fingerprint="M-M-H-M-M",
            probability=0.90,
            confidence=0.80,
            step=step,
        )
    consistent = BeliefModel()
    for step in range(4, 16):
        consistent.revise(
            fingerprint="M-M-H-M-M",
            probability=0.90,
            confidence=1.0,
            step=step,
        )

    last = None
    for step in range(4, 16):
        last = beliefs.revise(
            fingerprint="M-M-H-M-M",
            probability=0.05,
            confidence=1.0,
            step=step,
        )

    probability, certainty_after = beliefs.belief("M-M-H-M-M")
    assert last is not None
    assert probability < 0.5
    assert beliefs.states["M-M-H-M-M"].reversals == 1
    assert beliefs.states["M-M-H-M-M"].conflict > 0
    assert certainty_after < consistent.belief("M-M-H-M-M")[1]


def test_belief_model_is_bounded_and_evicts_weak_old_pattern():
    beliefs = BeliefModel(max_patterns=2)
    beliefs.revise(fingerprint="old", probability=0.5, confidence=0.0, step=0)
    beliefs.revise(fingerprint="strong", probability=0.9, confidence=1.0, step=1)
    beliefs.revise(fingerprint="new", probability=0.7, confidence=0.8, step=2)

    assert set(beliefs.states) == {"strong", "new"}


def test_agent_uses_only_prior_local_belief_in_current_assessment():
    agent = Agent("agent-belief")
    collective = CollectiveMemory()
    observation = Observation(0.42, 0.48, 0.50, 0.35, 0.40)
    fp = "M-M-M-M-M"

    baseline = agent.assess(observation, collective)
    for step in range(12):
        agent.beliefs.revise(
            fingerprint=fp,
            probability=0.90,
            confidence=0.90,
            step=step,
        )
    informed = agent.assess(observation, collective)

    assert informed.local_certainty > 0.5
    assert informed.threat_probability > baseline.threat_probability


def test_rejects_invalid_or_stale_evidence():
    beliefs = BeliefModel()
    beliefs.revise(fingerprint="pattern", probability=0.4, confidence=0.5, step=2)

    with pytest.raises(ValueError):
        beliefs.revise(fingerprint="pattern", probability=1.1, confidence=0.5, step=3)
    with pytest.raises(ValueError):
        beliefs.revise(fingerprint="pattern", probability=0.4, confidence=0.5, step=1)
