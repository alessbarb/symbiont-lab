"""Opaque executable actuator contract supplied by the embodiment.

The surface states only which opaque commands are legal.  Response quality,
latency, cost, degradation and functional role are not supplied as organism
knowledge; they must be learned from experienced consequences.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

from .types import ActuatorId

_SURFACE_SCHEMA = "symbiont-actuator-surface-v3"


def _opaque_actuator_id(index: int) -> ActuatorId:
    digest = sha256(f"{_SURFACE_SCHEMA}:{index}".encode("utf-8")).hexdigest()[:16]
    return f"actuator.{digest}"


@dataclass(frozen=True, slots=True)
class ActuatorChannel:
    slot_id: str
    actuator_id: ActuatorId
    command_min: float = 0.0
    command_max: float = 1.0
    neutral: float = 0.0
    available: bool = True

    def __post_init__(self) -> None:
        if not self.slot_id or not self.actuator_id:
            raise ValueError("actuator channel ids must be non-empty")
        minimum = float(self.command_min)
        maximum = float(self.command_max)
        neutral = float(self.neutral)
        if not 0.0 <= minimum <= neutral <= maximum <= 1.0:
            raise ValueError("actuator command contract must satisfy 0 <= min <= neutral <= max <= 1")
        if not isinstance(self.available, bool):
            raise ValueError("available must be boolean")


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

    def validate(self, actuator_id: ActuatorId, activation: float) -> float:
        channel = self.slot_for(actuator_id)
        if not channel.available:
            raise RuntimeError(f"actuator channel {actuator_id!r} is unavailable")
        value = float(activation)
        if not channel.command_min <= value <= channel.command_max:
            raise ValueError("motor command outside actuator contract")
        return value

    @classmethod
    def from_count(
        cls,
        count: int,
        *,
        fingerprint_material: str | None = None,
    ) -> "ActuatorSurface":
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 256:
            raise ValueError("actuator count must be an int in [0,256]")
        channels = tuple(
            ActuatorChannel(
                slot_id=f"motor_slot.{index}",
                actuator_id=_opaque_actuator_id(index),
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
        physical_contract: str | None = None,
    ) -> "ActuatorSurface":
        ports = tuple(str(value) for value in physical_port_ids)
        if len(ports) != len(set(ports)) or len(ports) > 256:
            raise ValueError("physical actuator ports must be unique and bounded")
        material = physical_contract or "|".join(ports)
        return cls.from_count(len(ports), fingerprint_material=material)


ActuatorConstitution = ActuatorSurface


def derive_actuator_constitution(
    source: int | Sequence[str],
    *,
    physical_contract: str | None = None,
) -> ActuatorConstitution:
    """Build only the legal opaque command surface for the current body."""
    if isinstance(source, int) and not isinstance(source, bool):
        return ActuatorSurface.from_count(
            source,
            fingerprint_material=physical_contract,
        )
    return ActuatorSurface.from_physical_ports(
        tuple(source),
        physical_contract=physical_contract,
    )


__all__ = [
    "ActuatorChannel",
    "ActuatorConstitution",
    "ActuatorSurface",
    "MotorSlot",
    "derive_actuator_constitution",
]
