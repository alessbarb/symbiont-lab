"""Irreversible, resource-backed viability state for Milestone I."""
from __future__ import annotations
from dataclasses import dataclass
import math
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


@dataclass(slots=True)
class LivingBodyState:
    """Single persistent owner of physical physiological state.

    Controllers may transform or project this state, but they must not keep
    independent copies of energy, integrity, temperature, age or vital state.
    Cognition never receives these field names directly.
    """

    energy_reserve: float = 1.0
    max_energy: float = 2.0
    structural_integrity: float = 1.0
    temperature: float = 0.5
    fatigue: float = 0.0
    age_ticks: int = 0
    vital_state: VitalState = VitalState.ACTIVE
    transitions: int = 0
    death_tick: int | None = None

    def __post_init__(self) -> None:
        numeric = {
            "energy_reserve": self.energy_reserve,
            "max_energy": self.max_energy,
            "structural_integrity": self.structural_integrity,
            "temperature": self.temperature,
            "fatigue": self.fatigue,
        }
        for name, value in numeric.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            value = float(value)
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            setattr(self, name, value)
        if self.max_energy <= 0.0:
            raise ValueError("max_energy must be positive")
        if not 0.0 <= self.energy_reserve <= self.max_energy:
            raise ValueError("energy_reserve out of bounds")
        if not 0.0 <= self.structural_integrity <= 1.0:
            raise ValueError("structural_integrity out of bounds")
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature out of bounds")
        if not 0.0 <= self.fatigue <= 1.0:
            raise ValueError("fatigue out of bounds")
        if isinstance(self.age_ticks, bool) or not isinstance(self.age_ticks, int) or self.age_ticks < 0:
            raise ValueError("age_ticks must be non-negative")
        if isinstance(self.transitions, bool) or not isinstance(self.transitions, int) or self.transitions < 0:
            raise ValueError("transitions must be non-negative")
        if self.vital_state is VitalState.DEAD and self.death_tick is None:
            raise ValueError("dead body requires death_tick")

    @property
    def alive(self) -> bool:
        return self.vital_state is not VitalState.DEAD

    @alive.setter
    def alive(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("alive must be boolean")
        if value:
            if self.vital_state is VitalState.DEAD:
                raise ValueError("death is irreversible")
            return
        self.mark_dead(self.age_ticks)

    def mark_dead(self, tick: int) -> None:
        if self.vital_state is VitalState.DEAD:
            return
        self.vital_state = VitalState.DEAD
        self.death_tick = int(tick)
        self.transitions += 1

    def transition(self, state: VitalState, *, tick: int) -> None:
        state = VitalState(state)
        if self.vital_state is VitalState.DEAD:
            return
        if state is not self.vital_state:
            self.vital_state = state
            self.transitions += 1
            if state is VitalState.DEAD:
                self.death_tick = int(tick)

    def consume_energy(self, amount: float) -> float:
        amount = float(amount)
        if not math.isfinite(amount) or amount < 0.0:
            raise ValueError("energy consumption must be finite and non-negative")
        consumed = min(self.energy_reserve, amount)
        self.energy_reserve -= consumed
        if self.energy_reserve <= 0.0:
            self.mark_dead(self.age_ticks)
        return consumed

    def add_energy(self, amount: float) -> float:
        amount = float(amount)
        if not math.isfinite(amount) or amount < 0.0:
            raise ValueError("energy intake must be finite and non-negative")
        if amount == 0.0 or not self.alive:
            return 0.0
        accepted = min(amount, self.max_energy - self.energy_reserve)
        self.energy_reserve += accepted
        return accepted

    def apply_wear(self, amount: float) -> None:
        amount = float(amount)
        if not math.isfinite(amount) or amount < 0.0:
            raise ValueError("wear must be finite and non-negative")
        self.structural_integrity = max(0.0, self.structural_integrity - amount)
        if self.structural_integrity <= 0.0:
            self.mark_dead(self.age_ticks)

    def advance_age(self) -> None:
        if self.alive:
            self.age_ticks += 1

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "energy_reserve": self.energy_reserve,
            "max_energy": self.max_energy,
            "structural_integrity": self.structural_integrity,
            "temperature": self.temperature,
            "fatigue": self.fatigue,
            "age_ticks": self.age_ticks,
            "vital_state": self.vital_state.value,
            "transitions": self.transitions,
            "death_tick": self.death_tick,
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "LivingBodyState":
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("invalid living body checkpoint")
        return cls(
            energy_reserve=float(payload["energy_reserve"]),
            max_energy=float(payload["max_energy"]),
            structural_integrity=float(payload["structural_integrity"]),
            temperature=float(payload["temperature"]),
            fatigue=float(payload["fatigue"]),
            age_ticks=int(payload["age_ticks"]),
            vital_state=VitalState(str(payload["vital_state"])),
            transitions=int(payload["transitions"]),
            death_tick=payload.get("death_tick"),
        )


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
