"""Evidence-derived motor competence abstractions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CompetenceMaturity(StrEnum):
    CANDIDATE = "candidate"
    EMERGING = "emerging"
    ESTABLISHED = "established"
    ROBUST = "robust"


@dataclass(slots=True)
class CompetenceEvidence:
    controller_seed_ref: str
    effect_evidence_refs: tuple[str, ...] = ()
    context_evidence_refs: tuple[str, ...] = ()
    controllability_evidence_refs: tuple[str, ...] = ()
    support: int = 0
    failures: int = 0

    @property
    def maturity(self) -> CompetenceMaturity:
        # Maturity is a projection of evidence and is never persisted separately.
        useful = max(0, self.support - self.failures)
        if useful >= 32 and self.failures <= max(1, self.support // 8):
            return CompetenceMaturity.ROBUST
        if useful >= 8:
            return CompetenceMaturity.ESTABLISHED
        if useful >= 3:
            return CompetenceMaturity.EMERGING
        return CompetenceMaturity.CANDIDATE


@dataclass(slots=True)
class CompetenceCandidate:
    candidate_id: str
    controller_seed: object
    evidence: CompetenceEvidence
    created_tick: int
    last_supported_tick: int

    @property
    def maturity(self) -> CompetenceMaturity:
        return self.evidence.maturity


@dataclass(slots=True)
class MotorCompetence:
    competence_id: str
    controller_id: str
    effect_id: str
    evidence: CompetenceEvidence
    surface_binding: str | None = None
    parent_competence_ids: tuple[str, ...] = ()
    controller_strategy_ref: str | None = None

    @property
    def maturity(self) -> CompetenceMaturity:
        return self.evidence.maturity

    @property
    def executable(self) -> bool:
        return self.surface_binding is not None and self.maturity in {
            CompetenceMaturity.ESTABLISHED,
            CompetenceMaturity.ROBUST,
        }


class CompetenceLibrary:
    def __init__(self, *, max_competences: int = 512) -> None:
        self._max = int(max_competences)
        self._items: dict[str, MotorCompetence] = {}

    def add(self, competence: MotorCompetence) -> None:
        self._items[competence.competence_id] = competence
        if len(self._items) > self._max:
            retained = sorted(
                self._items.values(),
                key=lambda item: (
                    -item.evidence.support,
                    item.evidence.failures,
                    item.competence_id,
                ),
            )[: self._max]
            self._items = {item.competence_id: item for item in retained}

    def get(self, competence_id: str) -> MotorCompetence | None:
        return self._items.get(competence_id)

    def for_effect(self, effect_id: str, *, surface_fingerprint: str | None = None) -> tuple[MotorCompetence, ...]:
        result = [
            item
            for item in self._items.values()
            if item.effect_id == effect_id
            and (
                surface_fingerprint is None
                or item.surface_binding is None
                or item.surface_binding == surface_fingerprint
            )
        ]
        return tuple(sorted(result, key=lambda item: (-item.evidence.support, item.competence_id)))

    def invalidate_execution_binding(self, surface_fingerprint: str) -> tuple[str, ...]:
        """Report incompatibility without changing learned evidence/confidence."""
        return tuple(
            sorted(
                item.competence_id
                for item in self._items.values()
                if item.surface_binding is not None
                and item.surface_binding != surface_fingerprint
            )
        )

    @property
    def items(self) -> tuple[MotorCompetence, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.competence_id))
