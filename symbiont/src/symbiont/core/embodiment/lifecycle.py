"""Explicit viability and irreversible organism continuity (v0.64)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .metabolism import ResourcePressure


class LifeState(StrEnum):
    ACTIVE = "active"
    STRESSED = "stressed"
    DORMANT = "dormant"
    DYING = "dying"
    DEAD = "dead"


class ViabilityController:
    SCHEMA_VERSION = 1

    def __init__(
        self, *, state: LifeState = LifeState.ACTIVE, organism_id: str | None = None
    ) -> None:
        self.state = LifeState(state)
        self.organism_id = organism_id
        self._death_finalized = self.state is LifeState.DEAD

    def transition(self, pressure: ResourcePressure, *, integrity: float) -> LifeState:
        if self.state is LifeState.DEAD:
            return self.state
        if not 0.0 <= integrity <= 1.0:
            raise ValueError("integrity must be within [0, 1]")
        pressure = ResourcePressure(pressure)
        if pressure is ResourcePressure.UNRECOVERABLE or integrity <= 0.0:
            self.state = LifeState.DYING
        elif pressure is ResourcePressure.SEVERE or integrity < 0.3:
            self.state = LifeState.DORMANT
        elif pressure is ResourcePressure.ELEVATED or integrity < 0.7:
            self.state = LifeState.STRESSED
        else:
            self.state = LifeState.ACTIVE
        return self.state

    def finalize_death(self) -> None:
        if self.state is not LifeState.DYING:
            raise ValueError("only a dying organism can finalize death")
        self.state = LifeState.DEAD
        self._death_finalized = True

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_id": self.organism_id,
            "state": self.state.value,
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "ViabilityController":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid viability checkpoint")
        return cls(state=payload["state"], organism_id=payload.get("organism_id"))


__all__ = ["LifeState", "ViabilityController"]
