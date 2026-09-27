"""ActionIntent lifecycle owned by IntentionDomain (§39-§71, §100)."""

from __future__ import annotations

import pytest

from symbiont.actuation.commitment import CommitmentStatus
from symbiont.agency.intention import IntentStatus
from symbiont.agency.prospective import ProspectiveDecision
from symbiont.core.domains.intention import (
    ANTICIPATED_EFFECT_OBSERVED,
    COMPETENCE_NOT_EXECUTABLE,
    EMBODIMENT_CHANGED,
    PROPOSAL_NOT_SELECTED,
    PROTECTION_TAKES_PRIORITY,
    REPEATED_HIGH_MISMATCH,
    IntentionDomain,
)
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject

DECISION = ProspectiveDecision(
    competence_id="competence.c",
    anticipated_effect_id="effect.e",
    prediction_ref="prediction.p",
    confidence=0.6,
    epistemic_relevance=0.4,
    homeostatic_relevance=0.0,
    origin_refs=("readout.primitive.competence.c", "affordance.a"),
    supporting_affordance_id="affordance.a",
)


def _active(domain: IntentionDomain, *, tick: int = 1):
    intent = domain.form(DECISION, context_ref="context.x", embodiment_id="e1", tick=tick)
    domain.activate(intent.intent_id, commitment_id="commitment.k", tick=tick)
    return intent


def _observe(domain, *, similarity, effect="effect.other", tick, status=CommitmentStatus.ACTIVE):
    return domain.observe_effect(
        observed_effect_id=effect,
        prediction_error=None,
        effect_similarity=similarity,
        tick=tick,
        commitment_id="commitment.k",
        commitment_status=status,
        competence_executable=True,
        embodiment_id="e1",
    )


def test_prospective_decision_can_form_pending_intent():
    domain = IntentionDomain(organism_id="organism.i")
    intent = domain.form(DECISION, context_ref="context.x", embodiment_id="e1", tick=4)
    assert intent.status is IntentStatus.PENDING
    assert intent.competence_id == "competence.c"
    assert intent.anticipated_effect_id == "effect.e"
    assert intent.origin_refs == DECISION.origin_refs
    assert intent.supporting_affordance_id == "affordance.a"
    assert intent.created_tick == 4 and intent.activated_tick is None


def test_pending_intent_has_no_motor_authority():
    domain = IntentionDomain(organism_id="organism.i")
    intent = domain.form(DECISION, context_ref=None, embodiment_id=None, tick=1)
    assert domain.active_commitment_id is None
    assert intent.activated_tick is None
    assert not any(hasattr(domain, name) for name in ("commit", "issue_command", "arbitrate"))


def test_selected_proposal_activates_intent():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain, tick=5)
    assert intent.status is IntentStatus.ACTIVE
    assert intent.activated_tick == 5
    assert domain.active_commitment_id == "commitment.k"


def test_unselected_proposal_rejects_intent():
    domain = IntentionDomain(organism_id="organism.i")
    intent = domain.form(DECISION, context_ref=None, embodiment_id=None, tick=1)
    outcome = domain.reject(intent.intent_id, reason=PROPOSAL_NOT_SELECTED, tick=1)
    assert intent.status is IntentStatus.REJECTED
    assert outcome.reason == PROPOSAL_NOT_SELECTED
    assert domain.counts[IntentStatus.REJECTED] == 1
    with pytest.raises(ValueError):
        domain.interrupt(intent.intent_id, reason=PROTECTION_TAKES_PRIORITY, tick=2)


def test_active_intent_can_be_interrupted():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain)
    domain.interrupt(intent.intent_id, reason=PROTECTION_TAKES_PRIORITY, tick=2)
    assert intent.status is IntentStatus.INTERRUPTED
    pending = IntentionDomain(organism_id="organism.j")
    held = pending.form(DECISION, context_ref=None, embodiment_id=None, tick=1)
    with pytest.raises(ValueError):
        pending.interrupt(held.intent_id, reason=PROTECTION_TAKES_PRIORITY, tick=1)


