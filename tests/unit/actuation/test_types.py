from __future__ import annotations

import math

import pytest

from symbiont.actuation.types import Actuation, MotorCandidate, MotorIntent


def test_motor_candidate_holds_actuator_id():
    candidate = MotorCandidate(actuator_id="actuator.deadbeef")
    assert candidate.actuator_id == "actuator.deadbeef"


def test_motor_intent_requires_activation_in_unit_range():
    MotorIntent(actuator_id="actuator.a", activation=0.0)
    MotorIntent(actuator_id="actuator.a", activation=1.0)
    with pytest.raises(ValueError):
        MotorIntent(actuator_id="actuator.a", activation=1.1)
    with pytest.raises(ValueError):
        MotorIntent(actuator_id="actuator.a", activation=-0.1)


def test_motor_intent_rejects_non_finite_and_bool_activation():
    for value in (math.nan, True, False):
        with pytest.raises(ValueError):
            MotorIntent(actuator_id="actuator.a", activation=value)


def test_actuation_contains_no_interpreted_health_or_cost():
    actuation = Actuation(actuator_id="actuator.a", requested=0.8, delivered=0.5)
    assert actuation.delivered == 0.5
    assert not hasattr(actuation, "cost")
    assert not hasattr(actuation, "health_at_execution")
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=-0.1)
