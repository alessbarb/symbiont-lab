"""Canonical body-boundary execution for Sensorimotor v2."""
from __future__ import annotations

from .action import MotorCommand
from .surface import ActuatorSurface
from .types import Actuation, MotorIntent


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

    def execute(
        self,
        intent: MotorIntent,
        surface: ActuatorSurface,
    ) -> Actuation:
        """Legacy migration/test helper; not an organism action authority."""
        delivered = surface.validate(intent.actuator_id, intent.activation)
        return Actuation(
            actuator_id=intent.actuator_id,
            requested=intent.activation,
            delivered=delivered,
        )
