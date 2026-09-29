from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceEvidenceOutcome(Enum):
    AGREEMENT = "agreement"
    CONTRADICTION = "contradiction"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class SourceEvidenceSample:
    tick: int
    outcome: SourceEvidenceOutcome
    compatibility: float
    quality: float
    freshness: float
    independence: float
    evidence_ref: str | None


@dataclass(slots=True)
class SourceEvidenceState:
    source_id: str
    samples: list[SourceEvidenceSample] = field(default_factory=list)
    agreements: int = 0
    contradictions: int = 0
    unresolved: int = 0
    independent_roots: int = 0

    def add_sample(self, sample: SourceEvidenceSample) -> None:
        self.samples.append(sample)
        if sample.outcome == SourceEvidenceOutcome.AGREEMENT:
            self.agreements += 1
        elif sample.outcome == SourceEvidenceOutcome.CONTRADICTION:
            self.contradictions += 1
        else:
            self.unresolved += 1

        # In a real implementation, independent_roots would track unique root_evidence_ids,
        # but as a simplified integer, we just increment for now or rely on the ledger.
        self.independent_roots += 1

    @property
    def mean_compatibility(self) -> float:
        if not self.samples:
            return 0.0
        return sum(s.compatibility for s in self.samples) / len(self.samples)

    @property
    def mean_quality(self) -> float:
        if not self.samples:
            return 0.0
        return sum(s.quality for s in self.samples) / len(self.samples)

    @property
    def mean_freshness(self) -> float:
        if not self.samples:
            return 0.0
        return sum(s.freshness for s in self.samples) / len(self.samples)

    @property
    def source_reliability(self) -> float:
        """Descriptive derivation of reliability, not an authoritative boolean truth."""
        total_resolved = self.agreements + self.contradictions
        if total_resolved == 0:
            return 0.5  # Neutral prior
        return self.agreements / total_resolved
