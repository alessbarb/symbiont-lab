#!/usr/bin/env python3
"""L6.9.4: reproducible cProfile pass over the current cognitive runtime.

This intentionally profiles the current implementation without changing
organism behavior. It attaches the canonical germinal cognition to the same
kind of generously provisioned organism used by the tick benchmark and prints
both cumulative-time and self-time rankings.

Host-backed semantic sensing remains enabled by default because this tool is a
performance profiler, not an equivalence harness. Use --synthetic to remove
real host sensing when a deterministic profile shape is preferred.

Usage:
    python scripts/profile_cognitive_hotpath.py --ticks 500
    python scripts/profile_cognitive_hotpath.py --ticks 1000 --top 50 --output /tmp/cognition.prof
    python scripts/profile_cognitive_hotpath.py --synthetic
"""
from __future__ import annotations

import argparse
import cProfile
import io
import pstats

from symbiont.cognition.birth import load_base_cognition
from symbiont.cognition.limits import KernelLimits
from symbiont.core.physiology import LivingBodyState
from symbiont.core.runtime import OrganismRuntime


def make_organism(*, synthetic: bool) -> OrganismRuntime:
    limits = KernelLimits()
    genome, graph = load_base_cognition(
        kernel_limits=limits,
        running_version=(0, 80, 0),
    )
    body = LivingBodyState(
        energy_reserve=1_000_000.0,
        max_energy=1_000_000.0,
    )
    return OrganismRuntime(
        organism_id="l6.9.4-profile",
        genome=genome,
        cognitive_graph=graph,
        kernel_limits=limits,
        actuation_enabled=True,
        motor_exploration_mode="babbling",
        bootstrap_semantic_senses=not synthetic,
        discover_senses=False,
        min_samples=1,
        investigate_ticks=0,
        living_body_state=body,
    )


def _render(stats: pstats.Stats, sort_key: str, top: int) -> str:
    stream = io.StringIO()
    stats.stream = stream
    stats.sort_stats(sort_key)
    stats.print_stats(top)
    return stream.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=500)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument(
        "--output",
        help="optional cProfile dump path for snakeviz/py-spy-compatible follow-up analysis",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="disable real host semantic sensing; useful for deterministic profile shape",
    )
    args = parser.parse_args()

    organism = make_organism(synthetic=args.synthetic)
    for _ in range(args.warmup):
        organism.tick()

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(args.ticks):
        organism.tick()
    profiler.disable()

    if args.output:
        profiler.dump_stats(args.output)

    stats = pstats.Stats(profiler)
    print("=== cumulative time ===")
    print(_render(stats, "cumulative", args.top))
    print("=== self time ===")
    print(_render(stats, "tottime", args.top))


if __name__ == "__main__":
    main()
