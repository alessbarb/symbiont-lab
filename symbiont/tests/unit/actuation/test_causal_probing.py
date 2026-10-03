"""Causal probing exploration (Factorized Effect Representation v1 §13)."""

from __future__ import annotations

import pytest

from symbiont.actuation.sensorimotor import CompetenceDevelopmentEngine

IDS = tuple(f"actuator.{index}" for index in range(6))


def _engine(**options) -> CompetenceDevelopmentEngine:
    return CompetenceDevelopmentEngine(IDS, organism_id="probe", **options)


def _vectors(engine, ticks, *, preference=()):
    return [
        {
            intent.actuator_id: intent.activation
            for intent in engine.motor_intents(tick, exploration_preference=preference)
        }
        for tick in range(ticks)
    ]


def test_probing_is_off_by_default_and_exploration_is_unchanged():
    default, explicit = _engine(), _engine(probing_share=0.0)
    assert not any(default.is_probing_epoch(epoch) for epoch in range(200))
    assert _vectors(default, 240) == _vectors(explicit, 240)


def test_probing_epoch_pulses_one_channel_with_quiet_windows():
    engine = _engine(probing_share=1.0)
    vectors = _vectors(engine, 24)
    for tick, vector in enumerate(vectors):
        if 4 <= tick < 10 or 14 <= tick < 20:
            assert len(vector) == 1
        else:
            assert vector == {}  # a genuine passive window
    assert len({next(iter(v)) for v in vectors if v}) == 1


def test_probed_unit_repeats_for_several_epochs_then_moves_on():
    engine = _engine(probing_share=1.0)
    probed = [next(iter(v)) for v in _vectors(engine, 24 * 8) if v]
    per_epoch = [probed[index * 12] for index in range(8)]
    assert len(set(per_epoch[:4])) == 1
    assert per_epoch[4] != per_epoch[0]


def test_probing_follows_the_exploration_preference():
    engine = _engine(probing_share=1.0)
    vectors = _vectors(engine, 24, preference=("actuator.3",))
    assert {next(iter(v)) for v in vectors if v} == {"actuator.3"}


def test_probing_respects_mutually_exclusive_groups():
    engine = _engine(probing_share=1.0, exclusive_actuator_groups=(("actuator.0", "actuator.1"),))
    for vector in _vectors(engine, 24 * 12):
        assert not {"actuator.0", "actuator.1"} <= set(vector)


def test_probing_is_deterministic_and_survives_checkpoint_mid_series():
    first = _engine(probing_share=0.5)
    for tick in range(24 * 5 + 7):
        first.motor_intents(tick)
    restored = CompetenceDevelopmentEngine.restore(
        first.checkpoint(), actuator_ids=IDS, organism_id="probe"
    )
    for tick in range(24 * 5 + 7, 24 * 12):
        assert restored.motor_intents(tick) == first.motor_intents(tick)


def test_invalid_probing_share_is_rejected():
    with pytest.raises(ValueError):
        _engine(probing_share=1.5)
