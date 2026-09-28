"""Visual Acquisition v1, D1: temporal visual structure (docs/design/vision/visual-acquisition-v1.md).

Evaluator-side only. For each seed a State X is made in the D1 nursery with
the vision body; every arm resumes from that same X. The organism is never
told what is visual: the target mapping is computed here from sensor sources.

Two modes, so that the horizon H can never be chosen by results:

- ``report_performance=False`` (development): only feasibility per candidate
  horizon (runtime, memory, number of visual targets predicted through the
  late window, numerical stability). No loss or gain is computed.
- ``report_performance=True`` (held-out, frozen H): the preregistered
  measurement and decision inputs.
"""

from __future__ import annotations

import math
import resource
import time
from dataclasses import dataclass, field
from statistics import median
from typing import Any, Iterable, Sequence

from symbiont.cognition.learning import huber_loss
from symbiont_lab.studies.ablations import CognitiveAcquisitionAblation

PROTOCOL = "learning.visual-acquisition-v1"
BODY_KIND = "anthropomorphic-v6-vision"
ENVIRONMENT = "vision-nursery-d1-v1"
X_TICKS = 4
ARMS = ("A", "B")
ARM_B_ABLATION = CognitiveAcquisitionAblation(plasticity_enabled=False, predictor_promotion=False)
MIN_VISUAL_TARGETS = 8
CANDIDATE_HORIZONS = (500, 1000, 1500, 2000)
LATE_WINDOW = 400

# Failure taxonomy (preregistration §8).
PASSED = "passed"
NOT_ASSESSABLE = "not_assessable"
PREEXISTING = "preexisting_structure_at_X"
NO_UTILITY = "no_predictive_utility"
NOT_ISOLATED = "acquisition_not_isolated"


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
    learned: list[float] = field(default_factory=list)
    persist: list[float] = field(default_factory=list)
    mean: list[float] = field(default_factory=list)
    zero: list[float] = field(default_factory=list)


@dataclass
class _Series:
    count: int = 0
    total: float = 0.0
    previous: float | None = None


Row = tuple[dict[str, float], dict[str, list[float]]]


def score_window(
    rows: Sequence[Row], *, targets: frozenset[str], start: int, stop: int
) -> dict[str, dict[str, float]]:
    """Per-target prequential losses over ``rows[start:stop]``.

    Baselines use the same activation series and Huber loss: persistence
    (previous value, the change-free baseline), causal running mean of all
    earlier values since X, and zero.
    """
    series: dict[str, _Series] = {}
    traces: dict[str, _TargetTrace] = {}
    for index, (activations, learned) in enumerate(rows[:stop]):
        in_window = index >= start
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
                trace.zero.append(huber_loss(value))
            state.previous = value
            state.count += 1
            state.total += value
    return {
        target: {
            "ticks": len(trace.learned),
            "learned_loss": sum(trace.learned) / len(trace.learned),
            "persist_loss": sum(trace.persist) / len(trace.persist),
            "mean_loss": sum(trace.mean) / len(trace.mean),
            "zero_loss": sum(trace.zero) / len(trace.zero),
        }
        for target, trace in traces.items()
        if trace.learned
    }


def full_window_targets(
    per_target: dict[str, dict[str, float]], *, window: int
) -> dict[str, dict[str, float]]:
    """Only targets predicted through the whole late window count."""
    return {name: row for name, row in per_target.items() if row["ticks"] == window}


def summarize(per_target: dict[str, dict[str, float]], *, window: int) -> dict[str, Any]:
    full = full_window_targets(per_target, window=window)

    def gain(baseline: str) -> float | None:
        if not full:
            return None
        return median(row[baseline] - row["learned_loss"] for row in full.values())

    return {
        "visual_targets_with_predictors": len(full),
        "assessable": len(full) >= MIN_VISUAL_TARGETS,
        "gain_persist": gain("persist_loss"),
        "gain_mean": gain("mean_loss"),
        "gain_zero": gain("zero_loss"),
    }


