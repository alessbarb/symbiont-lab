from __future__ import annotations

import pytest

from symbiont.actuation.constitution import MotorSlot
from symbiont.actuation.health import ActuatorState


def _slot() -> MotorSlot:
    return MotorSlot(
        slot_id="motor_slot.0",
        actuator_id="actuator.a",
        basal_cost=0.05,
        initial_health=1.0,
        execution_threshold=0.5,
    )


def test_from_slot_uses_slot_initial_values():
    state = ActuatorState.from_slot(_slot())
    assert state.actuator_id == "actuator.a"
    assert state.health == 1.0
    assert state.reliability == 1.0
    assert state.cost == 0.05


def test_degrade_clamps_health_to_zero_floor():
    state = ActuatorState.from_slot(_slot())
    state.degrade(1.5)
    assert state.health == 0.0


def test_degrade_rejects_negative_amount():
    state = ActuatorState.from_slot(_slot())
    with pytest.raises(ValueError):
        state.degrade(-0.1)


def test_payload_round_trip():
    state = ActuatorState.from_slot(_slot())
    state.degrade(0.3)
    restored = ActuatorState.from_payload(state.to_payload())
    assert restored.health == pytest.approx(0.7)
    assert restored.actuator_id == "actuator.a"


def test_from_payload_raises_on_out_of_range_health_instead_of_clamping():
    payload = {"actuator_id": "actuator.a", "health": 1.4, "reliability": 1.0, "cost": 0.05}
    with pytest.raises(ValueError):
        ActuatorState.from_payload(payload)


def test_from_payload_raises_on_missing_field():
    payload = {"actuator_id": "actuator.a", "health": 1.0, "cost": 0.05}
    with pytest.raises(ValueError):
        ActuatorState.from_payload(payload)
