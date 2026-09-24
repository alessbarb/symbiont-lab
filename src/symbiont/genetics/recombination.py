"""Genome v2 recombination with linkage groups."""
from __future__ import annotations

import copy
import random
from typing import Any

from .genome import Genome, GenomeCodec, _genome_to_plain_dict, flatten_genes
from .schema import DEFAULT_GENOME_SCHEMA, GenomeSchema


def _parts(locus: str) -> tuple[str, ...]:
    return tuple("min" if part == "minimum" else "max" if part == "maximum" else part for part in locus.split("."))


def _set_path(payload: dict[str, Any], locus: str, value: Any) -> None:
    parts = _parts(locus)
    current = payload
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            raise ValueError(f"invalid genome path {locus!r}")
        current = child
    current[parts[-1]] = value


def recombine_genomes(
    parent_a: Genome,
    parent_b: Genome,
    *,
    seed: int,
    schema: GenomeSchema = DEFAULT_GENOME_SCHEMA,
    new_genome_id: str | None = None,
) -> Genome:
    """Recombine declared loci or linkage groups without fitness information."""
    if parent_a.schema_version != parent_b.schema_version:
        raise ValueError("parents must use the same genome schema version")

    rng = random.Random(seed)
    a = flatten_genes(parent_a)
    b = flatten_genes(parent_b)
    schema.validate_flat(a)
    schema.validate_flat(b)

    payload = copy.deepcopy(_genome_to_plain_dict(parent_a))
    linkage = max(
        0.0,
        min(
            1.0,
            0.5
            * (
                parent_a.evolvability.recombination_linkage
                + parent_b.evolvability.recombination_linkage
            ),
        ),
    )

    for group, loci in sorted(schema.recombination_groups().items()):
        linked_choice = rng.random() < 0.5
        for locus in loci:
            use_linked = rng.random() < linkage
            choose_a = linked_choice if use_linked else rng.random() < 0.5
            _set_path(payload, locus, a[locus] if choose_a else b[locus])

    payload["parent_ids"] = [parent_a.genome_id, parent_b.genome_id]
    payload["genome_id"] = new_genome_id or f"genome_recombined_{seed & 0xffffffff:08x}"
    return GenomeCodec(schema).load(payload)


__all__ = ["recombine_genomes"]
