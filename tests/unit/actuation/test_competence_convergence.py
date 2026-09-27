"""Competence candidacy converges with causal knowledge (§28, §98, Wave 4)."""

from __future__ import annotations

from symbiont.actuation.dimension import opaque_dimension_id
from symbiont.actuation.intervention import opaque_channel_ref
from tests.unit.actuation.acquisition_support import (
    SURFACE,
    A,
    B,
    acquire_agentic_dimension,
    act,
    fresh_acquisition,
    rest,
)


def test_recurrent_pattern_without_stable_effect_does_not_promote():
    acquisition = fresh_acquisition()
    for tick in range(0, 16, 2):
        rest(acquisition, tick, {})
    # The pattern recurs, but its consequence never stabilizes.
    for index, tick in enumerate(range(20, 44, 2)):
        act(acquisition, tick, {A: 0.5}, {f"signal.{index}": 0.4})
    assert acquisition.signatures.recurring_count >= 1
    assert acquisition.ground_competence(controller_seed_ref="seed.a", patterns=({A: 0.5},)) is None


def test_stable_effect_without_reproducible_control_does_not_promote():
    acquisition = fresh_acquisition()
    # The effect is stable, but it happens just as often without intervention:
    # nothing about it is under the organism's reproducible control.
    for tick in range(0, 24, 2):
        rest(acquisition, tick, {"signal.a": 0.4})
    for tick in range(30, 46, 2):
        act(acquisition, tick, {A: 0.5}, {"signal.a": 0.4})
    assert acquisition.action_dimensions.items == ()
    assert acquisition.ground_competence(controller_seed_ref="seed.a", patterns=({A: 0.5},)) is None


def test_causal_dimension_plus_recurrent_controller_can_form_candidate():
    acquisition = fresh_acquisition()
    acquire_agentic_dimension(acquisition, channels={A: 0.5}, changes={"signal.a": 0.4})
    grounding = acquisition.ground_competence(
        controller_seed_ref="seed.a",
        patterns=({A: 0.4}, {A: 0.6}, {B: 0.3}),
    )
    assert grounding is not None
    assert grounding.dimension_id == opaque_dimension_id((opaque_channel_ref(A),))
    assert grounding.agency.confidence >= acquisition.dimension_policy.agentic_confidence
    assert grounding.controllability.confidence > 0.0
    assert grounding.evidence_refs
    assert grounding.temporal_signature.temporal_pattern_ref is not None


def test_competence_effect_comes_from_effect_space():
    acquisition = fresh_acquisition()
    acquire_agentic_dimension(acquisition, channels={A: 0.5}, changes={"signal.a": 0.4})
    grounding = acquisition.ground_competence(controller_seed_ref="seed.a", patterns=({A: 0.5},))
    assert grounding is not None
    effect = acquisition.effect_space.get(grounding.effect_id)
    assert effect is not None and "signal.a" in effect.feature_refs
    assert all(
        ref in {item.evidence_id for item in acquisition.causal_evidence.evidence}
        for ref in grounding.evidence_refs
    )


def test_unbound_dimension_cannot_ground_a_competence():
    acquisition = fresh_acquisition()
    acquire_agentic_dimension(acquisition, channels={A: 0.5}, changes={"signal.a": 0.4})
    acquisition.bind_surface(SURFACE.actuator_ids, surface_fingerprint="surface.other-body")
    assert acquisition.ground_competence(controller_seed_ref="seed.a", patterns=({A: 0.5},)) is None
