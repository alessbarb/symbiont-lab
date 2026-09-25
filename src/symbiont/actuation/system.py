"""Canonical body-boundary execution for Sensorimotor v2."""
from __future__ import annotations

from .action import MotorCommand
from .surface import ActuatorSurface
from .types import Actuation


class ActuatorSystem:
    """Validate and hand a committed command across the opaque body boundary."""

    def execute_command(
        self,
        command: MotorCommand,
        surface: ActuatorSurface,
    ) -> tuple[Actuation, ...]:
        if command.surface_fingerprint != surface.contract_fingerprint:
            raise RuntimeError("motor command targets a different actuator surface")
        delivered: list[Actuation] = []
        for actuator_id, activation in command.channels:
            value = surface.validate(actuator_id, activation)
            delivered.append(
                Actuation(
                    actuator_id=actuator_id,
                    requested=activation,
                    delivered=value,
                )
            )
        return tuple(delivered)
