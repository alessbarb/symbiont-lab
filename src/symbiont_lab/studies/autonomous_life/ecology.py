"""Evaluator-owned factorial studies for Genesis ecological emergence.

This module varies apparatus conditions only.  Organisms receive the same
opaque resource surfaces and never receive the condition label, metrics, or
the identity of the experimental arm.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from .genesis import build_genesis_harness
from .harness import HarnessConfig


DEFAULT_RESOURCE_PROFILES: tuple[tuple[float, float, float, float], ...] = (
    (0.30, 0.50, 0.70, 0.10),
    (0.10, 1.00, 1.40, 0.35),
    (0.02, 2.00, 1.00, 0.80),
)


@dataclass(frozen=True, slots=True)
class EcologyObservation:
    """Bounded post-run evidence for one apparatus condition and seed."""

    seed: int
    social_enabled: bool
    births: int
    deaths: int
    final_population: int
    mean_population: float | None
    niche_overlap: float | None
    homeostatic_rescue_events: int
    offspring_viability: float | None
    genetic_diversity: int
    extinct_genomes: int
    dominant_resource_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class EcologyReplayResult:
    """Replay-safe, identity-independent strategy evidence."""

    seed: int
    strategy_signature: tuple[tuple[float, ...], ...]
    replay_signature: tuple[tuple[float, ...], ...]
    late_strategy_signature: tuple[tuple[float, ...], ...]
    replay_late_strategy_signature: tuple[tuple[float, ...], ...]
    replay_equal: bool
    distinct_strategy_count: int
    late_distinct_strategy_count: int
    niche_overlap: float | None


def _strategy_signature(trace: object, *, start_tick: int = 1) -> tuple[tuple[float, ...], ...]:
    """Canonicalize acquisition strategy without relying on generated IDs."""
    observations = [item for item in trace.observations if item.tick >= start_tick]
    resource_ids = tuple(sorted({item.resource_id for item in observations
                                  if item.resource_id is not None}))
    by_subject: dict[str, dict[str, float]] = {}
    for item in observations:
        if item.resource_id is not None and item.resource_amount is not None:
            resources = by_subject.setdefault(item.organism_id, {})
            resources[item.resource_id] = resources.get(item.resource_id, 0.0) + max(0.0, item.resource_amount)
    vectors: list[tuple[float, ...]] = []
    for resources in by_subject.values():
        total = sum(resources.values())
        if total <= 0.0:
            continue
        vectors.append(tuple(round(resources.get(resource_id, 0.0) / total, 5)
                            for resource_id in resource_ids))
    return tuple(sorted(vectors))


def run_genesis_ecology_replay(
    config: HarnessConfig | None = None,
    *,
    seed: int = 7,
    social_enabled: bool = True,
    resource_profiles: tuple[tuple[float, float, float, float], ...] = DEFAULT_RESOURCE_PROFILES,
) -> EcologyReplayResult:
    """Replay one predeclared habitat and compare identity-independent strategies.

    UUIDs and evaluator labels are intentionally excluded.  A strategy is a
    normalized resource-acquisition vector; multiplicity is retained so the
    result can show both replay and differentiation.
    """
    selected = config or HarnessConfig(
        population=8, generations=1, ticks=256,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    first = build_genesis_harness(
        replace(selected, seed=seed), social_enabled=social_enabled,
        resource_profiles=resource_profiles,
    ).run()
    replay = build_genesis_harness(
        replace(selected, seed=seed), social_enabled=social_enabled,
        resource_profiles=resource_profiles,
    ).run()
    signature = _strategy_signature(first)
    replay_signature = _strategy_signature(replay)
    late_start = selected.ticks // 2 + 1
    late_signature = _strategy_signature(first, start_tick=late_start)
    replay_late_signature = _strategy_signature(replay, start_tick=late_start)
    return EcologyReplayResult(
        seed=seed,
        strategy_signature=signature,
        replay_signature=replay_signature,
        late_strategy_signature=late_signature,
        replay_late_strategy_signature=replay_late_signature,
        replay_equal=(signature == replay_signature
                      and late_signature == replay_late_signature),
        distinct_strategy_count=len(set(signature)),
        late_distinct_strategy_count=len(set(late_signature)),
        niche_overlap=first.metrics().niche_overlap,
    )


def _dominant_resource_counts(
    resource_use_by_subject: dict[str, dict[str, float]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for resources in resource_use_by_subject.values():
        if resources:
            dominant = max(resources, key=lambda resource: (resources[resource], resource))
            counts[dominant] += 1
    return dict(sorted(counts.items()))


def run_genesis_ecology_factorial(
    config: HarnessConfig | None = None,
    *,
    seeds: tuple[int, ...] = (7, 11, 19),
    social_conditions: tuple[bool, ...] = (False, True),
    resource_profiles: tuple[tuple[float, float, float, float], ...] = DEFAULT_RESOURCE_PROFILES,
) -> tuple[EcologyObservation, ...]:
    """Run independent Genesis ecological conditions without collapsing runs.

    The returned values are descriptive apparatus measurements.  They are not
    made available to any organism and do not define an organism reward.
    """
    if not seeds or len(seeds) > 64 or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must contain 1 to 64 unique values")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be integers")
    if not social_conditions or len(set(social_conditions)) != len(social_conditions):
        raise ValueError("social_conditions must contain unique boolean conditions")
    if any(not isinstance(condition, bool) for condition in social_conditions):
        raise ValueError("social_conditions must contain booleans")

    selected = config or HarnessConfig(
        population=8, generations=1, ticks=256,
        checkpoint_interval=64, random_checkpoint_count=0,
    )
    observations: list[EcologyObservation] = []
    for seed in seeds:
        for social_enabled in social_conditions:
            trace = build_genesis_harness(
                replace(selected, seed=seed),
                social_enabled=social_enabled,
                resource_profiles=resource_profiles,
            ).run()
            metrics = trace.metrics()
            evolutionary = trace.evolutionary[-1] if trace.evolutionary else None
            observations.append(EcologyObservation(
                seed=seed,
                social_enabled=social_enabled,
                births=metrics.births,
                deaths=metrics.deaths,
                final_population=metrics.final_population,
                mean_population=metrics.mean_population,
                niche_overlap=metrics.niche_overlap,
                homeostatic_rescue_events=metrics.homeostatic_rescue_events,
                offspring_viability=(
                    evolutionary.offspring_viability if evolutionary is not None else None
                ),
                genetic_diversity=(evolutionary.genetic_diversity if evolutionary is not None else 0),
                extinct_genomes=(len(evolutionary.extinct_genomes) if evolutionary is not None else 0),
                dominant_resource_counts=_dominant_resource_counts(
                    metrics.resource_use_by_subject
                ),
            ))
    return tuple(observations)


__all__ = [
    "DEFAULT_RESOURCE_PROFILES",
    "EcologyObservation",
    "EcologyReplayResult",
    "run_genesis_ecology_replay",
    "run_genesis_ecology_factorial",
]
