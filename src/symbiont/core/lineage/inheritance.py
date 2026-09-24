"""Separate genetic, epigenetic and cultural inheritance channels (v0.69)."""
from __future__ import annotations

from dataclasses import dataclass

from ...genetics.genome import Genome
from ...genetics.mutation import mutate_genome as _mutate_genome_v2


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


def mutate_genome(
    genome: Genome,
    *,
    sigma: float = 0.05,
    max_fields: int = 1,
    seed: int = 0,
) -> Genome:
    """Compatibility entrypoint to the single typed Genome v2 mutator.

    sigma/max_fields are accepted for source compatibility only. The effective
    per-locus mutation equation is owned by GenomeSchema and EvolvabilityGenes.
    """
    if not isinstance(genome, Genome):
        raise TypeError("mutate_genome requires canonical Genome v2")
    if not 0.0 <= sigma <= 1.0 or max_fields < 0:
        raise ValueError("invalid mutation bounds")
    if sigma == 0.0 or max_fields == 0:
        return genome
    return _mutate_genome_v2(genome, seed=seed)


from ..foundation.limits import OrganismLimits

_DEFAULT_LIMITS = OrganismLimits()


class InheritanceChannels:
    """Bounded post-birth channels; cultural data is never folded into genes."""

    def __init__(
        self,
        *,
        max_epigenetic: int = _DEFAULT_LIMITS.max_epigenetic_priors,
        max_cultural: int = _DEFAULT_LIMITS.max_cultural_artifacts,
    ) -> None:
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
