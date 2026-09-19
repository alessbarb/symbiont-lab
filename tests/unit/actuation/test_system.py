from __future__ import annotations

from symbiont.actuation.health import ActuatorState
from symbiont.actuation.system import ActuatorSystem
from symbiont.actuation.types import MotorIntent


def test_healthy_actuator_delivers_full_requested_activation():
    state = ActuatorState(actuator_id="actuator.a", health=1.0, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.a", activation=0.8)
    actuation = ActuatorSystem().execute(intent, state)
    assert actuation.requested == 0.8
    assert actuation.delivered == 0.8
    assert actuation.health_at_execution == 1.0


def test_degraded_actuator_delivers_less_than_requested():
    state = ActuatorState(actuator_id="actuator.a", health=0.5, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.a", activation=0.8)
    actuation = ActuatorSystem().execute(intent, state)
    assert actuation.delivered == 0.4  # 0.8 * health(0.5)


def test_zero_health_actuator_delivers_nothing():
    state = ActuatorState(actuator_id="actuator.a", health=0.0, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.a", activation=1.0)
    actuation = ActuatorSystem().execute(intent, state)
    assert actuation.delivered == 0.0


def test_cost_scales_with_requested_activation():
    state = ActuatorState(actuator_id="actuator.a", health=1.0, reliability=1.0, cost=0.1)
    low = ActuatorSystem().execute(MotorIntent(actuator_id="actuator.a", activation=0.2), state)
    high = ActuatorSystem().execute(MotorIntent(actuator_id="actuator.a", activation=1.0), state)
    assert high.cost > low.cost


def test_execute_rejects_mismatched_actuator_ids():
    state = ActuatorState(actuator_id="actuator.a", health=1.0, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.other", activation=0.5)
    import pytest

    with pytest.raises(ValueError):
        ActuatorSystem().execute(intent, state)
