"""Irreversible, resource-backed viability state for Milestone I."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from .metabolism import MetabolicSnapshot, ResourcePressure

from .physiology_config import (
    DEFAULT_PHYSIOLOGY_CONFIG,
    PhysiologyConfig,
)


class VitalState(StrEnum):
    ACTIVE = "active"
    STRESSED = "stressed"
    DORMANT = "dormant"
    AGONIZING = "agonizing"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class PhysiologySnapshot:

    state: VitalState
    transitions: int
    death_tick: int | None

class PhysiologyController:
    """Maps bounded metabolic pressure to viability; death cannot be undone."""
    def __init__(self, *, state: VitalState = VitalState.ACTIVE, transitions: int = 0, death_tick: int | None = None) -> None:
        if state is VitalState.DEAD and death_tick is None:
            raise ValueError("dead physiology requires death_tick")
        self._state, self._transitions, self._death_tick = state, transitions, death_tick

    @property
    def state(self) -> VitalState:
        return self._state

    def advance(self, metabolism: MetabolicSnapshot, *, tick: int, resting: bool = False) -> PhysiologySnapshot:
        if self._state is VitalState.DEAD:
            return self.snapshot()
        pressure = metabolism.pressure
        if pressure is ResourcePressure.UNRECOVERABLE:
            next_state = VitalState.DEAD
            self._death_tick = tick
        elif pressure is ResourcePressure.SEVERE:
            next_state = VitalState.DORMANT if resting else VitalState.AGONIZING
        elif pressure is ResourcePressure.ELEVATED:
            next_state = VitalState.STRESSED
        else:
            next_state = VitalState.ACTIVE
        if next_state is not self._state:
            self._transitions += 1
            self._state = next_state
        return self.snapshot()

    def snapshot(self) -> PhysiologySnapshot:
        return PhysiologySnapshot(self._state, self._transitions, self._death_tick)

    def checkpoint(self) -> dict[str, object]:
        return {"state": self._state.value, "transitions": self._transitions, "death_tick": self._death_tick}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "PhysiologyController":
        return cls(state=VitalState(str(payload["state"])), transitions=int(payload["transitions"]), death_tick=payload.get("death_tick"))
