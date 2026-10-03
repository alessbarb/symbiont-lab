from __future__ import annotations

import pytest

from symbiont.actuation.action import MotorCommand
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.actuation.system import ActuatorSystem


def _command(surface, actuator_id: str, activation: float) -> MotorCommand:
    return MotorCommand.from_mapping(
        command_id="command.test",
        commitment_id="commitment.test",
        controller_id="controller.test",
        competence_id=None,
        surface_fingerprint=surface.contract_fingerprint,
        channels={actuator_id: activation},
        issued_at_tick=1,
        embodiment_id="embodiment.test",
    )


def test_system_hands_committed_command_to_body_boundary_without_interpreting_health():
    surface = derive_actuator_constitution(1)
    actuator_id = surface.actuator_ids[0]
    actuations = ActuatorSystem().execute_command(
        _command(surface, actuator_id, 0.8),
        surface,
    )
    assert len(actuations) == 1
    assert actuations[0].requested == 0.8
    assert actuations[0].delivered == 0.8


def test_system_rejects_channel_outside_surface():
    surface = derive_actuator_constitution(1)
    with pytest.raises(KeyError):
        ActuatorSystem().execute_command(
            _command(surface, "actuator.other", 0.5),
            surface,
        )


def test_system_rejects_command_for_another_surface():
    surface = derive_actuator_constitution(1, physical_contract="surface.a")
    foreign = derive_actuator_constitution(1, physical_contract="surface.b")
    with pytest.raises(RuntimeError, match="different actuator surface"):
        ActuatorSystem().execute_command(
            _command(foreign, foreign.actuator_ids[0], 0.5),
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
