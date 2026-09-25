"""Non-semantic physical resource for Physics3D locomotion experiments."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

from .humanoid import SurfaceMaterial, apply_surface_material

RESOURCE_MATERIAL = SurfaceMaterial(
    lateral_friction=0.72,
    spinning_friction=0.02,
    rolling_friction=0.003,
    restitution=0.01,
    linear_damping=0.0,
    angular_damping=0.0,
)


@dataclass(slots=True)
class PhysicalResource:
    """Finite static material source with a local scalar field.

    The object owns world truth. The organism may receive only field magnitude
    through an opaque receptor and scalar absorbed material after physical
    contact.
    """

    p: object
    client_id: int
    position: tuple[float, float, float] = (3.0, 0.0, 0.18)
    radius: float = 0.18
    field_radius: float = 6.0
    remaining: float = 200.0
    transfer_per_tick: float = 2.0
    body_id: int = field(init=False)

    def __post_init__(self) -> None:
        if self.radius <= 0.0 or self.field_radius <= self.radius:
            raise ValueError("invalid physical resource geometry")
        if self.remaining < 0.0 or self.transfer_per_tick <= 0.0:
            raise ValueError("invalid physical resource capacity")
        collision = self.p.createCollisionShape(
            self.p.GEOM_SPHERE,
            radius=self.radius,
            physicsClientId=self.client_id,
        )
        visual = self.p.createVisualShape(
            self.p.GEOM_SPHERE,
            radius=self.radius,
            rgbaColor=(0.52, 0.78, 0.36, 1.0),
            physicsClientId=self.client_id,
        )
        self.body_id = self.p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=collision,
            baseVisualShapeIndex=visual,
            basePosition=self.position,
            physicsClientId=self.client_id,
        )
        apply_surface_material(
            self.p,
            self.body_id,
            -1,
            RESOURCE_MATERIAL,
            client_id=self.client_id,
        )

    def distance_to(self, point: tuple[float, float, float]) -> float:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(point, self.position)))

    def field_at(self, point: tuple[float, float, float]) -> float:
        """Local isotropic field; scalar only, with no direction or identity."""
        if self.remaining <= 0.0:
            return 0.0
        distance = self.distance_to(point)
        if distance >= self.field_radius:
            return 0.0
        normalized = max(0.0, 1.0 - distance / self.field_radius)
        return normalized * normalized

    def touching(self, body_id: int) -> bool:
        if self.remaining <= 0.0:
            return False
        contacts = self.p.getContactPoints(
            bodyA=body_id,
            bodyB=self.body_id,
            physicsClientId=self.client_id,
        )
        return bool(contacts)

    def offered_material(self) -> float:
        """Return the bounded amount physically available this cognitive tick."""
        if self.remaining <= 0.0:
            return 0.0
        return min(self.transfer_per_tick, self.remaining)

    def consume_absorbed(self, amount: float) -> float:
        """Remove only material actually accepted across the organism boundary."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(float(amount))
            or amount < 0.0
        ):
            raise ValueError("absorbed resource amount must be finite and non-negative")
        consumed = min(float(amount), self.remaining, self.transfer_per_tick)
        self.remaining -= consumed
        return consumed

    def take_contact_material(self, body_id: int) -> float:
        if not self.touching(body_id):
            return 0.0
        amount = self.offered_material()
        self.consume_absorbed(amount)
        return amount

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "position": [float(value) for value in self.position],
            "radius": float(self.radius),
            "field_radius": float(self.field_radius),
            "remaining": float(self.remaining),
            "transfer_per_tick": float(self.transfer_per_tick),
        }

    @classmethod
    def from_state(
        cls, p, client_id: int, payload: Mapping[str, object] | None
    ) -> "PhysicalResource":
        if payload is None:
            return cls(p, client_id)
        if int(payload.get("schema_version", -1)) != 1:
            raise ValueError("unsupported Physics3D resource state")
        position = tuple(float(value) for value in payload["position"])
        if len(position) != 3:
            raise ValueError("resource position must have three coordinates")
        return cls(
            p,
            client_id,
            position=position,
            radius=float(payload["radius"]),
            field_radius=float(payload["field_radius"]),
            remaining=float(payload["remaining"]),
            transfer_per_tick=float(payload["transfer_per_tick"]),
        )


__all__ = ["PhysicalResource", "RESOURCE_MATERIAL"]
