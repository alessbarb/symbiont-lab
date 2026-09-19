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


def test_restore_forwards_non_default_proposer_config():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {"candidates": {}, "probe_cursor": 0}

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


def test_restore_accepts_explicit_empty_state():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {"candidates": {}, "probe_cursor": 0}
    restored = restore_actuation_state(payload, constitution, organism_id="org-gate")
    assert restored.active_repertoire == ()


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
