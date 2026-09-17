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
class LocusAssociation:
    """Descriptive evaluator-side association for one inherited locus."""

    locus: str
    observations: int
    value_min: float
    value_max: float
    mean_persistence: float
    mean_selection_differential: float
    persistence_correlation: float | None
    selection_differential_correlation: float | None


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
    values_by_locus: dict[str, list[tuple[float, float, float]]] = {}
    for genome_id, loci in snapshot.genome_loci.items():
        persistence = snapshot.lineage_persistence.get(genome_id, 0.0)
        differential = snapshot.selection_differentials.get(genome_id, 0.0)
        for locus, value in loci:
            values_by_locus.setdefault(locus, []).append(
                (float(value), persistence, differential)
            )
    summaries: list[LocusAssociation] = []
    for locus, rows in sorted(values_by_locus.items()):
        values = [row[0] for row in rows]
        persistence = [row[1] for row in rows]
        differential = [row[2] for row in rows]
        summaries.append(LocusAssociation(
            locus=locus,
            observations=len(rows),
            value_min=round(min(values), 6),
            value_max=round(max(values), 6),
            mean_persistence=round(sum(persistence) / len(rows), 6),
            mean_selection_differential=round(sum(differential) / len(rows), 6),
            persistence_correlation=_correlation(values, persistence),
            selection_differential_correlation=_correlation(values, differential),
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


__all__ = [
    "EvolutionObservation", "LocusAssociation", "run_genesis_evolution_replicates",
    "summarize_locus_associations",
]
