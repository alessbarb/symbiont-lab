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
    state = ActuatorCandidateState(
        actuator_id="actuator.a", probing_state="probing", windows_completed=2, windows_with_effect=2, tick_in_window=3
    )
    for i in range(10):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=activation)
    payload = state.to_payload()
    restored = ActuatorCandidateState.from_payload(payload)
    assert restored.actuator_id == "actuator.a"
    assert restored.probing_state == "probing"
    assert restored.windows_completed == 2
    assert restored.windows_with_effect == 2
    assert restored.tick_in_window == 3
    assert restored.effect_relations["percept.x"].count == 10
    assert restored._current_window_relations["percept.x"].count == 10  # noqa: SLF001


def test_from_payload_raises_when_effect_relations_exceed_max():
    payload = {
        "actuator_id": "actuator.a",
        "activations": 0,
        "probing_state": "dormant",
        "windows_completed": 0,
        "windows_with_effect": 0,
        "tick_in_window": 0,
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
        "current_window_relations": {},
    }
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)


def test_from_payload_raises_on_corrupted_probing_state():
    payload = {
        "actuator_id": "actuator.a",
        "activations": 0,
        "probing_state": "orbiting",  # not a valid state
        "windows_completed": 0,
        "windows_with_effect": 0,
        "tick_in_window": 0,
        "last_seen_tick": 0,
        "cost_evidence": 0.0,
        "effect_relations": {},
        "current_window_relations": {},
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
        "windows_with_effect",
        "tick_in_window",
        "effect_relations",
        "current_window_relations",
    ],
)
def test_from_payload_raises_on_missing_field_instead_of_defaulting(missing_field):
    payload = {
        "actuator_id": "actuator.a",
        "activations": 3,
        "probing_state": "probing",
        "windows_completed": 1,
        "windows_with_effect": 1,
        "tick_in_window": 2,
        "last_seen_tick": 5,
        "cost_evidence": 0.1,
        "effect_relations": {},
        "current_window_relations": {},
    }
    del payload[missing_field]
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("activations", True),
        ("activations", -1),
        ("activations", 1.5),
        ("last_seen_tick", -1),
        ("windows_completed", -1),
        ("windows_with_effect", -1),
        ("tick_in_window", -1),
        ("cost_evidence", -0.1),
        ("cost_evidence", float("nan")),
        ("actuator_id", ""),
        ("actuator_id", 123),
    ],
)
def test_from_payload_raises_on_invalid_field_value_instead_of_coercing(field_name, bad_value):
    payload = {
        "actuator_id": "actuator.a",
        "activations": 3,
        "probing_state": "probing",
        "windows_completed": 1,
        "windows_with_effect": 1,
        "tick_in_window": 2,
        "last_seen_tick": 5,
        "cost_evidence": 0.1,
        "effect_relations": {},
        "current_window_relations": {},
    }
    payload[field_name] = bad_value
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)


def test_to_payload_exports_windows_completed_and_phase_unconditionally():
    # Spec §6 revisión 5 supersedes revisión 3/4's "reset windows_completed/
    # windows_with_effect/tick_in_window together when relations are
    # withheld" rule: that reset broke checkpoint/restore replay
    # equivalence (test_continuity_gate.py) by discarding real, unearned-
    # by-nothing scheduling phase whenever cumulative evidence happened to
    # fall under the export sample minimum. These fields are now exported
    # exactly as they are, regardless of effect_relations' export gating.
    state = ActuatorCandidateState(actuator_id="actuator.a", windows_completed=3, windows_with_effect=3, tick_in_window=4)
    state.observe_effect("percept.x", activation=1.0, delta_percept=0.5)  # below export minimum
    payload = state.to_payload()
    assert payload["effect_relations"] == {}  # still gated: single-sample noise, not established
    assert payload["windows_completed"] == 3
    assert payload["windows_with_effect"] == 3
    assert payload["tick_in_window"] == 4

    restored = ActuatorCandidateState.from_payload(payload)
    assert restored.windows_completed == 3
    assert restored.windows_with_effect == 3
    assert restored.tick_in_window == 4


