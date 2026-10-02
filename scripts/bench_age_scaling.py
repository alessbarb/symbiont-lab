#!/usr/bin/env python3
"""Longitudinal cost of one developing organism at several ages (issue #279).

One organism is developed once and its checkpoint is saved each time it
reaches a declared age (``develop``). The saved ages are then measured in
randomized order, each restored into a fresh Body (``measure``), so that every
age is the same individual and development time is not confounded with host
load. The subject is the private-model runtime in the deterministic
``CausalBody``: no physics engine, no World, no telemetry writer, so what is
timed is organism computation plus a trivial Body step, timed separately.

Per measurement, with the observer off unless stated:

* tick latency distribution (median, p95, p99, max) and throughput;
* the Body step, timed apart from the organism tick;
* the same window with the passive observer surface exercised;
* checkpoint build time, serialized size, and restore time;
* resident memory;
* the sizes of the structures that can grow with age;
* optionally, a cProfile attribution of a separate window (``--profile``).

Timing is not asserted anywhere. Usage:

    python scripts/bench_age_scaling.py develop --checkpoints DIR --ages 1000 5000
    python scripts/bench_age_scaling.py measure --checkpoints DIR --output out.json
"""

from __future__ import annotations

import argparse
import cProfile
import gc
import json
import os
import platform
import pstats
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from symbiont.cognition.limits import KernelLimits
from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime
from symbiont_lab.studies.learning.agency_acquisition_body import (
    CausalBody,
    build_subject,
    subject_lifecycle,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")


def _rss_mb() -> float:
    with open("/proc/self/statm", encoding="ascii") as handle:
        return int(handle.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1e6


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


def _summary(samples_s: list[float]) -> dict[str, float]:
    ms = [value * 1000.0 for value in samples_s]
    return {
        "median_ms": round(statistics.median(ms), 4),
        "mean_ms": round(statistics.fmean(ms), 4),
        "p95_ms": round(_percentile(ms, 0.95), 4),
        "p99_ms": round(_percentile(ms, 0.99), 4),
        "max_ms": round(max(ms), 4),
        "ticks_per_second": round(len(ms) / sum(samples_s), 2),
    }


def _observe(runtime: PrivateModelOrganismRuntime) -> None:
    """The passive observer surface, as scripts/bench_observability_tax.py."""
    _ = runtime.state_hash()
    _ = runtime.sensorimotor_snapshot
    _ = runtime.sensorimotor_competence_candidates
    _ = runtime.sensorimotor_competence_episodes
    _ = runtime.available_motor_competence_ids
    _ = runtime.body_schema.export_representation(current_tick=runtime.tick_count)
    _ = tuple(runtime._action_domain.acquisition.provenance.events())


def _window(
    runtime: PrivateModelOrganismRuntime, body: CausalBody, ticks: int, *, observed: bool
) -> dict[str, Any]:
    organism: list[float] = []
    body_step: list[float] = []
    observer: list[float] = []
    gc.collect()
    for _ in range(ticks):
        started = time.perf_counter()
        runtime.tick(include_observability=observed)
        mid = time.perf_counter()
        body.advance(runtime.last_actuations)
        done = time.perf_counter()
        organism.append(mid - started)
        body_step.append(done - mid)
        if observed:
            _observe(runtime)
            observer.append(time.perf_counter() - done)
    result: dict[str, Any] = {"organism_tick": _summary(organism), "body_step": _summary(body_step)}
    if observed:
        result["observer_read"] = _summary(observer)
    return result


def _sizes(runtime: PrivateModelOrganismRuntime) -> dict[str, int]:
    domain = runtime._action_domain
    acquisition = domain.acquisition
    graph = runtime.cognitive_bridge.graph
    sizes = {
        "graph_nodes": len(graph.nodes),
        "graph_edges": len(graph.edges),
        "experience_ledger_records": len(runtime.experience_ledger.records),
        "experience_archive_records": len(runtime.experience_archive.records),
        "model_registry_models": len(runtime.model_registry.records),
        "competences": len(domain.competence_library.items),
        "execution_bindings": len(domain.execution_bindings.items),
        "causal_evidence": len(acquisition.causal_evidence.evidence),
        "agency_estimates": len(acquisition.agency_model.estimates),
        "provenance_events": len(tuple(acquisition.provenance.events())),
        "adaptive_sense_states": len(runtime.adaptive_senses.states),
        "episodic_episodes": len(runtime._episodic_memory.episodes),
        "episodic_interpretations": sum(
            len(runtime._episodic_memory.interpretations_for(episode.episode_id))
            for episode in runtime._episodic_memory.episodes
        ),
        "concept_lineages": len(runtime.cognitive_bridge.concept_lineage),
    }
    return sizes


def _checkpoint(
    runtime: PrivateModelOrganismRuntime, body: CausalBody, seed: int
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = runtime.checkpoint(advance_lineage=False)
    built = time.perf_counter()
    encoded = json.dumps(payload, separators=(",", ":"))
    serialized = time.perf_counter()
    fresh_body = CausalBody(actuator_count=len(body.surface.actuator_ids), seed=seed)
    restore_started = time.perf_counter()
    _restore(json.loads(encoded), fresh_body)
    restored = time.perf_counter()
    by_field = sorted(
        ((len(json.dumps(value, separators=(",", ":"))), key) for key, value in payload.items()),
        reverse=True,
    )[:8]
    return {
        "build_ms": round((built - started) * 1000, 3),
        "serialize_ms": round((serialized - built) * 1000, 3),
        "restore_ms": round((restored - restore_started) * 1000, 3),
        "size_bytes": len(encoded),
        "largest_fields_bytes": {key: size for size, key in by_field},
    }


def _restore(payload: dict[str, Any], body: CausalBody) -> PrivateModelOrganismRuntime:
    return PrivateModelOrganismRuntime.from_checkpoint(
        payload,
        host_lifecycle=subject_lifecycle(body),
        host_reading_providers=(body,),
        kernel_limits=KernelLimits(),
        actuator_constitution_override=body.surface,
        bootstrap_semantic_senses=False,
        discover_senses=True,
        min_samples=1,
        interoception_mode="absent",
    )


def _learning_plan(runtime: PrivateModelOrganismRuntime) -> dict[str, Any]:
    """Cost of preparing private-model training (corpus and tokenizer), not training."""
    planner = getattr(runtime, "autonomous_private_learning_plan", None)
    if planner is None:
        return {"available": False}
    started = time.perf_counter()
    plan = planner()
    elapsed = time.perf_counter() - started
    result: dict[str, Any] = {"available": True, "plan_ms": round(elapsed * 1000, 3)}
    result["planned"] = plan is not None
    if plan is not None:
        result["vocabulary"] = len(plan.tokenizer.vocabulary)
    return result


def _profile(runtime: PrivateModelOrganismRuntime, body: CausalBody, ticks: int) -> list[dict]:
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(ticks):
        runtime.tick(include_observability=False)
        body.advance(runtime.last_actuations)
    profiler.disable()
    stats = pstats.Stats(profiler)
    total = sum(row[2] for row in stats.stats.values()) or 1.0  # type: ignore[attr-defined]
    rows = []
    for (filename, _line, name), (_cc, calls, tottime, cumtime, _callers) in stats.stats.items():  # type: ignore[attr-defined]
        if SRC not in filename:
            continue
        rows.append(
            {
                "function": f"{Path(filename).relative_to(SRC).as_posix()}:{name}",
                "calls_per_tick": round(calls / ticks, 2),
                "self_share": round(tottime / total, 4),
                "cumulative_ms_per_tick": round(cumtime * 1000 / ticks, 4),
                "self_ms_per_tick": round(tottime * 1000 / ticks, 4),
            }
        )
    rows.sort(key=lambda row: row["self_ms_per_tick"], reverse=True)
    return rows[:25]


def _host() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    return {
        "commit": commit,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
    }


def develop(args: argparse.Namespace) -> None:
    """Grow one organism and save its checkpoint each time it reaches an age."""
    args.checkpoints.mkdir(parents=True, exist_ok=True)
    body = CausalBody(actuator_count=args.actuators, seed=args.seed)
    runtime = build_subject(
        body,
        organism_id=f"age-scaling-{args.seed}",
        runtime_class=PrivateModelOrganismRuntime,
        factorized_effects=True,
    )
    log = []
    for age in sorted(args.ages):
        started = time.perf_counter()
        developed = 0
        while runtime.tick_count < age:
            runtime.tick(include_observability=False)
            body.advance(runtime.last_actuations)
            developed += 1
        elapsed = time.perf_counter() - started
        payload = runtime.checkpoint(advance_lineage=False)
        (args.checkpoints / f"age-{age:06d}.json").write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8"
        )
        log.append(
            {
                "age_ticks": runtime.tick_count,
                "development_ticks": developed,
                "development_ms_per_tick": round(elapsed * 1000 / max(developed, 1), 3),
                "load_average": os.getloadavg(),
            }
        )
        (args.checkpoints / "development.json").write_text(
            json.dumps(
                {**_host(), "seed": args.seed, "actuators": args.actuators, "ages": log}, indent=2
            ),
            encoding="utf-8",
        )
        print(json.dumps(log[-1]), file=sys.stderr, flush=True)


def measure(args: argparse.Namespace) -> None:
    """Measure saved ages in randomized order, each restored into a fresh Body.

    Development time and host load drift together, so ages are not measured
    while the organism grows. Every measurement restores the saved organism,
    runs a warmup longer than the reacclimation gate, and then times windows.
    """
    files = sorted(args.checkpoints.glob("age-*.json"))
    order = [(path, repeat) for repeat in range(args.repeats) for path in files]
    random.Random(args.order_seed).shuffle(order)
    report: dict[str, Any] = {
        **_host(),
        "seed": args.seed,
        "actuators": args.actuators,
        "window_ticks": args.window,
        "warmup_ticks": args.warmup,
        "repeats": args.repeats,
        "order": [f"{path.stem}#{repeat}" for path, repeat in order],
        "load_average_start": os.getloadavg(),
        "measurements": [],
    }
    for path, repeat in order:
        payload = json.loads(path.read_text(encoding="utf-8"))
        body = CausalBody(actuator_count=args.actuators, seed=args.seed)
        runtime = _restore(payload, body)
        for _ in range(args.warmup):
            runtime.tick(include_observability=False)
            body.advance(runtime.last_actuations)
        entry: dict[str, Any] = {
            "age_ticks": int(payload["saved_at_tick"]),
            "repeat": repeat,
            "rss_mb": round(_rss_mb(), 1),
            "sizes": _sizes(runtime),
            "observer_off": _window(runtime, body, args.window, observed=False),
            "observer_on": _window(runtime, body, args.window, observed=True),
            "checkpoint": _checkpoint(runtime, body, args.seed),
            "private_learning_plan": _learning_plan(runtime),
            "load_average": os.getloadavg(),
        }
        if args.profile and repeat == 0:
            entry["profile_top_self_time"] = _profile(runtime, body, args.window)
        report["measurements"].append(entry)
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps({"age": entry["age_ticks"], "repeat": repeat}), file=sys.stderr, flush=True
        )
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("develop", "measure"))
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--ages", type=int, nargs="+", default=[1000, 5000, 10000, 25000])
    parser.add_argument("--seed", type=int, default=127)
    parser.add_argument("--actuators", type=int, default=4)
    parser.add_argument("--window", type=int, default=200, help="ticks per timed window")
    parser.add_argument("--warmup", type=int, default=64, help="ticks after restore, untimed")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--order-seed", type=int, default=0)
    parser.add_argument("--profile", action="store_true", help="add a cProfile window per age")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    (develop if args.mode == "develop" else measure)(args)


if __name__ == "__main__":
    main()
