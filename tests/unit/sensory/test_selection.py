from __future__ import annotations

import math

import pytest

from symbiont.sensory.selection import (
    MIN_SELECTION_OBSERVATIONS,
    PairwisePredictiveEvidence,
    SensorySelectionEngine,
)


def test_pairwise_predictive_evidence_beats_persistence_for_linear_relation() -> None:
    evidence = PairwisePredictiveEvidence("sensor.a", "sensor.target")
    previous_x = 0.0
    previous_target = 0.0
    for tick in range(1, 80):
        x = math.sin(tick / 7.0)
        target = 2.0 * previous_x + 0.25
        evidence.observe(previous_x, target)
        previous_x = x
        previous_target = target

    assert evidence.observations >= MIN_SELECTION_OBSERVATIONS
    assert evidence.positive_gain > 0.5
    assert evidence.model_error_ewma < evidence.baseline_error_ewma


def test_selection_engine_does_not_need_an_evaluator_target_label() -> None:
    engine = SensorySelectionEngine()
    previous_driver = 0.0
    for tick in range(1, 80):
        driver = math.sin(tick / 5.0)
        outcome = 1.5 * previous_driver
        engine.observe(
            {
                "sensor.driver": driver,
                "sensor.noise": math.cos(tick * 1.7),
                "sensor.identity.outcome": outcome,
            },
            identity_targets={"sensor.identity.outcome"},
        )
        previous_driver = driver

    credits = engine.credits
    assert credits["sensor.driver"] > credits.get("sensor.noise", 0.0)


def test_selection_checkpoint_excludes_previous_raw_values() -> None:
    engine = SensorySelectionEngine()
    engine.observe(
        {"sensor.a": 1.0, "sensor.identity.target": 2.0},
        identity_targets={"sensor.identity.target"},
    )
    payload = engine.checkpoint()
    assert "previous" not in repr(payload).lower()

    restored = SensorySelectionEngine.restore(payload)
    assert restored.credits == {}


def test_selection_engine_is_bounded() -> None:
    engine = SensorySelectionEngine(max_pairs=4)
    for tick in range(12):
        values = {
            f"sensor.{index}": float(tick + index)
            for index in range(6)
        }
        values["sensor.identity.target"] = float(tick)
        engine.observe(values, identity_targets={"sensor.identity.target"})
    assert len(engine.checkpoint()["pairs"]) <= 4


def test_independent_noise_does_not_receive_credit_for_merely_beating_persistence() -> None:
    import random

    engine = SensorySelectionEngine()
    source_rng = random.Random(101)
    target_rng = random.Random(999)
    for _ in range(256):
        engine.observe(
            {
                "sensor.noise": source_rng.gauss(0.0, 1.0),
                "sensor.identity.target": target_rng.gauss(0.0, 1.0),
            },
            identity_targets={"sensor.identity.target"},
        )
    assert engine.credits.get("sensor.noise", 0.0) == 0.0
