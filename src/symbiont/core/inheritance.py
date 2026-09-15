"""Separate genetic, epigenetic and cultural inheritance channels (v0.69)."""
from __future__ import annotations

from dataclasses import dataclass
import random

from .heredity import HeritableGenome, _ALLOWED_LOCI


@dataclass(frozen=True, slots=True)
class EpigeneticPrior:
    key: str
    value: float

    def __post_init__(self) -> None:
        if not self.key or len(self.key) > 64 or not 0.0 <= self.value <= 1.0:
            raise ValueError("invalid epigenetic prior")


@dataclass(frozen=True, slots=True)
class CulturalArtifact:
    key: str
    value: float

    def __post_init__(self) -> None:
        if not self.key or len(self.key) > 64 or not 0.0 <= self.value <= 1.0:
            raise ValueError("invalid cultural artifact")


def mutate_genome(genome: HeritableGenome, *, sigma: float = 0.05, max_fields: int = 1,
                  seed: int = 0) -> HeritableGenome:
    """Apply bounded numeric mutation to declared loci only."""
    if not 0.0 <= sigma <= 1.0 or max_fields < 0:
        raise ValueError("invalid mutation bounds")
    rng = random.Random(seed)
    loci = list(genome.loci)
    for index in rng.sample(range(len(loci)), min(max_fields, len(loci))):
        key, value = loci[index]
        loci[index] = (key, max(0.0, min(1.0, value + rng.gauss(0.0, sigma))))
    return HeritableGenome(genome_id=f"{genome.genome_id}:mutant", loci=tuple(sorted(loci)))


class InheritanceChannels:
    """Bounded post-birth channels; cultural data is never folded into genes."""

    def __init__(self, *, max_epigenetic: int = 16, max_cultural: int = 32) -> None:
        if min(max_epigenetic, max_cultural) < 1:
            raise ValueError("inheritance bounds must be positive")
        self.max_epigenetic, self.max_cultural = max_epigenetic, max_cultural
        self.epigenetic: list[EpigeneticPrior] = []
        self.cultural: list[CulturalArtifact] = []

    def add_epigenetic(self, prior: EpigeneticPrior) -> bool:
        if len(self.epigenetic) >= self.max_epigenetic: return False
        self.epigenetic.append(prior); return True

    def add_cultural(self, artifact: CulturalArtifact) -> bool:
        if len(self.cultural) >= self.max_cultural: return False
        self.cultural.append(artifact); return True


__all__ = ["CulturalArtifact", "EpigeneticPrior", "InheritanceChannels", "mutate_genome"]
