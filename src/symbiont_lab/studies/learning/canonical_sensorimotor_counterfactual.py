"""Counterfactual actuator interventions on discovered motor primitives.

The organism is allowed to discover and replay a primitive first.  Two normal
twins and one intervention twin then start from the same organism checkpoint
and physical checkpoint.  The intervention changes only the physical mapping:
one opaque actuator implicated by the replay is forced to zero.  The learner
and cognitive state are never edited by the evaluator.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

_SENSORY_DIVERGENCE_THRESHOLD = 1e-4
_PHYSICAL_DIVERGENCE_THRESHOLD = 1e-5


@dataclass(frozen=True, slots=True)
class CounterfactualReplayTrial:
    seed: int
    checkpoint_tick: int
    primitive_id: str
    target_actuator_id: str
    target_effector_id: str
    horizon_ticks: int
    normal_replay_error: float
    target_action_ticks: int
    mean_sensory_divergence: float
    peak_sensory_divergence: float
    mean_physical_divergence: float
    peak_physical_divergence: float
    initial_state_identical: bool

    @property
    def intervention_validated(self) -> bool:
        return (
            self.initial_state_identical
            and self.normal_replay_error <= _SENSORY_DIVERGENCE_THRESHOLD
            and self.target_action_ticks > 0
            and self.mean_sensory_divergence > _SENSORY_DIVERGENCE_THRESHOLD
            and self.mean_physical_divergence > _PHYSICAL_DIVERGENCE_THRESHOLD
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["intervention_validated"] = self.intervention_validated
        return payload


@dataclass(frozen=True, slots=True)
class CounterfactualReplayStudy:
    seeds: tuple[int, ...]
    warmup_ticks: int
    horizon_ticks: int
    trials: tuple[CounterfactualReplayTrial, ...]

    @property
    def validated_trials(self) -> int:
        return sum(trial.intervention_validated for trial in self.trials)

    @property
    def validated(self) -> bool:
        return bool(self.trials) and self.validated_trials == len(self.trials)

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "warmup_ticks": self.warmup_ticks,
            "horizon_ticks": self.horizon_ticks,
            "trials": [trial.as_dict() for trial in self.trials],
            "validated_trials": self.validated_trials,
            "validated": self.validated,
        }


def _state_digest(*payloads: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payloads,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _find_replay_checkpoint(
    seed: int,
    *,
    warmup_ticks: int,
    physics_substeps_per_tick: int,
) -> tuple[dict[str, Any], dict[str, object], str, str, str, int]:
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        physics_substeps_per_tick=physics_substeps_per_tick,
    ) as runtime:
        for _ in range(warmup_ticks):
            tick = runtime.step()
            snapshot = runtime.organism.sensorimotor_snapshot
            if not (
                snapshot is not None
                and snapshot.replay_active
                and snapshot.replay_primitive_id is not None
                and snapshot.cognitive_primitives > 0
            ):
                continue

            checkpoint = runtime.checkpoint()
            physical_state, physical_tick = runtime.physical_checkpoint()
            if physical_tick != tick.tick:
                raise RuntimeError("organism and physical checkpoints are misaligned")
            sensorimotor = checkpoint["actuation"]["sensorimotor"]
            primitive_id = str(snapshot.replay_primitive_id)
            primitive = next(
                item for item in sensorimotor["primitives"] if item["primitive_id"] == primitive_id
            )
            sequence = primitive["sequence"]
            replay_step = int(sensorimotor["replay_step"])
            pattern = sequence[min(replay_step, len(sequence) - 1)]
            target_actuator_id, _level = max(
                pattern,
                key=lambda item: (int(item[1]), str(item[0])),
            )
            target_effector_id = runtime._actuator_to_effector[target_actuator_id]
            return (
                deepcopy(checkpoint),
                deepcopy(physical_state),
                primitive_id,
                str(target_actuator_id),
                str(target_effector_id),
                tick.tick,
            )
    raise RuntimeError(
        f"seed {seed} did not reach a cognitive primitive replay within {warmup_ticks} ticks"
    )


def _rollout(
    *,
    seed: int,
    checkpoint: dict[str, Any],
    physical_state: dict[str, object],
    target_effector_id: str,
    horizon_ticks: int,
    intervene: bool,
    physics_substeps_per_tick: int,
) -> tuple[list[dict[str, float]], list[tuple[float, float, float]], list[dict[str, object]]]:
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        physics_substeps_per_tick=physics_substeps_per_tick,
        runtime_checkpoint=deepcopy(checkpoint),
        physical_state=deepcopy(physical_state),
    ) as runtime:
        original_apply = runtime.apparatus.apply_effectors
        if intervene:

            def masked_apply(values):
                masked = dict(values)
                masked[target_effector_id] = 0.0
                return original_apply(masked)

            runtime.apparatus.apply_effectors = masked_apply

        sensory: list[dict[str, float]] = []
        positions: list[tuple[float, float, float]] = []
        actions: list[dict[str, object]] = []
        for _ in range(horizon_ticks):
            tick = runtime.step()
            telemetry = runtime.passive_telemetry_state()
            sensory_values = telemetry["pre"]["sensory_input"]["values"]
            sensory.append({str(key): float(value) for key, value in sensory_values.items()})
            positions.append(tick.base_position)
            actions.append(telemetry["action"])
            if not tick.alive:
                break
        return sensory, positions, actions


def _mapping_distance(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    return sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys) / max(1, len(keys))


def _position_distance(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    return sum((left[index] - right[index]) ** 2 for index in range(3)) ** 0.5


def _target_delivered(action: Mapping[str, object], target_actuator_id: str) -> bool:
    actuations = action.get("actuations", [])
    return any(
        isinstance(item, Mapping)
        and item.get("actuator_id") == target_actuator_id
        and float(item.get("delivered", 0.0)) > 0.08
        for item in actuations
    )


def run_counterfactual_replay_trial(
    seed: int,
    *,
    warmup_ticks: int = 64,
    horizon_ticks: int = 8,
    physics_substeps_per_tick: int = 1,
) -> CounterfactualReplayTrial:
    if warmup_ticks < 1 or horizon_ticks < 1 or physics_substeps_per_tick < 1:
        raise ValueError("warmup_ticks, horizon_ticks and substeps must be positive")
    (
        checkpoint,
        physical_state,
        primitive_id,
        target_actuator_id,
        target_effector_id,
        checkpoint_tick,
    ) = _find_replay_checkpoint(
        seed,
        warmup_ticks=warmup_ticks,
        physics_substeps_per_tick=physics_substeps_per_tick,
    )
    initial_digest = _state_digest(checkpoint, physical_state)
    normal_a, positions_a, actions_a = _rollout(
        seed=seed,
        checkpoint=checkpoint,
        physical_state=physical_state,
        target_effector_id=target_effector_id,
        horizon_ticks=horizon_ticks,
        intervene=False,
        physics_substeps_per_tick=physics_substeps_per_tick,
    )
    normal_b, positions_b, _actions_b = _rollout(
        seed=seed,
        checkpoint=checkpoint,
        physical_state=physical_state,
        target_effector_id=target_effector_id,
        horizon_ticks=horizon_ticks,
        intervene=False,
        physics_substeps_per_tick=physics_substeps_per_tick,
    )
    intervention, positions_i, _actions_i = _rollout(
        seed=seed,
        checkpoint=checkpoint,
        physical_state=physical_state,
        target_effector_id=target_effector_id,
        horizon_ticks=horizon_ticks,
        intervene=True,
        physics_substeps_per_tick=physics_substeps_per_tick,
    )
    normal_replay_error = max(
        (_mapping_distance(left, right) for left, right in zip(normal_a, normal_b)),
        default=0.0,
    )
    sensory_divergences = [
        _mapping_distance(left, right) for left, right in zip(normal_a, intervention)
    ]
    physical_divergences = [
        _position_distance(left, right) for left, right in zip(positions_a, positions_i)
    ]
    return CounterfactualReplayTrial(
        seed=int(seed),
        checkpoint_tick=checkpoint_tick,
        primitive_id=primitive_id,
        target_actuator_id=target_actuator_id,
        target_effector_id=target_effector_id,
        horizon_ticks=min(len(normal_a), len(intervention)),
        normal_replay_error=normal_replay_error,
        target_action_ticks=sum(
            _target_delivered(action, target_actuator_id) for action in actions_a
        ),
        mean_sensory_divergence=sum(sensory_divergences) / max(1, len(sensory_divergences)),
        peak_sensory_divergence=max(sensory_divergences, default=0.0),
        mean_physical_divergence=sum(physical_divergences) / max(1, len(physical_divergences)),
        peak_physical_divergence=max(physical_divergences, default=0.0),
        initial_state_identical=(initial_digest == _state_digest(checkpoint, physical_state)),
    )


def run_counterfactual_replay_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    warmup_ticks: int = 64,
    horizon_ticks: int = 8,
    physics_substeps_per_tick: int = 1,
    steps: int | None = None,
) -> CounterfactualReplayStudy:
    if steps is not None:
        # The generic declarative runner uses ``steps`` for the discovery
        # budget.  The short counterfactual horizon is deliberately fixed by
        # this protocol's preregistration.
        warmup_ticks = int(steps)
    normalized_seeds = tuple(int(seed) for seed in seeds)
    trials = tuple(
        run_counterfactual_replay_trial(
            seed,
            warmup_ticks=warmup_ticks,
            horizon_ticks=horizon_ticks,
            physics_substeps_per_tick=physics_substeps_per_tick,
        )
        for seed in normalized_seeds
    )
    return CounterfactualReplayStudy(
        seeds=normalized_seeds,
        warmup_ticks=int(warmup_ticks),
        horizon_ticks=int(horizon_ticks),
        trials=trials,
    )


__all__ = [
    "CounterfactualReplayStudy",
    "CounterfactualReplayTrial",
    "run_counterfactual_replay_study",
    "run_counterfactual_replay_trial",
]
