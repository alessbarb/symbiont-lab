"""Typed Genome v2 mutation."""
from __future__ import annotations

import copy
import math
import random
from typing import Any

from .genome import Genome, GenomeCodec, _genome_to_plain_dict
from .schema import DEFAULT_GENOME_SCHEMA, GeneType, GenomeSchema, MutationMode


def _path_parts(locus: str) -> tuple[str, ...]:
    return tuple("min" if part == "minimum" else "max" if part == "maximum" else part for part in locus.split("."))


def _set_path(payload: dict[str, Any], locus: str, value: Any) -> None:
    parts = _path_parts(locus)
    current: dict[str, Any] = payload
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            raise ValueError(f"invalid genome path {locus!r}")
        current = child
    current[parts[-1]] = value


def _family_scale(genome: Genome, locus: str) -> float:
    family = locus.split(".", 1)[0]
    mapping = {
        "development": genome.evolvability.development_mutation_scale,
        "plasticity": genome.evolvability.plasticity_mutation_scale,
        "regulation": genome.evolvability.regulation_mutation_scale,
        "sensorimotor": genome.evolvability.sensorimotor_mutation_scale,
        "structure": genome.evolvability.structure_mutation_scale,
    }
    return max(0.0, float(mapping.get(family, 1.0)))


def mutate_genome(
    genome: Genome,
    *,
    seed: int,
    schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
    new_genome_id: str | None = None,
) -> Genome:
    """Return a new genotype using only typed, schema-declared mutation."""
    rng = random.Random(seed)
    payload = copy.deepcopy(_genome_to_plain_dict(genome))
    changed = False
    from .genome import flatten_genes

    values = flatten_genes(genome)
    for locus, current in sorted(values.items()):
        spec = schema.spec(locus)
        if not spec.inheritable or rng.random() > spec.mutation_probability:
            continue

        scale = spec.mutation_scale * _family_scale(genome, locus)
        if spec.gene_type == GeneType.INT:
            step = max(1, int(round(scale)))
            proposed = int(current) + rng.choice((-step, step))
            value = spec.clamp(proposed)
        elif spec.gene_type == GeneType.FLOAT:
            if spec.mutation_mode == MutationMode.LOG_SCALE:
                base = max(float(current), 1e-12)
                proposed = math.exp(math.log(base) + rng.gauss(0.0, scale))
            else:
                proposed = float(current) + rng.gauss(0.0, scale)
            value = spec.clamp(proposed)
        elif spec.gene_type == GeneType.BOOL:
            value = not bool(current)
        elif spec.gene_type == GeneType.ENUM:
            choices = tuple(choice for choice in spec.choices if choice != current)
            value = rng.choice(choices) if choices else current
        else:
            value = current

        if value != current:
            _set_path(payload, locus, value)
            changed = True

    parent_id = genome.genome_id
    payload["parent_ids"] = [parent_id]
    payload["genome_id"] = new_genome_id or (
        f"genome_{genome.genotype_hash[:12]}_m{seed & 0xffff:x}"
        if changed
        else f"genome_{genome.genotype_hash[:12]}_clone{seed & 0xffff:x}"
    )
    return GenomeCodec(schema).load(payload)


__all__ = ["mutate_genome"]
