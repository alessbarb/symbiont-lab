"""Synthetic adversarial ecology accounting (v0.76)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdversarialAssessment:
    accepted: bool
    stale: bool
    poisoning: bool
    sybil_pressure: float


class AdversarialEcology:
    def __init__(self, *, max_age: int = 10, max_sources: int = 32) -> None:
        if max_age < 0 or max_sources <= 0:
            raise ValueError("invalid adversarial bounds")
        self.max_age = max_age
        self.max_sources = max_sources
        self._last_seen: dict[str, int] = {}

    def assess(self, source: str, tick: int, *, age: int, contradiction: bool = False) -> AdversarialAssessment:
        if not source or tick < 0 or age < 0:
            raise ValueError("invalid adversarial observation")
        stale = age > self.max_age
        previous = self._last_seen.get(source, -1)
        replay = tick <= previous
        self._last_seen[source] = max(previous, tick)
        sybil_pressure = min(1.0, len(self._last_seen) / self.max_sources)
        poisoning = bool(contradiction and not stale)
        return AdversarialAssessment(not (stale or replay), stale, poisoning, sybil_pressure)


__all__ = ["AdversarialAssessment", "AdversarialEcology"]
