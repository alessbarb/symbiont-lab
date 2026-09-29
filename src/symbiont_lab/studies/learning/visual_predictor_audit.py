"""EW-D1A: visual predictor formation audit (observer-side, read-only).

Explains why D1 development found only 1/4/5 visual targets predicted through
the whole late window while 143-170 visual senses existed. It traces each
stage of the organism's own predictor pipeline for visual versus non-visual
targets:

    visual sense admitted -> sense node in cognition -> shadow hypothesis
    (candidate / supported / contradicted / retired) -> promotion nominee in
    structural contention -> predictor node -> retirement

It reads internal state only; it never mutates the organism and never
computes the D1 evaluator metric (no baseline loss or gain). Counts of the
organism's own shadow statuses are mechanistic, not a performance measure.
"""

from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any, Iterable

from symbiont_lab.studies.learning.visual_acquisition import (
    BODY_KIND,
    ENVIRONMENT,
    LATE_WINDOW,
    _visual_receptor_ids,
    make_state_x,
    visual_targets,
)

PROTOCOL = "learning.visual-predictor-audit"


def _predictor_nodes(graph: Any) -> dict[str, str]:
    """predictor node id -> predicted node id."""
    return {
        node.node_id: node.predicts_node_id
        for node in graph.nodes
        if getattr(node.kind, "value", node.kind) == "predictor" and node.predicts_node_id
    }


def _sense_nodes(graph: Any) -> set[str]:
    return {
        node.node_id for node in graph.nodes if getattr(node.kind, "value", node.kind) == "sense"
    }


def snapshot(runtime: Any, visual_ids: frozenset[str]) -> dict[str, Any]:
    """Stage counts at one tick, split visual / non-visual target."""
    organism = runtime.organism
    bridge = organism._cognitive_bridge
    graph = bridge._graph
    sensors = organism._sensory_system.sensors
    visual = visual_targets(sensors, visual_ids)
    all_senses = {sensor.cognitive_name for sensor in sensors}
    sense_nodes = _sense_nodes(graph)
    graph_ids = {node.node_id for node in graph.nodes}
    shadows = bridge._predictors.shadows.values()
    shadow_status = {"visual": Counter(), "other": Counter()}
    for shadow in shadows:
        side = "visual" if shadow.target_id in visual else "other"
        shadow_status[side][shadow.status] += 1
        if shadow.promotable:
            shadow_status[side]["promotable"] += 1
    predictors = _predictor_nodes(graph)
    pending = [
        candidate_id
        for candidate_id in bridge._contention.candidates
        if candidate_id.startswith("predictor:")
    ]
    return {
        "tick": runtime.tick_count,
        "visual_senses_admitted": len(visual),
        "other_senses_admitted": len(all_senses - visual),
        "visual_senses_in_graph": len(visual & graph_ids),
        "other_senses_in_graph": len((all_senses - visual) & graph_ids),
        "sense_nodes_total": len(sense_nodes & graph_ids),
        "shadows_total": len(bridge._predictors.shadows),
        "shadow_live_limit": bridge._predictors.live_shadow_limit(bridge._kernel_limits.max_nodes),
        "shadows_visual": dict(shadow_status["visual"]),
        "shadows_other": dict(shadow_status["other"]),
        "predictors_visual": sum(1 for target in predictors.values() if target in visual),
        "predictors_other": sum(1 for target in predictors.values() if target not in visual),
        "promotion_candidates_pending": len(pending),
        "graph_nodes": len(graph.nodes),
        "max_nodes": bridge._kernel_limits.max_nodes,
        "predictor_ids": sorted(predictors),
        "predictor_targets": predictors,
        "visual_target_ids": sorted(visual),
    }


def lifespans(presence: dict[str, list[int]], *, last_tick: int) -> dict[str, Any]:
    """Summarize contiguous presence runs of predictor ids (in sampled ticks)."""
    spans = []
    ongoing = 0
    for ticks in presence.values():
        spans.append(ticks[-1] - ticks[0])
        if ticks[-1] == last_tick:
            ongoing += 1
    return {
        "count": len(spans),
        "median_span_ticks": median(spans) if spans else None,
        "max_span_ticks": max(spans) if spans else None,
        "alive_at_end": ongoing,
        "at_least_late_window": sum(1 for span in spans if span >= LATE_WINDOW),
    }


def audit_seed(seed: int, *, ticks: int, every: int) -> dict[str, Any]:
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    visual_ids = _visual_receptor_ids()
    state_x = make_state_x(seed)
    runtime = PyBulletEmbodimentRuntime(
        gui=False,
        seed=seed,
        body_kind=BODY_KIND,
        environment=ENVIRONMENT,
        runtime_checkpoint=state_x["organism"],
        physical_state=state_x["body"],
    )
    samples = []
    presence: dict[str, list[int]] = {}
    target_of: dict[str, str] = {}
    visual_seen: set[str] = set()
    visual_history: list[set[str]] = []
    try:
        for index in range(1, ticks + 1):
            runtime.step(include_observability=False)
            if index % every:
                continue
            snap = snapshot(runtime, visual_ids)
            for predictor_id in snap.pop("predictor_ids"):
                presence.setdefault(predictor_id, []).append(index)
            target_of.update(snap.pop("predictor_targets"))
            current_visual = set(snap.pop("visual_target_ids"))
            visual_seen |= current_visual
            visual_history.append(current_visual)
            samples.append(snap)
    finally:
        runtime.close()

    visual_now = visual_history[-1] if visual_history else set()
    visual_presence = {pid: t for pid, t in presence.items() if target_of[pid] in visual_seen}
    other_presence = {pid: t for pid, t in presence.items() if target_of[pid] not in visual_seen}
    churn = [
        len(previous ^ current) for previous, current in zip(visual_history, visual_history[1:])
    ]
    return {
        "seed": seed,
        "visual_predictors_at_x": state_x["visual_predictors_at_x"],
        "samples": samples,
        "visual_predictor_lifespans": lifespans(visual_presence, last_tick=ticks),
        "other_predictor_lifespans": lifespans(other_presence, last_tick=ticks),
        "visual_targets_ever": len(visual_seen),
        "visual_targets_at_end": len(visual_now),
        "visual_target_churn_per_sample": {
            "max": max(churn) if churn else 0,
            "total": sum(churn),
        },
    }


def run_visual_predictor_audit(
    *, seeds: Iterable[int], ticks: int = 2000, every: int = 50
) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "body_kind": BODY_KIND,
        "environment": ENVIRONMENT,
        "arm": "A",
        "ticks": ticks,
        "sample_every": every,
        "per_seed": [audit_seed(int(seed), ticks=ticks, every=every) for seed in seeds],
    }


__all__ = ["PROTOCOL", "lifespans", "run_visual_predictor_audit", "snapshot"]
