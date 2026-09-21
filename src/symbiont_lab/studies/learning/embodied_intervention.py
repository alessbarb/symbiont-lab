"""Causal intervention test for the opaque Physics3D sensorimotor surface.

This is still apparatus-only.  It asks a narrower question than prediction:
does removing one opaque effector after a fixed tick produce a reproducible
change in the opaque receptor trajectory, relative to an identical replay?
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Iterable

from .embodied_sensorimotor_shadow import _action, _new_apparatus


@dataclass(frozen=True, slots=True)
class InterventionSeedResult:
    seed: int
    target_effector: int
    intervention_tick: int
    replay_error: float
    mean_post_intervention_divergence: float
    peak_post_intervention_divergence: float
    intervention_detectable: bool


@dataclass(frozen=True, slots=True)
class EmbodiedInterventionStudy:
    seeds: tuple[int, ...]
    target_effectors: tuple[int, ...]
    ticks: int
    intervention_tick: int
    physics_substeps_per_tick: int
    per_seed: tuple[InterventionSeedResult, ...]
    replay_deterministic: bool
    all_interventions_detectable: bool
    mean_post_intervention_divergence: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _rollout(
    *, seed: int, actions: list[list[float]], substeps: int, intervention_tick: int | None,
    target_effector: int | None,
) -> list[list[float]]:
    try:
        import pybullet
    except ImportError as exc:  # pragma: no cover - optional apparatus dependency
        raise RuntimeError("install the physics3d extra to run this study") from exc
    client_id, apparatus = _new_apparatus(pybullet, seed=seed, time_step=1.0 / 240.0)
    observations: list[list[float]] = []
    try:
        for tick, original in enumerate(actions):
            values = list(original)
            if (
                intervention_tick is not None
                and target_effector is not None
                and tick >= intervention_tick
            ):
                values[target_effector] = 0.0
            sampled = apparatus.sample_receptors()
            observations.append([
                float(sampled[receptor_id]) for receptor_id in apparatus.receptor_ids
            ])
            apparatus.apply_effectors(dict(zip(apparatus.effector_ids, values)))
            for _ in range(substeps):
                apparatus.prepare_physics_substep()
                pybullet.stepSimulation(physicsClientId=client_id)
    finally:
        pybullet.disconnect(physicsClientId=client_id)
    return observations


def run_embodied_intervention(
    seeds: Iterable[int] = (101, 127, 149),
    *, ticks: int = 128, intervention_tick: int = 48,
    target_effectors: Iterable[int] = (0, 7, 14, 21),
    physics_substeps_per_tick: int = 2, divergence_threshold: float = 1e-4,
) -> EmbodiedInterventionStudy:
    seed_list = tuple(seeds)
    targets = tuple(target_effectors)
    if not seed_list or not targets:
        raise ValueError("seeds and target_effectors must not be empty")
    if ticks < 64 or intervention_tick < 1 or intervention_tick >= ticks - 8:
        raise ValueError("ticks/intervention_tick leave insufficient post-intervention data")
    if physics_substeps_per_tick < 1:
        raise ValueError("physics_substeps_per_tick must be positive")
    if any(index < 0 or index >= 28 for index in targets):
        raise ValueError("target_effectors must be opaque slots within [0, 27]")

    results: list[InterventionSeedResult] = []
    for seed in seed_list:
        rng = random.Random(seed)
        effector_ids = tuple(f"eff.{index}" for index in range(28))
        actions = [_action(rng, effector_ids) for _ in range(ticks)]
        baseline = _rollout(
            seed=seed, actions=actions, substeps=physics_substeps_per_tick,
            intervention_tick=None, target_effector=None,
        )
        replay = _rollout(
            seed=seed, actions=actions, substeps=physics_substeps_per_tick,
            intervention_tick=None, target_effector=None,
        )
        replay_error = sum(
            abs(a - b)
            for left, right in zip(baseline, replay)
            for a, b in zip(left, right)
        ) / max(1, (ticks * len(baseline[0])))
        for target in targets:
            intervention = _rollout(
                seed=seed, actions=actions, substeps=physics_substeps_per_tick,
                intervention_tick=intervention_tick, target_effector=target,
            )
            divergences = [
                sum(abs(a - b) for a, b in zip(base, changed)) / len(base)
                for base, changed in zip(baseline, intervention)
            ][intervention_tick:]
            results.append(InterventionSeedResult(
                seed=seed, target_effector=target, intervention_tick=intervention_tick,
                replay_error=replay_error,
                mean_post_intervention_divergence=sum(divergences) / len(divergences),
                peak_post_intervention_divergence=max(divergences),
                intervention_detectable=(
                    sum(divergences) / len(divergences) > divergence_threshold
                ),
            ))
    mean = sum(item.mean_post_intervention_divergence for item in results) / len(results)
    return EmbodiedInterventionStudy(
        seeds=seed_list, target_effectors=targets, ticks=ticks,
        intervention_tick=intervention_tick,
        physics_substeps_per_tick=physics_substeps_per_tick,
        per_seed=tuple(results),
        replay_deterministic=all(item.replay_error <= divergence_threshold for item in results),
        all_interventions_detectable=all(item.intervention_detectable for item in results),
        mean_post_intervention_divergence=mean,
    )


__all__ = ["EmbodiedInterventionStudy", "run_embodied_intervention"]
