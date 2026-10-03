"""Revision Coherence v1 Gate W1 on a live organism (E6 body, both effect modes)."""

from __future__ import annotations

import copy

import pytest

from lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    subject_lifecycle,
)
from symbiont.actuation.binding import BindingStatus, StalenessReason
from symbiont.cognition.limits import KernelLimits
from symbiont.core.orchestration.runtime import OrganismRuntime


def _states(runtime):
    domain = runtime._action_domain
    return {
        c.competence_id: domain.competence_availability(c) for c in domain.competence_library.items
    }


@pytest.mark.parametrize("factorized", [False, True])
def test_no_competence_is_ever_suppressed_and_admissible(factorized):
    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="gate-w1", factorized_effects=factorized)
    seen = 0
    for _ in range(900):
        runtime.tick()
        body.advance(runtime.last_actuations)
        for state in _states(runtime).values():
            seen += 1
            assert not (state.suppressed and state.admissible_now)
            if state.executable_now:
                assert state.binding_status is not BindingStatus.INVALIDATED
                assert state.surface_match and state.controller_available
    assert seen > 0


def test_surface_change_is_traced_and_projection_survives_restore():
    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="gate-w1-restore", factorized_effects=True)
    for _ in range(600):
        runtime.tick()
        body.advance(runtime.last_actuations)
    domain = runtime._action_domain
    bound = domain.execution_bindings.items
    assert bound, "the fixture must have acquired a binding"
    events = []
    runtime.provenance.subscribe(events.append)
    first = bound[0]
    domain.execution_bindings.bind_from_evidence(
        competence_id=first.competence_id,
        surface_fingerprint="surface.other",
        effect_id=first.effect_id,
        evidence_refs=("ev.surface",),
        reliability=first.reliability,
        controllability=first.controllability,
        tick=runtime.tick_count,
    )
    domain.reconcile_binding_status(tick=runtime.tick_count)
    stale = domain.execution_bindings.get(first.competence_id)
    assert stale.status is BindingStatus.STALE
    assert stale.status_reason is StalenessReason.SURFACE_NOT_CURRENT
    traced = [e for e in events if e.domain == "binding" and e.subject.id == first.competence_id]
    # New evidence may first revalidate it (e.g. from controller staleness);
    # the surface change is then the last, traced revision.
    last = traced[-1]
    assert last.operation == "stale" and last.rule == "surface_not_current"
    assert last.parameters["revision"] == stale.revision

    twin_body = copy.deepcopy(body)
    twin = OrganismRuntime.from_checkpoint(
        runtime.checkpoint(),
        host_lifecycle=subject_lifecycle(twin_body),
        host_reading_providers=(twin_body,),
        kernel_limits=KernelLimits(),
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
    )
    assert _states(twin) == _states(runtime)


def test_footprint_membership_options_survive_restore():
    from lab.studies.learning.footprint_precision import apply_membership

    body = CausalBody(actuator_count=4, seed=127)
    runtime = build_subject(body, organism_id="membership-restore", factorized_effects=True)
    apply_membership(runtime, "TM")
    for _ in range(50):
        runtime.tick()
        body.advance(runtime.last_actuations)
    twin_body = copy.deepcopy(body)
    twin = OrganismRuntime.from_checkpoint(
        runtime.checkpoint(),
        host_lifecycle=subject_lifecycle(twin_body),
        host_reading_providers=(twin_body,),
        kernel_limits=KernelLimits(),
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
    )
    acquisition = twin._action_domain.acquisition
    assert acquisition.footprint_quiet_near == 8 and acquisition.footprint_multiplicity
    assert acquisition.footprints.exit_margin == acquisition.footprints.enter_margin / 2
