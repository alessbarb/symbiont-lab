from __future__ import annotations

import random

import pytest

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.checkpoint import export_actuation_state, restore_actuation_state
from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.proposer import ActuatorProposer

_ORGANISM_ID = "org-continuity"
_WINDOW_TICKS = 8
_MIN_PROBING_WINDOWS = 2
_EFFECT_THRESHOLD = 0.6
_PROBE_LIMIT = 1
_SEED = 17
# Chosen mid-window (tick_in_window == 6 at the split point, < window_ticks
# == 8), well past the point any relation has established count >= 1 for
# this single-actuator setup, so the checkpoint captures live, real
# evidence — a meaningful mid-window continuity test.
_SPLIT_TICK = 6
_TOTAL_TICKS = _WINDOW_TICKS * 3  # three full windows


def _constitution():
    return derive_actuator_constitution(MotorGenes(slot_count=1))


def _feed_ticks(proposer: ActuatorProposer, rng: random.Random, *, start_tick: int, end_tick: int) -> None:
    for tick in range(start_tick, end_tick):
        plan = proposer.probing_plan(tick=tick)
        for actuator_id, on in plan.items():
            activation = 1.0 if on else 0.0
            delta = activation + rng.gauss(0, 0.02)  # causal signal, same generator draw order in both runs
            proposer.record_effect(actuator_id, "percept.x", activation=activation, delta_percept=delta, tick=tick)
        for actuator_id in plan:
            proposer.advance_tick(actuator_id)


def _snapshot(proposer: ActuatorProposer) -> dict:
    return {
        "active_repertoire": proposer.active_repertoire,
        "probe_cursor": proposer._probe_cursor,  # noqa: SLF001 — test-only introspection
        "states": {
            state.actuator_id: {
                "probing_state": state.probing_state,
                "activations": state.activations,
                "windows_completed": state.windows_completed,
                "windows_with_effect": state.windows_with_effect,
                "tick_in_window": state.tick_in_window,
                "effect_relations": dict(state.effect_relations),
                "current_window_relations": dict(state._current_window_relations),  # noqa: SLF001
            }
            for state in proposer.states
        },
    }


def test_checkpoint_restore_mid_window_reproduces_uninterrupted_run():
    """Run A: probe continuously for the full run.
    Run B: probe up to a mid-window split, checkpoint, restore, then probe
    the rest — using the SAME signal-generator draw sequence as run A.

    Both runs must end in an identical state: calendar decisions (implied by
    identical tick_in_window/windows_completed and therefore identical
    probing_calendar lookups), candidate states, effect relations (bit-exact
    PairAccumulator equality, since to_payload/from_payload round-trips
    floats with no precision loss), and active repertoire.
    """
    constitution = _constitution()

    # Run A: uninterrupted.
    proposer_a = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    rng_a = random.Random(_SEED)
    _feed_ticks(proposer_a, rng_a, start_tick=0, end_tick=_TOTAL_TICKS)

    # Run B: split at _SPLIT_TICK, checkpoint, restore, continue.
    proposer_b = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    rng_b = random.Random(_SEED)  # identical seed, consumed in the same call order as rng_a up to the split
    _feed_ticks(proposer_b, rng_b, start_tick=0, end_tick=_SPLIT_TICK)

    payload = export_actuation_state(proposer_b)
    # Sanity check this is a meaningful mid-window checkpoint: evidence
    # actually survived the export (nothing is withheld or reset — spec
    # §16.6 rev5).
    (actuator_id,) = constitution.actuator_ids
    assert payload["candidates"][actuator_id]["effect_relations"]["percept.x"]["count"] == _SPLIT_TICK
    assert payload["candidates"][actuator_id]["tick_in_window"] == _SPLIT_TICK

    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    _feed_ticks(restored, rng_b, start_tick=_SPLIT_TICK, end_tick=_TOTAL_TICKS)

    assert _snapshot(restored) == _snapshot(proposer_a)


@pytest.mark.parametrize("split_tick", [0, 1, 2, 3, 6, 8, 9, 15, 20])
def test_checkpoint_restore_is_bit_exact_from_any_tick_including_the_first_sample(split_tick):
    """Spec §16.6 rev5: checkpoint state is not filtered externally-
    observable state — there is no sample-count floor below which a
    restore is allowed to diverge from an uninterrupted run. This was a
    real bug in an earlier draft (a min-sample export gate silently
    dropped a relation's history below that count, permanently diverging
    the cumulative Welford accumulator afterward — a single withheld
    sample can never be "caught up" later since it's a running aggregate,
    not a replayable log). Verified here at split_tick == 0 (checkpoint
    before any sample exists at all) through several window boundaries.
    """
    constitution = _constitution()

    proposer_a = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    rng_a = random.Random(_SEED)
    _feed_ticks(proposer_a, rng_a, start_tick=0, end_tick=_TOTAL_TICKS)

    proposer_b = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    rng_b = random.Random(_SEED)
    _feed_ticks(proposer_b, rng_b, start_tick=0, end_tick=split_tick)

    payload = export_actuation_state(proposer_b)
    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    _feed_ticks(restored, rng_b, start_tick=split_tick, end_tick=_TOTAL_TICKS)

    assert _snapshot(restored) == _snapshot(proposer_a)


def _feed_ticks_multi(proposer: ActuatorProposer, rng: random.Random, causal_id: str, *, start_tick: int, end_tick: int) -> None:
    for tick in range(start_tick, end_tick):
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


def test_checkpoint_restore_after_completed_windows_with_multiple_actuators():
    """The single-actuator test above never exercises a split where
    windows_completed is already nonzero — with probe_limit=1 rotating
    across 3 actuators, each is probed roughly every third tick, so windows
    complete at different, non-aligned tick offsets per actuator. This is
    exactly the scenario revision-4's now-removed reset would have
    corrupted: a nonzero windows_completed reset to 0 would desync the
    restored window_index (used for probing_calendar) from the index the
    evidence was actually recorded under, for whichever actuator had
    already completed one or more windows at the split point."""
    constitution = derive_actuator_constitution(MotorGenes(slot_count=3))
    causal_id = constitution.actuator_ids[0]
    total_ticks = _WINDOW_TICKS * 5
    split_tick = 30  # well past several actuators' first window completions

    proposer_a = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=1,
    )
    rng_a = random.Random(_SEED)
    _feed_ticks_multi(proposer_a, rng_a, causal_id, start_tick=0, end_tick=total_ticks)

    proposer_b = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=1,
    )
    rng_b = random.Random(_SEED)
    _feed_ticks_multi(proposer_b, rng_b, causal_id, start_tick=0, end_tick=split_tick)

    payload = export_actuation_state(proposer_b)
    # Sanity: at least one actuator has genuinely completed a window by the
    # split point — otherwise this test wouldn't exercise the nonzero-
    # windows_completed case at all.
    assert any(c["windows_completed"] > 0 for c in payload["candidates"].values())

    restored = restore_actuation_state(
        payload,
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=1,
    )
    _feed_ticks_multi(restored, rng_b, causal_id, start_tick=split_tick, end_tick=total_ticks)

    assert _snapshot(restored) == _snapshot(proposer_a)
