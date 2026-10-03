from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class HeritagePattern:
    fingerprint: str
    threat_probability: float
    certainty: float
    support: int
    source_generation: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class SpeciesHeritage:
    generation: int
    patterns: tuple[HeritagePattern, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "generation": self.generation,
            "patterns": [pattern.as_dict() for pattern in self.patterns],
        }


def apply_heritage(ledger: object, heritage: SpeciesHeritage | None) -> None:
    """Acquired social/cultural state is not copied into offspring germline."""
    pass


def distill_heritage(
    ledger: object,
    *,
    generation: int,
    max_patterns: int = 24,
    min_reports: int = 6,
    min_sources: int = 4,
    min_certainty: float = 0.68,
    min_separation: float = 0.20,
) -> SpeciesHeritage:
    """No learned cultural content enters the germline."""
    return SpeciesHeritage(generation=max(0, generation), patterns=())
