"""Body catalog for Physics3D embodiments.

The registry is apparatus-owned.  It exposes only body contracts and factories;
it never supplies semantic labels to the organism.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .humanoid import (
    BODY_KIND,
    BODY_STATE_SCHEMA_VERSION,
    GROUND_MATERIAL,
    MOTOR_DOF,
    TOTAL_RECEPTOR_COUNT,
    HumanoidPhysics,
)


@dataclass(frozen=True, slots=True)
class BodyDescriptor:
    body_kind: str
    display_name: str
    version: int
    motor_dof: int
    receptor_count: int
    effector_count: int
    apparatus_factory: Callable[[Any, int], Any]
    ground_material: Any

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.body_kind,
            "body_kind": self.body_kind,
            "display_name": self.display_name,
            "version": self.version,
            "motor_dof": self.motor_dof,
            "receptor_count": self.receptor_count,
            "effector_count": self.effector_count,
            "available": True,
        }


class BodyRegistry:
    def __init__(self, descriptors: tuple[BodyDescriptor, ...]) -> None:
        self._descriptors = {descriptor.body_kind: descriptor for descriptor in descriptors}
        if not self._descriptors:
            raise ValueError("body registry requires at least one descriptor")

    def get(self, body_kind: str) -> BodyDescriptor:
        try:
            return self._descriptors[str(body_kind)]
        except KeyError as exc:
            raise ValueError(f"unsupported body kind: {body_kind}") from exc

    def list(self) -> tuple[BodyDescriptor, ...]:
        return tuple(self._descriptors[key] for key in sorted(self._descriptors))


ANTHROPOMORPHIC_V4 = BodyDescriptor(
    body_kind=BODY_KIND,
    display_name="Anthropomorphic",
    version=BODY_STATE_SCHEMA_VERSION,
    motor_dof=MOTOR_DOF,
    receptor_count=TOTAL_RECEPTOR_COUNT,
    effector_count=MOTOR_DOF * 2,
    apparatus_factory=HumanoidPhysics,
    ground_material=GROUND_MATERIAL,
)

DEFAULT_BODY_REGISTRY = BodyRegistry((ANTHROPOMORPHIC_V4,))


__all__ = [
    "ANTHROPOMORPHIC_V4",
    "BodyDescriptor",
    "BodyRegistry",
    "DEFAULT_BODY_REGISTRY",
]
