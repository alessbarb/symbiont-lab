#!/usr/bin/env python3
"""Canonical reproducible tick benchmark (L6.9.1 — perf phase, measure only).

Fixed seed, fixed genome, fixed (generously energy-provisioned) body, no
World — ticks OrganismRuntime directly. Reports ticks/s, ms/tick, and peak
RSS delta, for 1/10/100 organisms and a configurable tick budget. This is
the baseline every later optimization in the perf phase must reproduce
losslessly (L6.9.8: state_hash equivalence, not just speed).

Usage:
    python scripts/bench_organism_tick.py
    python scripts/bench_organism_tick.py --organisms 1 10 100 --ticks 2000
"""

from __future__ import annotations

import argparse
import gc
import json
import resource
import time

from symbiont.core.physiology import LivingBodyState
from symbiont.core.runtime import OrganismDeadError, OrganismRuntime

from symbiont import __version__ as symbiont_version
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.limits import KernelLimits

_SEED = 7


def _base_genome():
    version = tuple(int(part) for part in (symbiont_version.split(".") + ["0", "0"])[:3])
    return load_base_genome(
        kernel_limits=KernelLimits(),
        running_version=version,
    )


def make_organism(organism_id: str, genome) -> OrganismRuntime:
    # Generously provisioned so the organism survives the full tick budget —
    # the benchmark measures tick cost, not lifespan.
    body = LivingBodyState(energy_reserve=1_000_000.0, max_energy=1_000_000.0)
    return OrganismRuntime(
        organism_id=organism_id,
        genome=genome,
        actuation_enabled=True,
        actuator_constitution=derive_actuator_constitution(
            8,
            physical_contract="benchmark-body-v2",
        ),
        bootstrap_semantic_senses=True,
        discover_senses=False,
        min_samples=1,
        investigate_ticks=0,
        living_body_state=body,
    )


def run(n_organisms: int, n_ticks: int, *, seed: int = _SEED) -> dict[str, object]:
    genome = _base_genome()
    organisms = [make_organism(f"bench-{seed}-{i}", genome) for i in range(n_organisms)]

    gc.collect()
    gc.disable()
    rss_before_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    ticks_completed = 0
    deaths = 0
    t0 = time.perf_counter()
    for _ in range(n_ticks):
        for organism in organisms:
            try:
                organism.tick()
                ticks_completed += 1
            except OrganismDeadError:
                deaths += 1
    elapsed = time.perf_counter() - t0
    rss_after_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    gc.enable()

    return {
        "organisms": n_organisms,
        "ticks_requested": n_ticks * n_organisms,
        "ticks_completed": ticks_completed,
        "deaths": deaths,
        "wall_seconds": round(elapsed, 4),
        "ticks_per_second": round(ticks_completed / elapsed, 1) if elapsed > 0 else None,
        "ms_per_tick": round(elapsed / ticks_completed * 1000, 4) if ticks_completed else None,
        "peak_rss_kb": rss_after_kb,
        "peak_rss_delta_kb": rss_after_kb - rss_before_kb,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organisms", type=int, nargs="+", default=[1, 10, 100])
    parser.add_argument("--ticks", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=_SEED)
    args = parser.parse_args()

    results = [run(n, args.ticks, seed=args.seed) for n in args.organisms]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