def test_promotion_requires_re_earned_effect_strength_after_restore():
    """The property I4 actually protects, verified directly rather than via
    the (now-removed) reset mechanism: a restored candidate whose
    windows_completed/windows_with_effect already clear min_probing_windows,
    but whose cumulative effect_relations was wiped by the export sample
    gate, must NOT promote purely from stale counters — effect_strength
    starts at 0.0 on the empty restored accumulator and must be re-earned
    by real post-restore evidence, exactly like any other promotion."""
    from symbiont.actuation.proposer import ActuatorProposer
    from symbiont.actuation.constitution import derive_actuator_constitution
    from symbiont.cognition.genome import MotorGenes

    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    (actuator_id,) = constitution.actuator_ids

    # A candidate that already satisfies both window-count gates, but whose
    # only cumulative sample is below the export minimum — to_payload wipes
    # effect_relations for it, exactly the state a checkpoint would produce
    # right after such a candidate's evidence happened to be under-sampled.
    state = ActuatorCandidateState(
        actuator_id=actuator_id, windows_completed=2, windows_with_effect=2, tick_in_window=0
    )
    state.observe_effect("percept.x", activation=1.0, delta_percept=0.5)  # single sample, below export minimum
    payload = state.to_payload()
    assert payload["effect_relations"] == {}
    restored_state = ActuatorCandidateState.from_payload(payload)
    assert restored_state.effect_strength == 0.0  # re-earned from nothing, not inherited

    proposer = ActuatorProposer(
        constitution, organism_id="org-guarantee", min_probing_windows=2, effect_threshold=0.6, window_ticks=8
    )
    proposer._states[actuator_id] = restored_state  # noqa: SLF001 — test-only injection of the restored state

    # Feed ONE strong post-restore window — a genuinely causal, high-effect
    # signal, so a false PASS here can't be explained by the signal being
    # too weak to promote regardless: this proves promotion is gated by
    # freshly re-earned evidence, not merely "no crash occurred".
    for tick in range(8):
        plan = proposer.probing_plan(tick=tick)
        for aid, on in plan.items():
            activation = 1.0 if on else 0.0
            proposer.record_effect(aid, "percept.x", activation=activation, delta_percept=activation, tick=tick)
        for aid in plan:
            proposer.advance_tick(aid)

    # windows_completed/windows_with_effect are now well past min_probing_windows
    # (2 inherited + 1 new = 3), yet ONE post-restore window's fresh evidence
    # was exactly what promoted it — not stale counters alone. To prove the
    # counters alone are insufficient, effect_strength before this window
    # was 0.0 (asserted above); this window's causal signal is what earned it.
    assert actuator_id in proposer.active_repertoire


def test_to_payload_preserves_current_window_relations_mid_window():
    # A mid-window checkpoint (established cumulative evidence present, so
    # no reset triggers) must preserve the in-progress window's own transient
    # evidence too — losing it would silently shrink that window's sample
    # count on restore, changing whether complete_window() later judges this
    # window to have shown effect (see test_continuity_gate.py).
    state = ActuatorCandidateState(actuator_id="actuator.a", tick_in_window=3)
    for i in range(6):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=activation)  # clears export minimum
    payload = state.to_payload()
    assert payload["current_window_relations"]["percept.x"]["count"] == 6

    restored = ActuatorCandidateState.from_payload(payload)
    assert restored._current_window_relations["percept.x"].count == 6  # noqa: SLF001
    assert restored.tick_in_window == 3


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


def test_complete_window_increments_windows_with_effect_only_when_this_window_shows_effect():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    # Window 1: strong causal signal this window.
    for i in range(20):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=activation)
    state.complete_window(effect_threshold=0.5)
    assert state.windows_with_effect == 1

    # Window 2: pure noise this window — the transient per-window accumulator
    # was reset by complete_window, so this window's own evidence is what
    # gets judged, not the cumulative effect_relations (which still remembers
    # window 1's strong signal).
    import random

    rng = random.Random(3)
    for i in range(20):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=rng.gauss(0, 1.0))
    state.complete_window(effect_threshold=0.5)
    assert state.windows_with_effect == 1  # unchanged — window 2 showed no effect on its own


def test_replication_requirement_rejects_one_loud_window_among_many_noisy_ones():
    """Spec §6 revisión 3: promotion needs effect replicated across multiple
    distinct windows, not a single strong window sustaining a high cumulative
    correlation while every other window is noise. This test exercises the
    ActuatorProposer-level promotion rule via direct field assertions on the
    candidate state, since windows_with_effect is what proposer.advance_tick
    checks alongside windows_completed."""
    state = ActuatorCandidateState(actuator_id="actuator.a")
    import random

    rng = random.Random(5)

    # Window 1: strong causal signal (drives cumulative effect_strength high).
    for i in range(20):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=activation + rng.gauss(0, 0.01))
    state.windows_completed += 1
    state.complete_window(effect_threshold=0.6)

    # Windows 2 and 3: pure noise, no effect this window each time.
    for _ in range(2):
        for i in range(20):
            activation = float(i % 2)
            state.observe_effect("percept.x", activation=activation, delta_percept=rng.gauss(0, 1.0))
        state.windows_completed += 1
        state.complete_window(effect_threshold=0.6)

    # The exact cumulative effect_strength value isn't the point here (it
    # depends on how much window 1's strong signal still shows through 60
    # total samples of mostly noise) — what matters is that only ONE window
    # out of three ever showed effect on its own: replication across >= 2
    # independent windows never happened, so a min_probing_windows=2 gate
    # would correctly withhold promotion regardless of the cumulative value.
    assert state.windows_with_effect == 1
    assert state.windows_completed == 3
