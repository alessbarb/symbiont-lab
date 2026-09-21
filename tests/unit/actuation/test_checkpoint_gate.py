from __future__ import annotations

import pytest

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.checkpoint import export_actuation_state, restore_actuation_state
from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.proposer import ActuatorProposer


def _dormant_candidate_payload(actuator_id: str) -> dict:
    return {
        "actuator_id": actuator_id,
        "activations": 0,
        "cost_evidence": 0.0,
        "probing_state": "dormant",
        "last_seen_tick": 0,
        "effect_relations": {},
    }


def test_restore_raises_when_candidates_key_missing_entirely():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {}  # no "candidates" key at all
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_accepts_explicit_empty_state_for_a_body_with_no_actuators():
    # An empty "candidates" dict is only valid when the constitution itself
    # defines zero actuators (a genuinely empty body) — set(payload.candidates)
    # must equal set(constitution.actuator_ids) exactly (spec §15/P0.2).
    # export_actuation_state always exports one entry per actuator_id, so an
    # empty candidates dict against a NON-empty constitution is a truncated
    # checkpoint, not a valid "never explored anything" state — see
    # test_restore_raises_when_candidate_set_does_not_match_constitution.
    constitution = derive_actuator_constitution(MotorGenes(slot_count=0))
    payload = {"candidates": {}}
    restored = restore_actuation_state(payload, constitution, organism_id="org-gate")
    assert restored.active_repertoire == ()


def test_restore_raises_when_candidate_set_does_not_match_constitution():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=3))
    (actuator_id,) = constitution.actuator_ids[:1]
    # Only one of the three actuators the constitution defines is present —
    # a truncated/foreign checkpoint, even though every entry it DOES have
    # is individually well-formed and refers to a real actuator_id.
    payload = {"candidates": {actuator_id: _dormant_candidate_payload(actuator_id)}}
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_raises_when_candidate_key_does_not_match_its_own_actuator_id_field():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    id_a, id_b = constitution.actuator_ids
    # Candidate stored under key id_a, but its own actuator_id field says id_b
    # — both are real, known ids, so the old subset-only check would have
    # passed this silently.
    payload = {
        "candidates": {
            id_a: _dormant_candidate_payload(id_b),
            id_b: _dormant_candidate_payload(id_b),
        },
    }
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_rejects_candidate_actuator_id_not_in_constitution():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {
        "candidates": {
            "actuator.not-in-constitution": {
                "actuator_id": "actuator.not-in-constitution",
                "activations": 1,
                "cost_evidence": 0.0,
                "probing_state": "active",
                "last_seen_tick": 0,
                "effect_relations": {},
            }
        },
    }
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_raises_when_active_candidate_evidence_does_not_satisfy_promotion():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    candidate = _dormant_candidate_payload(actuator_id)
    candidate["probing_state"] = "active"  # claims active with zero recorded evidence
    payload = {"candidates": {actuator_id: candidate}}
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate", effect_threshold=0.6)


def test_restore_accepts_legacy_naturally_promoted_active_candidate_without_windows():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution,
        organism_id="org-natural-legacy",
        effect_threshold=0.6,
    )
    for tick in range(12):
        activation = 0.2 + 0.05 * tick
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=activation * 0.9,
            tick=tick,
        )
        proposer.consider_natural_evidence(actuator_id, min_samples=12)

    payload = export_actuation_state(proposer)
    candidate = payload["candidates"][actuator_id]
    assert candidate["probing_state"] == "active"

    # Reproduce the exact pre-marker checkpoint shape from before
    # natural_promotion_samples existed.
    candidate.pop("natural_promotion_samples", None)

    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id="org-natural-legacy",
        effect_threshold=0.6,
    )
    assert restored.active_repertoire == (actuator_id,)


def test_natural_promotion_threshold_round_trips_explicitly():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution,
        organism_id="org-natural-new",
        effect_threshold=0.6,
    )
    for tick in range(7):
        activation = 0.1 + 0.1 * tick
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=activation,
            tick=tick,
        )
        proposer.consider_natural_evidence(actuator_id, min_samples=7)

    payload = export_actuation_state(proposer)
    assert payload["candidates"][actuator_id]["natural_promotion_samples"] == 7

    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id="org-natural-new",
        effect_threshold=0.6,
    )
    state = restored.states[0]
    assert state.probing_state == "active"
    assert state.natural_promotion_samples == 7


def test_restore_accepts_naturally_promoted_candidate_after_effect_strength_decays():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution,
        organism_id="org-natural-decay",
        effect_threshold=0.5,
    )

    # First establish strong natural evidence and promote.
    for tick in range(12):
        activation = 0.2 + 0.05 * tick
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=activation,
            tick=tick,
        )
        proposer.consider_natural_evidence(actuator_id, min_samples=12)

    assert proposer.states[0].probing_state == "active"
    assert proposer.states[0].natural_promotion_samples == 12

    # Then add enough decorrelating experience for the current aggregate to
    # fall below the original promotion threshold. Active status is historical
    # and must remain restorable.
    for tick in range(12, 80):
        activation = 0.2 + 0.01 * (tick % 7)
        delta = 0.3 if tick % 2 else -0.3
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=delta,
            tick=tick,
        )

    payload = export_actuation_state(proposer)
    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id="org-natural-decay",
        effect_threshold=0.5,
    )
    assert restored.active_repertoire == (actuator_id,)