def a_beats_b_on_intersection(
    a_targets: dict[str, dict[str, float]], b_targets: dict[str, dict[str, float]]
) -> dict[str, Any]:
    """§7.4: compare A and B only where both predict the same targets."""
    if len(b_targets) < MIN_VISUAL_TARGETS:
        return {"b_assessable": False, "intersection": None, "a_better": True}
    shared = sorted(set(a_targets) & set(b_targets))
    if not shared:
        return {"b_assessable": True, "intersection": 0, "a_better": False}
    a_loss = median(a_targets[name]["learned_loss"] for name in shared)
    b_loss = median(b_targets[name]["learned_loss"] for name in shared)
    return {
        "b_assessable": True,
        "intersection": len(shared),
        "a_median_learned_loss": a_loss,
        "b_median_learned_loss": b_loss,
        "a_better": a_loss < b_loss,
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
    state_x: dict[str, Any],
    *,
    seed: int,
    arm: str,
    horizons: Sequence[int],
    late_window: int,
    report_performance: bool,
) -> dict[str, Any]:
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm}")
    horizons = tuple(sorted(int(h) for h in horizons))
    if not horizons or horizons[0] <= late_window:
        raise ValueError("every horizon must exceed the late window")
    visual_ids = _visual_receptor_ids()
    runtime = PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        body_kind=BODY_KIND,
        environment=ENVIRONMENT,
        runtime_checkpoint=state_x["organism"],
        physical_state=state_x["body"],
    )
    if arm == "B":
        ARM_B_ABLATION.apply(runtime.organism)
    window_starts = {h - late_window: h for h in horizons}
    targets_at: dict[int, frozenset[str]] = {}
    elapsed_at: dict[int, float] = {}
    rss_at: dict[int, int] = {}
    rows: list[Row] = []
    started = time.perf_counter()
    try:
        for index in range(horizons[-1]):
            if index in window_starts:
                targets_at[window_starts[index]] = visual_targets(
                    runtime.organism._sensory_system.sensors, visual_ids
                )
            runtime.step(include_observability=True)
            cognition = getattr(runtime.last_organism_result, "cognition", None)
            learned: dict[str, list[float]] = {}
            activations: dict[str, float] = {}
            if cognition is not None:
                for error in cognition.prediction_errors:
                    learned.setdefault(error.target_id, []).append(float(error.loss))
                activations = dict(cognition.activations)
            rows.append((activations, learned))
            if index + 1 in horizons:
                elapsed_at[index + 1] = time.perf_counter() - started
                rss_at[index + 1] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    finally:
        runtime.close()

    per_horizon = {}
    for horizon in horizons:
        per_target = score_window(
            rows, targets=targets_at[horizon], start=horizon - late_window, stop=horizon
        )
        full = full_window_targets(per_target, window=late_window)
        feasibility = {
            "wall_s": round(elapsed_at[horizon], 1),
            "max_rss_mb": rss_at[horizon],
            "visual_targets_at_window_start": len(targets_at[horizon]),
            "visual_targets_predicted_full_window": len(full),
            "numerically_stable": all(
                math.isfinite(value) for row in full.values() for value in row.values()
            ),
        }
        entry: dict[str, Any] = {"feasibility": feasibility}
        if report_performance:
            entry["performance"] = summarize(per_target, window=late_window)
            entry["full_window_targets"] = full
        per_horizon[str(horizon)] = entry
    return {"seed": seed, "arm": arm, "horizons": per_horizon}


def run_visual_acquisition_study(
    *,
    seeds: Iterable[int],
    horizons: Sequence[int] = CANDIDATE_HORIZONS,
    late_window: int = LATE_WINDOW,
    report_performance: bool = False,
) -> dict[str, Any]:
    horizons = tuple(sorted(int(h) for h in horizons))
    if report_performance and len(horizons) != 1:
        raise ValueError("performance is reported only at a single frozen horizon")
    per_seed = []
    for seed in seeds:
        state_x = make_state_x(int(seed))
        arms = {
            arm: run_arm(
                state_x,
                seed=int(seed),
                arm=arm,
                horizons=horizons,
                late_window=late_window,
                report_performance=report_performance,
            )
            for arm in ARMS
        }
        per_seed.append(
            {
                "seed": int(seed),
                "visual_predictors_at_x": state_x["visual_predictors_at_x"],
                "arms": arms,
            }
        )
    result: dict[str, Any] = {
        "protocol": PROTOCOL,
        "body_kind": BODY_KIND,
        "environment": ENVIRONMENT,
        "arm_b_ablation": ARM_B_ABLATION.as_dict(),
        "horizons": list(horizons),
        "late_window": late_window,
        "report_performance": report_performance,
        "per_seed": per_seed,
    }
    if report_performance:
        result["decision_inputs"] = decision_inputs(per_seed, horizon=str(horizons[0]))
    return result


def decision_inputs(per_seed: list[dict[str, Any]], *, horizon: str) -> dict[str, Any]:
    """§7 criteria and §8 classification, evaluated mechanically."""
    seeds = []
    for row in per_seed:
        a = row["arms"]["A"]["horizons"][horizon]
        b = row["arms"]["B"]["horizons"][horizon]
        perf = a["performance"]
        comparison = a_beats_b_on_intersection(a["full_window_targets"], b["full_window_targets"])
        assessable = bool(perf["assessable"])
        utility = assessable and all(
            perf[key] is not None and perf[key] > 0
            for key in ("gain_persist", "gain_mean", "gain_zero")
        )
        novelty = row["visual_predictors_at_x"] == 0
        if not assessable:
            classification = NOT_ASSESSABLE
        elif not novelty:
            classification = PREEXISTING
        elif not utility:
            classification = NO_UTILITY
        elif not comparison["a_better"]:
            classification = NOT_ISOLATED
        else:
            classification = PASSED
        seeds.append(
            {
                "seed": row["seed"],
                "assessable": assessable,
                "utility": utility,
                "novelty": novelty,
                "a_vs_b": comparison,
                "classification": classification,
            }
        )
    assessable = [item for item in seeds if item["assessable"]]
    if len(assessable) < 2:
        overall = NOT_ASSESSABLE
    elif any(item["classification"] == PREEXISTING for item in assessable):
        overall = PREEXISTING
    elif any(item["classification"] == NO_UTILITY for item in assessable):
        overall = NO_UTILITY
    elif any(item["classification"] == NOT_ISOLATED for item in assessable):
        overall = NOT_ISOLATED
    else:
        overall = PASSED
    return {"per_seed": seeds, "assessable_seeds": [i["seed"] for i in assessable], "d1": overall}


__all__ = [
    "ARMS",
    "ARM_B_ABLATION",
    "BODY_KIND",
    "CANDIDATE_HORIZONS",
    "ENVIRONMENT",
    "LATE_WINDOW",
    "MIN_VISUAL_TARGETS",
    "PROTOCOL",
    "a_beats_b_on_intersection",
    "decision_inputs",
    "make_state_x",
    "run_arm",
    "run_visual_acquisition_study",
    "score_window",
    "summarize",
    "visual_targets",
]
