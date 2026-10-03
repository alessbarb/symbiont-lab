"""Reproduction and inheritance package generation for laboratory evolution."""

from __future__ import annotations

from lab.evolution.mutation import mutate_genome
from lab.evolution.recombination import recombine_genomes
from symbiont.genetics.genome import Genome
from symbiont.genetics.germline import (
    EpigeneticMark,
    EpigeneticProtocol,
    GermlineState,
    InheritancePackage,
)
from symbiont.genetics.schema import DEFAULT_GENOME_SCHEMA, GenomeSchema


def create_offspring_package(
    parent_genome: Genome,
    parent_germline: GermlineState,
    *,
    seed: int,
    generation: int,
    second_parent_genome: Genome | None = None,
    schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
    epigenetic_protocol: EpigeneticProtocol | None = None,
) -> InheritancePackage:
    """Create offspring without learned cognitive or embodiment state."""
    if second_parent_genome is None:
        child = mutate_genome(parent_genome, seed=seed, schema=schema)
        parents = (parent_genome.genome_id,)
    else:
        recombined = recombine_genomes(
            parent_genome,
            second_parent_genome,
            seed=seed,
            schema=schema,
        )
        child = mutate_genome(recombined, seed=seed ^ 0x5A17, schema=schema)
        parents = (parent_genome.genome_id, second_parent_genome.genome_id)

    marks: list[EpigeneticMark] = []
    protocol = epigenetic_protocol or EpigeneticProtocol()
    if protocol.enabled:
        candidates = {
            **parent_germline.inherited_marks,
            **parent_germline.acquired_marks,
        }
        for locus, mark in sorted(candidates.items()):
            if not schema.spec(locus).regulable:
                continue
            decayed = mark.decay(protocol.decay)
            if decayed is not None:
                marks.append(decayed)
        marks = marks[: protocol.max_marks]

    return InheritancePackage(
        genome=child,
        epigenetic_marks=tuple(marks),
        parent_ids=parents,
        generation=generation,
    )


__all__ = ["create_offspring_package"]
