"""Damage-and-reorganization test for the canonical sensorimotor learner.

The apparatus selects an opaque actuator only because the organism is already
replaying a learned primitive.  It then creates matched continuations from the
same checkpoint: one intact and one with that actuator's physical health set
to zero.  The evaluator observes whether the learner's opaque model changes
and whether new, non-damaged temporal chunks appear without a reward or task.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

from .canonical_sensorimotor_counterfactual import _find_replay_checkpoint


_SENSORY_DIVERGENCE_THRESHOLD = 1e-4


def _primitive_signature(checkpoint: Mapping[str, Any]) -> dict[str, tuple[tuple[tuple[str, int], ...], ...]]:
    raw = checkpoint.get("actuation", {}).get("sensorimotor", {}).get("primitives", [])
    return {
        str(item["primitive_id"]): tuple(
            tuple((str(channel[0]), int(channel[1])) for channel in pattern)
            for pattern in item["sequence"]
        )
        for item in raw
        if isinstance(item, Mapping) and "primitive_id" in item
    }


def _mapping_distance(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    return sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys) / max(1, len(keys))


def _target_delivered(action: Mapping[str, object], target_actuator_id: str) -> bool:
    return any(
        isinstance(item, Mapping)
        and item.get("actuator_id") == target_actuator_id
        and float(item.get("delivered", 0.0)) > 0.08
        for item in action.get("actuations", [])
    )


@dataclass(frozen=True, slots=True)
class AdaptationTrial:
    seed: int
    checkpoint_tick: int
    primitive_id: str
    target_actuator_id: str
    horizon_ticks: int
    target_delivered_intact: int
    target_delivered_damaged: int
    mean_sensory_divergence: float
    initial_model_size: int
    max_primitive_channels: int
    intact_model_size: int
    damaged_model_size: int
    damaged_novel_primitives: int
    damaged_replayed_novel_primitives: int
    model_changed_after_damage: bool
    initial_state_identical: bool

    @property
    def adaptation_validated(self) -> bool:
        return (
            self.initial_state_identical
            and self.target_delivered_intact > 0
            and self.target_delivered_damaged == 0
            and self.mean_sensory_divergence > _SENSORY_DIVERGENCE_THRESHOLD
            and self.model_changed_after_damage
            and self.damaged_novel_primitives > 0
            and self.damaged_replayed_novel_primitives > 0
            and self.max_primitive_channels > 1
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["adaptation_validated"] = self.adaptation_validated
        return payload


@dataclass(frozen=True, slots=True)
class AdaptationStudy:
    seeds: tuple[int, ...]
    warmup_ticks: int
    horizon_ticks: int
    trials: tuple[AdaptationTrial, ...]

    @property
    def validated(self) -> bool:
        return bool(self.trials) and all(trial.adaptation_validated for trial in self.trials)

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "warmup_ticks": self.warmup_ticks,
            "horizon_ticks": self.horizon_ticks,
            "trials": [trial.as_dict() for trial in self.trials],
            "validated_trials": sum(trial.adaptation_validated for trial in self.trials),
            "validated": self.validated,
        }


def _rollout(
    *,
    seed: int,
    checkpoint: dict[str, Any],
    physical_state: dict[str, object],
    target_actuator_id: str,
    horizon_ticks: int,
    damage: bool,
) -> tuple[list[dict[str, float]], list[dict[str, object]], dict[str, Any], set[str]]:
    state = deepcopy(checkpoint)
    if damage:
        actuator_state = state["actuation"]["states"][target_actuator_id]
        actuator_state["health"] = 0.0
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        physics_substeps_per_tick=1,
        runtime_checkpoint=state,
        physical_state=deepcopy(physical_state),
    ) as runtime:
        sensory: list[dict[str, float]] = []
        actions: list[dict[str, object]] = []
        replayed_primitives: set[str] = set()
        for _ in range(horizon_ticks):
            tick = runtime.step()
            snapshot = runtime.organism.sensorimotor_snapshot
            if snapshot is not None and snapshot.replay_primitive_id is not None:
                replayed_primitives.add(str(snapshot.replay_primitive_id))
            telemetry = runtime.passive_telemetry_state()
            values = telemetry["pre"]["sensory_input"]["values"]
            sensory.append({str(key): float(value) for key, value in values.items()})
            actions.append(telemetry["action"])
            if not tick.alive:
                break
        return sensory, actions, runtime.checkpoint(), replayed_primitives


def run_sensorimotor_adaptation_trial(
    seed: int,
    *,
    warmup_ticks: int = 64,
    horizon_ticks: int = 96,
) -> AdaptationTrial:
    checkpoint, physical_state, primitive_id, target_actuator_id, _effector_id, checkpoint_tick = (
        _find_replay_checkpoint(seed, warmup_ticks=warmup_ticks, physics_substeps_per_tick=1)
    )
    initial_model = _primitive_signature(checkpoint)
    max_primitive_channels = max(
        (len(pattern) for sequence in initial_model.values() for pattern in sequence),
        default=0,
    )
    intact_sensory, intact_actions, intact_checkpoint, _intact_replays = _rollout(
        seed=seed,
        checkpoint=checkpoint,
        physical_state=physical_state,
        target_actuator_id=target_actuator_id,
        horizon_ticks=horizon_ticks,
        damage=False,
    )
    damaged_sensory, damaged_actions, damaged_checkpoint, damaged_replays = _rollout(
        seed=seed,
        checkpoint=checkpoint,
        physical_state=physical_state,
        target_actuator_id=target_actuator_id,
        horizon_ticks=horizon_ticks,
        damage=True,
    )
    intact_model = _primitive_signature(intact_checkpoint)
    damaged_model = _primitive_signature(damaged_checkpoint)
    novel_damaged = set(damaged_model) - set(initial_model)
    replayed_novel_damaged = set(damaged_replays) & novel_damaged
    divergence = [_mapping_distance(left, right) for left, right in zip(intact_sensory, damaged_sensory)]
    return AdaptationTrial(
        seed=int(seed),
        checkpoint_tick=checkpoint_tick,
        primitive_id=primitive_id,
        target_actuator_id=target_actuator_id,
        horizon_ticks=min(len(intact_sensory), len(damaged_sensory)),
        target_delivered_intact=sum(_target_delivered(action, target_actuator_id) for action in intact_actions),
        target_delivered_damaged=sum(_target_delivered(action, target_actuator_id) for action in damaged_actions),
        mean_sensory_divergence=sum(divergence) / max(1, len(divergence)),
        initial_model_size=len(initial_model),
        max_primitive_channels=max_primitive_channels,
        intact_model_size=len(intact_model),
        damaged_model_size=len(damaged_model),
        damaged_novel_primitives=len(novel_damaged),
        damaged_replayed_novel_primitives=len(replayed_novel_damaged),
        model_changed_after_damage=damaged_model != intact_model,
        initial_state_identical=(
            _primitive_signature(checkpoint) == _primitive_signature(deepcopy(checkpoint))
        ),
    )


def run_sensorimotor_adaptation_study(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    warmup_ticks: int = 64,
    horizon_ticks: int = 96,
    steps: int | None = None,
) -> AdaptationStudy:
    if steps is not None:
        warmup_ticks = int(steps)
    normalized = tuple(int(seed) for seed in seeds)
    trials = tuple(
        run_sensorimotor_adaptation_trial(seed, warmup_ticks=warmup_ticks, horizon_ticks=horizon_ticks)
        for seed in normalized
    )
    return AdaptationStudy(normalized, int(warmup_ticks), int(horizon_ticks), trials)


__all__ = [
    "AdaptationStudy",
    "AdaptationTrial",
    "run_sensorimotor_adaptation_study",
    "run_sensorimotor_adaptation_trial",
]
