"""Transactional organism identity, lineage and habitat birth authority (v0.65)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid
import math


@dataclass(frozen=True, slots=True)
class BirthRecord:
    organism_id: str
    parent_ids: tuple[str, ...]
    genome_id: str
    generation: int


@dataclass(frozen=True, slots=True)
class DeathRecord:
    organism_id: str
    released_units: float


class HabitatBirthAuthority:
    """Small, explicit authority; it allocates slots but never starts processes."""

    SCHEMA_VERSION = 1

    def __init__(self, *, habitat_id: str, capacity: int, resource_budget: float) -> None:
        if not isinstance(habitat_id, str) or not habitat_id or isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1 or not isinstance(resource_budget, (int, float)) or isinstance(resource_budget, bool) or not math.isfinite(resource_budget) or resource_budget < 0:
            raise ValueError("invalid habitat authority limits")
        self.habitat_id, self.capacity, self.resource_budget = habitat_id, capacity, float(resource_budget)
        self._live: dict[str, float] = {}
        self._lineage: dict[str, BirthRecord] = {}
        self._deaths: list[DeathRecord] = []
        self._dead_ids: set[str] = set()

    @property
    def live_ids(self) -> tuple[str, ...]:
        return tuple(self._live)

    def register_existing(self, *, organism_id: str, genome_id: str, generation: int = 0,
                          resource_units: float = 1.0) -> BirthRecord | None:
        """Register an explicitly created runtime as a habitat parent.

        Registration is bounded and consumes the same allocation as a birth;
        it never starts a process or bypasses carrying capacity.
        """
        if (not organism_id or not genome_id or organism_id in self._dead_ids or generation < 0 or resource_units <= 0
                or organism_id in self._live or len(self._live) >= self.capacity
                or resource_units > self.resource_budget):
            return None
        record = BirthRecord(organism_id, (), genome_id, generation)
        self._live[organism_id] = float(resource_units)
        self.resource_budget -= float(resource_units)
        self._lineage[organism_id] = record
        return record

    def birth(self, *, genome_id: str, parent_ids: tuple[str, ...] = (), generation: int = 0, resource_units: float = 1.0) -> BirthRecord | None:
        if not genome_id or generation < 0 or resource_units <= 0 or not math.isfinite(resource_units) or len(self._live) >= self.capacity:
            return None
        if resource_units > self.resource_budget:
            return None
        if any(parent not in self._lineage or parent not in self._live for parent in parent_ids):
            return None
        organism_id = f"org_{uuid.uuid4().hex[:16]}"
        record = BirthRecord(organism_id, tuple(parent_ids), genome_id, generation)
        self._live[organism_id] = float(resource_units)
        self.resource_budget -= float(resource_units)
        self._lineage[organism_id] = record
        return record

    def death(self, organism_id: str) -> DeathRecord | None:
        units = self._live.pop(organism_id, None)
        if units is None:
            return None
        self.resource_budget += units
        record = DeathRecord(organism_id, units)
        self._deaths.append(record)
        self._dead_ids.add(organism_id)
        return record

    def checkpoint(self) -> dict[str, Any]:
        return {"schema_version": self.SCHEMA_VERSION, "habitat_id": self.habitat_id,
                "capacity": self.capacity, "resource_budget": self.resource_budget,
                "live": dict(self._live),
                "lineage": [{"organism_id": r.organism_id, "parent_ids": list(r.parent_ids), "genome_id": r.genome_id, "generation": r.generation} for r in self._lineage.values()],
                "deaths": [{"organism_id": d.organism_id, "released_units": d.released_units} for d in self._deaths]}

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "HabitatBirthAuthority":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid lineage checkpoint")
        a = cls(habitat_id=payload["habitat_id"], capacity=payload["capacity"], resource_budget=payload["resource_budget"])
        a._live = {str(k): float(v) for k, v in payload.get("live", {}).items()}
        if len(a._live) > a.capacity:
            raise ValueError("lineage checkpoint exceeds habitat capacity")
        for raw in payload.get("lineage", []):
            record = BirthRecord(str(raw["organism_id"]), tuple(raw.get("parent_ids", ())), str(raw["genome_id"]), int(raw["generation"]))
            a._lineage[record.organism_id] = record
        a._deaths = [DeathRecord(str(d["organism_id"]), float(d["released_units"])) for d in payload.get("deaths", [])]
        a._dead_ids = {d.organism_id for d in a._deaths}
        if not math.isfinite(a.resource_budget) or a.resource_budget < 0 or any(not math.isfinite(v) or v <= 0 for v in a._live.values()):
            raise ValueError("invalid lineage checkpoint values")
        return a


__all__ = ["BirthRecord", "DeathRecord", "HabitatBirthAuthority"]
