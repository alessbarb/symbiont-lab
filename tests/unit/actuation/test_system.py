from __future__ import annotations

import pytest

from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.actuation.system import ActuatorSystem
from symbiont.actuation.types import MotorIntent


def test_system_hands_legal_command_to_body_boundary_without_interpreting_health():
    surface = derive_actuator_constitution(1)
    actuator_id = surface.actuator_ids[0]
    intent = MotorIntent(actuator_id=actuator_id, activation=0.8)
    actuation = ActuatorSystem().execute(intent, surface)
    assert actuation.requested == 0.8
    assert actuation.delivered == 0.8


def test_system_rejects_channel_outside_surface():
    surface = derive_actuator_constitution(1)
    with pytest.raises(KeyError):
        ActuatorSystem().execute(
            MotorIntent(actuator_id="actuator.other", activation=0.5),
            surface,
        )


def test_surface_is_command_contract_not_body_model():
    channel = derive_actuator_constitution(1).slots[0]
    assert hasattr(channel, "command_min")
    assert hasattr(channel, "command_max")
    assert hasattr(channel, "neutral")
    assert not hasattr(channel, "initial_health")
    assert not hasattr(channel, "basal_cost")
    assert not hasattr(channel, "execution_threshold")
