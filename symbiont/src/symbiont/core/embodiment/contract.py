"""Canonical opaque sensorimotor contract for Embodiment v2.

The contract describes only the surfaces made available to the organism.  It
never exports anatomy, simulator link names, body-kind labels, actuator roles
or learned response quality.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

from ...actuation.surface import ActuatorSurface

_CONTRACT_SCHEMA = "symbiont-embodiment-contract-v3"
_PERCEPTUAL_SURFACE_SCHEMA = "symbiont-perceptual-surface-v1"


def _opaque_percept_id(index: int) -> str:
    digest = sha256(f"{_PERCEPTUAL_SURFACE_SCHEMA}:{index}".encode("utf-8")).hexdigest()[:16]
    return f"percept.{digest}"


@dataclass(frozen=True, slots=True)
class PerceptualChannel:
    """One opaque perceptual channel exposed by an embodiment."""

    slot_id: str
    percept_id: str
    available: bool = True

    def __post_init__(self) -> None:
        if not self.slot_id or not self.percept_id:
            raise ValueError("perceptual channel ids must be non-empty")
        if not isinstance(self.available, bool):
            raise ValueError("available must be boolean")


@dataclass(frozen=True, slots=True)
class PerceptualSurface:
    """Opaque perceptual surface; physical sensor semantics stay outside cognition."""

    channels: tuple[PerceptualChannel, ...]
    surface_fingerprint: str

    def __post_init__(self) -> None:
        ids = [item.percept_id for item in self.channels]
        if len(ids) != len(set(ids)):
            raise ValueError("percept ids must be unique")
        if not self.surface_fingerprint:
            raise ValueError("surface_fingerprint must not be empty")

    @property
    def percept_ids(self) -> tuple[str, ...]:
        return tuple(item.percept_id for item in self.channels)

    @classmethod
    def from_count(
        cls,
        count: int,
        *,
        fingerprint_material: str | None = None,
    ) -> "PerceptualSurface":
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 1024:
            raise ValueError("perceptual count must be an int in [0,1024]")
        channels = tuple(
            PerceptualChannel(
                slot_id=f"percept_slot.{index}",
                percept_id=_opaque_percept_id(index),
            )
            for index in range(count)
        )
        material = fingerprint_material or f"count:{count}"
        digest = sha256(f"{_PERCEPTUAL_SURFACE_SCHEMA}:{material}".encode("utf-8")).hexdigest()
        return cls(channels=channels, surface_fingerprint=digest)

    @classmethod
    def from_physical_ports(
        cls,
        physical_port_ids: Sequence[str],
        *,
        physical_contract: str | None = None,
    ) -> "PerceptualSurface":
        ports = tuple(str(value) for value in physical_port_ids)
        if len(ports) != len(set(ports)) or len(ports) > 1024:
            raise ValueError("physical receptor ports must be unique and bounded")
        material = physical_contract or "|".join(ports)
        return cls.from_count(len(ports), fingerprint_material=material)


@dataclass(frozen=True, slots=True)
class TimingContract:
    """Only timing facts required to interpret the exposed interface."""

    tick_hz: float | None = None
    command_hold_ticks: int = 1

    def __post_init__(self) -> None:
        if self.tick_hz is not None and self.tick_hz <= 0.0:
            raise ValueError("tick_hz must be positive")
        if self.command_hold_ticks < 1:
            raise ValueError("command_hold_ticks must be positive")


@dataclass(frozen=True, slots=True)
class EmbodimentContract:
    """Portable body-agnostic contract between Symbiont and one Body."""

    perceptual_surface: PerceptualSurface
    actuator_surface: ActuatorSurface
    timing: TimingContract = TimingContract()
    exclusive_actuator_groups: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        known = set(self.actuator_surface.actuator_ids)
        seen: set[str] = set()
        normalized: list[tuple[str, ...]] = []
        for raw_group in self.exclusive_actuator_groups:
            group = tuple(sorted(str(value) for value in raw_group))
            if len(group) < 2 or len(set(group)) != len(group):
                raise ValueError("exclusive actuator groups must contain unique ids")
            if not set(group).issubset(known):
                raise ValueError("exclusive actuator group references unknown actuator")
            if seen.intersection(group):
                raise ValueError("exclusive actuator groups must be disjoint")
            seen.update(group)
            normalized.append(group)
        normalized.sort()
        object.__setattr__(
            self,
            "exclusive_actuator_groups",
            tuple(normalized),
        )

    @property
    def contract_fingerprint(self) -> str:
        material = {
            "schema": _CONTRACT_SCHEMA,
            "perceptual_surface": self.perceptual_surface.surface_fingerprint,
            "actuator_surface": self.actuator_surface.contract_fingerprint,
            "tick_hz": self.timing.tick_hz,
            "command_hold_ticks": self.timing.command_hold_ticks,
            "exclusive_actuator_groups": [list(group) for group in self.exclusive_actuator_groups],
        }
        raw = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 3,
            "contract_fingerprint": self.contract_fingerprint,
            "perceptual_surface": {
                "surface_fingerprint": self.perceptual_surface.surface_fingerprint,
                "channels": [
                    {
                        "slot_id": item.slot_id,
                        "percept_id": item.percept_id,
                        "available": item.available,
                    }
                    for item in self.perceptual_surface.channels
                ],
            },
            "actuator_surface": {
                "contract_fingerprint": self.actuator_surface.contract_fingerprint,
                "channels": [
                    {
                        "slot_id": item.slot_id,
                        "actuator_id": item.actuator_id,
                        "command_min": item.command_min,
                        "command_max": item.command_max,
                        "neutral": item.neutral,
                        "available": item.available,
                    }
                    for item in self.actuator_surface.channels
                ],
            },
            "timing": {
                "tick_hz": self.timing.tick_hz,
                "command_hold_ticks": self.timing.command_hold_ticks,
            },
            "exclusive_actuator_groups": [list(group) for group in self.exclusive_actuator_groups],
        }


__all__ = [
    "EmbodimentContract",
    "PerceptualChannel",
    "PerceptualSurface",
    "TimingContract",
]
