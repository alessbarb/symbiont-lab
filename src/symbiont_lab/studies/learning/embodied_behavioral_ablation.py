from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime


_MOTOR_PREFIX = "readout_motor:"
_PRIMITIVE_PREFIX = "readout_primitive:"


@dataclass(frozen=True, slots=True)
class BehavioralAblationCondition:
    condition: str
    ticks_completed: int
    alive: bool
    displacement_delta: float
    resource_progress_delta: float
    cognition_motor_ticks: int
    mixed_motor_ticks: int
    primitive_motor_ticks: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BehavioralAblationTrial:
    seed: int
    warmup_ticks: int
    trigger_found: bool
    trigger_reason: str
    lesioned_edges: int
    normal: BehavioralAblationCondition | None
    lesion: BehavioralAblationCondition | None
    displacement_effect: float | None
    resource_progress_effect: float | None

    @property
    def causally_testable(self) -> bool:
        return (
            self.trigger_found
            and self.normal is not None
            and self.lesion is not None
            and self.lesioned_edges > 0
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["causally_testable"] = self.causally_testable
        return payload


@dataclass(frozen=True, slots=True)
class BehavioralAblationStudy:
    seeds: tuple[int, ...]
    trials: tuple[BehavioralAblationTrial, ...]

    @property
    def testable_trials(self) -> int:
        return sum(trial.causally_testable for trial in self.trials)

    def as_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "trials": [trial.as_dict() for trial in self.trials],
            "testable_trials": self.testable_trials,
        }


def _freeze_cognitive_learning(checkpoint: dict[str, Any]) -> None:
    bridge = checkpoint.get("cognitive_bridge")
    if not isinstance(bridge, dict):
        raise ValueError("checkpoint has no cognitive bridge")
    safety = bridge.get("safety_state")
    if not isinstance(safety, dict):
        safety = {"consecutive_failures": 0, "frozen": True}
        bridge["safety_state"] = safety
    else:
        safety["frozen"] = True


def _lesion_cognitive_motor_outputs(checkpoint: dict[str, Any]) -> int:
    """Remove only learned graph edges feeding cognitive motor outputs.

    Motor/primitive readout nodes, actuator constitution, sensorimotor learner,
    physiology, sensory state and all other cognitive structure are preserved.
    """
    bridge = checkpoint.get("cognitive_bridge")
    if not isinstance(bridge, dict):
        return 0
    graph = bridge.get("graph")
    if not isinstance(graph, dict):
        return 0
    raw_edges = graph.get("edges")
    if not isinstance(raw_edges, list):
        return 0

    retained: list[object] = []
    removed = 0
    for entry in raw_edges:
        if not isinstance(entry, Mapping):
            retained.append(entry)
            continue
        target_id = str(entry.get("target_id", ""))
        if target_id.startswith(_MOTOR_PREFIX) or target_id.startswith(_PRIMITIVE_PREFIX):
            removed += 1
            continue
        retained.append(entry)
    graph["edges"] = retained

    # A pending structural proposal could otherwise reconstruct a cognitive
    # motor output during a supposedly frozen lesion evaluation.
    raw_candidates = bridge.get("structural_candidates")
    if isinstance(raw_candidates, list):
        bridge["structural_candidates"] = [
            entry
            for entry in raw_candidates
            if not (
                isinstance(entry, Mapping)
                and str(entry.get("family", ""))
                in {"motor_readout", "primitive_readout"}
            )
        ]
    return removed


def _run_clone(
    *,
    seed: int,
    runtime_checkpoint: dict[str, Any],
    physical_state: dict[str, object],
    horizon_ticks: int,
    condition: str,
) -> BehavioralAblationCondition:
    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        runtime_checkpoint=runtime_checkpoint,
        physical_state=physical_state,
    ) as runtime:
        start_displacement = None
        start_progress = None
        last = None
        cognition_ticks = 0
        mixed_ticks = 0
        primitive_ticks = 0

        for _ in range(horizon_ticks):
            last = runtime.step()
            if start_displacement is None:
                start_displacement = last.displacement_from_origin
                start_progress = last.resource_progress
            origin = last.motor_origin
            cognition_ticks += int(origin == "cognition")
            mixed_ticks += int(origin == "mixed")
            primitive_ticks += int(origin == "primitive")
            if not last.alive:
                break

        if last is None:
            raise RuntimeError("behavioral ablation clone produced no ticks")
        return BehavioralAblationCondition(
            condition=condition,
            ticks_completed=last.tick,
            alive=last.alive,
            displacement_delta=(
                last.displacement_from_origin
                - float(start_displacement or 0.0)
            ),
            resource_progress_delta=(
                last.resource_progress
                - float(start_progress or 0.0)
            ),
            cognition_motor_ticks=cognition_ticks,
            mixed_motor_ticks=mixed_ticks,
            primitive_motor_ticks=primitive_ticks,
        )


