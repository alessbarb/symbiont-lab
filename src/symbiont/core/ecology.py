"""Finite shared habitat resources for bounded populations (v0.70)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HabitatSnapshot:
    habitat_id: str
    population: int
    capacity: int
    available_resources: float


class SharedHabitat:
    SCHEMA_VERSION = 1
    def __init__(self, *, habitat_id: str, capacity: int, resources: float) -> None:
        if not habitat_id or capacity < 1 or resources < 0:
            raise ValueError("invalid habitat bounds")
        self.habitat_id, self.capacity = habitat_id, capacity
        self._resources = float(resources)
        self._allocations: dict[str, float] = {}

    def has_allocation(self, organism_id: str) -> bool:
        return organism_id in self._allocations

    def admit(self, organism_id: str, units: float) -> bool:
        if not organism_id or units <= 0 or organism_id in self._allocations:
            return False
        if len(self._allocations) >= self.capacity or units > self._resources:
            return False
        self._allocations[organism_id] = float(units); self._resources -= float(units); return True

    def release(self, organism_id: str) -> float:
        units = self._allocations.pop(organism_id, 0.0)
        self._resources += units
        return units

    def snapshot(self) -> HabitatSnapshot:
        return HabitatSnapshot(self.habitat_id, len(self._allocations), self.capacity, self._resources)

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": self.SCHEMA_VERSION, "habitat_id": self.habitat_id,
                "capacity": self.capacity, "resources": self._resources, "allocations": dict(self._allocations)}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object]) -> "SharedHabitat":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid habitat checkpoint")
        h = cls(habitat_id=str(payload["habitat_id"]), capacity=int(payload["capacity"]), resources=float(payload["resources"]))
        h._allocations = {str(k): float(v) for k, v in dict(payload.get("allocations", {})).items()}
        if len(h._allocations) > h.capacity or any(v <= 0 for v in h._allocations.values()):
            raise ValueError("invalid habitat allocations")
        return h


__all__ = ["HabitatSnapshot", "SharedHabitat"]
