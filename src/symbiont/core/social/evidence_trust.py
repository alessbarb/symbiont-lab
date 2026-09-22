"""Separate evidence dimensions for exchange evaluation (v0.73)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceTrust:
    compatibility: float
    quality: float
    freshness: float
    independence: float
    source_reliability: float

    def __post_init__(self) -> None:
        values = (self.compatibility, self.quality, self.freshness, self.independence, self.source_reliability)
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("evidence dimensions must be between 0 and 1")

    @property
    def aggregate(self) -> float:
        return sum((self.compatibility, self.quality, self.freshness, self.independence, self.source_reliability)) / 5


__all__ = ["EvidenceTrust"]
