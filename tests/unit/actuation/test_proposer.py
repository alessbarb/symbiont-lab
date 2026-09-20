from __future__ import annotations

import random

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.proposer import ActuatorProposer


def _constitution(slot_count: int = 2):
    return derive_actuator_constitution(MotorGenes(slot_count=slot_count))


def test_new_proposer_has_all_actuators_dormant():
    constitution = _constitution()
    proposer = ActuatorProposer(constitution, organism_id="org-1")
    assert proposer.active_repertoire == ()
    assert all(state.probing_state == "dormant" for state in proposer.states)


def test_probing_plan_only_selects_up_to_probe_limit_candidates():
    constitution = _constitution(slot_count=6)
    proposer = ActuatorProposer(constitution, organism_id="org-1", probe_limit=1)
    plan = proposer.probing_plan(tick=0)
    assert len(plan) <= 1


def test_causal_actuator_reaches_active_after_enough_windows():
    constitution = _constitution(slot_count=2)
    causal_id, sham_id = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-1", min_probing_windows=2, effect_threshold=0.6, window_ticks=8, probe_limit=2
    )
    rng = random.Random(11)

    total_ticks = 8 * 3  # three full windows of 8 ticks each
    for tick in range(total_ticks):
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

    assert causal_id in proposer.active_repertoire
    assert sham_id not in proposer.active_repertoire


def test_one_loud_window_among_noisy_ones_does_not_promote():
    """Spec §6 revisión 3: a single strong window must not carry the whole
    candidate to active by inflating cumulative effect_strength while every
    other window shows nothing on its own — promotion requires the effect
    to replicate across min_probing_windows separate windows."""
    constitution = _constitution(slot_count=1)
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-1", min_probing_windows=3, effect_threshold=0.6, window_ticks=8, probe_limit=1
    )
    rng = random.Random(5)

    total_ticks = 8 * 4  # four windows: one strong, three noise
    for tick in range(total_ticks):
        window_index = tick // 8
        plan = proposer.probing_plan(tick=tick)
        for pid, on in plan.items():
            activation = 1.0 if on else 0.0
            if window_index == 0:
                delta = activation + rng.gauss(0, 0.02)  # strong causal signal, window 0 only
            else:
                delta = rng.gauss(0, 1.0)  # pure noise every other window
            proposer.record_effect(pid, "percept.x", activation=activation, delta_percept=delta, tick=tick)
        for pid in plan:
            proposer.advance_tick(pid)

    state = next(s for s in proposer.states if s.actuator_id == actuator_id)
    assert state.windows_completed == 4
    assert state.windows_with_effect < 3  # never replicated across 3 separate windows
    assert actuator_id not in proposer.active_repertoire


def test_probing_candidate_stays_probing_before_min_windows_reached():
    constitution = _constitution(slot_count=1)
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(constitution, organism_id="org-1", min_probing_windows=5, window_ticks=8)
    for tick in range(8):  # exactly one full window, min_probing_windows requires five
        proposer.probing_plan(tick=tick)
        proposer.record_effect(actuator_id, "percept.x", activation=1.0, delta_percept=1.0, tick=tick)
        proposer.advance_tick(actuator_id)
    state = next(s for s in proposer.states if s.actuator_id == actuator_id)
    assert state.probing_state == "probing"
    assert state.windows_completed == 1
    assert actuator_id not in proposer.active_repertoire


def test_natural_evidence_can_promote_without_running_probing_calendar():
    constitution = _constitution(slot_count=1)
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution,
        organism_id="org-natural",
        effect_threshold=0.6,
    )

    for tick in range(12):
        activation = 0.2 + 0.05 * tick
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=activation * 0.8,
            tick=tick,
        )
        proposer.consider_natural_evidence(actuator_id, min_samples=12)

    state = proposer.states[0]
    assert state.windows_completed == 0
    assert state.windows_with_effect == 0
    assert state.tick_in_window == 0
    assert actuator_id in proposer.active_repertoire


def test_natural_evidence_does_not_promote_before_minimum_samples():
    constitution = _constitution(slot_count=1)
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(constitution, organism_id="org-natural")

    for tick in range(11):
        activation = 0.1 + 0.06 * tick
        proposer.record_effect(
            actuator_id,
            "percept.x",
            activation=activation,
            delta_percept=activation,
            tick=tick,
        )

    assert proposer.consider_natural_evidence(actuator_id, min_samples=12) is False
    assert proposer.active_repertoire == ()
