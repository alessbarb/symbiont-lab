"""Evaluator-only measurements for multigenerational lineage studies."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from symbiont.core.birth_authority import HabitatBirthAuthority


@dataclass(frozen=True, slots=True)
class EvolutionarySnapshot:
    """A measurement of lineage composition, not an organism fitness value."""

    live_population: int
    live_genome_frequencies: dict[str, int]
    live_generation_frequencies: dict[int, int]
    observed_genomes: tuple[str, ...]
    extinct_genomes: tuple[str, ...]
    observed_generations: tuple[int, ...]
    deaths: int
    genetic_diversity: int = 0
    lineage_persistence: dict[str, float] = field(default_factory=dict)
    selection_differentials: dict[str, float] = field(default_factory=dict)
    offspring_viability: float | None = None
    genome_loci: dict[str, tuple[tuple[str, float], ...]] = field(default_factory=dict)
    genome_lifespans: dict[str, tuple[int, ...]] = field(default_factory=dict)
    genome_resource_use: dict[str, float] = field(default_factory=dict)
    genome_reproduction_counts: dict[str, int] = field(default_factory=dict)


def measure_lineages(
    authority: HabitatBirthAuthority,
    *,
    genome_loci: dict[str, tuple[tuple[str, float], ...]] | None = None,
    organism_lifespans: dict[str, int] | None = None,
    organism_resource_use: dict[str, float] | None = None,
    organism_reproduction_counts: dict[str, int] | None = None,
) -> EvolutionarySnapshot:
    """Measure current and historical lineage composition after a run step.

    The authority is an apparatus-owned boundary.  This function has no path
    back into an organism and deliberately does not produce a scalar fitness.
    """
    records = authority.lineage_records
    live = set(authority.live_ids)
    live_records = [record for record in records if record.organism_id in live]
    live_genomes = Counter(record.genome_id for record in live_records)
    live_generations = Counter(record.generation for record in live_records)
    births_by_genome = Counter(record.genome_id for record in records)
    offspring = [record for record in records if record.parent_ids]
    observed = {record.genome_id for record in records}
    extinct = {
        record.genome_id for record in records
        if record.organism_id not in live
        and not any(other.genome_id == record.genome_id and other.organism_id in live
                    for other in records)
    }
    return EvolutionarySnapshot(
        live_population=len(live_records),
        live_genome_frequencies=dict(sorted(live_genomes.items())),
        live_generation_frequencies=dict(sorted(live_generations.items())),
        observed_genomes=tuple(sorted(observed)),
        extinct_genomes=tuple(sorted(extinct)),
        observed_generations=tuple(sorted({record.generation for record in records})),
        deaths=len(authority.death_records),
        genetic_diversity=len(observed),
        # This is an evaluator-side cohort measure: the fraction of observed
        # births for a genome that remains live at the sampling point.  It is
        # deliberately not exposed to an organism and is not called fitness.
        lineage_persistence={
            genome_id: round(live_genomes.get(genome_id, 0) / birth_count, 6)
            for genome_id, birth_count in sorted(births_by_genome.items())
        },
        # Difference between the genome's current live share and its share of
        # all observed births.  This is a descriptive selection differential,
        # not a reward or an input to behavior.
        selection_differentials=_selection_differentials(
            births_by_genome, live_genomes, len(live_records)
        ),
        # A point-in-time cohort measure: surviving authorized descendants
        # divided by all authorized descendant births observed so far. Founder
        # registrations are intentionally excluded from this denominator.
        offspring_viability=(round(
            sum(record.organism_id in live for record in offspring) / len(offspring), 6
        ) if offspring else None),
        genome_loci={
            str(genome_id): tuple((str(key), float(value)) for key, value in loci)
            for genome_id, loci in sorted((genome_loci or {}).items())
        },
        genome_lifespans=_group_by_genome(
            records,
            organism_lifespans or {},
            aggregate="tuple",
        ),
        genome_resource_use=_group_by_genome(
            records,
            organism_resource_use or {},
            aggregate="sum",
        ),
        genome_reproduction_counts=_group_by_genome(
            records,
            organism_reproduction_counts or {},
            aggregate="count",
        ),
    )


def _group_by_genome(
    records: tuple[object, ...],
    values: dict[str, int | float],
    *,
    aggregate: str,
) -> dict[str, tuple[int, ...]] | dict[str, float] | dict[str, int]:
    """Group bounded subject outcomes by evaluator-owned genome identity."""
    grouped: dict[str, list[int | float]] = {}
    for record in records:
        organism_id = str(getattr(record, "organism_id", ""))
        if organism_id not in values:
            continue
        genome_id = str(getattr(record, "genome_id", ""))
        grouped.setdefault(genome_id, []).append(values[organism_id])
    if aggregate == "tuple":
        return {
            genome_id: tuple(int(value) for value in sorted(items))
            for genome_id, items in sorted(grouped.items())
        }
    if aggregate == "sum":
        return {
            genome_id: round(sum(float(value) for value in items), 6)
            for genome_id, items in sorted(grouped.items())
        }
    if aggregate == "count":
        return {
            genome_id: int(sum(int(value) for value in items))
            for genome_id, items in sorted(grouped.items())
        }
    raise ValueError("unsupported lineage outcome aggregate")


def _selection_differentials(
    births_by_genome: Counter[str],
    live_by_genome: Counter[str],
    live_population: int,
) -> dict[str, float]:
    """Return live-share minus birth-share for each observed genome."""
    total_births = sum(births_by_genome.values())
    if not total_births:
        return {}
    return {
        genome_id: round(
            (live_by_genome.get(genome_id, 0) / live_population
             if live_population else 0.0)
            - (birth_count / total_births),
            6,
        )
        for genome_id, birth_count in sorted(births_by_genome.items())
    }


__all__ = ["EvolutionarySnapshot", "measure_lineages"]
