"""Immutable contracts for innate reactivity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReactiveState:
    """Semantic-free constitutional urgency for one organism tick."""

    interrupt: float
    withdrawal: float
    stabilization: float
    conservation: float
    attention: float
    deviation: float
    deviation_velocity: float
    surprise: float
    signature: str

    @property
    def acute(self) -> bool:
        return self.withdrawal >= 0.55 or self.interrupt >= 0.70
