from __future__ import annotations

import pytest

from symbiont.actuation.candidate import ActuatorCandidateState, _MAX_EFFECT_RELATIONS_PER_CANDIDATE


def test_new_candidate_starts_dormant_with_zero_effect_strength():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    assert state.probing_state == "dormant"
    assert state.effect_strength == 0.0


def test_observe_effect_accumulates_into_named_percept_relation():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    for i in range(10):
        activation = float(i % 2)
        delta = activation * 1.0  # perfectly causal signal
        state.observe_effect("percept.x", activation=activation, delta_percept=delta)
    assert "percept.x" in state.effect_relations
    assert state.effect_relations["percept.x"].count == 10


def test_effect_strength_is_high_for_causal_relation_and_low_for_noise():
    causal = ActuatorCandidateState(actuator_id="actuator.causal")
    sham = ActuatorCandidateState(actuator_id="actuator.sham")
    import random

    rng = random.Random(7)
    for i in range(40):
        activation = float(i % 2)
        causal.observe_effect("percept.x", activation=activation, delta_percept=activation + rng.gauss(0, 0.01))
        sham.observe_effect("percept.x", activation=activation, delta_percept=rng.gauss(0, 1.0))
    assert causal.effect_strength > 0.9
    assert causal.effect_strength > sham.effect_strength


def test_effect_relations_bounded_by_max_per_candidate():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    last_percept_id = ""
    for i in range(_MAX_EFFECT_RELATIONS_PER_CANDIDATE + 5):
        last_percept_id = f"percept.{i}"
        state.observe_effect(last_percept_id, activation=1.0, delta_percept=0.5)
    assert len(state.effect_relations) == _MAX_EFFECT_RELATIONS_PER_CANDIDATE
    assert last_percept_id in state.effect_relations


def test_export_withholds_relations_below_minimum_samples():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    state.observe_effect("percept.x", activation=1.0, delta_percept=0.5)  # one sample only
    payload = state.to_payload()
    assert payload["effect_relations"] == {}


def test_export_restore_round_trip_preserves_established_relations():
    state = ActuatorCandidateState(actuator_id="actuator.a", probing_state="probing", windows_completed=2)
    for i in range(10):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=activation)
    payload = state.to_payload()
    restored = ActuatorCandidateState.from_payload(payload)
    assert restored.actuator_id == "actuator.a"
    assert restored.probing_state == "probing"
    assert restored.windows_completed == 2
    assert restored.effect_relations["percept.x"].count == 10


def test_from_payload_raises_when_effect_relations_exceed_max():
    payload = {
        "actuator_id": "actuator.a",
        "activations": 0,
        "probing_state": "dormant",
        "windows_completed": 0,
        "last_seen_tick": 0,
        "cost_evidence": 0.0,
        "effect_relations": {
            f"percept.{i}": {
                "count": 10,
                "mean_x": 0.0,
                "mean_y": 0.0,
                "m2_x": 1.0,
                "m2_y": 1.0,
                "c_xy": 0.5,
            }
            for i in range(_MAX_EFFECT_RELATIONS_PER_CANDIDATE + 1)
        },
    }
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)


def test_from_payload_raises_on_corrupted_probing_state():
    payload = {
        "actuator_id": "actuator.a",
        "activations": 0,
        "probing_state": "orbiting",  # not a valid state
        "windows_completed": 0,
        "last_seen_tick": 0,
        "cost_evidence": 0.0,
        "effect_relations": {},
    }
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)
