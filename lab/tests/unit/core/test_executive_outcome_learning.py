"""Executive Outcome Learning v1 inside the organism (EOL §5-§10 release gate)."""

from __future__ import annotations

import copy
from dataclasses import replace

from lab.integration.organism import restore_canonical_organism
from lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    subject_lifecycle,
)
from symbiont.actuation.commitment import CommitmentStatus
from symbiont.agency.affordance import ActionAffordance, affordance_id_for
from symbiont.agency.executive_outcome import CausalRevisionState
from symbiont.agency.intention import IntentStatus
from symbiont.agency.prospective import (
    ExecutiveAdmissionPolicy,
    ProspectiveDecision,
    admit_afforded_action,
)
from symbiont.cognition.limits import KernelLimits
from symbiont.core.domains.intention import (
    COMPETENCE_NOT_EXECUTABLE,
    PROPOSAL_NOT_SELECTED,
    PROTECTION_TAKES_PRIORITY,
    IntentionDomain,
    IntentionPolicy,
)
from symbiont.core.orchestration.runtime import OrganismRuntime


def _decision(competence_id: str, effect_id: str) -> ProspectiveDecision:
    return ProspectiveDecision(
        competence_id=competence_id,
        anticipated_effect_id=effect_id,
        prediction_ref=None,
        confidence=0.5,
        epistemic_relevance=0.5,
        homeostatic_relevance=0.0,
        origin_refs=(f"readout.primitive.{competence_id}",),
    )


def _affordance(competence_id: str, effect_id: str) -> ActionAffordance:
    return ActionAffordance(
        affordance_id=affordance_id_for(
            competence_id=competence_id,
            anticipated_effect_id=effect_id,
            context_ref="context.x",
            embodiment_id="e1",
        ),
        competence_id=competence_id,
        anticipated_effect_id=effect_id,
        context_ref="context.x",
        embodiment_id="e1",
        prediction_confidence=0.5,
        controllability=0.5,
        executability_confidence=1.0,
        prediction_ref=None,
        evidence_refs=(),
    )


class _Probe:
    """Stand-in for the action domain's material causal/binding state."""

    def __init__(self) -> None:
        self.states: dict[tuple, CausalRevisionState] = {}

    def __call__(self, key):
        return self.states.setdefault(
            key,
            CausalRevisionState(
                binding_fingerprint="surface|1",
                executable=True,
                controllability_revision=1,
                agency_revision=1,
            ),
        )


def _domain(**policy) -> tuple[IntentionDomain, _Probe]:
    domain = IntentionDomain(organism_id="organism.i", policy=IntentionPolicy(**policy))
    probe = _Probe()
    domain.revision_probe = probe
    return domain, probe


def _run(domain, competence_id, effect_id, *, tick, binding_valid=True):
    intent = domain.form(
        _decision(competence_id, effect_id), context_ref="context.x", embodiment_id="e1", tick=tick
    )
    domain.activate(
        intent.intent_id, commitment_id=f"commitment.{tick}", tick=tick, binding_valid=binding_valid
    )
    return intent


def _observe(domain, *, tick, similarity=0.0, effect="effect.other", status=None):
    return domain.observe_effect(
        observed_effect_id=effect,
        prediction_error=None,
        effect_similarity=similarity,
        tick=tick,
        commitment_id=domain.active_commitment_id,
        commitment_status=status,
        competence_executable=True,
        embodiment_id="e1",
    )


def _factor(domain, competence_id, effect_id):
    return domain.admission_modulation(competence_id=competence_id, anticipated_effect_id=effect_id)


def test_real_satisfaction_changes_only_matching_key_admission():
    domain, _probe = _domain()
    _run(domain, "competence.a", "effect.a", tick=1)
    _observe(domain, tick=2, similarity=1.0, effect="effect.a")
    assert _factor(domain, "competence.a", "effect.a").factor > 1.0
    assert not _factor(domain, "competence.b", "effect.b").had_history
    # Same competence, other effect: separate relation.
    assert not _factor(domain, "competence.a", "effect.b").had_history


def test_real_failures_change_only_matching_key_admission():
    domain, _probe = _domain()
    _run(domain, "competence.a", "effect.a", tick=1)
    for tick in range(2, 5):
        _observe(domain, tick=tick)  # repeated high mismatch
    _run(domain, "competence.b", "effect.b", tick=10)
    _observe(domain, tick=11, status=CommitmentStatus.FAILED)  # controller terminal failure
    contradicted = _factor(domain, "competence.a", "effect.a").factor
    terminal = _factor(domain, "competence.b", "effect.b").factor
    assert 0.5 <= terminal < contradicted < 1.0
    assert not _factor(domain, "competence.c", "effect.c").had_history


