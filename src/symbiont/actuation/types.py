from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

ActuatorId = str


def _require_finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _require_unit_range(value: Any, field: str) -> float:
    number = _require_finite(value, field)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be within [0.0, 1.0]")
    return number


def _require_nonneg_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an int")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _require_nonneg_finite(value: Any, field: str) -> float:
    number = _require_finite(value, field)
    if number < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return number


@dataclass(frozen=True, slots=True)
class MotorCandidate:
    """A motor channel not yet consolidated into the active repertoire."""

    actuator_id: ActuatorId


@dataclass(frozen=True, slots=True)
class MotorIntent:
    """What the organism intends to do, before the body executes it."""

    actuator_id: ActuatorId
    activation: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "activation", _require_unit_range(self.activation, "activation"))


@dataclass(frozen=True, slots=True)
class Actuation:
    """What the body actually delivered. No World consequence lives here."""

    actuator_id: ActuatorId
    requested: float
    delivered: float
    cost: float
    health_at_execution: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested", _require_unit_range(self.requested, "requested"))
        object.__setattr__(self, "delivered", _require_unit_range(self.delivered, "delivered"))
        object.__setattr__(self, "health_at_execution", _require_unit_range(self.health_at_execution, "health_at_execution"))
        cost = _require_finite(self.cost, "cost")
        if cost < 0.0:
            raise ValueError("cost must be non-negative")
        object.__setattr__(self, "cost", cost)
