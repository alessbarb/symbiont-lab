from __future__ import annotations

from .health import ActuatorState
from .types import Actuation, MotorIntent


class ActuatorSystem:
    """Resolves a MotorIntent into an Actuation, given the body's own state.

    Pure with respect to World: nothing here knows what ``delivered``
    causes outside the organism (spec §2 — the World consequence is never
    part of Actuation).
    """

    def execute(self, intent: MotorIntent, state: ActuatorState) -> Actuation:
        if intent.actuator_id != state.actuator_id:
            raise ValueError(
                f"intent for {intent.actuator_id!r} cannot be executed against state for {state.actuator_id!r}"
            )
        delivered = intent.activation * state.health * state.reliability
        cost = state.cost * intent.activation
        return Actuation(
            actuator_id=intent.actuator_id,
            requested=intent.activation,
            delivered=delivered,
            cost=cost,
            health_at_execution=state.health,
        )
