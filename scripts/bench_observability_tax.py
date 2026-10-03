#!/usr/bin/env python3
"""Measure current observability tax without turning timing into a CI assertion.

P0 records the cost delta between a headless matched run and one that exercises
the passive observer surface.  P1 should reduce this delta while the deterministic
performance gate keeps both runs causally identical.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time

from lab.studies.learning.agency_acquisition_body import CausalBody, build_subject
from symbiont.core.orchestration.runtime import OrganismRuntime


def _subject(seed: int) -> tuple[OrganismRuntime, CausalBody]:
    body = CausalBody(actuator_count=4, seed=seed)
    runtime = build_subject(
        body,
        organism_id=f"observability-benchmark-{seed}",
        factorized_effects=True,
    )
    return runtime, body


def _observe(runtime: OrganismRuntime) -> None:
    _ = runtime.state_hash()
    _ = runtime.sensorimotor_snapshot
    _ = runtime.sensorimotor_competence_candidates
    _ = runtime.sensorimotor_competence_episodes
    _ = runtime.available_motor_competence_ids
    _ = runtime.body_schema.export_representation(current_tick=runtime.tick_count)
    _ = tuple(runtime._action_domain.acquisition.provenance.events())


def _run(*, ticks: int, seed: int, observed: bool) -> dict[str, object]:
    runtime, body = _subject(seed)

    # Fixed warm-up avoids timing object construction and first-import effects.
    warmup = min(100, max(10, ticks // 10))
    for _ in range(warmup):
        runtime.tick(include_observability=observed)
        body.advance(runtime.last_actuations)

    start_hash = runtime.state_hash()
    started = time.perf_counter()
    for _ in range(ticks):
        runtime.tick(include_observability=observed)
        body.advance(runtime.last_actuations)
    elapsed = time.perf_counter() - started

    return {
        "mode": "observer_on" if observed else "observer_off",
        "ticks": ticks,
        "elapsed_s": elapsed,
        "ms_per_tick": elapsed * 1000.0 / ticks,
        "ticks_per_s": ticks / elapsed,
        "start_hash": start_hash,
        "end_hash": runtime.state_hash(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=500)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=127)
    args = parser.parse_args()

    if args.ticks <= 0 or args.repeats <= 0:
        parser.error("--ticks and --repeats must be positive")

    off = []
    on = []
    for repeat in range(args.repeats):
        # Alternate order to reduce systematic warm-cache/thermal bias.
        modes = (False, True) if repeat % 2 == 0 else (True, False)
        for observed in modes:
            sample = _run(ticks=args.ticks, seed=args.seed, observed=observed)
            (on if observed else off).append(sample)

    off_ms = [float(row["ms_per_tick"]) for row in off]
    on_ms = [float(row["ms_per_tick"]) for row in on]
    off_median = statistics.median(off_ms)
    on_median = statistics.median(on_ms)
    tax_ms = on_median - off_median
    tax_pct = (tax_ms / off_median * 100.0) if off_median else 0.0
    paired_tax_ms = [
        float(right["ms_per_tick"]) - float(left["ms_per_tick"])
        for left, right in zip(off, on, strict=True)
    ]

    report = {
        "seed": args.seed,
        "ticks": args.ticks,
        "repeats": args.repeats,
        "observer_off_ms_per_tick_median": off_median,
        "observer_on_ms_per_tick_median": on_median,
        "observability_tax_ms_per_tick": tax_ms,
        "observability_tax_percent": tax_pct,
        "paired_tax_ms_per_tick": paired_tax_ms,
        "paired_tax_ms_per_tick_median": statistics.median(paired_tax_ms),
        "observer_off_samples": off,
        "observer_on_samples": on,
        "note": (
            "Timing is evidence, not a deterministic test. "
            "Use tests/experimental_integrity/test_performance_optimization_gate.py "
            "for causal equivalence."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
