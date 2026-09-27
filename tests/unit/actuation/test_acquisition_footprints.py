"""Footprints maintained by AgencyAcquisition (Factorized Effects §14.1, Causal Provenance v1)."""

from __future__ import annotations

import json

from symbiont.actuation.acquisition import AgencyAcquisition
from symbiont.actuation.action import MotorCommand
from symbiont.actuation.commitment import ActionCommitment
from symbiont.actuation.effects import atoms_from_changes
from symbiont.actuation.footprint import footprint_entity_id, version_ref
from symbiont.actuation.intervention import opaque_channel_ref
from tests.unit.actuation.acquisition_support import SURFACE, A, fresh_acquisition, rest

CAUSED = {"signal.a": 0.5}


def _pulse(acquisition, tick, index, *, windows=6, onset=CAUSED):
    commitment = ActionCommitment(
        commitment_id=f"commitment.p{index}",
        proposal_id=f"proposal.p{index}",
        effect_target_id=None,
        competence_id=None,
        started_tick=tick,
        controller_id="controller.sensorimotor-exploration",
        surface_fingerprint=SURFACE.contract_fingerprint,
    )
    for step in range(windows):
        command = MotorCommand.from_mapping(
            command_id=f"command.p{index}.{step}",
            commitment_id=commitment.commitment_id,
            controller_id=commitment.controller_id,
            competence_id=None,
            surface_fingerprint=SURFACE.contract_fingerprint,
            channels={A: 0.5},
            issued_at_tick=tick + step,
        )
        acquisition.open_attempt(
            command=command,
            commitment=commitment,
            context_ref="context.unit",
            actuation_ref=f"actuation.p{index}.{step}",
            tick=tick + step,
        )
        changes = onset if step == 0 else {}
        transition = acquisition.close_attempt(
            tick=tick + step + 1,
            state_before_ref=f"state.{tick + step}",
            state_after_ref=f"state.{tick + step + 1}",
            prediction_ref=None,
            observed_effect_id=None,
            prediction_error=None,
            observed_changes=changes,
        )
        acquisition.learn(transition, body_schema=None)
    return tick + windows


def _develop(acquisition, pulses=10):
    tick = 0
    for index in range(pulses):
        tick = _pulse(acquisition, tick, index)
        for _ in range(4):
            rest(acquisition, tick, {"signal.z": 0.3} if tick % 8 == 0 else {})
            tick += 1
    _pulse(acquisition, tick, pulses)  # opens the next pulse: closes the last
    return tick


def test_pulses_on_one_channel_form_a_traced_footprint():
    acquisition = fresh_acquisition()
    _develop(acquisition)
    source = (opaque_channel_ref(A),)
    content, atoms = acquisition.footprints.footprint_of(source)
    (caused,) = atoms_from_changes(CAUSED)
    assert atoms == frozenset({caused.effect_id})
    entity = footprint_entity_id(source)
    current = version_ref(entity, acquisition.footprints.version_of(source).version)
    assert current in acquisition.provenance.live_refs()
    (estimate,) = [
        ref for ref in acquisition.provenance.causes_of(current) if ref.kind == "atom_estimate"
    ]
    causes = acquisition.provenance.causes_of(estimate)
    assert any(ref.kind == "commitment" for ref in causes)
    assert any(ref.kind == "passive_windows" for ref in causes)


def test_ablated_arms_form_no_footprint():
    for options in ({"use_counterfactual_evidence": False}, {"use_agency_model": False}):
        acquisition = AgencyAcquisition(**options)
        acquisition.bind_surface(
            SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint
        )
        _develop(acquisition)
        assert acquisition.footprints.footprints == {}
        assert acquisition.provenance.events() == ()


