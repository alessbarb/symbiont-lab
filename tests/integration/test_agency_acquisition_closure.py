"""Fresh organism -> acquired agency -> deliberate reuse (§104-§111, §118).

A newborn canonical runtime is embodied in an opaque causal body.  No fixture
declares dimensions, competences, effects or which actuator matters; the
body's ground truth stays apparatus-side.  Each test follows the same
organism through its own development.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from symbiont.actuation.model import CausalSourceKind
from symbiont.agency.intention import IntentStatus
from symbiont.core.domains.intention import SUPERSEDED_BY_PROTECTION
from symbiont.core.regulation.types import ReactiveState
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject

pytestmark = pytest.mark.slow


def _subject(seed: int = 7, actuators: int = 4):
    body = CausalBody(actuator_count=actuators, seed=seed)
    return body, build_subject(body, organism_id=f"closure-{seed}")


def _tick(runtime, body):
    result = runtime.tick()
    body.advance(runtime.last_actuations)
    return result


def _run_until(runtime, body, predicate, *, limit: int = 1500):
    for _ in range(limit):
        _tick(runtime, body)
        if predicate():
            return runtime.tick_count
    pytest.fail("developmental milestone was not reached")


def test_fresh_organism_starts_without_agency_but_can_act():
    body, runtime = _subject()
    domain = runtime._action_domain
    assert domain.action_dimensions.items == ()
    assert domain.competence_library.items == ()
    assert domain.intention.active is None
    assert len(domain.surface.actuator_ids) == 4  # 0 of N physical opportunities known
    commands = attempts = effects = 0
    for _ in range(12):
        _tick(runtime, body)
        commands += int(domain.last_motor_command is not None)
        attempts = domain.acquisition.attempt_count
        effects = len(domain.effect_space.effects)
    assert commands > 0 and attempts > 0 and effects > 0
    assert domain.competence_library.items == ()


def test_dimension_emerges_from_repeated_intervention_evidence():
    body, runtime = _subject()
    domain = runtime._action_domain
    _run_until(runtime, body, lambda: bool(domain.action_dimensions.items))
    dimension = domain.action_dimensions.items[0]
    ledger = domain.causal_evidence
    assert dimension.dimension_id not in domain.surface.actuator_ids
    members = dimension.intervention_signature_refs
    assert all(domain.intervention_signatures.get(ref) is not None for ref in members)
    assert sum(ledger.signature_support(ref) for ref in members) >= 2
    supporting = [
        item for item in ledger.intervention_evidence if item.intervention_signature_id in members
    ]
    assert supporting and all(item.competence_id is None for item in supporting)
    assert domain.competence_library.items == ()


def test_body_schema_learns_before_any_competence():
    body, runtime = _subject()
    domain = runtime._action_domain
    _run_until(
        runtime,
        body,
        lambda: (
            bool(domain.action_dimensions.items)
            and runtime._body_schema.sensorimotor_dependency_evidence_count > 0
        ),
    )
    assert domain.competence_library.items == ()
    assert domain.agency_model.estimates_for(CausalSourceKind.INTERVENTION)


@dataclass
class _Acquired:
    body: CausalBody
    runtime: object
    competence_id: str


@pytest.fixture(scope="module")
def acquired() -> _Acquired:
    body, runtime = _subject()
    domain = runtime._action_domain
    _run_until(runtime, body, lambda: bool(domain.competence_library.items))
    return _Acquired(body, runtime, domain.competence_library.items[0].competence_id)


def test_competence_is_acquired_through_the_causal_chain(acquired):
    domain = acquired.runtime._action_domain
    competence = domain.competence_library.get(acquired.competence_id)
    assert competence is not None and competence.effect_id is not None
    assert domain.effect_space.get(competence.effect_id) is not None  # Effect
    # exploration -> signatures -> ActionDimension with controllability and agency
    grounded = [
        estimate
        for estimate in domain.agency_model.estimates_for(CausalSourceKind.DIMENSION)
        if estimate.effect_id == competence.effect_id
        and estimate.confidence >= domain.acquisition.dimension_policy.agentic_confidence
    ]
    assert grounded
    control = domain.controllability_model.estimate(
        source_kind=CausalSourceKind.DIMENSION,
        source_ref=grounded[0].source_ref,
        effect_id=competence.effect_id,
    )
    assert control is not None and control.confidence > 0.0
    binding = domain.execution_bindings.get(competence.competence_id)
    evidence_ids = {item.evidence_id: item for item in domain.causal_evidence.evidence}
    assert binding is not None and binding.evidence_refs
    assert all(
        evidence_ids[ref].competence_id is None
        for ref in competence.evidence.controllability_evidence_refs
        if ref in evidence_ids
    )


def test_acquired_competence_is_currently_afforded(acquired):
    domain = acquired.runtime._action_domain
    _run_until(
        acquired.runtime,
        acquired.body,
        lambda: (
            any(item.competence_id == acquired.competence_id for item in domain.last_affordances)
            or bool(domain.last_affordances)
        ),
        limit=400,
    )
    affordance = domain.last_affordances[0]
    assert domain.effect_space.get(affordance.anticipated_effect_id) is not None
    rendered = repr(affordance)
    assert all(actuator_id not in rendered for actuator_id in domain.surface.actuator_ids)


def test_intentional_execution_and_real_satisfaction(acquired):
    runtime, body = acquired.runtime, acquired.body
    domain = runtime._action_domain
    chain = {}

    def active_with_command():
        held = domain.intention.active
        commitment = domain.active_commitment
        command = domain.last_motor_command
        if (
            held is not None
            and held.status is IntentStatus.ACTIVE
            and commitment is not None
            and commitment.intent_id == held.intent_id
            and command is not None
            and command.commitment_id == commitment.commitment_id
        ):
            chain.update(intent=held, commitment=commitment, command=command)
            return True
        return False

    _run_until(runtime, body, active_with_command, limit=1500)
    intent = chain["intent"]
    commitment = chain["commitment"]
    # ActionAffordance -> ProspectiveDecision -> ActionIntent -> ActionProposal
    #   -> ActionCommitment -> MotorCommand -> ActionAttempt
    assert intent.supporting_affordance_id is not None
    assert domain.last_proposal is not None and domain.last_proposal.intent_id == intent.intent_id
    assert commitment.competence_id == intent.competence_id
    assert domain.acquisition.pending_attempt is not None
    assert domain.acquisition.pending_attempt.commitment_id == commitment.commitment_id
    assert domain.trace_action(chain["command"].command_id).commitment_id == (
        commitment.commitment_id
    )

    def satisfied():
        return any(
            outcome.status is IntentStatus.SATISFIED for outcome in domain.intention.last_outcomes
        )

    _run_until(runtime, body, satisfied, limit=1500)
    (outcome,) = [
        item for item in domain.intention.last_outcomes if item.status is IntentStatus.SATISFIED
    ]
    assert outcome.effect_similarity == 1.0
    assert outcome.observed_effect_id == outcome.anticipated_effect_id
    assert (
        domain.acquisition.effect_matcher.match(
            domain.effect_space,
            expected_effect_id=outcome.anticipated_effect_id,
            observed_effect_id=outcome.observed_effect_id,
        )
        == 1.0
    )


class _Threatened:
    """Apparatus condition: constant withdrawal urgency (no semantic label)."""

    def evaluate(self, *, percepts, homeostatic_deviation):
        return ReactiveState(
            interrupt=0.9,
            withdrawal=0.9,
            stabilization=0.0,
            conservation=0.0,
            attention=0.9,
            deviation=homeostatic_deviation,
            deviation_velocity=0.0,
            surprise=0.0,
            signature="reactive.threat",
        )


class _LearnedRelief:
    def __init__(self, delegate):
        self._delegate = delegate

    def best(self, *, signature, candidates):
        return candidates[0] if candidates else None

    def __getattr__(self, name):
        return getattr(self._delegate, name)


def test_protection_rejects_pending_cognitive_intent(acquired):
    runtime, body = acquired.runtime, acquired.body
    domain = runtime._action_domain
    runtime._innate_reactivity = _Threatened()
    runtime._reactive_memory = _LearnedRelief(runtime._reactive_memory)
    found = {}

    def rejected_by_protection():
        for outcome in domain.intention.last_outcomes:
            if (
                outcome.status is IntentStatus.REJECTED
                and outcome.reason == SUPERSEDED_BY_PROTECTION
            ):
                found["outcome"] = outcome
                return True
        return False

    _run_until(runtime, body, rejected_by_protection, limit=400)
    assert runtime.last_action_source == "protection"
    assert domain.active_commitment is not None
    assert domain.active_commitment.intent_id is None
    assert domain.active_commitment.commitment_id != found["outcome"].commitment_id