def _trigger_reason(tick) -> str | None:
    if tick.motor_origin in {"cognition", "mixed"}:
        return f"motor_origin:{tick.motor_origin}"
    if tick.cognitive_motor_primitives > 0:
        return "cognitive_motor_primitive"
    return None


def _trial(
    seed: int,
    *,
    warmup_ticks: int,
    horizon_ticks: int,
) -> BehavioralAblationTrial:
    checkpoint: dict[str, Any] | None = None
    physical_state: dict[str, object] | None = None
    reason = ""

    with PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        organism_id=f"symbiont:behavioral-ablation:{seed}",
    ) as runtime:
        for _ in range(warmup_ticks):
            tick = runtime.step()
            trigger = _trigger_reason(tick)
            if trigger is not None:
                checkpoint = runtime.checkpoint()
                physical_state, physical_tick = runtime.physical_checkpoint()
                if physical_tick != runtime.tick_count:
                    raise RuntimeError("organism and physical checkpoints are not aligned")
                reason = trigger
                break
            if not tick.alive:
                break

    if checkpoint is None or physical_state is None:
        return BehavioralAblationTrial(
            seed=seed,
            warmup_ticks=warmup_ticks,
            trigger_found=False,
            trigger_reason="no_cognitive_motor_output",
            lesioned_edges=0,
            normal=None,
            lesion=None,
            displacement_effect=None,
            resource_progress_effect=None,
        )

    normal_checkpoint = deepcopy(checkpoint)
    lesion_checkpoint = deepcopy(checkpoint)
    _freeze_cognitive_learning(normal_checkpoint)
    _freeze_cognitive_learning(lesion_checkpoint)
    lesioned_edges = _lesion_cognitive_motor_outputs(lesion_checkpoint)

    normal = _run_clone(
        seed=seed,
        runtime_checkpoint=normal_checkpoint,
        physical_state=deepcopy(physical_state),
        horizon_ticks=horizon_ticks,
        condition="normal_frozen",
    )
    lesion = _run_clone(
        seed=seed,
        runtime_checkpoint=lesion_checkpoint,
        physical_state=deepcopy(physical_state),
        horizon_ticks=horizon_ticks,
        condition="motor_output_lesion_frozen",
    )

    return BehavioralAblationTrial(
        seed=seed,
        warmup_ticks=warmup_ticks,
        trigger_found=True,
        trigger_reason=reason,
        lesioned_edges=lesioned_edges,
        normal=normal,
        lesion=lesion,
        displacement_effect=normal.displacement_delta - lesion.displacement_delta,
        resource_progress_effect=(
            normal.resource_progress_delta - lesion.resource_progress_delta
        ),
    )


def run_embodied_behavioral_ablation(
    seeds: Iterable[int] = (101, 127, 149),
    *,
    ticks: int = 3000,
    horizon_ticks: int = 256,
) -> BehavioralAblationStudy:
    seed_list = tuple(seeds)
    if not seed_list:
        raise ValueError("seeds must not be empty")
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 128:
        raise ValueError("ticks must be at least 128")
    if (
        isinstance(horizon_ticks, bool)
        or not isinstance(horizon_ticks, int)
        or not 32 <= horizon_ticks <= 2048
    ):
        raise ValueError("horizon_ticks must be within [32, 2048]")

    return BehavioralAblationStudy(
        seeds=seed_list,
        trials=tuple(
            _trial(
                seed,
                warmup_ticks=ticks,
                horizon_ticks=horizon_ticks,
            )
            for seed in seed_list
        ),
    )


__all__ = [
    "BehavioralAblationCondition",
    "BehavioralAblationStudy",
    "BehavioralAblationTrial",
    "run_embodied_behavioral_ablation",
]
