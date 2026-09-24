from __future__ import annotations

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.limits import KernelLimits
from symbiont.core.inheritance import (
    CulturalArtifact,
    EpigeneticPrior,
    InheritanceChannels,
    mutate_genome,
)


def _genome():
    return load_base_genome(
        kernel_limits=KernelLimits(),
        running_version=(0, 80, 0),
    )


def test_legacy_mutation_entrypoint_delegates_to_genome_v2():
    genome = _genome()
    a = mutate_genome(genome, seed=3)
    b = mutate_genome(genome, seed=3)
    assert a == b
    assert a.schema_version == 2


def test_channels_are_separate_and_bounded():
    channels = InheritanceChannels(max_epigenetic=1, max_cultural=1)
    assert channels.add_epigenetic(EpigeneticPrior("x", 0.2))
    assert not channels.add_epigenetic(EpigeneticPrior("y", 0.3))
    assert channels.add_cultural(CulturalArtifact("k", 0.4))
    assert not channels.add_cultural(CulturalArtifact("l", 0.5))
