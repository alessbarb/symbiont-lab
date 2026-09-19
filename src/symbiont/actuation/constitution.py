from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from symbiont.cognition.genome import MotorGenes

from .types import ActuatorId

_ACTUATION_SCHEMA = "symbiont-actuation-v1"


def _slot_id(index: int) -> str:
    return f"motor_slot.{index}"


def _actuator_id_for_slot(slot_id: str) -> ActuatorId:
    digest = sha256(f"{_ACTUATION_SCHEMA}:{slot_id}".encode("utf-8")).hexdigest()[:16]
    return f"actuator.{digest}"


@dataclass(frozen=True, slots=True)
class MotorSlot:
    slot_id: str
    actuator_id: ActuatorId
    basal_cost: float
    initial_health: float
    execution_threshold: float


@dataclass(frozen=True, slots=True)
class ActuatorConstitution:
    slots: tuple[MotorSlot, ...]

    @property
    def actuator_ids(self) -> tuple[ActuatorId, ...]:
        return tuple(slot.actuator_id for slot in self.slots)

    def slot_for(self, actuator_id: ActuatorId) -> MotorSlot:
        for slot in self.slots:
            if slot.actuator_id == actuator_id:
                return slot
        raise KeyError(f"unknown actuator_id {actuator_id!r}")


def derive_actuator_constitution(motor: MotorGenes) -> ActuatorConstitution:
    """Deterministic body-constitution derivation.

    Only ``motor`` is consulted — never the enclosing genome's id or hash —
    so a mutation to any non-motor gene cannot rename an inherited actuator.
    """
    slots = tuple(
        MotorSlot(
            slot_id=(slot_id := _slot_id(index)),
            actuator_id=_actuator_id_for_slot(slot_id),
            basal_cost=motor.basal_cost,
            initial_health=motor.initial_health,
            execution_threshold=motor.execution_threshold,
        )
        for index in range(motor.slot_count)
    )
    return ActuatorConstitution(slots=slots)
