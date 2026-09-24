"""Minimal evidence-first sequential competence composition."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SequentialCompositionEvidence:
    first_competence_id: str
    second_competence_id: str
    effect_id: str
    support: int = 0
    failures: int = 0

    @property
    def established(self) -> bool:
        return self.support >= 4 and self.support >= 2 * max(1, self.failures)


class CompositionEngine:
    def __init__(self) -> None:
        self._sequential: dict[tuple[str, str, str], SequentialCompositionEvidence] = {}

    def observe(self, first: str, second: str, effect_id: str, *, success: bool) -> SequentialCompositionEvidence:
        key = (first, second, effect_id)
        evidence = self._sequential.setdefault(
            key, SequentialCompositionEvidence(first, second, effect_id)
        )
        if success:
            evidence.support += 1
        else:
            evidence.failures += 1
        return evidence

    @property
    def established(self) -> tuple[SequentialCompositionEvidence, ...]:
        return tuple(item for item in self._sequential.values() if item.established)