def test_neutral_outcomes_create_no_evidence():
    domain, _probe = _domain()
    pending = domain.form(
        _decision("competence.a", "effect.a"), context_ref="context.x", embodiment_id="e1", tick=1
    )
    domain.reject(pending.intent_id, reason=PROPOSAL_NOT_SELECTED, tick=1)
    active = _run(domain, "competence.a", "effect.a", tick=2)
    domain.interrupt(active.intent_id, reason=PROTECTION_TAKES_PRIORITY, tick=3)
    _run(domain, "competence.a", "effect.a", tick=4, binding_valid=False)
    _observe(domain, tick=5, status=CommitmentStatus.FAILED)  # no valid binding at start
    assert len(domain.outcome_ledger) == 0

    unreconciled, _ = _domain(reconcile_observed_effects=False)
    _run(unreconciled, "competence.a", "effect.a", tick=1)
    _observe(unreconciled, tick=2, status=CommitmentStatus.COMPLETED)  # unverified completion
    assert len(unreconciled.outcome_ledger) == 0


def test_disabled_outcome_learning_records_nothing_and_never_modulates():
    domain, _probe = _domain(executive_outcome_learning=False)
    _run(domain, "competence.a", "effect.a", tick=1)
    _observe(domain, tick=2, similarity=1.0, effect="effect.a")
    assert len(domain.outcome_ledger) == 0
    assert not _factor(domain, "competence.a", "effect.a").had_history


def test_invalidation_suppresses_until_relevant_revision():
    domain, probe = _domain()
    intent = _run(domain, "competence.a", "effect.a", tick=1)
    domain.invalidate(intent.intent_id, reason=COMPETENCE_NOT_EXECUTABLE, tick=2)
    key = ("competence.a", "effect.a")
    assert _factor(domain, *key).suppressed
    probe.states[key] = replace(probe.states[key], binding_fingerprint="surface|2")
    assert not _factor(domain, *key).suppressed


def test_unrelated_causal_revision_does_not_lift_suppression():
    domain, probe = _domain()
    intent = _run(domain, "competence.a", "effect.a", tick=1)
    domain.invalidate(intent.intent_id, reason=COMPETENCE_NOT_EXECUTABLE, tick=2)
    other = ("competence.b", "effect.b")
    probe(other)
    probe.states[other] = replace(
        probe.states[other], controllability_revision=99, executable=False
    )
    assert _factor(domain, "competence.a", "effect.a").suppressed


def test_admission_uses_executive_history_without_altering_recorded_relevance():
    domain, _probe = _domain()
    for tick in range(1, 20, 4):
        _run(domain, "competence.a", "effect.a", tick=tick)
        _observe(domain, tick=tick + 1, status=CommitmentStatus.FAILED)
    affordances = (_affordance("competence.a", "effect.a"), _affordance("competence.b", "effect.b"))

    def history(affordance):
        return domain.admission_modulation(
            competence_id=affordance.competence_id,
            anticipated_effect_id=affordance.anticipated_effect_id,
        )

    common = dict(
        affordances=affordances,
        primitive_readouts={"competence.a": 1.0, "competence.b": 1.0},
        epistemic_value=lambda competence_id: 0.0,
        homeostatic_relevance=lambda competence_id: 0.0,
        policy=ExecutiveAdmissionPolicy(),
    )
    without = admit_afforded_action(**common)
    with_history = admit_afforded_action(**common, executive_history=history)
    assert without is not None and without.competence_id == "competence.a"
    assert with_history is not None and with_history.competence_id == "competence.b"
    assert with_history.epistemic_relevance == 0.5  # 1 - prediction confidence, unscaled


def test_organism_installs_the_revision_probe_across_restore():
    body = CausalBody(actuator_count=4, seed=7)
    runtime = build_subject(body, organism_id="eol-probe")
    domain = runtime._action_domain
    assert domain.intention.revision_probe is not None
    domain.restore_intention(domain.intention.checkpoint(), tick=0)
    assert domain.intention.revision_probe == domain.causal_revision_state


def _developed(seed: int, *, limit: int) -> tuple[OrganismRuntime, CausalBody]:
    body = CausalBody(actuator_count=4, seed=seed)
    runtime = build_subject(body, organism_id=f"eol-{seed}")
    for _ in range(limit):
        runtime.tick()
        body.advance(runtime.last_actuations)
        if len(runtime._action_domain.intention.outcome_ledger):
            break
    return runtime, body


