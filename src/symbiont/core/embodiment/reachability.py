"""Learned action-relative reachability for the current embodiment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class ReachabilityRelation:
    state_region_id: str
    competence_id: str
    support: int = 0
    failures: int = 0
    last_evidence_tick: int = 0

    @property
    def confidence(self) -> float:
        total = self.support + self.failures
        return self.support / total if total else 0.0


class ReachabilityModel:
    """Bounded relation between opaque perceptual regions and competences."""

    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = 2048) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._relations: dict[tuple[str, str], ReachabilityRelation] = {}

    def observe(
        self,
        state_region_id: str,
        competence_id: str,
        *,
        tick: int,
        success: bool,
    ) -> ReachabilityRelation:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        key = (str(state_region_id), str(competence_id))
        item = self._relations.get(key)
        if item is None:
            item = ReachabilityRelation(*key)
            self._relations[key] = item
        if success:
            item.support = min(65535, item.support + 1)
        else:
            item.failures = min(65535, item.failures + 1)
        item.last_evidence_tick = tick
        self._enforce_bound()
        return item

    def _enforce_bound(self) -> None:
        if len(self._relations) <= self.capacity:
            return
        retained = sorted(
            self._relations.values(),
            key=lambda item: (
                -(item.support + item.failures),
                -item.last_evidence_tick,
                item.state_region_id,
                item.competence_id,
            ),
        )[: self.capacity]
        self._relations = {(item.state_region_id, item.competence_id): item for item in retained}

    @property
    def relations(self) -> tuple[ReachabilityRelation, ...]:
        return tuple(
            sorted(
                self._relations.values(),
                key=lambda item: (item.state_region_id, item.competence_id),
            )
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "relations": [
                {
                    "state_region_id": item.state_region_id,
                    "competence_id": item.competence_id,
                    "support": item.support,
                    "failures": item.failures,
                    "last_evidence_tick": item.last_evidence_tick,
                }
                for item in self.relations
            ],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "ReachabilityModel":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported reachability checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 2048)))
        raw = payload.get("relations", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded reachability checkpoint")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid reachability relation")
            item = ReachabilityRelation(
                state_region_id=str(entry["state_region_id"]),
                competence_id=str(entry["competence_id"]),
                support=int(entry.get("support", 0)),
                failures=int(entry.get("failures", 0)),
                last_evidence_tick=int(entry.get("last_evidence_tick", 0)),
            )
            obj._relations[(item.state_region_id, item.competence_id)] = item
        return obj


__all__ = ["ReachabilityModel", "ReachabilityRelation"]
