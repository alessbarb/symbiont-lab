from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constitution import MotorSlot
from .types import ActuatorId, _require_finite, _require_unit_range


@dataclass(slots=True)
class ActuatorState:
    """Physiological state of one actuator: health/reliability/cost.

    ``degrade`` models ordinary wear (spec §15: "actuator unavailable/
    degraded"). A malformed checkpoint payload must raise, never coerce
    into a plausible-looking degraded state — that would disguise data
    corruption as fisiología.
    """

    actuator_id: ActuatorId
    health: float
    reliability: float
    cost: float

    @classmethod
    def from_slot(cls, slot: MotorSlot) -> "ActuatorState":
        return cls(actuator_id=slot.actuator_id, health=slot.initial_health, reliability=1.0, cost=slot.basal_cost)

    def degrade(self, amount: float) -> None:
        amount = _require_finite(amount, "amount")
        if amount < 0.0:
            raise ValueError("amount must be non-negative")
        self.health = max(0.0, min(1.0, self.health - amount))

    def to_payload(self) -> dict[str, Any]:
        return {
            "actuator_id": self.actuator_id,
            "health": self.health,
            "reliability": self.reliability,
            "cost": self.cost,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ActuatorState":
        required = {"actuator_id", "health", "reliability", "cost"}
        missing = required - set(payload)
        if missing:
            raise ValueError(f"ActuatorState payload missing fields: {sorted(missing)}")
        return cls(
            actuator_id=str(payload["actuator_id"]),
            health=_require_unit_range(payload["health"], "health"),
            reliability=_require_unit_range(payload["reliability"], "reliability"),
            cost=_require_finite(payload["cost"], "cost"),
        )
