"""Revision Coherence v1 §3.9 decision 1: causal evidence invalidates a binding.

Executions that do not confirm a VALID binding accumulate; after at least 4,
the binding is INVALIDATED when the Wilson upper bound of their (zero) match
rate falls below the rate at which its effect appears at rest over the same
length. A confirmation resets the evidence.
"""

from __future__ import annotations

from types import SimpleNamespace

from symbiont.actuation.binding import (
    BindingStatus,
    CompetenceExecutionBindingRegistry,
    InvalidationReason,
)
from symbiont_lab.studies.learning.agency_acquisition_body import CausalBody, build_subject


def _organism():
    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="binding-invalidation", factorized_effects=True)
    for _ in range(600):
        runtime.tick()
        body.advance(runtime.last_actuations)
    domain = runtime._action_domain
    domain.binding_invalidation = "rest"  # control arm, off by default (§3.11)
    binding = next(b for b in domain.execution_bindings.items if b.status is BindingStatus.VALID)
    return runtime, domain, binding


def _execution(binding, index, *, length):
    start = binding.last_evidence_tick + 1 + index * length
    return SimpleNamespace(
        competence_id=binding.competence_id,
        commitment_id=f"commitment.test.{index}",
        started_tick=start,
        ended_tick=start + length,
    )


def test_unconfirmed_long_executions_invalidate_with_traced_causes():
    runtime, domain, binding = _organism()
    events = []
    runtime.provenance.subscribe(events.append)
    for index in range(3):
        domain._judge_binding_after(_execution(binding, index, length=5000))
    assert domain.execution_bindings.get(binding.competence_id).status is BindingStatus.VALID

    domain._judge_binding_after(_execution(binding, 3, length=5000))
    invalid = domain.execution_bindings.get(binding.competence_id)
    assert invalid.status is BindingStatus.INVALIDATED
    assert invalid.status_reason is InvalidationReason.CAUSAL_RELATION_REVISED
    availability = domain.competence_availability(
        domain.competence_library.get(binding.competence_id)
    )
    assert not availability.executable_now and not availability.predictable_now

    domain.reconcile_binding_status(tick=runtime.tick_count)
    (event,) = [
        e for e in events if e.domain == "binding" and e.subject.id == binding.competence_id
    ]
    assert event.operation == "invalidated" and event.rule == "causal_relation_revised"
    assert {ref.id for ref in event.caused_by if ref.kind == "commitment"} == {
        f"commitment.test.{index}" for index in range(4)
    }


def test_confirmation_resets_and_counts_survive_restore():
    _runtime, domain, binding = _organism()
    registry = domain.execution_bindings
    for index in range(2):
        domain._judge_binding_after(_execution(binding, index, length=5000))
    restored = CompetenceExecutionBindingRegistry.restore(registry.checkpoint())
    assert restored.checkpoint() == registry.checkpoint()

    registry.bind_from_evidence(
        competence_id=binding.competence_id,
        surface_fingerprint=binding.surface_fingerprint,
        effect_id=binding.effect_id,
        evidence_refs=("ev.confirm",),
        reliability=binding.reliability,
        controllability=binding.controllability,
        tick=binding.last_evidence_tick + 20_000,
    )
    assert binding.competence_id not in registry.checkpoint()["unconfirmed_executions"]


def _history_organism():
    runtime, domain, binding = _organism()
    domain.binding_invalidation = "history"
    return runtime, domain, binding


def _run(domain, binding, index, *, matched):
    execution = _execution(binding, index, length=6)
    if matched:  # a confirming execution refreshes the binding during it
        domain.execution_bindings.bind_from_evidence(
            competence_id=binding.competence_id,
            surface_fingerprint=binding.surface_fingerprint,
            effect_id=binding.effect_id,
            evidence_refs=(f"ev.{index}",),
            reliability=binding.reliability,
            controllability=binding.controllability,
            tick=execution.started_tick + 1,
        )
    domain._judge_binding_after(execution)


def test_history_rule_invalidates_a_binding_that_stops_matching():
    # Binding Degradation v1 §2: reference 8/8, then 0/8 -> invalidated.
    runtime, domain, binding = _history_organism()
    for index in range(8):
        _run(domain, binding, index, matched=True)
    for index in range(8, 15):
        _run(domain, binding, index, matched=False)
    assert domain.execution_bindings.get(binding.competence_id).status is BindingStatus.VALID
    _run(domain, binding, 15, matched=False)
    invalid = domain.execution_bindings.get(binding.competence_id)
    assert invalid.status is BindingStatus.INVALIDATED
    assert invalid.status_reason is InvalidationReason.EVIDENCE_CONTRADICTED


def test_history_rule_keeps_a_binding_that_performs_as_confirmed():
    _runtime, domain, binding = _history_organism()
    for index in range(40):
        _run(domain, binding, index, matched=index % 2 == 0)  # 50% throughout
    assert domain.execution_bindings.get(binding.competence_id).status is BindingStatus.VALID
    history = domain.execution_bindings.checkpoint()["revision_history"][binding.competence_id]
    assert history["ref_n"] == 8 and history["new_n"] == 32
