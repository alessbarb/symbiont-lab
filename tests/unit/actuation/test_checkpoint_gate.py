from __future__ import annotations

import random

import pytest

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.checkpoint import export_actuation_state, restore_actuation_state
from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.proposer import ActuatorProposer


def _run_causal_vs_sham(
    proposer: ActuatorProposer, causal_id: str, sham_id: str, *, windows: int, seed: int, window_ticks: int = 8
) -> None:
    rng = random.Random(seed)
    for tick in range(window_ticks * windows):
        plan = proposer.probing_plan(tick=tick)
        for actuator_id, on in plan.items():
            activation = 1.0 if on else 0.0
            if actuator_id == causal_id:
                delta = activation + rng.gauss(0, 0.02)
            else:
                delta = rng.gauss(0, 1.0)
            proposer.record_effect(actuator_id, "percept.x", activation=activation, delta_percept=delta, tick=tick)
        for actuator_id in plan:
            proposer.advance_tick(actuator_id)


def test_p0_gate_causal_actuator_promoted_sham_actuator_is_not():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    causal_id, sham_id = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-gate", min_probing_windows=3, effect_threshold=0.6, window_ticks=8, probe_limit=2
    )

    _run_causal_vs_sham(proposer, causal_id, sham_id, windows=4, seed=42)

    assert causal_id in proposer.active_repertoire
    assert sham_id not in proposer.active_repertoire


def test_export_restore_round_trip_preserves_active_repertoire():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    causal_id, sham_id = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-gate", min_probing_windows=3, effect_threshold=0.6, window_ticks=8, probe_limit=2
    )
    _run_causal_vs_sham(proposer, causal_id, sham_id, windows=4, seed=42)

    payload = export_actuation_state(proposer)
    restored = restore_actuation_state(payload, constitution, organism_id="org-gate")

    assert restored.active_repertoire == proposer.active_repertoire


def _dormant_candidate_payload(actuator_id: str) -> dict:
    return {
        "actuator_id": actuator_id,
        "activations": 0,
        "cost_evidence": 0.0,
        "probing_state": "dormant",
        "last_seen_tick": 0,
        "windows_completed": 0,
        "windows_with_effect": 0,
        "tick_in_window": 0,
        "effect_relations": {},
        "current_window_relations": {},
    }


def test_restore_forwards_non_default_proposer_config():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    payload = {"candidates": {actuator_id: _dormant_candidate_payload(actuator_id)}, "probe_cursor": 0}

    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id="org-gate",
        min_probing_windows=7,
        effect_threshold=0.9,
        window_ticks=13,
        probe_limit=4,
    )

    assert restored._min_probing_windows == 7  # noqa: SLF001
    assert restored._effect_threshold == 0.9  # noqa: SLF001
    assert restored._window_ticks == 13  # noqa: SLF001
    assert restored._probe_limit == 4  # noqa: SLF001


def test_restore_raises_when_candidates_key_missing_entirely():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {"probe_cursor": 0}  # no "candidates" key at all
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_raises_when_probe_cursor_key_missing_entirely():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {"candidates": {}}  # no "probe_cursor" key at all
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
    payload = {"candidates": {}, "probe_cursor": 0}
    restored = restore_actuation_state(payload, constitution, organism_id="org-gate")
    assert restored.active_repertoire == ()


def test_restore_raises_when_candidate_set_does_not_match_constitution():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=3))
    (actuator_id,) = constitution.actuator_ids[:1]
    # Only one of the three actuators the constitution defines is present —
    # a truncated/foreign checkpoint, even though every entry it DOES have
    # is individually well-formed and refers to a real actuator_id.
    payload = {"candidates": {actuator_id: _dormant_candidate_payload(actuator_id)}, "probe_cursor": 0}
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
        "probe_cursor": 0,
    }
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_raises_on_non_int_or_negative_probe_cursor():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=0))
    for bad_cursor in (True, -1, 1.5, "0"):
        payload = {"candidates": {}, "probe_cursor": bad_cursor}
        with pytest.raises(ValueError):
            restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_raises_when_windows_with_effect_exceeds_windows_completed():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    candidate = _dormant_candidate_payload(actuator_id)
    candidate["windows_completed"] = 2
    candidate["windows_with_effect"] = 5  # impossible: more replicated windows than elapsed windows
    payload = {"candidates": {actuator_id: candidate}, "probe_cursor": 0}
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")


