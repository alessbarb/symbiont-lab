"""Embodiment-local execution authority for learned motor competences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .competence import CompetenceMaturity, MotorCompetence


@dataclass(frozen=True, slots=True)
class CompetenceExecutionBinding:
    """Current-body evidence that one general competence can execute here."""

    competence_id: str
    surface_fingerprint: str
    effect_id: str
    evidence_refs: tuple[str, ...]
    reliability: float
    controllability: float
    last_evidence_tick: int

    def __post_init__(self) -> None:
        if not self.competence_id or not self.surface_fingerprint or not self.effect_id:
            raise ValueError("execution binding identifiers must be non-empty")
        if not self.evidence_refs:
            raise ValueError("execution binding requires current factual evidence")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("binding reliability must be in [0,1]")
        if not 0.0 <= self.controllability <= 1.0:
            raise ValueError("binding controllability must be in [0,1]")
        if self.last_evidence_tick < 0:
            raise ValueError("last_evidence_tick must be non-negative")


class CompetenceExecutionBindingRegistry:
    """Bounded current-embodiment authority, separate from competence knowledge."""

    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = 512) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self._items: dict[str, CompetenceExecutionBinding] = {}

    def bind_from_evidence(
        self,
        *,
        competence_id: str,
        surface_fingerprint: str,
        effect_id: str,
        evidence_refs: tuple[str, ...],
        reliability: float,
        controllability: float,
        tick: int,
    ) -> CompetenceExecutionBinding:
        existing = self._items.get(competence_id)
        refs = tuple(
            dict.fromkeys(
                (existing.evidence_refs if existing is not None else ()) + tuple(evidence_refs)
            )
        )
        binding = CompetenceExecutionBinding(
            competence_id=competence_id,
            surface_fingerprint=surface_fingerprint,
            effect_id=effect_id,
            evidence_refs=refs,
            reliability=max(0.0, min(1.0, float(reliability))),
            controllability=max(0.0, min(1.0, float(controllability))),
            last_evidence_tick=int(tick),
        )
        self._items[competence_id] = binding
        self._enforce_bound()
        return binding

    def _enforce_bound(self) -> None:
        if len(self._items) <= self.capacity:
            return
        retained = sorted(
            self._items.values(),
            key=lambda item: (
                -item.last_evidence_tick,
                -item.controllability,
                -item.reliability,
                item.competence_id,
            ),
        )[: self.capacity]
        self._items = {item.competence_id: item for item in retained}

    def get(self, competence_id: str) -> CompetenceExecutionBinding | None:
        return self._items.get(competence_id)

    def is_executable(
        self,
        competence: MotorCompetence,
        *,
        surface_fingerprint: str | None,
    ) -> bool:
        if surface_fingerprint is None:
            return False
        binding = self._items.get(competence.competence_id)
        return (
            binding is not None
            and binding.surface_fingerprint == surface_fingerprint
            and bool(binding.evidence_refs)
            and competence.maturity in {CompetenceMaturity.ESTABLISHED, CompetenceMaturity.ROBUST}
        )

    def invalid_for_surface(self, surface_fingerprint: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                competence_id
                for competence_id, binding in self._items.items()
                if binding.surface_fingerprint != surface_fingerprint
            )
        )

    @property
    def items(self) -> tuple[CompetenceExecutionBinding, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.competence_id))

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "items": [
                {
                    "competence_id": item.competence_id,
                    "surface_fingerprint": item.surface_fingerprint,
                    "effect_id": item.effect_id,
                    "evidence_refs": list(item.evidence_refs),
                    "reliability": item.reliability,
                    "controllability": item.controllability,
                    "last_evidence_tick": item.last_evidence_tick,
                }
                for item in self.items
            ],
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
    ) -> "CompetenceExecutionBindingRegistry":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported competence execution binding checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 512)))
        raw = payload.get("items", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded competence execution bindings")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid competence execution binding")
            binding = CompetenceExecutionBinding(
                competence_id=str(entry["competence_id"]),
                surface_fingerprint=str(entry["surface_fingerprint"]),
                effect_id=str(entry["effect_id"]),
                evidence_refs=tuple(str(value) for value in entry.get("evidence_refs", [])),
                reliability=float(entry.get("reliability", 0.0)),
                controllability=float(entry.get("controllability", 0.0)),
                last_evidence_tick=int(entry.get("last_evidence_tick", 0)),
            )
            obj._items[binding.competence_id] = binding
        return obj


__all__ = [
    "CompetenceExecutionBinding",
    "CompetenceExecutionBindingRegistry",
]
