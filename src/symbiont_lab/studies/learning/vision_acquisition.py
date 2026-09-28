"""Vision Acquisition v1, D1: temporal visual structure (docs/design/core/vision-acquisition-v1.md).

Evaluator-side only. For each seed a State X is made in the D1 nursery with
the vision body; every arm resumes from that same X. The organism is never
told what is visual: the target mapping is computed here from sensor sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any, Iterable

from symbiont.cognition.learning import huber_loss

BODY_KIND = "anthropomorphic-v6-vision"
ENVIRONMENT = "vision-nursery-d1-v1"
X_TICKS = 4
ARMS = ("A", "B")
MIN_VISUAL_TARGETS = 8


def _visual_receptor_ids() -> frozenset[str]:
    from symbiont_lab.physics3d.vision import visual_receptor_contract_ids

    return frozenset(visual_receptor_contract_ids())


def visual_targets(sensors: Iterable[Any], visual_ids: frozenset[str]) -> frozenset[str]:
    """Cognitive names of senses whose sources are all visual receptors."""
    return frozenset(
        sensor.cognitive_name
        for sensor in sensors
        if sensor.source_ids and all(source in visual_ids for source in sensor.source_ids)
    )


@dataclass
class _TargetTrace:
    """Prequential losses for one target over the late window."""

    learned: list[float] = field(default_factory=list)
    persist: list[float] = field(default_factory=list)
    mean: list[float] = field(default_factory=list)


@dataclass
class _Series:
    """Causal running statistics of a target's activation since first seen."""

    count: int = 0
    total: float = 0.0
    previous: float | None = None


def score_late_window(
    ticks: Iterable[tuple[dict[str, float], dict[str, list[float]]]],
    *,
    targets: frozenset[str],
    late_start: int,
) -> dict[str, dict[str, float]]:
    """Per-target learned vs baseline Huber loss over the late window.

    ``ticks`` yields ``(activations, learned_losses_by_target)`` for every
    tick from X onward. Baselines use the same activation series and loss:
    persistence predicts the previous value, running mean the causal mean
    of all earlier values.
    """
    series: dict[str, _Series] = {}
    traces: dict[str, _TargetTrace] = {}
    for index, (activations, learned) in enumerate(ticks):
        in_window = index >= late_start
        for target in targets:
            if target not in activations:
                continue
            value = float(activations[target])
            state = series.setdefault(target, _Series())
            if in_window and state.previous is not None and learned.get(target):
                trace = traces.setdefault(target, _TargetTrace())
                trace.learned.append(sum(learned[target]) / len(learned[target]))
                trace.persist.append(huber_loss(value - state.previous))
                trace.mean.append(huber_loss(value - state.total / state.count))
            state.previous = value
            state.count += 1
            state.total += value
    return {
        target: {
            "ticks": len(trace.learned),
            "learned_loss": sum(trace.learned) / len(trace.learned),
            "persist_loss": sum(trace.persist) / len(trace.persist),
            "mean_loss": sum(trace.mean) / len(trace.mean),
        }
        for target, trace in traces.items()
        if trace.learned
    }


def summarize(per_target: dict[str, dict[str, float]], *, window: int) -> dict[str, Any]:
    """Only targets predicted through the whole late window count (§5)."""
    full = {name: row for name, row in per_target.items() if row["ticks"] == window}
    return {
        "visual_targets_with_predictors": len(full),
        "assessable": len(full) >= MIN_VISUAL_TARGETS,
        "gain_persist": (
            median(row["persist_loss"] - row["learned_loss"] for row in full.values())
            if full
            else None
        ),
        "gain_mean": (
            median(row["mean_loss"] - row["learned_loss"] for row in full.values())
            if full
            else None
        ),
    }


def _predicted_visual_targets(runtime: Any, visual_ids: frozenset[str]) -> int:
    targets = visual_targets(runtime.organism._sensory_system.sensors, visual_ids)
    graph = runtime.organism.checkpoint(advance_lineage=False)["cognitive_bridge"]["graph"]
    return sum(
        1
        for node in graph["nodes"]
        if node.get("kind") == "predictor" and node.get("predicts_node_id") in targets
    )


