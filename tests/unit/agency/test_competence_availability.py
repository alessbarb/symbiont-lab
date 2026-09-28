"""The canonical competence availability projection (Revision Coherence v1 §3.1-§3.3)."""

from __future__ import annotations

import pytest

from symbiont.actuation.binding import (
    BindingStatus,
    CompetenceExecutionBinding,
    CompetenceExecutionBindingRegistry,
    InvalidationReason,
    StalenessReason,
)
from symbiont.actuation.competence import CompetenceMaturity
from symbiont.agency.availability import AvailabilityReason, PredictionScope, derive_availability


class _Competence:
    def __init__(self, maturity=CompetenceMaturity.ESTABLISHED, effect_id="effect.e"):
        self.competence_id = "competence.a"
        self.maturity = maturity
        self.effect_id = effect_id


def _binding(**overrides):
    fields = dict(
        competence_id="competence.a",
        surface_fingerprint="surface.s",
        effect_id="effect.e",
        evidence_refs=("ev.1",),
        reliability=0.9,
        controllability=0.9,
        last_evidence_tick=5,
    )
    fields.update(overrides)
    return CompetenceExecutionBinding(**fields)


def _derive(binding, *, controller=True, suppressed=False, surface="surface.s", **competence):
    return derive_availability(
        _Competence(**competence),
        binding=binding,
        effect_known=True,
        surface_fingerprint=surface,
        controller_available=controller,
        suppressed=suppressed,
    )


def test_suppressed_competence_stays_predictable_and_executable_but_not_admissible():
    state = _derive(_binding(), suppressed=True)
    assert state.predictable_now and state.executable_now and state.testable_now
    assert not state.admissible_now and not state.actionable_test_now
    assert state.prediction_scope is PredictionScope.CURRENT
    assert state.reason is AvailabilityReason.EXECUTIVELY_SUPPRESSED


def test_historical_knowledge_survives_a_non_current_surface():
    stale = _binding(status=BindingStatus.STALE, status_reason=StalenessReason.SURFACE_NOT_CURRENT)
    state = _derive(stale, surface="surface.other")
    assert state.predictable_now and not state.executable_now
    assert state.prediction_scope is PredictionScope.HISTORICAL


def test_uncertain_current_scope_and_invalidated_bindings():
    controller = _binding(
        status=BindingStatus.STALE, status_reason=StalenessReason.CONTROLLER_UNAVAILABLE
    )
    assert _derive(controller, controller=False).prediction_scope is (
        PredictionScope.UNCERTAIN_CURRENT
    )
    invalid = _binding(
        status=BindingStatus.INVALIDATED,
        status_reason=InvalidationReason.CAUSAL_RELATION_REVISED,
    )
    state = _derive(invalid)
    assert not state.predictable_now and not state.executable_now
    assert state.reason is AvailabilityReason.BINDING_INVALIDATED


def test_executability_reads_live_conditions_not_a_lagging_status():
    # Recorded stale for a controller that has since become available again.
    stale = _binding(
        status=BindingStatus.STALE, status_reason=StalenessReason.CONTROLLER_UNAVAILABLE
    )
    assert _derive(stale, controller=True).executable_now
    assert not _derive(_binding(), controller=False).executable_now
    assert _derive(None).reason is AvailabilityReason.UNBOUND
    assert _derive(_binding(), maturity=CompetenceMaturity.CANDIDATE).reason is (
        AvailabilityReason.NOT_MATURE
    )


def test_binding_status_invariants():
    with pytest.raises(ValueError):
        _binding(status=BindingStatus.VALID, status_reason=StalenessReason.EVIDENCE_AGED)
    with pytest.raises(ValueError):
        _binding(status=BindingStatus.STALE)
    with pytest.raises(ValueError):
        _binding(status=BindingStatus.INVALIDATED, status_reason=StalenessReason.EVIDENCE_AGED)


def test_lifecycle_transitions_are_traced_and_evidence_revalidates():
    registry = CompetenceExecutionBindingRegistry()
    kwargs = dict(
        competence_id="competence.a",
        surface_fingerprint="surface.s",
        effect_id="effect.e",
        evidence_refs=("ev.1",),
        reliability=0.9,
        controllability=0.9,
    )
    registry.bind_from_evidence(tick=1, **kwargs)
    registry.set_status(
        "competence.a",
        BindingStatus.INVALIDATED,
        InvalidationReason.EVIDENCE_CONTRADICTED,
        tick=4,
    )
    # Only new evidence leaves INVALIDATED; a status write cannot.
    assert registry.set_status("competence.a", BindingStatus.VALID, None, tick=5) is None
    registry.bind_from_evidence(tick=9, **{**kwargs, "evidence_refs": ("ev.2",)})
    (binding,) = registry.items
    assert binding.status is BindingStatus.VALID and binding.revision == 2
    assert binding.valid_from_tick == 9 and binding.last_evidence_tick == 9
    transitions = registry.drain_transitions()
    assert [(t.previous_status, t.binding.status) for t in transitions] == [
        (BindingStatus.VALID, BindingStatus.INVALIDATED),
        (BindingStatus.INVALIDATED, BindingStatus.VALID),
    ]
    restored = CompetenceExecutionBindingRegistry.restore(registry.checkpoint())
    assert restored.items == registry.items
