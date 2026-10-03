"""Intent reconciliation precedes new cognition and deliberation (§76, §103)."""

from __future__ import annotations

import pytest

from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject
from symbiont.agency.intention import IntentStatus
from symbiont.agency.prospective import ProspectiveDecision
from symbiont.core.domains.action import ActionDomain
from symbiont.core.domains.cognition import CognitionDomain
from symbiont.core.domains.intention import IntentionDomain


def _run_until_satisfied(monkeypatch, ticks: int = 600):
    body = CausalBody(actuator_count=4, seed=7)
    runtime = build_subject(body, organism_id="feedback-ordering")
    seen_by_cognition: dict[int, tuple] = {}
    seen_by_act: dict[int, tuple] = {}

    original_cognition = CognitionDomain.step
    original_act = ActionDomain.act

    def cognition_spy(self, **kwargs):
        seen_by_cognition[kwargs["context"].symbiont_tick] = kwargs[
            "action_projection"
        ].intent_outcomes
        return original_cognition(self, **kwargs)

    def act_spy(self, cognition, percepts, observation, **kwargs):
        seen_by_act[observation.tick] = tuple(
            (outcome.intent_id, outcome.status) for outcome in self.intention.last_outcomes
        )
        return original_act(self, cognition, percepts, observation, **kwargs)

    monkeypatch.setattr(CognitionDomain, "step", cognition_spy)
    monkeypatch.setattr(ActionDomain, "act", act_spy)
    for _ in range(ticks):
        runtime.tick()
        body.advance(runtime.last_actuations)
        satisfied = [
            outcome
            for outcome in runtime._action_domain.intention.last_outcomes
            if outcome.status is IntentStatus.SATISFIED
        ]
        if satisfied:
            return runtime, satisfied[0], seen_by_cognition, seen_by_act
    pytest.fail("no intent was satisfied by real consequences")


def test_previous_effect_reconciles_intent_before_new_deliberation(monkeypatch):
    runtime, outcome, _cognition, seen_by_act = _run_until_satisfied(monkeypatch)
    tick = outcome.tick
    # The satisfaction produced by the previous command is already settled
    # when this tick's deliberation (act) begins.
    assert (outcome.intent_id, IntentStatus.SATISFIED) in seen_by_act[tick]
    held = runtime._action_domain.intention.active
    assert held is None or held.intent_id != outcome.intent_id or held.terminal


def test_cognition_sees_intent_satisfaction_same_tick(monkeypatch):
    _runtime, outcome, seen_by_cognition, _act = _run_until_satisfied(monkeypatch)
    projected = seen_by_cognition[outcome.tick]
    assert (outcome.intent_id, outcome.competence_id, "satisfied", outcome.reason) in projected


def test_failed_intent_is_not_reused_as_active():
    domain = IntentionDomain(organism_id="organism.i")
    decision = ProspectiveDecision(
        competence_id="competence.c",
        anticipated_effect_id="effect.e",
        prediction_ref=None,
        confidence=0.5,
        epistemic_relevance=0.5,
        homeostatic_relevance=0.0,
        origin_refs=("readout.primitive.competence.c",),
    )
    failed = domain.form(decision, context_ref=None, embodiment_id=None, tick=1)
    domain.activate(failed.intent_id, commitment_id="commitment.a", tick=1)
    domain.fail(failed.intent_id, reason="stagnation", tick=5)
    retry = domain.form(decision, context_ref=None, embodiment_id=None, tick=6)
    assert retry.intent_id != failed.intent_id
    assert failed.status is IntentStatus.FAILED
    with pytest.raises(KeyError):
        domain.activate(failed.intent_id, commitment_id="commitment.b", tick=6)
