from __future__ import annotations

import random
from dataclasses import replace
from typing import Literal

from symbiont.cognition.genome import Genome, RangeSpec


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mutate_continuous_fields(genome: Genome, *, sigma: float, max_fields: int, rng: random.Random) -> Genome:
    candidates: list[str] = [
        "learning_rate",
        "forgetting_rate",
        "eligibility_decay",
        "grow_threshold",
        "prune_threshold",
        "continuous_sigma",
    ]
    chosen = rng.sample(candidates, k=min(max_fields, len(candidates)))

    plasticity = genome.plasticity
    structure = genome.structure
    continuous_sigma = genome.mutation_policy.continuous_sigma

    if "learning_rate" in chosen:
        spec = plasticity.learning_rate
        new_initial = _clip(spec.initial + rng.gauss(0.0, sigma), spec.minimum, spec.maximum)
        plasticity = replace(plasticity, learning_rate=RangeSpec(initial=new_initial, minimum=spec.minimum, maximum=spec.maximum))
    if "forgetting_rate" in chosen:
        spec = plasticity.forgetting_rate
        new_initial = _clip(spec.initial + rng.gauss(0.0, sigma), spec.minimum, spec.maximum)
        plasticity = replace(plasticity, forgetting_rate=RangeSpec(initial=new_initial, minimum=spec.minimum, maximum=spec.maximum))
    if "eligibility_decay" in chosen:
        plasticity = replace(plasticity, eligibility_decay=_clip(plasticity.eligibility_decay + rng.gauss(0.0, sigma), 0.0, 1.0))

    if "grow_threshold" in chosen:
        structure = replace(structure, grow_threshold=_clip(structure.grow_threshold + rng.gauss(0.0, sigma), 0.0, 1.0))
    if "prune_threshold" in chosen:
        structure = replace(structure, prune_threshold=_clip(structure.prune_threshold + rng.gauss(0.0, sigma), 0.0, 1.0))

    mutation_policy = genome.mutation_policy
    if "continuous_sigma" in chosen:
        mutation_policy = replace(mutation_policy, continuous_sigma=_clip(continuous_sigma + rng.gauss(0.0, sigma), 0.0, 1.0))

    return replace(genome, plasticity=plasticity, structure=structure, mutation_policy=mutation_policy)


def mutate_soft_budget(genome: Genome, *, field: Literal["soft_node_budget", "soft_edge_budget"], delta: int) -> Genome:
    development = genome.development
    current = getattr(development, field)
    new_value = max(1, current + delta)
    changes: dict[str, int] = {field: new_value}
    if field == "soft_node_budget" and development.sense_node_budget > new_value:
        changes["sense_node_budget"] = new_value
    development = replace(development, **changes)
    return replace(genome, development=development)


def derive_child_genome(parent: Genome, *, new_genome_id: str, mutated: Genome) -> Genome:
    return replace(mutated, genome_id=new_genome_id, parent_ids=(parent.genome_id,))
