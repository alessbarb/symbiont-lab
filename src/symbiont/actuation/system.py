from __future__ import annotations

from .surface import ActuatorSurface
from .types import Actuation, MotorIntent


class ActuatorSystem:
    """Validate and hand a command across the opaque body boundary.

    It does not simulate actuator health, reliability, cost or environmental
    effect.  Those are body-side consequences.
    """

    def execute(
        self,
        intent: MotorIntent,
        surface: ActuatorSurface,
    ) -> Actuation:
        delivered = surface.validate(intent.actuator_id, intent.activation)
        return Actuation(
            actuator_id=intent.actuator_id,
            requested=intent.activation,
            delivered=delivered,
        )
