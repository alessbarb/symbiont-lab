"""Transactional organism identity, lineage and habitat carrying capacity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid


@dataclass(frozen=True, slots=True)
class BirthRecord:
    organism_id: str
    parent_ids: tuple[str, ...]
    genome_id: str
    generation: int


@dataclass(frozen=True, slots=True)
class DeathRecord:
    organism_id: str


class HabitatBirthAuthority:
    """Allocate identity and finite population slots; never physical resources."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        habitat_id: str,
        capacity: int,
        organism_id_prefix: str | None = None,
    ) -> None:
        if (
            not isinstance(habitat_id, str)
            or not habitat_id
            or isinstance(capacity, bool)
            or not isinstance(capacity, int)
            or capacity < 1
        ):
            raise ValueError("invalid habitat authority limits")
        self.habitat_id = habitat_id
        self.capacity = capacity
        if organism_id_prefix is not None and (
            not isinstance(organism_id_prefix, str)
            or not organism_id_prefix
            or len(organism_id_prefix) > 32
        ):
            raise ValueError("invalid organism ID prefix")
        self.organism_id_prefix = organism_id_prefix
        self._birth_counter = 0
        self._live: set[str] = set()
        self._lineage: dict[str, BirthRecord] = {}
        self._deaths: list[DeathRecord] = []
        self._dead_ids: set[str] = set()

    @property
    def live_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._live))

    @property
    def lineage_records(self) -> tuple[BirthRecord, ...]:
        return tuple(self._lineage.values())

    @property
    def death_records(self) -> tuple[DeathRecord, ...]:
        return tuple(self._deaths)

    def register_existing(
        self,
        *,
        organism_id: str,
        genome_id: str,
        generation: int = 0,
    ) -> BirthRecord | None:
        """Register one pre-existing organism if a population slot is free."""
        if (
            not organism_id
            or not genome_id
            or organism_id in self._dead_ids
            or generation < 0
            or organism_id in self._live
            or len(self._live) >= self.capacity
        ):
            return None
        record = BirthRecord(organism_id, (), genome_id, generation)
        self._live.add(organism_id)
        self._lineage[organism_id] = record
        return record

    def birth(
        self,
        *,
        genome_id: str,
        parent_ids: tuple[str, ...] = (),
        generation: int = 0,
    ) -> BirthRecord | None:
        """Allocate one descendant identity and slot.

        Material/energy conservation is owned by the reproducing body.  This
        authority may deny capacity, but cannot mint, reserve, or release
        physical resource.
        """
        if not genome_id or generation < 0 or len(self._live) >= self.capacity:
            return None
        if any(parent not in self._lineage or parent not in self._live for parent in parent_ids):
            return None
        if self.organism_id_prefix is None:
            organism_id = f"org_{uuid.uuid4().hex[:16]}"
        else:
            organism_id = f"{self.organism_id_prefix}-{self._birth_counter:06d}"
            self._birth_counter += 1
        if organism_id in self._live or organism_id in self._dead_ids:
            raise ValueError("organism ID allocator collision")
        record = BirthRecord(organism_id, tuple(parent_ids), genome_id, generation)
        self._live.add(organism_id)
        self._lineage[organism_id] = record
        return record

    def death(self, organism_id: str) -> DeathRecord | None:
        if organism_id not in self._live:
            return None
        self._live.remove(organism_id)
        record = DeathRecord(organism_id)
        self._deaths.append(record)
        self._dead_ids.add(organism_id)
        return record

    def checkpoint(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "habitat_id": self.habitat_id,
            "capacity": self.capacity,
            "organism_id_prefix": self.organism_id_prefix,
            "birth_counter": self._birth_counter,
            "live": sorted(self._live),
            "lineage": [
                {
                    "organism_id": r.organism_id,
                    "parent_ids": list(r.parent_ids),
                    "genome_id": r.genome_id,
                    "generation": r.generation,
                }
                for r in self._lineage.values()
            ],
            "deaths": [{"organism_id": d.organism_id} for d in self._deaths],
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "HabitatBirthAuthority":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid lineage checkpoint")
        authority = cls(
            habitat_id=payload["habitat_id"],
            capacity=payload["capacity"],
            organism_id_prefix=payload.get("organism_id_prefix"),
        )
        counter = payload.get("birth_counter", 0)
        if isinstance(counter, bool) or not isinstance(counter, int) or counter < 0:
            raise ValueError("invalid birth counter")
        authority._birth_counter = counter

        raw_live = payload.get("live", [])
        if not isinstance(raw_live, list) or any(not isinstance(item, str) or not item for item in raw_live):
            raise ValueError("invalid lineage live set")
        authority._live = set(raw_live)
        if len(authority._live) > authority.capacity:
            raise ValueError("lineage checkpoint exceeds habitat capacity")

        for raw in payload.get("lineage", []):
            record = BirthRecord(
                str(raw["organism_id"]),
                tuple(raw.get("parent_ids", ())),
                str(raw["genome_id"]),
                int(raw["generation"]),
            )
            authority._lineage[record.organism_id] = record

        authority._deaths = [
            DeathRecord(str(item["organism_id"]))
            for item in payload.get("deaths", [])
        ]
        authority._dead_ids = {item.organism_id for item in authority._deaths}
        if not authority._live.issubset(authority._lineage):
            raise ValueError("live organism missing lineage record")
        if authority._live & authority._dead_ids:
            raise ValueError("organism cannot be both live and dead")
        return authority

    def restore_checkpoint(self, payload: dict[str, Any]) -> None:
        restored = type(self).from_checkpoint(payload)
        if restored.habitat_id != self.habitat_id or restored.capacity != self.capacity:
            raise ValueError("lineage checkpoint identity or capacity mismatch")
        self.organism_id_prefix = restored.organism_id_prefix
        self._birth_counter = restored._birth_counter
        self._live = restored._live
        self._lineage = restored._lineage
        self._deaths = restored._deaths
        self._dead_ids = restored._dead_ids


__all__ = ["BirthRecord", "DeathRecord", "HabitatBirthAuthority"]
