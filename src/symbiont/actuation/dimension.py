"""Organism-owned action dimensions.

Cognitive Atlas v2 spec Sec 9: a dimension the organism knows it can act
along, distinct from the raw actuator surface (`ActuatorChannel`) and from
any embodiment-specific binding. Identity is opaque and derived only from
the backing slot; no physical, joint or effector semantics are accepted
here.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

_DIMENSION_SCHEMA = "symbiont-action-dimension-v1"


def opaque_dimension_id(actuator_slot_id: str) -> str:
    digest = sha256(f"{_DIMENSION_SCHEMA}:{actuator_slot_id}".encode("utf-8")).hexdigest()[:16]
    return f"action.dimension.{digest}"


@dataclass(frozen=True, slots=True)
class ActionDimension:
    dimension_id: str
    actuator_slot_id: str
    availability: bool
    controllability: float
    confidence: float
    usage_count: int
    embodiment_bound: bool

    def __post_init__(self) -> None:
        if not self.dimension_id.startswith("action.dimension."):
            raise ValueError("dimension_id must be opaque and organism-owned")
        if not self.actuator_slot_id:
            raise ValueError("action dimension requires a backing actuator slot")
        if not 0.0 <= self.controllability <= 1.0:
            raise ValueError("controllability must be in [0,1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        if self.usage_count < 0:
            raise ValueError("usage_count must be non-negative")


class ActionDimensionRegistry:
    """Bounded, evidence-derived registry of discovered action dimensions."""

    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = 512) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._items: dict[str, ActionDimension] = {}

    def discover(self, actuator_slot_id: str) -> str:
        """Register (idempotently) a dimension backed by this actuator slot."""
        dimension_id = opaque_dimension_id(actuator_slot_id)
        if dimension_id not in self._items:
            self._items[dimension_id] = ActionDimension(
                dimension_id=dimension_id,
                actuator_slot_id=actuator_slot_id,
                availability=True,
                controllability=0.0,
                confidence=0.0,
                usage_count=0,
                embodiment_bound=False,
            )
            self._enforce_bound()
        return dimension_id

    def record_usage(
        self,
        dimension_id: str,
        *,
        controllability: float,
        confidence: float,
        embodiment_bound: bool,
    ) -> ActionDimension:
        existing = self._items.get(dimension_id)
        if existing is None:
            raise KeyError(f"unknown action dimension: {dimension_id}")
        updated = ActionDimension(
            dimension_id=existing.dimension_id,
            actuator_slot_id=existing.actuator_slot_id,
            availability=existing.availability,
            controllability=max(0.0, min(1.0, float(controllability))),
            confidence=max(0.0, min(1.0, float(confidence))),
            usage_count=existing.usage_count + 1,
            embodiment_bound=bool(embodiment_bound),
        )
        self._items[dimension_id] = updated
        return updated

    def _enforce_bound(self) -> None:
        if len(self._items) <= self.capacity:
            return
        retained = sorted(
            self._items.values(),
            key=lambda item: (-item.usage_count, item.dimension_id),
        )[: self.capacity]
        self._items = {item.dimension_id: item for item in retained}

    def get(self, dimension_id: str) -> ActionDimension | None:
        return self._items.get(dimension_id)

    @property
    def items(self) -> tuple[ActionDimension, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.dimension_id))

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "items": [
                {
                    "dimension_id": item.dimension_id,
                    "actuator_slot_id": item.actuator_slot_id,
                    "availability": item.availability,
                    "controllability": item.controllability,
                    "confidence": item.confidence,
                    "usage_count": item.usage_count,
                    "embodiment_bound": item.embodiment_bound,
                }
                for item in self.items
            ],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "ActionDimensionRegistry":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported action dimension checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 512)))
        raw = payload.get("items", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded action dimensions")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid action dimension entry")
            dimension = ActionDimension(
                dimension_id=str(entry["dimension_id"]),
                actuator_slot_id=str(entry["actuator_slot_id"]),
                availability=bool(entry.get("availability", True)),
                controllability=float(entry.get("controllability", 0.0)),
                confidence=float(entry.get("confidence", 0.0)),
                usage_count=int(entry.get("usage_count", 0)),
                embodiment_bound=bool(entry.get("embodiment_bound", False)),
            )
            obj._items[dimension.dimension_id] = dimension
        return obj


__all__ = [
    "ActionDimension",
    "ActionDimensionRegistry",
    "opaque_dimension_id",
]
