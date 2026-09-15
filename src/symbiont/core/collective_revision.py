"""Evidence-weighted collective revision without majority-as-truth (v0.74)."""
from __future__ import annotations

from dataclasses import dataclass

from .evidence_trust import EvidenceTrust


@dataclass(frozen=True, slots=True)
class RevisionResult:
    claim: str
    probability: float
    certainty: float
    contributors: int
    dissent: bool


def revise_claim(claim: str, reports: list[tuple[bool, EvidenceTrust]]) -> RevisionResult:
    if not claim or not reports:
        raise ValueError("claim and reports are required")
    weights = [trust.aggregate for _, trust in reports]
    total = sum(weights)
    probability = sum(weight * int(vote) for (vote, _), weight in zip(reports, weights)) / max(total, 1e-9)
    dissent = any(vote != (probability >= 0.5) for vote, _ in reports)
    certainty = min(1.0, 0.25 * min(len(reports) / 4.0, 1.0) + 0.5 * abs(probability - 0.5) * 2 + (0.25 if not dissent else 0.0))
    return RevisionResult(claim, probability, certainty, len(reports), dissent)


__all__ = ["RevisionResult", "revise_claim"]