def test_restore_raises_when_tick_in_window_is_out_of_range():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    candidate = _dormant_candidate_payload(actuator_id)
    candidate["tick_in_window"] = 8  # window_ticks default is 8 — must be strictly less
    payload = {"candidates": {actuator_id: candidate}, "probe_cursor": 0}
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate", window_ticks=8)


def test_restore_raises_when_active_candidate_evidence_does_not_satisfy_promotion():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    candidate = _dormant_candidate_payload(actuator_id)
    candidate["probing_state"] = "active"
    candidate["windows_completed"] = 0  # claims active, but zero windows ever elapsed
    candidate["windows_with_effect"] = 0
    payload = {"candidates": {actuator_id: candidate}, "probe_cursor": 0}
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate", min_probing_windows=2, effect_threshold=0.6)


def test_restore_accepts_active_candidate_whose_evidence_genuinely_satisfies_promotion():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-gate", min_probing_windows=2, effect_threshold=0.6, window_ticks=8, probe_limit=1
    )
    rng = random.Random(3)
    for tick in range(16):
        plan = proposer.probing_plan(tick=tick)
        for aid, on in plan.items():
            activation = 1.0 if on else 0.0
            proposer.record_effect(aid, "percept.x", activation=activation, delta_percept=activation + rng.gauss(0, 0.02), tick=tick)
        for aid in plan:
            proposer.advance_tick(aid)
    assert actuator_id in proposer.active_repertoire  # sanity: genuinely promoted

    payload = export_actuation_state(proposer)
    restored = restore_actuation_state(
        payload, constitution, organism_id="org-gate", min_probing_windows=2, effect_threshold=0.6, window_ticks=8, probe_limit=1
    )
    assert actuator_id in restored.active_repertoire


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
                "windows_completed": 3,
                "effect_relations": {},
            }
        },
        "probe_cursor": 0,
    }
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")



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
    assert candidate["windows_completed"] == 0
    assert candidate["windows_with_effect"] == 0

    # Reproduce the exact pre-fix checkpoint shape currently present in
    # persisted Physics3D subjects.
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

    assert proposer.states[0].effect_strength < 0.5

    payload = export_actuation_state(proposer)
    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id="org-natural-decay",
        effect_threshold=0.5,
    )
    assert restored.active_repertoire == (actuator_id,)


def test_restore_accepts_probing_promoted_candidate_after_cumulative_effect_weakens():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution,
        organism_id="org-probing-decay",
        min_probing_windows=2,
        effect_threshold=0.5,
        window_ticks=8,
        probe_limit=1,
    )

    # Two replicated causal windows promote the candidate.
    for tick in range(16):
        plan = proposer.probing_plan(tick=tick)
        for aid, on in plan.items():
            activation = 1.0 if on else 0.0
            proposer.record_effect(
                aid,
                "percept.x",
                activation=activation,
                delta_percept=activation,
                tick=tick,
            )
        for aid in plan:
            proposer.advance_tick(aid)

    assert proposer.states[0].probing_state == "active"
    assert proposer.states[0].windows_with_effect >= 2

    # Later observations may reduce the cumulative correlation.
    for tick in range(16, 96):
        activation = 1.0 if tick % 2 else 0.0
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=(0.4 if tick % 3 else -0.4),
            tick=tick,
        )

    assert proposer.states[0].effect_strength < 0.5

    payload = export_actuation_state(proposer)
    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id="org-probing-decay",
        min_probing_windows=2,
        effect_threshold=0.5,
        window_ticks=8,
        probe_limit=1,
    )
    assert restored.active_repertoire == (actuator_id,)
