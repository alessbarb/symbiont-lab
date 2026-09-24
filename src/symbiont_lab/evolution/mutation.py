from __future__ import annotations

import random
from dataclasses import replace
from typing import Literal

from symbiont.genetics.genome import Genome
from symbiont.genetics.mutation import mutate_genome as _mutate_genome


def mutate_continuous_fields(
    genome: Genome,
    *,
    sigma: float,
    max_fields: int,
    rng: random.Random,
) -> Genome:
    """Compatibility wrapper over canonical typed Genome v2 mutation.

    Lab code may choose a deterministic mutation event, but it cannot define a
    second mutation model. sigma and max_fields are retained only as
    historical API parameters; mutation scales and per-locus probabilities are
    constitutional GenomeSchema/evolvability concerns.
    """
    if sigma < 0.0:
        raise ValueError("sigma must be non-negative")
    if max_fields < 0:
        raise ValueError("max_fields must be non-negative")
    if max_fields == 0 or sigma == 0.0:
        return genome

    seed = rng.randrange(0, 2**31)
    return _mutate_genome(genome, seed=seed)


def mutate_soft_budget(
    genome: Genome,
    *,
    field: Literal["soft_node_budget", "soft_edge_budget"],
    delta: int,
) -> Genome:
    """Explicit Lab intervention for one-variable developmental studies."""
    if isinstance(delta, bool) or not isinstance(delta, int):
        raise ValueError("delta must be an int")
    development = genome.development
    current = getattr(development, field)
    new_value = max(1, current + delta)
    changes: dict[str, int] = {field: new_value}
    if field == "soft_node_budget" and development.sense_node_budget > new_value:
        changes["sense_node_budget"] = new_value
    development = replace(development, **changes)
    return replace(genome, development=development)


def derive_child_genome(
    parent: Genome,
    *,
    new_genome_id: str,
    mutated: Genome,
) -> Genome:
    """Materialize a child genome instance without embedding genealogy."""
    if not new_genome_id:
        raise ValueError("new_genome_id must not be empty")
    return replace(mutated, genome_id=new_genome_id)


__all__ = [
    "derive_child_genome",
    "mutate_continuous_fields",
    "mutate_soft_budget",
]