def test_executive_failure_does_not_modify_causal_models():
    runtime, _body = _developed(127, limit=600)
    domain = runtime._action_domain
    acquisition = domain.acquisition
    intention = domain.intention
    held = intention.active
    if held is not None and not held.terminal:
        if held.status is IntentStatus.PENDING:
            intention.reject(held.intent_id, reason=PROPOSAL_NOT_SELECTED, tick=runtime.tick_count)
        else:
            intention.interrupt(
                held.intent_id, reason=PROTECTION_TAKES_PRIORITY, tick=runtime.tick_count
            )
    competence = next(
        item for item in domain.competence_library.items if item.effect_id is not None
    )

    def causal_state():
        return (
            acquisition.controllability_model.checkpoint(),
            acquisition.agency_model.checkpoint(),
            acquisition.causal_evidence.checkpoint(),
            copy.deepcopy(domain.competence_library.items),
        )

    before = causal_state()
    tick = runtime.tick_count
    intent = intention.form(
        _decision(competence.competence_id, competence.effect_id),
        context_ref="context.x",
        embodiment_id=domain.embodiment_id,
        tick=tick,
    )
    intention.activate(
        intent.intent_id, commitment_id="commitment.eol", tick=tick, binding_valid=True
    )
    intention.fail(intent.intent_id, reason="controller_terminal_failure", tick=tick + 1)
    intent = intention.form(
        _decision(competence.competence_id, competence.effect_id),
        context_ref="context.x",
        embodiment_id=domain.embodiment_id,
        tick=tick + 2,
    )
    intention.activate(intent.intent_id, commitment_id="commitment.eol2", tick=tick + 2)
    intention.invalidate(intent.intent_id, reason=COMPETENCE_NOT_EXECUTABLE, tick=tick + 3)
    assert (
        intention.outcome_ledger.get((competence.competence_id, competence.effect_id)) is not None
    )
    assert causal_state() == before


def _restored(runtime: OrganismRuntime, body: CausalBody) -> tuple[OrganismRuntime, CausalBody]:
    twin_body = copy.deepcopy(body)
    twin = restore_canonical_organism(
        runtime.checkpoint(),
        host_lifecycle=subject_lifecycle(twin_body),
        host_reading_providers=(twin_body,),
        kernel_limits=KernelLimits(),
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
    )
    return twin, twin_body


def test_checkpoint_restore_is_trajectory_identical_with_executive_evidence():
    """Evidence round-trips exactly and restored continuations are identical.

    A restored organism cold-starts its open ActionAttempt (Agency v1 §82.3),
    so it is compared with another restored continuation, not with the
    uninterrupted run.
    """
    runtime, body = _developed(127, limit=1500)
    ledger = runtime._action_domain.intention.outcome_ledger
    assert len(ledger) >= 1
    first, first_body = _restored(runtime, body)
    second, second_body = _restored(runtime, body)
    assert first._action_domain.intention.outcome_ledger.checkpoint() == ledger.checkpoint()
    for _ in range(300):
        for twin, twin_body in ((first, first_body), (second, second_body)):
            twin.tick()
            twin_body.advance(twin.last_actuations)
    assert (
        first._action_domain.intention.outcome_ledger.checkpoint()
        == second._action_domain.intention.outcome_ledger.checkpoint()
    )
    assert (
        first._action_domain.causal_evidence.evidence
        == second._action_domain.causal_evidence.evidence
    )


def test_suppression_and_its_lifting_are_traced():
    from symbiont.provenance import ProvenanceLog

    domain, probe = _domain()
    domain.provenance = ProvenanceLog()
    intent = _run(domain, "competence.a", "effect.a", tick=1)
    domain.invalidate(intent.intent_id, reason=COMPETENCE_NOT_EXECUTABLE, tick=2)
    learned = [e for e in domain.provenance.events() if e.operation == "learn"]
    assert learned[-1].rule == "suppress" and learned[-1].parameters["suppressed"] is True
    key = ("competence.a", "effect.a")
    probe.states[key] = replace(probe.states[key], binding_fingerprint="surface|2")
    domain.admission_modulation(
        competence_id="competence.a", anticipated_effect_id="effect.a", tick=9
    )
    (lift,) = [e for e in domain.provenance.events() if e.operation == "lift_suppression"]
    assert lift.tick == 9 and lift.parameters["binding_fingerprint"] == "surface|2"
