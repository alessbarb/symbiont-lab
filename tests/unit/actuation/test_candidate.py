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


@pytest.mark.parametrize(
    "missing_field",
    [
        "actuator_id",
        "activations",
        "cost_evidence",
        "probing_state",
        "last_seen_tick",
        "windows_completed",
        "effect_relations",
    ],
)
def test_from_payload_raises_on_missing_field_instead_of_defaulting(missing_field):
    payload = {
        "actuator_id": "actuator.a",
        "activations": 3,
        "probing_state": "probing",
        "windows_completed": 1,
        "last_seen_tick": 5,
        "cost_evidence": 0.1,
        "effect_relations": {},
    }
    del payload[missing_field]
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)


def test_to_payload_resets_windows_completed_when_all_relations_withheld():
    # A candidate that has already completed several probing windows but
    # whose only evidence is under the export sample minimum must not
    # export windows_completed as-is (spec §6 revisión 3 / I4): a restored
    # candidate would otherwise start from empty accumulators while already
    # sitting at/above the promotion threshold, promoting on a single
    # post-restore window with no real evidence behind it.
    state = ActuatorCandidateState(actuator_id="actuator.a", windows_completed=3)
    state.observe_effect("percept.x", activation=1.0, delta_percept=0.5)  # below export minimum
    payload = state.to_payload()
    assert payload["effect_relations"] == {}
    assert payload["windows_completed"] == 0

    restored = ActuatorCandidateState.from_payload(payload)
    assert restored.windows_completed == 0


def test_to_payload_resets_windows_completed_when_no_relations_observed_at_all():
    # No effect_relations were ever observed either — an exported empty
    # effect_relations must never carry forward windows_completed progress
    # that has zero evidence behind it (same I4 hazard as the withheld case:
    # a caller could have run probing_plan/advance_tick for several windows
    # while record_effect never fired, e.g. no percepts that window).
    state = ActuatorCandidateState(actuator_id="actuator.a", windows_completed=2)
    payload = state.to_payload()
    assert payload["effect_relations"] == {}
    assert payload["windows_completed"] == 0


def test_observe_effect_pairing_contract_correct_vs_wrong_time_shift():
    """Spec §6 revisión 4: activation(t) must pair with percept(t+1)-percept(t),
    never a same-tick delta. Drive a real two-tick percept series across a
    one-tick-lag causal channel and prove the accumulator setup only reveals
    the causal relation when the caller does the pairing correctly.
    """
    import random

    rng = random.Random(11)
    n_ticks = 40

    # i.i.d. activations (not alternating): alternation would make
    # activation(t-1) perfectly anti-correlated with activation(t), which
    # would make the lagged-wrong arm below score high for the wrong
    # reason (effect_strength takes abs()). i.i.d. keeps activation(t-1)
    # genuinely uncorrelated with activation(t).
    activations: list[float] = [rng.choice([0.0, 1.0]) for _ in range(n_ticks)]
    # percept only moves on the tick AFTER an activation (one-tick lag).
    percept: list[float] = [0.0]
    for t in range(n_ticks):
        percept.append(percept[-1] + activations[t] + rng.gauss(0, 0.02))

    correct = ActuatorCandidateState(actuator_id="actuator.correct")
    same_tick_wrong = ActuatorCandidateState(actuator_id="actuator.same-tick-wrong")
    lagged_wrong = ActuatorCandidateState(actuator_id="actuator.lagged-wrong")
    for t in range(n_ticks):
        correct.observe_effect(
            "percept.x", activation=activations[t], delta_percept=percept[t + 1] - percept[t]
        )
        # Wrong #1: same-tick delta (percept(t) - percept(t)), i.e. no real
        # time-shift at all — always exactly zero for this series.
        same_tick_wrong.observe_effect(
            "percept.x", activation=activations[t], delta_percept=percept[t] - percept[t]
        )
        # Wrong #2: a real, non-degenerate delta series, but taken from
        # BEFORE the activation (percept(t) - percept(t-1)) instead of
        # after it — proves the contract is about which tick boundary is
        # used, not merely "delta must be nonzero".
        if t >= 1:
            lagged_wrong.observe_effect(
                "percept.x", activation=activations[t], delta_percept=percept[t] - percept[t - 1]
            )

    assert correct.effect_strength > 0.9
    assert same_tick_wrong.effect_strength == 0.0
    assert lagged_wrong.effect_strength < 0.5