def make_state_x(seed: int) -> dict[str, Any]:
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    runtime = PyBulletEmbodimentRuntime(
        gui=False, seed=seed, body_kind=BODY_KIND, environment=ENVIRONMENT
    )
    try:
        for _ in range(X_TICKS):
            runtime.step(include_observability=False)
        body, tick = runtime.physical_checkpoint()
        body["symbiont_ticks"] = tick
        return {
            "organism": runtime.checkpoint(lifecycle_state="dormant"),
            "body": body,
            "visual_predictors_at_x": _predicted_visual_targets(runtime, _visual_receptor_ids()),
        }
    finally:
        runtime.close()


def run_arm(
    state_x: dict[str, Any], *, seed: int, arm: str, ticks: int, late_window: int
) -> dict[str, Any]:
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm}")
    visual_ids = _visual_receptor_ids()
    runtime = PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        body_kind=BODY_KIND,
        environment=ENVIRONMENT,
        runtime_checkpoint=state_x["organism"],
        physical_state=state_x["body"],
    )
    runtime.organism.cognitive_plasticity_ablated = arm == "B"
    try:
        rows: list[tuple[dict[str, float], dict[str, list[float]]]] = []
        targets: frozenset[str] = frozenset()
        for index in range(ticks):
            runtime.step(include_observability=True)
            result = runtime.last_organism_result
            cognition = getattr(result, "cognition", None)
            if cognition is None:
                rows.append(({}, {}))
                continue
            learned: dict[str, list[float]] = {}
            for error in cognition.prediction_errors:
                learned.setdefault(error.target_id, []).append(float(error.loss))
            rows.append((dict(cognition.activations), learned))
            if index == ticks - late_window:
                targets = visual_targets(runtime.organism._sensory_system.sensors, visual_ids)
        per_target = score_late_window(rows, targets=targets, late_start=ticks - late_window)
        return {
            "seed": seed,
            "arm": arm,
            "ticks": ticks,
            "visual_targets": len(targets),
            **summarize(per_target, window=late_window),
            "per_target": per_target,
        }
    finally:
        runtime.close()


def run_vision_acquisition_d1_study(
    *, seeds: Iterable[int], ticks: int = 2000, late_window: int = 400
) -> dict[str, Any]:
    if late_window >= ticks:
        raise ValueError("late_window must be shorter than the run")
    per_seed = []
    for seed in seeds:
        state_x = make_state_x(int(seed))
        arms = {
            arm: run_arm(state_x, seed=int(seed), arm=arm, ticks=ticks, late_window=late_window)
            for arm in ARMS
        }
        per_seed.append(
            {
                "seed": int(seed),
                "visual_predictors_at_x": state_x["visual_predictors_at_x"],
                "arms": arms,
            }
        )
    return {
        "protocol": "learning.vision-acquisition-d1",
        "body_kind": BODY_KIND,
        "environment": ENVIRONMENT,
        "ticks": ticks,
        "late_window": late_window,
        "per_seed": per_seed,
        "decision_inputs": decision_inputs(per_seed),
    }


def decision_inputs(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """§7 criteria, evaluated mechanically; interpretation stays in research/."""
    assessable = [row for row in per_seed if row["arms"]["A"]["assessable"]]

    def b_consistent(row: dict[str, Any]) -> bool:
        a, b = row["arms"]["A"], row["arms"]["B"]
        return (not b["assessable"]) or (b["gain_persist"] < a["gain_persist"])

    return {
        "assessable_seeds": [row["seed"] for row in assessable],
        "d1_assessable": len(assessable) >= 2,
        "c2_utility": bool(assessable)
        and all(
            row["arms"]["A"]["gain_persist"] > 0 and row["arms"]["A"]["gain_mean"] > 0
            for row in assessable
        ),
        "c3_novelty": all(row["visual_predictors_at_x"] == 0 for row in assessable),
        "c4_acquisition_not_sensors": all(b_consistent(row) for row in assessable),
    }


__all__ = [
    "ARMS",
    "BODY_KIND",
    "ENVIRONMENT",
    "MIN_VISUAL_TARGETS",
    "decision_inputs",
    "make_state_x",
    "run_arm",
    "run_vision_acquisition_d1_study",
    "score_late_window",
    "summarize",
    "visual_targets",
]
