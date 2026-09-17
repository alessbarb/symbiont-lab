"""Evaluator-owned replicated studies for multigenerational Genesis runs."""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import sqrt

from .evolution import EvolutionarySnapshot
from .genesis import build_genesis_harness
from .harness import HarnessConfig


@dataclass(frozen=True, slots=True)
class EvolutionObservation:
    """One independent run and its final evaluator-only lineage snapshot."""

    seed: int
    snapshot: EvolutionarySnapshot


@dataclass(frozen=True, slots=True)
class AdaptiveDifferentialObservation:
    """One evaluator-side trait/pressure cohort outcome."""

    seed: int
    pressure: tuple[str, ...]
    trait: str
    trait_value: float
    live_population: int
    deaths: int
    offspring_viability: float | None


@dataclass(frozen=True, slots=True)
class LocusAssociation:
    """Descriptive evaluator-side association for one inherited locus."""

    locus: str
    observations: int
    value_min: float
    value_max: float
    mean_persistence: float
    mean_selection_differential: float
    mean_lifespan: float
    mean_resource_use: float | None
    mean_reproduction_count: float
    persistence_correlation: float | None
    selection_differential_correlation: float | None
    lifespan_correlation: float | None
    resource_use_correlation: float | None
    reproduction_correlation: float | None


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    covariance = sum((a - left_mean) * (b - right_mean)
                     for a, b in zip(left, right))
    left_variance = sum((a - left_mean) ** 2 for a in left)
    right_variance = sum((b - right_mean) ** 2 for b in right)
    if left_variance == 0.0 or right_variance == 0.0:
        return None
    return round(covariance / sqrt(left_variance * right_variance), 6)


def summarize_locus_associations(
    snapshot: EvolutionarySnapshot,
) -> tuple[LocusAssociation, ...]:
    """Summarize inherited-locus relationships after a run.

    This is strictly post-run apparatus analysis.  It describes associations
    with evaluator measures and never creates a runtime fitness value or an
    organism-facing signal.
    """
    values_by_locus: dict[str, list[tuple[float, float, float, float, float | None, float]]] = {}
    for genome_id, loci in snapshot.genome_loci.items():
        persistence = snapshot.lineage_persistence.get(genome_id, 0.0)
        differential = snapshot.selection_differentials.get(genome_id, 0.0)
        lifespans = snapshot.genome_lifespans.get(genome_id, ())
        lifespan = sum(lifespans) / len(lifespans) if lifespans else 0.0
        resource_use = snapshot.genome_resource_use.get(genome_id)
        reproduction_count = snapshot.genome_reproduction_counts.get(genome_id, 0)
        for locus, value in loci:
            values_by_locus.setdefault(locus, []).append(
                (float(value), persistence, differential, lifespan,
                 resource_use, float(reproduction_count))
            )
    summaries: list[LocusAssociation] = []
    for locus, rows in sorted(values_by_locus.items()):
        values = [row[0] for row in rows]
        persistence = [row[1] for row in rows]
        differential = [row[2] for row in rows]
        lifespan = [row[3] for row in rows]
        reproduction_count = [row[5] for row in rows]
        resource_pairs = [(row[0], row[4]) for row in rows if row[4] is not None]
        observed_resource_values = [value for _, value in resource_pairs]
        summaries.append(LocusAssociation(
            locus=locus,
            observations=len(rows),
            value_min=round(min(values), 6),
            value_max=round(max(values), 6),
            mean_persistence=round(sum(persistence) / len(rows), 6),
            mean_selection_differential=round(sum(differential) / len(rows), 6),
            mean_lifespan=round(sum(lifespan) / len(rows), 6),
            mean_resource_use=(
                round(sum(observed_resource_values) / len(observed_resource_values), 6)
                if observed_resource_values else None
            ),
            mean_reproduction_count=round(sum(reproduction_count) / len(rows), 6),
            persistence_correlation=_correlation(values, persistence),
            selection_differential_correlation=_correlation(values, differential),
            lifespan_correlation=_correlation(values, lifespan),
            resource_use_correlation=_correlation(
                [value for value, _ in resource_pairs], observed_resource_values
            ),
            reproduction_correlation=_correlation(values, reproduction_count),
        ))
    return tuple(summaries)


def run_genesis_evolution_replicates(
    config: HarnessConfig | None = None,
    *,
    seeds: tuple[int, ...] = (7, 11, 19),
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
    founder_loci: tuple[tuple[str, float], ...] | None = None,
) -> tuple[EvolutionObservation, ...]:
    """Run independent evolutionary conditions without collapsing evidence.

    All returned values belong to the apparatus.  The seed, locus table,
    persistence and selection differential are never projected to organisms.
    """
    if not seeds or len(seeds) > 64 or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain 1 to 64 unique values")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be integers")
    if not isinstance(social_enabled, bool):
        raise ValueError("social_enabled must be a boolean")
    selected = config or HarnessConfig(
        population=8, generations=2, ticks=600,
        checkpoint_interval=600, random_checkpoint_count=0,
    )
    observations: list[EvolutionObservation] = []
    for seed in seeds:
        trace = build_genesis_harness(
            replace(selected, seed=seed),
            reproduction_enabled=True,
            social_enabled=social_enabled,
            resource_profiles=resource_profiles,
            founder_loci=founder_loci,
        ).run()
        if not trace.evolutionary:
            raise RuntimeError("Genesis evolution run produced no evaluator snapshot")
        observations.append(EvolutionObservation(seed=seed, snapshot=trace.evolutionary[-1]))
    return tuple(observations)


def run_genesis_adaptive_differential(
    config: HarnessConfig | None = None,
    *,
    trait: str = "behavior_exploration",
    control_value: float = 0.0,
    selected_value: float = 0.1,
    seeds: tuple[int, ...] = (7, 11, 19),
    pressures: tuple[tuple[str, ...], ...] = ((), ("stale_resources",)),
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
) -> tuple[AdaptiveDifferentialObservation, ...]:
    """Run a predeclared heritable-trait by environmental-pressure study."""
    if not isinstance(trait, str) or not trait:
        raise ValueError("trait must be a non-empty locus name")
    if not seeds or len(seeds) > 64 or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain 1 to 64 unique values")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be integers")
    if not pressures or any(len(set(pressure)) != len(pressure) for pressure in pressures):
        raise ValueError("pressures must contain unique condition names")
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=128,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    observations: list[AdaptiveDifferentialObservation] = []
    for pressure in pressures:
        for value in (control_value, selected_value):
            for seed in seeds:
                run_config = replace(selected, seed=seed,
                                     adversarial_conditions=pressure)
                result = run_genesis_evolution_replicates(
                    run_config, seeds=(seed,), social_enabled=social_enabled,
                    resource_profiles=resource_profiles,
                    founder_loci=((trait, value),),
                )[0].snapshot
                observations.append(AdaptiveDifferentialObservation(
                    seed=seed, pressure=pressure, trait=trait,
                    trait_value=value, live_population=result.live_population,
                    deaths=result.deaths,
                    offspring_viability=result.offspring_viability,
                ))
    return tuple(observations)


__all__ = [
    "AdaptiveDifferentialObservation", "EvolutionObservation", "LocusAssociation",
    "run_genesis_adaptive_differential", "run_genesis_evolution_replicates",
    "summarize_locus_associations",
]