def test_checkpoint_continues_the_same_footprints_and_provenance():
    continuous = fresh_acquisition()
    tick = _develop(continuous, pulses=6)
    restored = fresh_acquisition()
    payload = json.loads(
        json.dumps(
            {
                "effect_space": continuous.effect_space.checkpoint(),
                "causal_evidence": continuous.causal_evidence.checkpoint(),
                "acquisition": continuous.checkpoint(),
            }
        )
    )
    restored.restore_causal_state(
        effect_space=payload["effect_space"],
        causal_evidence=payload["causal_evidence"],
        acquisition=payload["acquisition"],
        body_schema=None,
    )
    mark = len(continuous.provenance.events())
    for acquisition in (continuous, restored):
        t = tick + 10
        for index in range(20, 26):
            t = _pulse(acquisition, t, index)
            for _ in range(4):
                rest(acquisition, t, {})
                t += 1
    assert restored.footprints.checkpoint() == continuous.footprints.checkpoint()
    assert restored.provenance.events() == continuous.provenance.events()[mark:]
    assert (
        restored.provenance.checkpoint()["frontier"]
        == continuous.provenance.checkpoint()["frontier"]
    )


def test_footprint_grounding_is_provisional_union_then_traced():
    from symbiont.actuation.acquisition import AgencyAcquisition as Acquisition
    from symbiont.actuation.footprint import footprint_effect_id

    acquisition = Acquisition(footprint_effects=True)
    acquisition.bind_surface(SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint)
    _develop(acquisition)
    grounding = acquisition.ground_competence(
        controller_seed_ref="primitive.x",
        patterns=({A: 0.5, SURFACE.actuator_ids[1]: 0.5},),
        tick=999,
    )
    assert grounding is not None
    channels = tuple(sorted(opaque_channel_ref(a) for a in (A, SURFACE.actuator_ids[1])))
    assert grounding.effect_id == footprint_effect_id(channels)
    (caused,) = atoms_from_changes(CAUSED)
    assert acquisition.effect_space.footprint_atoms(grounding.effect_id) == (caused.effect_id,)
    assert grounding.evidence_refs
    event = acquisition.provenance.events()[-1]
    assert (event.domain, event.operation, event.rule) == (
        "competence",
        "ground",
        "footprint_union",
    )
    assert event.parameters["provisional"] is True and event.parameters["covered_channels"] == 1
    entity = footprint_entity_id((opaque_channel_ref(A),))
    assert all(
        ref.kind == "footprint_version" and ref.id.startswith(entity) for ref in event.caused_by
    )


def test_footprint_grounding_needs_a_footprint_and_whole_state_path_is_unchanged_when_off():
    from symbiont.actuation.acquisition import AgencyAcquisition as Acquisition

    fresh = Acquisition(footprint_effects=True)
    fresh.bind_surface(SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint)
    assert fresh.ground_competence(controller_seed_ref="p", patterns=({A: 0.5},)) is None
    off = fresh_acquisition()
    _develop(off)
    grounding = off.ground_competence(controller_seed_ref="p", patterns=({A: 0.5},))
    assert grounding is None or not grounding.effect_id.startswith("effect.entity.")


def test_footprint_mode_and_atom_catalog_survive_checkpoint():
    from symbiont.actuation.acquisition import AgencyAcquisition as Acquisition

    source = Acquisition(footprint_effects=True)
    source.bind_surface(SURFACE.actuator_ids, surface_fingerprint=SURFACE.contract_fingerprint)
    _develop(source)
    payload = json.loads(
        json.dumps(
            {
                "effect_space": source.effect_space.checkpoint(),
                "causal_evidence": source.causal_evidence.checkpoint(),
                "acquisition": source.checkpoint(),
            }
        )
    )
    restored = fresh_acquisition()
    restored.restore_causal_state(
        effect_space=payload["effect_space"],
        causal_evidence=payload["causal_evidence"],
        acquisition=payload["acquisition"],
        body_schema=None,
    )
    assert restored.footprint_effects is True
    args = {"controller_seed_ref": "p", "patterns": ({A: 0.5},), "tick": 5}
    assert (
        restored.ground_competence(**args).effect_id == source.ground_competence(**args).effect_id
    )
