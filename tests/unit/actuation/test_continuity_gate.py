from __future__ import annotations

import random

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
# N is chosen mid-window (tick_in_window == 6 at the split point, < window_ticks
# == 8) and >= the export sample minimum (6, see candidate.py's
# _MIN_RELATION_SAMPLES_FOR_EXPORT) so the checkpoint captures live,
# non-reset evidence — a meaningful mid-window continuity test, not a
# trivial "everything got wiped and restarted from zero" case.
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
    # actually survived the export (wasn't reset to empty/zero).
    (actuator_id,) = constitution.actuator_ids
    assert payload["candidates"][actuator_id]["effect_relations"] != {}
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


def test_checkpoint_below_two_samples_discards_that_relation_atomically_then_converges():
    """Spec §16.6: the replay-equivalence contract is per-relation, not
    absolute. A relation with fewer than 2 cumulative samples at checkpoint
    time is deliberately, atomically discarded (both its cumulative
    PairAccumulator AND its in-progress current-window fragment) — the
    principled privacy floor (a count==1 Welford mean IS the raw sample).
    Once a relation clears 2 samples, checkpoint/restore is bit-exact from
    that point forward. This test checks that documented boundary directly,
    rather than treating early splits as a silently-known failure."""
    constitution = _constitution()
    (actuator_id,) = constitution.actuator_ids

    proposer = ActuatorProposer(
        constitution,
        organism_id=_ORGANISM_ID,
        min_probing_windows=_MIN_PROBING_WINDOWS,
        effect_threshold=_EFFECT_THRESHOLD,
        window_ticks=_WINDOW_TICKS,
        probe_limit=_PROBE_LIMIT,
    )
    rng = random.Random(_SEED)
    _feed_ticks(proposer, rng, start_tick=0, end_tick=1)  # exactly one sample recorded

    payload = export_actuation_state(proposer)
    candidate_payload = payload["candidates"][actuator_id]
    # Documented discard: below the 2-sample floor, both the cumulative
    # relation and its current-window fragment are atomically absent.
    assert candidate_payload["effect_relations"] == {}
    assert candidate_payload["current_window_relations"] == {}

    # One more tick reaches count == 2 — now it clears the floor and both
    # a fresh export AND the live in-memory state agree going forward.
    _feed_ticks(proposer, rng, start_tick=1, end_tick=2)
    payload_at_two = export_actuation_state(proposer)
    established = payload_at_two["candidates"][actuator_id]
    assert established["effect_relations"]["percept.x"]["count"] == 2
    assert established["current_window_relations"]["percept.x"]["count"] == 2


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
