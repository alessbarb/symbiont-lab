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


def test_motor_intent_rejects_non_finite_activation():
    with pytest.raises(ValueError):
        MotorIntent(actuator_id="actuator.a", activation=math.nan)


def test_actuation_requires_delivered_le_requested_domain_and_finite_cost():
    actuation = Actuation(
        actuator_id="actuator.a", requested=0.8, delivered=0.5, cost=0.1, health_at_execution=0.9
    )
    assert actuation.delivered == 0.5
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=-0.1, cost=0.1, health_at_execution=0.9)
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=0.5, cost=-0.1, health_at_execution=0.9)
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=0.5, cost=0.1, health_at_execution=1.5)
