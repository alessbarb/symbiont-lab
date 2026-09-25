"""Evidence-derived motor competence abstractions."""
from __future__ import annotations

from dataclasses import dataclass
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
    reproducibility: float = 0.0
    controllability: float = 0.0
    directional_consistency: float = 0.0

    @property
    def maturity(self) -> CompetenceMaturity:
        """Evidence projection only; no separately mutable maturity truth."""
        if (
            self.support < 2
            or self.controllability <= 0.002
            or self.reproducibility < (2.0 / 3.0)
            or self.directional_consistency < 0.60
        ):
            if self.support >= 2 and self.controllability > 0.0:
                return CompetenceMaturity.EMERGING
            return CompetenceMaturity.CANDIDATE
        if (
            self.support >= 8
            and self.reproducibility >= 0.85
            and self.directional_consistency >= 0.80
            and self.failures <= max(1, self.support // 8)
        ):
            return CompetenceMaturity.ROBUST
        return CompetenceMaturity.ESTABLISHED


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
    effect_id: str | None
    evidence: CompetenceEvidence
    parent_competence_ids: tuple[str, ...] = ()
    controller_strategy_ref: str | None = None

    @property
    def maturity(self) -> CompetenceMaturity:
        return self.evidence.maturity

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

    def for_effect(self, effect_id: str) -> tuple[MotorCompetence, ...]:
        result = [
            item
            for item in self._items.values()
            if item.effect_id == effect_id
        ]
        return tuple(
            sorted(
                result,
                key=lambda item: (-item.evidence.support, item.competence_id),
            )
        )

    @property
    def items(self) -> tuple[MotorCompetence, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.competence_id))
