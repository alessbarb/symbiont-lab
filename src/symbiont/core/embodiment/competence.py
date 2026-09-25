"""Embodiment-local realization of transferable motor competences."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class EmbodiedCompetence:
    competence_id: str
    embodiment_id: str
    surface_binding: str | None = None
    controller_realization_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    reliability: float = 0.0
    controllability: float = 0.0
    prediction_error: float = 1.0

    @property
    def executable(self) -> bool:
        return (
            self.surface_binding is not None
            and self.controller_realization_ref is not None
            and bool(self.evidence_refs)
            and self.reliability >= 0.60
            and self.controllability >= 0.35
        )

    def revalidate(
        self,
        *,
        surface_fingerprint: str,
        controller_realization_ref: str,
        evidence_refs: tuple[str, ...],
        reliability: float,
        controllability: float,
        prediction_error: float,
    ) -> None:
        if not evidence_refs:
            raise ValueError("embodied competence revalidation requires current evidence")
        self.surface_binding = str(surface_fingerprint)
        self.controller_realization_ref = str(controller_realization_ref)
        self.evidence_refs = tuple(dict.fromkeys(self.evidence_refs + evidence_refs))
        self.reliability = max(0.0, min(1.0, float(reliability)))
        self.controllability = max(0.0, min(1.0, float(controllability)))
        self.prediction_error = max(0.0, float(prediction_error))

    def checkpoint(self) -> dict[str, object]:
        return {
            "competence_id": self.competence_id,
            "embodiment_id": self.embodiment_id,
            "surface_binding": self.surface_binding,
            "controller_realization_ref": self.controller_realization_ref,
            "evidence_refs": list(self.evidence_refs),
            "reliability": self.reliability,
            "controllability": self.controllability,
            "prediction_error": self.prediction_error,
        }


class EmbodiedCompetenceLibrary:
    SCHEMA_VERSION = 1

    def __init__(self, *, embodiment_id: str, capacity: int = 512) -> None:
        if not embodiment_id:
            raise ValueError("embodiment_id must not be empty")
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.embodiment_id = embodiment_id
        self.capacity = int(capacity)
        self._items: dict[str, EmbodiedCompetence] = {}

    def candidate(self, competence_id: str) -> EmbodiedCompetence:
        item = self._items.get(competence_id)
        if item is None:
            item = EmbodiedCompetence(
                competence_id=competence_id,
                embodiment_id=self.embodiment_id,
            )
            self._items[competence_id] = item
            self._enforce_bound()
        return item

    def _enforce_bound(self) -> None:
        if len(self._items) <= self.capacity:
            return
        retained = sorted(
            self._items.values(),
            key=lambda item: (
                not item.executable,
                -item.reliability,
                -item.controllability,
                item.competence_id,
            ),
        )[: self.capacity]
        self._items = {item.competence_id: item for item in retained}

    @property
    def items(self) -> tuple[EmbodiedCompetence, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.competence_id))

    @property
    def executable_count(self) -> int:
        return sum(1 for item in self._items.values() if item.executable)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "embodiment_id": self.embodiment_id,
            "capacity": self.capacity,
            "items": [item.checkpoint() for item in self.items],
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
        *,
        embodiment_id: str,
    ) -> "EmbodiedCompetenceLibrary":
        if payload is None:
            return cls(embodiment_id=embodiment_id)
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported embodied-competence checkpoint")
        if payload.get("embodiment_id") != embodiment_id:
            raise ValueError("embodied competence library belongs to another embodiment")
        obj = cls(
            embodiment_id=embodiment_id,
            capacity=int(payload.get("capacity", 512)),
        )
        raw = payload.get("items", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded embodied competence library")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid embodied competence entry")
            item = EmbodiedCompetence(
                competence_id=str(entry["competence_id"]),
                embodiment_id=embodiment_id,
                surface_binding=(
                    str(entry["surface_binding"])
                    if entry.get("surface_binding") is not None
                    else None
                ),
                controller_realization_ref=(
                    str(entry["controller_realization_ref"])
                    if entry.get("controller_realization_ref") is not None
                    else None
                ),
                evidence_refs=tuple(str(value) for value in entry.get("evidence_refs", [])),
                reliability=float(entry.get("reliability", 0.0)),
                controllability=float(entry.get("controllability", 0.0)),
                prediction_error=float(entry.get("prediction_error", 1.0)),
            )
            obj._items[item.competence_id] = item
        return obj


__all__ = ["EmbodiedCompetence", "EmbodiedCompetenceLibrary"]
