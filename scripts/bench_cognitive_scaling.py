#!/usr/bin/env python3
"""L6.9.4: deterministic CognitiveGraph activation scaling benchmark.

Measures the cost of the graph hot path itself, independent of host sensing,
World, PyBullet, telemetry and OrganismRuntime orchestration. Synthetic graphs
are deterministic and intentionally exceed canonical KernelLimits only inside
this benchmark apparatus so we can observe scaling before a future learned
graph ever reaches those sizes.

Usage:
    python scripts/bench_cognitive_scaling.py
    python scripts/bench_cognitive_scaling.py --nodes 32 64 128 256 512 --ticks 5000 --fan-in 4

The benchmark does not mutate production defaults or organism behavior.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import time

from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode, TickContext
from symbiont.cognition.limits import KernelLimits
from symbiont.cognition.types import EdgeKind, NodeKind


def _build_graph(node_count: int, fan_in: int) -> tuple[CognitiveGraph, dict[str, float]]:
    if node_count < 4:
        raise ValueError("node_count must be >= 4")
    if fan_in < 1:
        raise ValueError("fan_in must be >= 1")

    sense_count = max(2, min(16, node_count // 8))
    readout_count = 1
    concept_count = node_count - sense_count - readout_count
    if concept_count < 1:
        raise ValueError("node_count leaves no room for concepts")

    senses = [
        PlasticNode(node_id=f"sense_{i:04d}", kind=NodeKind.SENSE)
        for i in range(sense_count)
    ]
    concepts = [
        PlasticNode(node_id=f"concept_{i:05d}", kind=NodeKind.CONCEPT)
        for i in range(concept_count)
    ]
    readout = PlasticNode(node_id="readout_0000", kind=NodeKind.READOUT)
    nodes = tuple([*senses, *concepts, readout])

    edges: list[PlasticEdge] = []
    all_prior: list[PlasticNode] = list(senses)
    for idx, target in enumerate(concepts):
        # Deterministic bounded fan-in. Sense-origin edges may be delay=0;
        # recurrent/concept-origin edges are delay=1, matching graph invariants.
        sources = all_prior[-fan_in:] if len(all_prior) >= fan_in else all_prior
        for source in sources:
            edges.append(
                PlasticEdge(
                    source_id=source.node_id,
                    target_id=target.node_id,
                    kind=EdgeKind.EXCITATORY,
                    weight=0.25,
                    plasticity=0.5,
                    delay_ticks=0 if source.kind is NodeKind.SENSE else 1,
                )
            )
        all_prior.append(target)

    # Readout integrates the most recent concepts. Keep the same bounded fan-in.
    for source in concepts[-fan_in:]:
        edges.append(
            PlasticEdge(
                source_id=source.node_id,
                target_id=readout.node_id,
                kind=EdgeKind.EXCITATORY,
                weight=0.25,
                plasticity=0.5,
                delay_ticks=1,
            )
        )

    limits = KernelLimits(
        max_nodes=max(128, node_count),
        max_concepts=max(32, concept_count),
        max_edges=max(1024, len(edges)),
    )
    graph = CognitiveGraph(nodes=nodes, edges=tuple(edges), kernel_limits=limits)
    inputs = {
        sense.node_id: math.sin((i + 1) * 0.37)
        for i, sense in enumerate(senses)
    }
    return graph, inputs


def _run_case(node_count: int, fan_in: int, ticks: int, warmup: int) -> dict[str, object]:
    graph, inputs = _build_graph(node_count, fan_in)
    previous: dict[str, float] = {}

    for tick in range(1, warmup + 1):
        frame = graph.activate(inputs, TickContext(tick=tick), previous=previous)
        previous = dict(frame.activations)

    gc.collect()
    gc.disable()
    t0 = time.perf_counter()
    for offset in range(ticks):
        tick = warmup + offset + 1
        frame = graph.activate(inputs, TickContext(tick=tick), previous=previous)
        previous = dict(frame.activations)
    elapsed = time.perf_counter() - t0
    gc.enable()

    graph_ticks_per_second = ticks / elapsed if elapsed else float("inf")
    us_per_graph_tick = (elapsed / ticks) * 1_000_000 if ticks else 0.0
    edges = len(graph.edges)
    nodes = len(graph.nodes)
    return {
        "nodes": nodes,
        "edges": edges,
        "fan_in": fan_in,
        "ticks": ticks,
        "warmup": warmup,
        "wall_seconds": round(elapsed, 6),
        "graph_ticks_per_second": round(graph_ticks_per_second, 1),
        "us_per_graph_tick": round(us_per_graph_tick, 3),
        "node_updates_per_second": round(graph_ticks_per_second * nodes, 1),
        "edge_visits_per_second_upper_bound": round(graph_ticks_per_second * edges * 2, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nodes",
        type=int,
        nargs="+",
        default=[32, 64, 128, 256, 512, 1024],
        help="synthetic graph sizes to benchmark",
    )
    parser.add_argument("--fan-in", type=int, default=4)
    parser.add_argument("--ticks", type=int, default=5000)
    parser.add_argument("--warmup", type=int, default=200)
    args = parser.parse_args()

    results = [
        _run_case(node_count, args.fan_in, args.ticks, args.warmup)
        for node_count in args.nodes
    ]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
