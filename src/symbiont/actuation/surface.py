"""Opaque actuator surface supplied by the current embodiment.

The surface is body-owned. It contains no anatomy labels and is never derived
from Genome. Physical adapters may supply cost/health/threshold metadata as
current-body properties.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Sequence

from .types import ActuatorId, _require_unit_range

_SURFACE_SCHEMA = "symbiont-actuator-surface-v2"


def _opaque_actuator_id(index: int) -> ActuatorId:
    digest = sha256(f"{_SURFACE_SCHEMA}:{index}".encode("utf-8")).hexdigest()[:16]
    return f"actuator.{digest}"


@dataclass(frozen=True, slots=True)
class ActuatorChannel:
    slot_id: str
    actuator_id: ActuatorId
    basal_cost: float = 0.0
    initial_health: float = 1.0
    execution_threshold: float = 0.0

    def __post_init__(self) -> None:
        if not self.slot_id or not self.actuator_id:
            raise ValueError("actuator channel ids must be non-empty")
        object.__setattr__(self, "basal_cost", _require_unit_range(self.basal_cost, "basal_cost"))
        object.__setattr__(self, "initial_health", _require_unit_range(self.initial_health, "initial_health"))
        object.__setattr__(
            self,
            "execution_threshold",
            _require_unit_range(self.execution_threshold, "execution_threshold"),
        )


MotorSlot = ActuatorChannel


@dataclass(frozen=True, slots=True)
class ActuatorSurface:
    channels: tuple[ActuatorChannel, ...]
    contract_fingerprint: str

    def __post_init__(self) -> None:
        ids = [channel.actuator_id for channel in self.channels]
        if len(ids) != len(set(ids)):
            raise ValueError("actuator ids must be unique")
        if not self.contract_fingerprint:
            raise ValueError("contract_fingerprint must not be empty")

    @property
    def slots(self) -> tuple[ActuatorChannel, ...]:
        return self.channels

    @property
    def actuator_ids(self) -> tuple[ActuatorId, ...]:
        return tuple(channel.actuator_id for channel in self.channels)

    def slot_for(self, actuator_id: ActuatorId) -> ActuatorChannel:
        for channel in self.channels:
            if channel.actuator_id == actuator_id:
                return channel
        raise KeyError(f"unknown actuator_id {actuator_id!r}")

    @classmethod
    def from_count(
        cls,
        count: int,
        *,
        basal_cost: float = 0.0,
        initial_health: float = 1.0,
        execution_threshold: float = 0.0,
        fingerprint_material: str | None = None,
    ) -> "ActuatorSurface":
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 256:
            raise ValueError("actuator count must be an int in [0,256]")
        channels = tuple(
            ActuatorChannel(
                slot_id=f"motor_slot.{index}",
                actuator_id=_opaque_actuator_id(index),
                basal_cost=basal_cost,
                initial_health=initial_health,
                execution_threshold=execution_threshold,
            )
            for index in range(count)
        )
        material = fingerprint_material or f"count:{count}"
        fingerprint = sha256(f"{_SURFACE_SCHEMA}:{material}".encode("utf-8")).hexdigest()
        return cls(channels=channels, contract_fingerprint=fingerprint)

    @classmethod
    def from_physical_ports(
        cls,
        physical_port_ids: Sequence[str],
        *,
        basal_cost: float = 0.0,
        initial_health: float = 1.0,
        execution_threshold: float = 0.0,
        physical_contract: str | None = None,
    ) -> "ActuatorSurface":
        ports = tuple(str(value) for value in physical_port_ids)
        if len(ports) != len(set(ports)) or len(ports) > 256:
            raise ValueError("physical actuator ports must be unique and bounded")
        # Port labels stay on the body side. Opaque actuator ids depend only on
        # ordinal cardinality; the fingerprint detects body-contract changes.
        material = physical_contract or "|".join(ports)
        return cls.from_count(
            len(ports),
            basal_cost=basal_cost,
            initial_health=initial_health,
            execution_threshold=execution_threshold,
            fingerprint_material=material,
        )


ActuatorConstitution = ActuatorSurface


def derive_actuator_constitution(
    source: int | Sequence[str],
    *,
    basal_cost: float = 0.0,
    initial_health: float = 1.0,
    execution_threshold: float = 0.0,
    physical_contract: str | None = None,
) -> ActuatorConstitution:
    """Build an opaque surface from body-owned cardinality or physical ports."""
    if isinstance(source, int) and not isinstance(source, bool):
        return ActuatorSurface.from_count(
            source,
            basal_cost=basal_cost,
            initial_health=initial_health,
            execution_threshold=execution_threshold,
            fingerprint_material=physical_contract,
        )
    return ActuatorSurface.from_physical_ports(
        tuple(source),
        basal_cost=basal_cost,
        initial_health=initial_health,
        execution_threshold=execution_threshold,
        physical_contract=physical_contract,
    )


__all__ = [
    "ActuatorChannel",
    "ActuatorConstitution",
    "ActuatorSurface",
    "MotorSlot",
    "derive_actuator_constitution",
]
