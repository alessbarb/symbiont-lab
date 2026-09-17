"""Evaluator-owned replicated studies for multigenerational Genesis runs."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .evolution import EvolutionarySnapshot
from .genesis import build_genesis_harness
from .harness import HarnessConfig


@dataclass(frozen=True, slots=True)
class EvolutionObservation:
    """One independent run and its final evaluator-only lineage snapshot."""

    seed: int
    snapshot: EvolutionarySnapshot


def run_genesis_evolution_replicates(
    config: HarnessConfig | None = None,
    *,
    seeds: tuple[int, ...] = (7, 11, 19),
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] | None = None,
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
        ).run()
        if not trace.evolutionary:
            raise RuntimeError("Genesis evolution run produced no evaluator snapshot")
        observations.append(EvolutionObservation(seed=seed, snapshot=trace.evolutionary[-1]))
    return tuple(observations)


__all__ = ["EvolutionObservation", "run_genesis_evolution_replicates"]
