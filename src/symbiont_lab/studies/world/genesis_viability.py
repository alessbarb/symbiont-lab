"""Genesis viability characterization.

This is observational characterization, not a survival success test. It runs
canonical clean populations and reports physical outcomes without changing
cognition or tuning World parameters.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, median
from typing import Sequence

from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.topology import HexTopology


@dataclass(frozen=True, slots=True)
class FounderViabilityResult:
    organism_id: str
    lifespan_ticks: int
    alive_at_end: bool
    death_cause: str | None
    absorbed: float
    motor_cost: float
    basal_cost: float
    basal_wear: float
    deferred_damage: float
    hazard_damage: float
    move_count: int
    hazard_exposure_count: int
    final_q: int
    final_r: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GenesisViabilitySeedResult:
    seed: int
    founders: tuple[FounderViabilityResult, ...]
    extinction_tick: int | None
    survivors: int
    deaths: int
    births: int
    median_lifespan: float
    mean_lifespan: float
    final_pairwise_distance_mean: float

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "founders": [item.as_dict() for item in self.founders],
            "extinction_tick": self.extinction_tick,
            "survivors": self.survivors,
            "deaths": self.deaths,
            "births": self.births,
            "median_lifespan": self.median_lifespan,
            "mean_lifespan": self.mean_lifespan,
            "final_pairwise_distance_mean": self.final_pairwise_distance_mean,
        }


@dataclass(frozen=True, slots=True)
class GenesisViabilityCharacterization:
    seeds: tuple[int, ...]
    steps: int
    founders_per_seed: int
    width: int
    height: int
    per_seed: tuple[GenesisViabilitySeedResult, ...]
    extinction_fraction: float
    survivor_fraction: float
    overall_median_lifespan: float
    replay_deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "study_id": "world.genesis-viability-characterization",
            "seeds": list(self.seeds),
            "steps": self.steps,
            "founders_per_seed": self.founders_per_seed,
            "width": self.width,
            "height": self.height,
            "per_seed": [item.as_dict() for item in self.per_seed],
            "extinction_fraction": self.extinction_fraction,
            "survivor_fraction": self.survivor_fraction,
            "overall_median_lifespan": self.overall_median_lifespan,
            "replay_deterministic": self.replay_deterministic,
        }


def _normalize_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    result = tuple(seeds)
    if not result or len(result) > 64 or len(set(result)) != len(result):
        raise ValueError("seeds must contain between 1 and 64 unique entries")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in result):
        raise ValueError("seeds must contain integers only")
    return result


def _pairwise_distance_mean(pop: PopulationGenesisRuntime) -> float:
    cells = [pop.state.bodies[oid].occupied_cell for oid in pop.organism_ids]
    if len(cells) < 2:
        return 0.0
    distances = [
        float(cells[i].distance(cells[j]))
        for i in range(len(cells))
        for j in range(i + 1, len(cells))
    ]
    return mean(distances) if distances else 0.0


def _run_seed(
    seed: int,
    *,
    steps: int,
    founders: int,
    width: int,
    height: int,
) -> GenesisViabilitySeedResult:
    topology = HexTopology(width=width, height=height)
    ids = tuple(f"founder-{index}" for index in range(founders))
    cells = founder_placement(seed, topology, founders)
    pop = PopulationGenesisRuntime(
        organism_ids=ids,
        world_seed=seed,
        ground_truth=build_ground_truth(),
        topology=topology,
        start_cells=cells,
        movement_enabled=True,
        experimental_clean=True,
    )
    pop.assert_experimental_boundary()
    pop.run(steps)

    balances: dict[str, list[object]] = {oid: [] for oid in ids}
    death_events: dict[str, object] = {}
    move_counts = {oid: 0 for oid in ids}
    hazard_counts = {oid: 0 for oid in ids}
    births = 0

    for event in pop.journal:
        if event.kind == "PHYSIOLOGY_BALANCE" and event.actor in balances:
            balances[event.actor].append(event)
        elif event.kind == "DEATH" and event.actor in balances:
            death_events[event.actor] = event
        elif event.kind == "MOVE" and event.actor in move_counts:
            move_counts[event.actor] += 1
        elif event.kind == "HAZARD_EXPOSURE" and event.actor in hazard_counts:
            hazard_counts[event.actor] += 1
        elif event.kind == "BIRTH":
            births += 1

    results: list[FounderViabilityResult] = []
    for oid in ids:
        events = balances[oid]
        death = death_events.get(oid)
        alive = pop.is_alive(oid)
        lifespan = (
            int(death.tick) + 1
            if death is not None
            else min(steps, len(events))
        )
        sums = {
            key: sum(float(event.payload.get(key, 0.0)) for event in events)
            for key in (
                "absorbed",
                "motor_cost",
                "basal_cost",
                "basal_wear",
                "deferred_damage",
                "hazard_damage",
            )
        }
        cell = pop.state.bodies[oid].occupied_cell
        results.append(
            FounderViabilityResult(
                organism_id=oid,
                lifespan_ticks=lifespan,
                alive_at_end=alive,
                death_cause=(
                    str(death.payload.get("cause"))
                    if death is not None and death.payload.get("cause") is not None
                    else None
                ),
                absorbed=sums["absorbed"],
                motor_cost=sums["motor_cost"],
                basal_cost=sums["basal_cost"],
                basal_wear=sums["basal_wear"],
                deferred_damage=sums["deferred_damage"],
                hazard_damage=sums["hazard_damage"],
                move_count=move_counts[oid],
                hazard_exposure_count=hazard_counts[oid],
                final_q=cell.q,
                final_r=cell.r,
            )
        )

    survivors = sum(item.alive_at_end for item in results)
    extinction_tick = None
    if survivors == 0 and death_events:
        extinction_tick = max(int(event.tick) for event in death_events.values())

    lifespans = [item.lifespan_ticks for item in results]
    return GenesisViabilitySeedResult(
        seed=seed,
        founders=tuple(results),
        extinction_tick=extinction_tick,
        survivors=survivors,
        deaths=founders - survivors,
        births=births,
        median_lifespan=float(median(lifespans)),
        mean_lifespan=float(mean(lifespans)),
        final_pairwise_distance_mean=_pairwise_distance_mean(pop),
    )


def run_genesis_viability_characterization(
    *,
    seeds: Sequence[int] = (101, 127, 149, 173, 211, 257, 307, 353, 401, 457),
    steps: int = 600,
    founders: int = 8,
    width: int = 8,
    height: int = 8,
) -> GenesisViabilityCharacterization:
    normalized = _normalize_seeds(seeds)
    if steps < 1 or steps > 100_000:
        raise ValueError("steps must be within [1,100000]")
    if founders < 1 or founders > width * height:
        raise ValueError("founders must fit within topology")
    if width < 1 or height < 1:
        raise ValueError("world dimensions must be positive")

    results = tuple(
        _run_seed(seed, steps=steps, founders=founders, width=width, height=height)
        for seed in normalized
    )
    replay = tuple(
        _run_seed(seed, steps=steps, founders=founders, width=width, height=height)
        for seed in normalized
    )

    all_founders = [founder for seed_result in results for founder in seed_result.founders]
    extinction_fraction = (
        sum(result.extinction_tick is not None for result in results) / len(results)
    )
    survivor_fraction = (
        sum(founder.alive_at_end for founder in all_founders) / len(all_founders)
    )
    overall_median = float(median([founder.lifespan_ticks for founder in all_founders]))

    return GenesisViabilityCharacterization(
        seeds=normalized,
        steps=steps,
        founders_per_seed=founders,
        width=width,
        height=height,
        per_seed=results,
        extinction_fraction=extinction_fraction,
        survivor_fraction=survivor_fraction,
        overall_median_lifespan=overall_median,
        replay_deterministic=results == replay,
    )


__all__ = [
    "FounderViabilityResult",
    "GenesisViabilitySeedResult",
    "GenesisViabilityCharacterization",
    "run_genesis_viability_characterization",
]
