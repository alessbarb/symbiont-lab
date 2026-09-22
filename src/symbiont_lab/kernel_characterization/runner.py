from __future__ import annotations

import gc
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode, TickContext
from symbiont.cognition.types import EdgeKind, NodeKind

from .config import BASELINE_KERNEL, KernelVariant, complete_kernel
from .metrics import summarize
from .pareto import pareto_frontier
from .protocols import DEFAULT_SEEDS, phases


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _graph(variant: KernelVariant) -> tuple[CognitiveGraph, tuple[str, ...]]:
    count = variant.max_nodes
    sense_count = min(4, count - 2)
    concepts = min(variant.max_concepts, max(1, count - sense_count - 1))
    state_count = count - sense_count - concepts - 1
    senses = [PlasticNode(f"sense_{i}", NodeKind.SENSE) for i in range(sense_count)]
    concepts_nodes = [PlasticNode(f"concept_{i}", NodeKind.CONCEPT) for i in range(concepts)]
    states = [PlasticNode(f"state_{i}", NodeKind.STATE) for i in range(state_count)]
    readout = PlasticNode("readout", NodeKind.READOUT)
    nodes = (*senses, *concepts_nodes, *states, readout)
    edges: list[PlasticEdge] = []
    previous = senses[0].node_id
    for node in (*concepts_nodes, *states, readout):
        edges.append(PlasticEdge(previous, node.node_id, EdgeKind.EXCITATORY, 0.25, 0.5, 0 if previous.startswith("sense_") else 1))
        previous = node.node_id
    return CognitiveGraph(nodes=nodes, edges=tuple(edges), kernel_limits=variant.limits()), tuple(item.node_id for item in senses)


def _run_seed(variant: KernelVariant, seed: int, phase_ticks: int | None) -> dict[str, Any]:
    started = time.perf_counter()
    graph, sense_ids = _graph(variant)
    previous: dict[str, float] = {}
    errors: list[float] = []
    saturation = 0
    recovery_tick: int | None = None
    tick = 0
    tracemalloc.start()
    try:
        for phase in phases(phase_ticks):
            for _ in range(phase.ticks):
                tick += 1
                regime = 1.0 if phase.name not in {"regime_change", "absence"} else -1.0
                perturbation = 0.0 if phase.name != "perturbation" else 0.35
                inputs = {
                    node_id: math.sin((seed + tick) * (index + 1) * 0.017) * regime + perturbation
                    for index, node_id in enumerate(sense_ids)
                }
                frame = graph.activate(inputs, TickContext(tick=tick), previous=previous)
                previous = dict(frame.activations)
                observed = frame.readouts.get("readout", 0.0)
                target = math.tanh(sum(inputs.values()) / max(1, len(inputs)))
                error = abs(target - observed)
                errors.append(error)
                saturation += int(abs(observed) >= 0.95)
                if phase.name == "recovery" and recovery_tick is None and error < 0.25:
                    recovery_tick = tick
        _, peak = tracemalloc.get_traced_memory()
        elapsed = time.perf_counter() - started
        payload = json.dumps({"nodes": len(graph.nodes), "edges": len(graph.edges)}, sort_keys=True).encode()
        return {
            "seed": seed,
            "max_nodes": variant.max_nodes,
            "prediction_error": sum(errors) / len(errors),
            "predictive_gain": max(0.0, errors[0] - errors[-1]),
            "adaptation_latency": float(recovery_tick or len(errors)),
            "retention": max(0.0, 1.0 - errors[-1]),
            "recovery_latency": float(recovery_tick or len(errors)),
            "nodes_used": len(graph.nodes),
            "node_utilization": len(graph.nodes) / variant.max_nodes,
            "concepts_used": sum(node.kind is NodeKind.CONCEPT for node in graph.nodes),
            "edges_used": len(graph.edges),
            "structural_churn": 0,
            "cpu_time_per_tick": elapsed / max(1, tick),
            "peak_memory": peak,
            "checkpoint_bytes": len(payload),
            "saturation_events": saturation,
            "frozen_events": 0,
            "recovery_events": int(recovery_tick is not None),
        }
    except Exception as exc:  # The failure is data in a characterization run.
        return {"seed": seed, "max_nodes": variant.max_nodes, "failure": f"{type(exc).__name__}: {exc}"}
    finally:
        tracemalloc.stop()
        gc.collect()