def test_active_intent_can_be_invalidated():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain)
    outcome = domain.observe_effect(
        observed_effect_id=None,
        prediction_error=None,
        effect_similarity=None,
        tick=2,
        commitment_id=None,
        commitment_status=CommitmentStatus.ACTIVE,
        competence_executable=False,
        embodiment_id="e1",
    )
    assert intent.status is IntentStatus.INVALIDATED
    assert outcome.reason == COMPETENCE_NOT_EXECUTABLE
    other = IntentionDomain(organism_id="organism.j")
    moved = _active(other)
    other.observe_effect(
        observed_effect_id=None,
        prediction_error=None,
        effect_similarity=None,
        tick=2,
        commitment_id=None,
        commitment_status=CommitmentStatus.ACTIVE,
        competence_executable=True,
        embodiment_id="e2",
    )
    assert moved.status is IntentStatus.INVALIDATED
    assert moved.termination_reason == EMBODIMENT_CHANGED


def test_matching_effect_satisfies_intent():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain)
    outcome = _observe(domain, similarity=1.0, effect="effect.e", tick=2)
    assert intent.status is IntentStatus.SATISFIED
    assert outcome.reason == ANTICIPATED_EFFECT_OBSERVED
    assert domain.satisfied_count == 1


def test_single_mismatch_does_not_immediately_fail():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain)
    assert _observe(domain, similarity=0.0, tick=2) is None
    assert intent.status is IntentStatus.ACTIVE


def test_repeated_terminal_mismatch_can_fail():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain)
    outcomes = [_observe(domain, similarity=0.0, tick=tick) for tick in (2, 3, 4)]
    assert outcomes[:2] == [None, None]
    assert intent.status is IntentStatus.FAILED
    assert outcomes[2].reason == REPEATED_HIGH_MISMATCH
    exhausted = IntentionDomain(organism_id="organism.j")
    other = _active(exhausted)
    _observe(exhausted, similarity=0.0, tick=2, status=CommitmentStatus.COMPLETED)
    assert other.status is IntentStatus.FAILED


def test_same_intent_persists_across_ticks():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain, tick=1)
    for tick in (2, 3):
        assert _observe(domain, similarity=0.0, effect=None, tick=tick) is None
        assert domain.active is intent and intent.status is IntentStatus.ACTIVE


def test_identical_intent_is_not_recreated_every_tick():
    domain = IntentionDomain(organism_id="organism.i")
    first = domain.form(DECISION, context_ref=None, embodiment_id=None, tick=1)
    again = domain.form(DECISION, context_ref=None, embodiment_id=None, tick=2)
    assert again is first
    other = ProspectiveDecision(
        competence_id="competence.other",
        anticipated_effect_id="effect.e",
        prediction_ref=None,
        confidence=0.5,
        epistemic_relevance=0.5,
        homeostatic_relevance=0.0,
        origin_refs=("readout.primitive.competence.other",),
    )
    with pytest.raises(RuntimeError):
        domain.form(other, context_ref=None, embodiment_id=None, tick=2)


def test_runtime_intent_keeps_identity_while_its_commitment_runs():
    body = CausalBody(actuator_count=4, seed=7)
    runtime = build_subject(body, organism_id="intent-persistence")
    domain = runtime._action_domain
    seen: dict[str, set[int]] = {}
    for _ in range(3000):
        runtime.tick()
        body.advance(runtime.last_actuations)
        held = domain.intention.active
        if held is not None and held.status is IntentStatus.ACTIVE:
            seen.setdefault(held.intent_id, set()).add(runtime.tick_count)
            assert domain.active_commitment is not None
            assert domain.active_commitment.intent_id == held.intent_id
        if any(len(ticks) >= 2 for ticks in seen.values()):
            break
    assert any(len(ticks) >= 2 for ticks in seen.values())


def test_intention_checkpoint_keeps_only_live_intent():
    domain = IntentionDomain(organism_id="organism.i")
    intent = _active(domain)
    payload = domain.checkpoint()
    restored = IntentionDomain.restore(payload, organism_id="organism.i")
    assert restored.active is not None and restored.active.intent_id == intent.intent_id
    assert restored.active_commitment_id == "commitment.k"
    _observe(domain, similarity=1.0, effect="effect.e", tick=2)
    finished = IntentionDomain.restore(domain.checkpoint(), organism_id="organism.i")
    assert finished.active is None
    assert finished.counts[IntentStatus.SATISFIED] == 1
