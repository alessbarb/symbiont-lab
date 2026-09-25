"""Shadow-only test of predictive body dynamics on the opaque 3D surface.

This module deliberately does not construct an OrganismRuntime.  It exercises
the same bounded opaque receptor/effector contract through the lab apparatus,
so the result cannot change Symbiont behaviour or leak evaluator truth into
cognition.  It is a falsifiable pre-integration experiment.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Iterable

from symbiont_lab.modeling import SparseEchoStateRegressor
from symbiont_lab.physics3d.humanoid import GROUND_MATERIAL, HumanoidPhysics, apply_surface_material


def _huber(error: float) -> float:
    magnitude = abs(error)
    return 0.5 * error * error if magnitude <= 1.0 else magnitude - 0.5


@dataclass(frozen=True, slots=True)
class ShadowCondition:
    condition: str
    test_loss: float
    persistence_loss: float
    gain_over_persistence: float


@dataclass(frozen=True, slots=True)
class EmbodiedShadowSeedResult:
    seed: int
    receptor_count: int
    effector_count: int
    causal: ShadowCondition
    action_shuffled: ShadowCondition
    no_action: ShadowCondition
    causal_margin_over_best_control: float
    causal_beats_controls: bool


@dataclass(frozen=True, slots=True)
class EmbodiedSensorimotorShadowStudy:
    seeds: tuple[int, ...]
    ticks: int
    physics_substeps_per_tick: int
    reservoir_size: int
    per_seed: tuple[EmbodiedShadowSeedResult, ...]
    all_seeds_causal_beats_controls: bool
    mean_causal_margin: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _new_apparatus(pybullet, *, seed: int, time_step: float):
    del seed  # retained in the signature to keep the harness explicit/deterministic
    client_id = pybullet.connect(pybullet.DIRECT)
    if client_id < 0:
        raise RuntimeError("failed to connect to PyBullet")
    pybullet.setGravity(0.0, 0.0, -9.81, physicsClientId=client_id)
    pybullet.setTimeStep(time_step, physicsClientId=client_id)
    pybullet.setPhysicsEngineParameter(
        numSolverIterations=30,
        fixedTimeStep=time_step,
        physicsClientId=client_id,
    )
    plane_shape = pybullet.createCollisionShape(
        pybullet.GEOM_PLANE,
        planeNormal=(0.0, 0.0, 1.0),
        physicsClientId=client_id,
    )
    plane_id = pybullet.createMultiBody(
        baseMass=0.0,
        baseCollisionShapeIndex=plane_shape,
        physicsClientId=client_id,
    )
    apply_surface_material(pybullet, plane_id, -1, GROUND_MATERIAL, client_id=client_id)
    apparatus = HumanoidPhysics(pybullet, client_id)
    # Match the embodiment runtime's passive settling before observations.
    apparatus.apply_effectors({})
    for _ in range(720):
        apparatus.prepare_physics_substep()
        pybullet.stepSimulation(physicsClientId=client_id)
    return client_id, apparatus


def _action(rng: random.Random, effector_ids: tuple[str, ...]) -> list[float]:
    """Opaque bounded babbling: one paired port per joint, with sparse drive."""
    values = [0.0] * len(effector_ids)
    for index in range(0, len(values), 2):
        if rng.random() < 0.35:
            values[index + (1 if rng.random() < 0.5 else 0)] = rng.uniform(0.0, 0.45)
    return values


def _trace(*, seed: int, ticks: int, substeps: int) -> tuple[list[list[float]], list[list[float]]]:
    try:
        import pybullet
    except ImportError as exc:  # pragma: no cover - optional apparatus dependency
        raise RuntimeError("install the physics3d extra to run this study") from exc

    client_id, apparatus = _new_apparatus(pybullet, seed=seed, time_step=1.0 / 240.0)
    rng = random.Random(seed)
    observations: list[list[float]] = []
    actions: list[list[float]] = []
    try:
        for _ in range(ticks):
            observations.append(
                [
                    float(apparatus.sample_receptors()[receptor_id])
                    for receptor_id in apparatus.receptor_ids
                ]
            )
            current_action = _action(rng, apparatus.effector_ids)
            actions.append(current_action)
            apparatus.apply_effectors(dict(zip(apparatus.effector_ids, current_action)))
            for _ in range(substeps):
                apparatus.prepare_physics_substep()
                pybullet.stepSimulation(physicsClientId=client_id)
    finally:
        pybullet.disconnect(physicsClientId=client_id)
    return observations, actions


def _condition_actions(
    actions: list[list[float]], *, condition: str, seed: int
) -> list[list[float]]:
    if condition == "causal":
        return [list(row) for row in actions]
    if condition == "no_action":
        return [[0.0] * len(actions[0]) for _ in actions]
    if condition == "action_shuffled":
        shuffled = [list(row) for row in actions]
        random.Random(seed).shuffle(shuffled)
        if len(shuffled) > 1 and shuffled == actions:
            shuffled = shuffled[1:] + shuffled[:1]
        return shuffled
    raise ValueError("unknown condition")


def _run_condition(
    *,
    seed: int,
    observations: list[list[float]],
    actions: list[list[float]],
    condition: str,
    reservoir_size: int,
) -> ShadowCondition:
    conditioned = _condition_actions(actions, condition=condition, seed=seed + 31_337)
    receptor_count = len(observations[0])
    effector_count = len(conditioned[0])
    model = SparseEchoStateRegressor(
        input_dim=receptor_count + effector_count,
        output_dim=receptor_count,
        reservoir_size=reservoir_size,
        connectivity=0.15,
        spectral_scale=0.85,
        leak_rate=0.35,
        learning_rate=0.2,
        seed=seed,
        mechanism_id=f"embodied-shadow-{condition}",
    )
    split = max(32, int(0.7 * len(actions)))
    split = min(split, len(actions) - 16)
    for index in range(split):
        model.observe((*observations[index], *conditioned[index]))
        model.learn(observations[index + 1])
    losses: list[float] = []
    persistence: list[float] = []
    for index in range(split, len(actions) - 1):
        model.observe((*observations[index], *conditioned[index]))
        prediction = model.predict()
        if prediction is None:
            raise RuntimeError("shadow model produced no prediction")
        target = observations[index + 1]
        losses.extend(_huber(target[i] - prediction.value[i]) for i in range(receptor_count))
        persistence.extend(
            _huber(target[i] - observations[index][i]) for i in range(receptor_count)
        )
    loss = sum(losses) / len(losses)
    baseline = sum(persistence) / len(persistence)
    return ShadowCondition(condition, loss, baseline, baseline - loss)


def run_embodied_sensorimotor_shadow(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 160,
    physics_substeps_per_tick: int = 2,
    reservoir_size: int = 16,
) -> EmbodiedSensorimotorShadowStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    if ticks < 64:
        raise ValueError("ticks must be at least 64")
    if physics_substeps_per_tick < 1:
        raise ValueError("physics_substeps_per_tick must be positive")
    results: list[EmbodiedShadowSeedResult] = []
    for seed in seed_list:
        observations, actions = _trace(seed=seed, ticks=ticks, substeps=physics_substeps_per_tick)
        conditions = {
            name: _run_condition(
                seed=seed,
                observations=observations,
                actions=actions,
                condition=name,
                reservoir_size=reservoir_size,
            )
            for name in ("causal", "action_shuffled", "no_action")
        }
        causal = conditions["causal"]
        shuffled = conditions["action_shuffled"]
        no_action = conditions["no_action"]
        margin = causal.gain_over_persistence - max(
            shuffled.gain_over_persistence, no_action.gain_over_persistence
        )
        results.append(
            EmbodiedShadowSeedResult(
                seed=seed,
                receptor_count=len(observations[0]),
                effector_count=len(actions[0]),
                causal=causal,
                action_shuffled=shuffled,
                no_action=no_action,
                causal_margin_over_best_control=margin,
                causal_beats_controls=(
                    causal.gain_over_persistence > shuffled.gain_over_persistence
                    and causal.gain_over_persistence > no_action.gain_over_persistence
                ),
            )
        )
    return EmbodiedSensorimotorShadowStudy(
        seeds=seed_list,
        ticks=ticks,
        physics_substeps_per_tick=physics_substeps_per_tick,
        reservoir_size=reservoir_size,
        per_seed=tuple(results),
        all_seeds_causal_beats_controls=all(item.causal_beats_controls for item in results),
        mean_causal_margin=sum(item.causal_margin_over_best_control for item in results)
        / len(results),
    )


__all__ = ["EmbodiedSensorimotorShadowStudy", "run_embodied_sensorimotor_shadow"]