def _run_physics_seed(variant: KernelVariant, seed: int, phase_ticks: int | None) -> dict[str, Any]:
    """Run the same protocol against the real Physics3D apparatus.

    This is deliberately opt-in and headless. The apparatus receives only its
    normal opaque sensor surface; the variant is retained by the lab runner,
    never exposed through organism observations.
    """
    from symbiont_lab.physics3d.runtime import PyBulletEmbodimentRuntime

    started = time.perf_counter()
    errors: list[float] = []
    organism_times: list[float] = []
    try:
        with PyBulletEmbodimentRuntime(
            gui=False,
            seed=seed,
            kernel_limits=variant.limits(),
        ) as runtime:
            for phase in phases(phase_ticks):
                for _ in range(phase.ticks):
                    record = runtime.step()
                    if record.prediction_error is not None:
                        errors.append(float(record.prediction_error))
                    organism_times.append(float(record.organism_ms))
            graph = runtime.organism.cognitive_bridge.graph
            nodes_used = len(graph.nodes) if graph is not None else 0
            concepts_used = (
                sum(node.kind is NodeKind.CONCEPT for node in graph.nodes)
                if graph is not None
                else 0
            )
            edges_used = len(graph.edges) if graph is not None else 0
            checkpoint_bytes = len(json.dumps(runtime.checkpoint(), sort_keys=True).encode())
        elapsed = time.perf_counter() - started
        initial = errors[0] if errors else 0.0
        final = errors[-1] if errors else 0.0
        return {
            "seed": seed,
            "max_nodes": variant.max_nodes,
            "prediction_error": sum(errors) / len(errors) if errors else 0.0,
            "predictive_gain": max(0.0, initial - final),
            "adaptation_latency": float(len(errors)),
            "retention": max(0.0, 1.0 - final),
            "recovery_latency": float(len(errors)),
            "nodes_used": nodes_used,
            "node_utilization": nodes_used / variant.max_nodes,
            "concepts_used": concepts_used,
            "edges_used": edges_used,
            "structural_churn": 0,
            "cpu_time_per_tick": (sum(organism_times) / len(organism_times) / 1000.0) if organism_times else 0.0,
            "peak_memory": 0,
            "checkpoint_bytes": checkpoint_bytes,
            "saturation_events": 0,
            "frozen_events": 0,
            "recovery_events": int(bool(errors)),
            "wall_seconds": elapsed,
        }
    except Exception as exc:
        return {"seed": seed, "max_nodes": variant.max_nodes, "failure": f"{type(exc).__name__}: {exc}"}


def run_k1(
    variants: list[KernelVariant],
    *,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    phase_ticks: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    raw = [row for variant in variants for row in (_run_seed(variant, seed, phase_ticks) for seed in seeds)]
    grouped = [{"max_nodes": variant.max_nodes, **summarize([row for row in raw if row["max_nodes"] == variant.max_nodes])} for variant in variants]
    return raw, {"protocol": "K1-A", "variants": grouped}, pareto_frontier(raw)


def run_k1_b(
    variants: list[KernelVariant],
    *,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    phase_ticks: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    if any(variant.max_nodes < 192 for variant in variants):
        raise ValueError("K1-B Physics3D variants require at least 192 nodes")
    raw = [row for variant in variants for row in (_run_physics_seed(variant, seed, phase_ticks) for seed in seeds)]
    grouped = [{"max_nodes": variant.max_nodes, **summarize([row for row in raw if row["max_nodes"] == variant.max_nodes])} for variant in variants]
    return raw, {"protocol": "K1-B", "variants": grouped}, pareto_frontier(raw)


def write_run(
    output_dir: Path,
    variants: list[KernelVariant],
    seeds: tuple[int, ...],
    phase_ticks: int | None,
    *,
    arm: str = "k1-a",
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    if arm == "k1-a":
        raw, summary, frontier = run_k1(variants, seeds=seeds, phase_ticks=phase_ticks)
    elif arm == "k1-b":
        raw, summary, frontier = run_k1_b(variants, seeds=seeds, phase_ticks=phase_ticks)
    else:
        raise ValueError(f"unsupported K1 arm: {arm}")
    manifest = {
        "protocol": "K1-A" if arm == "k1-a" else "K1-B",
        "protocol_version": 1,
        "arm": "abstract_synthetic" if arm == "k1-a" else "physics3d_embodied",
        "commit_sha": _git_sha(),
        "seeds": list(seeds),
        "phase_ticks": phase_ticks,
        "kernel_baseline": complete_kernel(BASELINE_KERNEL),
        "genome": {
            "kind": "synthetic_capacity_probe" if arm == "k1-a" else "genome_symbiont_physics3d_v9",
            "genome_id": None if arm == "k1-a" else "genome_symbiont_physics3d_v9",
            "note": "K1-A does not use an organism genome; K1-B uses the canonical Physics3D genome.",
            "sense_count": 4 if arm == "k1-a" else 107,
            "concept_limit": BASELINE_KERNEL.max_concepts,
        },
        "variants": [variant.as_dict() for variant in variants],
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    run_id = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    run_dir = output_dir / run_id
    run_dir.mkdir(exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (run_dir / "raw.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in raw))
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (run_dir / "pareto.json").write_text(json.dumps(frontier, indent=2, sort_keys=True) + "\n")
    report = [f"# {'K1-A' if arm == 'k1-a' else 'K1-B'} kernel characterization", "", "Preliminary screening; not evidence for a canonical limit.", "", f"Run: `{run_id}`", "", "## Pareto candidates", ""]
    report.extend(f"- {row['max_nodes']} nodes: gain={float(row['predictive_gain']):.6g}, cpu/tick={float(row['cpu_time_per_tick']):.6g}" for row in frontier)
    (run_dir / "report.md").write_text("\n".join(report) + "\n")
    return run_dir
