"""Irreversible, resource-backed viability state for Milestone I."""
from __future__ import annotations
from dataclasses import dataclass, field
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
class BodyStructureState:
    """Bounded, per-structure physical damage record (L5.5.1).

    ``structure_id`` is opaque body-substrate identity (an actuator slot_id
    today); it names no anatomy or function. ``functional_capacity`` and
    ``repair_progress`` are stored/checkpointed scaffolding — see
    research/audits/current/2026-09-body-structure-state-v1-debt.md for what
    does not yet read or write them.
    """

    structure_id: str
    integrity: float = 1.0
    wear: float = 0.0
    damage: float = 0.0
    repair_progress: float = 0.0
    functional_capacity: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.structure_id, str) or not self.structure_id:
            raise ValueError("structure_id must be a non-empty string")
        numeric = {
            "integrity": self.integrity,
            "wear": self.wear,
            "damage": self.damage,
            "repair_progress": self.repair_progress,
            "functional_capacity": self.functional_capacity,
        }
        for name, value in numeric.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be numeric")
            value = float(value)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} out of bounds")
            setattr(self, name, value)

    def checkpoint(self) -> dict[str, object]:
        return {
            "structure_id": self.structure_id,
            "integrity": self.integrity,
            "wear": self.wear,
            "damage": self.damage,
            "repair_progress": self.repair_progress,
            "functional_capacity": self.functional_capacity,
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "BodyStructureState":
        return cls(
            structure_id=str(payload["structure_id"]),
            integrity=float(payload["integrity"]),
            wear=float(payload["wear"]),
            damage=float(payload["damage"]),
            repair_progress=float(payload["repair_progress"]),
            functional_capacity=float(payload["functional_capacity"]),
        )


@dataclass(slots=True)
class LivingBodyState:
    """Single persistent owner of one Body physiological state.

    ``age_ticks`` and ``death_tick`` are Body-local biological time. They are
    deliberately independent from the persistent Symbiont historical tick.
    Cognition never receives these field names directly.
    """
    energy_reserve: float = 1.0
    max_energy: float = 2.0
    structural_integrity: float = 1.0
    temperature: float = 0.5
    fatigue: float = 0.0
    growth_progress: float = 0.0
    senescence: float = 0.0
    age_ticks: int = 0
    vital_state: VitalState = VitalState.ACTIVE
    transitions: int = 0
    death_tick: int | None = None
    metabolic_capacity: dict[str, float] = field(default_factory=dict)
    metabolic_replenishment: dict[str, float] = field(default_factory=dict)
    metabolic_reserve: dict[str, float] = field(default_factory=dict)
    structure_states: dict[str, "BodyStructureState"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        numeric = {
            "energy_reserve": self.energy_reserve,
            "max_energy": self.max_energy,
            "structural_integrity": self.structural_integrity,
            "temperature": self.temperature,
            "fatigue": self.fatigue,
            "growth_progress": self.growth_progress,
            "senescence": self.senescence,
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
        if not 0.0 <= self.growth_progress <= 1.0:
            raise ValueError("growth_progress out of bounds")
        if not 0.0 <= self.senescence <= 1.0:
            raise ValueError("senescence out of bounds")
        if isinstance(self.age_ticks, bool) or not isinstance(self.age_ticks, int) or self.age_ticks < 0:
            raise ValueError("age_ticks must be non-negative")
        if isinstance(self.transitions, bool) or not isinstance(self.transitions, int) or self.transitions < 0:
            raise ValueError("transitions must be non-negative")
        if self.vital_state is VitalState.DEAD and self.death_tick is None:
            raise ValueError("dead body requires death_tick")
        if self.death_tick is not None:
            if (
                isinstance(self.death_tick, bool)
                or not isinstance(self.death_tick, int)
                or self.death_tick < 0
            ):
                raise ValueError("death_tick must be a non-negative Body-local age tick")
        for field_name in (
            "metabolic_capacity",
            "metabolic_replenishment",
            "metabolic_reserve",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, dict):
                raise ValueError(f"{field_name} must be a dict")
            normalized: dict[str, float] = {}
            for key, value in values.items():
                if (
                    not isinstance(key, str)
                    or not key
                    or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    raise ValueError(f"invalid {field_name} entry")
                normalized[key] = float(value)
            setattr(self, field_name, normalized)
        if not isinstance(self.structure_states, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, BodyStructureState)
            or key != value.structure_id
            for key, value in self.structure_states.items()
        ):
            raise ValueError("structure_states must map structure_id to its own state")
        if self.structure_states:
            self.structural_integrity = self._aggregate_structural_integrity()

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
        """Transition physical viability using a Body-local age tick."""
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("physiology transition tick must be Body-local")
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

    def _aggregate_structural_integrity(self) -> float:
        values = [structure.integrity for structure in self.structure_states.values()]
        return sum(values) / len(values)

    def apply_structural_delta(self, delta: float) -> None:
        """Uniform, untargeted integrity change (L5.5.1 v1: no structure
        targeting yet — see
        research/audits/current/2026-09-body-structure-state-v1-debt.md #1).

        The single write path behind every integrity change: ``apply_wear``,
        the homeostatic repair cycle and any direct ``integrity =`` set all
        route through here, so ``structure_states`` (when present) and the
        aggregate scalar never drift out of sync. Applied identically to
        every tracked structure — not divided among them — so the aggregate
        moves by exactly ``delta`` when structures start uniform, matching
        the pre-structure scalar behavior.
        """
        delta = float(delta)
        if not math.isfinite(delta):
            raise ValueError("structural delta must be finite")
        if self.structure_states:
            for structure in self.structure_states.values():
                structure.integrity = max(0.0, min(1.0, structure.integrity + delta))
                if delta < 0.0:
                    structure.wear = min(1.0, structure.wear - delta)
                    structure.damage = min(1.0, structure.damage - delta)
                else:
                    structure.repair_progress = min(1.0, structure.repair_progress + delta)
            self.structural_integrity = self._aggregate_structural_integrity()
        else:
            self.structural_integrity = max(
                0.0, min(1.0, self.structural_integrity + delta)
            )
        if self.structural_integrity <= 0.0:
            self.mark_dead(self.age_ticks)

    def apply_wear(self, amount: float) -> None:
        amount = float(amount)
        if not math.isfinite(amount) or amount < 0.0:
            raise ValueError("wear must be finite and non-negative")
        self.apply_structural_delta(-amount)

    def advance_age(self) -> None:
        """Advance this Body biological age by one executed live tick."""
        if self.alive:
            self.age_ticks += 1

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 3,
            "energy_reserve": self.energy_reserve,
            "max_energy": self.max_energy,
            "structural_integrity": self.structural_integrity,
            "temperature": self.temperature,
            "fatigue": self.fatigue,
            "growth_progress": self.growth_progress,
            "senescence": self.senescence,
            "age_ticks": self.age_ticks,
            "vital_state": self.vital_state.value,
            "transitions": self.transitions,
            "death_tick": self.death_tick,
            "metabolic_capacity": dict(self.metabolic_capacity),
            "metabolic_replenishment": dict(self.metabolic_replenishment),
            "metabolic_reserve": dict(self.metabolic_reserve),
            "structure_states": {
                structure_id: structure.checkpoint()
                for structure_id, structure in sorted(self.structure_states.items())
            },
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "LivingBodyState":
        if not isinstance(payload, dict) or payload.get("schema_version") not in (2, 3):
            raise ValueError("invalid living body checkpoint")
        raw_structures = payload.get("structure_states", {})
        if not isinstance(raw_structures, dict):
            raise ValueError("invalid living body checkpoint: structure_states")
        structure_states = {
            structure_id: BodyStructureState.from_checkpoint(raw_state)
            for structure_id, raw_state in raw_structures.items()
        }
        if any(
            structure_id != state.structure_id
            for structure_id, state in structure_states.items()
        ):
            raise ValueError(
                "invalid living body checkpoint: structure_states key/id mismatch"
            )
        return cls(
            energy_reserve=float(payload["energy_reserve"]),
            max_energy=float(payload["max_energy"]),
            structural_integrity=float(payload["structural_integrity"]),
            temperature=float(payload["temperature"]),
            fatigue=float(payload["fatigue"]),
            growth_progress=float(payload["growth_progress"]),
            senescence=float(payload["senescence"]),
            age_ticks=int(payload["age_ticks"]),
            vital_state=VitalState(str(payload["vital_state"])),
            transitions=int(payload["transitions"]),
            death_tick=payload.get("death_tick"),
            metabolic_capacity=dict(payload.get("metabolic_capacity", {})),
            metabolic_replenishment=dict(payload.get("metabolic_replenishment", {})),
            metabolic_reserve=dict(payload.get("metabolic_reserve", {})),
            structure_states=structure_states,
        )


@dataclass(frozen=True, slots=True)
class PhysiologySnapshot:

    state: VitalState
    transitions: int
    death_tick: int | None

class PhysiologyController:
    """Maps metabolic pressure to viability on one shared LivingBodyState."""

    def __init__(
        self,
        *,
        state: VitalState = VitalState.ACTIVE,
        transitions: int = 0,
        death_tick: int | None = None,
        body_state: LivingBodyState | None = None,
    ) -> None:
        if body_state is None:
            body_state = LivingBodyState(
                vital_state=state,
                transitions=transitions,
                death_tick=death_tick,
            )
        else:
            if state is not VitalState.ACTIVE and state is not body_state.vital_state:
                raise ValueError("physiology state contradicts living body state")
            if transitions not in (0, body_state.transitions):
                raise ValueError("physiology transitions contradict living body state")
            if death_tick is not None and death_tick != body_state.death_tick:
                raise ValueError("physiology death_tick contradicts living body state")
        self._body_state = body_state

    @property
    def body_state(self) -> LivingBodyState:
        return self._body_state

    @property
    def state(self) -> VitalState:
        return self._body_state.vital_state

    def advance(
        self,
        metabolism: MetabolicSnapshot,
        *,
        tick: int,
        resting: bool = False,
    ) -> PhysiologySnapshot:
        if self.state is VitalState.DEAD:
            return self.snapshot()
        pressure = metabolism.pressure
        if self._body_state.energy_reserve <= 0.0:
            next_state = VitalState.DEAD
        elif pressure is ResourcePressure.UNRECOVERABLE:
            next_state = VitalState.DEAD
        elif pressure is ResourcePressure.SEVERE:
            next_state = VitalState.DORMANT if resting else VitalState.AGONIZING
        elif pressure is ResourcePressure.ELEVATED:
            next_state = VitalState.STRESSED
        else:
            next_state = VitalState.ACTIVE
        self._body_state.transition(next_state, tick=tick)
        return self.snapshot()

    def snapshot(self) -> PhysiologySnapshot:
        return PhysiologySnapshot(
            self._body_state.vital_state,
            self._body_state.transitions,
            self._body_state.death_tick,
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "state": self._body_state.vital_state.value,
            "transitions": self._body_state.transitions,
            "death_tick": self._body_state.death_tick,
        }

    @classmethod
    def from_checkpoint(
        cls,
        payload: dict[str, object],
        *,
        body_state: LivingBodyState | None = None,
    ) -> "PhysiologyController":
        state = VitalState(str(payload["state"]))
        transitions = int(payload["transitions"])
        death_tick = payload.get("death_tick")
        if body_state is None:
            return cls(
                state=state,
                transitions=transitions,
                death_tick=death_tick,
            )
        if (
            body_state.vital_state is not state
            or body_state.transitions != transitions
            or body_state.death_tick != death_tick
        ):
            raise ValueError("physiology checkpoint contradicts living body state")
        return cls(body_state=body_state)

__all__ = [
    "BodyStructureState",
    "LivingBodyState",
    "PhysiologyController",
    "PhysiologySnapshot",
    "VitalState",
]
