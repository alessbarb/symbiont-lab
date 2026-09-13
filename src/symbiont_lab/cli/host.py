from __future__ import annotations

import argparse
import json
import sys

from symbiont.core import attend_to_host
from symbiont.host import (
    CheckpointError,
    acclimate_local_host,
    current_time_bucket,
    discover_local_host,
    export_checkpoint,
    import_checkpoint,
    learn_local_host_rhythms,
    monitor_local_host,
    perceive_local_host,
    sample_local_host,
    second_look_at_local_host,
    track_local_host_drift,
)


def build_host_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="host_action", required=True)
    sub.add_parser(
        "discover",
        help="Discover the safe, read-only, identity-free capabilities this host offers",
    )
    sub.add_parser(
        "sample",
        help="Sample typed readings for the capabilities this host discovers",
    )
    monitor_cmd = sub.add_parser(
        "monitor",
        help="Run a bounded number of discovery+sampling ticks with backoff and bounded history",
    )
    monitor_cmd.add_argument(
        "--ticks",
        type=int,
        default=3,
        help="Number of ticks to run (1-1000, default 3)",
    )
    sub.add_parser(
        "perceive",
        help="Synthesize platform-neutral percepts from this host's real readings",
    )
    acclimate_cmd = sub.add_parser(
        "acclimate",
        help="Learn a descriptive baseline per capability; withholds any threat conclusion",
    )
    acclimate_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to seed the baseline with (1-1000, default 5)",
    )
    rhythms_cmd = sub.add_parser(
        "rhythms",
        help="Learn a per-time-bucket baseline and co-occurrence for this host's percepts",
    )
    rhythms_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to seed the current time bucket with (1-1000, default 5)",
    )
    drift_cmd = sub.add_parser(
        "drift",
        help="Classify each percept against its own aging baseline: isolated, gradual or regime shift",
    )
    drift_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to observe (1-1000, default 5)",
    )
    checkpoint_cmd = sub.add_parser(
        "checkpoint",
        help="Export/import safe abstract host beliefs — never raw readings or timestamps",
    )
    checkpoint_sub = checkpoint_cmd.add_subparsers(dest="checkpoint_action", required=True)
    checkpoint_export_cmd = checkpoint_sub.add_parser(
        "export",
        help="Learn from the built-in providers and print a schema-versioned checkpoint",
    )
    checkpoint_export_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to learn from before exporting (1-1000, default 5)",
    )
    checkpoint_sub.add_parser(
        "import",
        help="Restore safe abstract beliefs from a checkpoint JSON document read on stdin",
    )
    attend_cmd = sub.add_parser(
        "attend",
        help="Allocate a hard attention budget across this host's capabilities by uncertainty and cost",
    )
    attend_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Number of ticks to acclimate from before allocating attention (1-1000, default 5)",
    )
    attend_cmd.add_argument(
        "--budget",
        type=float,
        default=1.0,
        help="Total attention budget to allocate this tick (must be positive, default 1.0)",
    )
    second_look_cmd = sub.add_parser(
        "second-look",
        help="Temporarily sample one already-discovered capability at higher resolution",
    )
    second_look_cmd.add_argument(
        "--capability-id",
        required=True,
        help="Capability id to look more closely at (must already be discovered/available)",
    )
    second_look_cmd.add_argument(
        "--ticks",
        type=int,
        default=5,
        help="Maximum number of ticks to sample before the session ends (1-1000, default 5)",
    )


def run_host_command(args: argparse.Namespace) -> int:
    if args.host_action == "discover":
        manifest = discover_local_host()
        payload = {
            "schema_version": manifest.schema_version,
            "capabilities": [
                {
                    "capability_id": capability.capability_id,
                    "kind": capability.kind.value,
                    "source": capability.source,
                    "access": capability.access.value,
                    "scope": capability.scope.value,
                    "available": capability.available,
                    "detail": dict(capability.detail),
                }
                for capability in manifest.capabilities
            ],
            "failures": [
                {"provider_id": failure.provider_id, "reason": failure.reason}
                for failure in manifest.failures
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "sample":
        manifest = discover_local_host()
        readings, failures = sample_local_host(manifest)
        payload = {
            "readings": [reading.as_dict() for reading in readings],
            "failures": [
                {"provider_id": failure.provider_id, "reason": failure.reason}
                for failure in failures
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "monitor":
        ticks = min(max(int(args.ticks), 1), 1000)
        lifecycle = monitor_local_host()
        snapshots = []
        for _ in range(ticks):
            snapshot = lifecycle.tick()
            snapshots.append(
                {
                    "tick": snapshot.tick,
                    "readings": [reading.as_dict() for reading in snapshot.readings],
                    "reading_failures": [
                        {"provider_id": failure.provider_id, "reason": failure.reason}
                        for failure in snapshot.reading_failures
                    ],
                    "backed_off_providers": list(snapshot.backed_off_providers),
                }
            )
        payload = {
            "snapshots": snapshots,
            "capability_changes": list(lifecycle.capability_changes()),
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "perceive":
        percepts = perceive_local_host()
        payload = {"percepts": [percept.as_dict() for percept in percepts]}
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "acclimate":
        ticks = min(max(int(args.ticks), 1), 1000)
        acclimation, _ = acclimate_local_host(ticks=ticks)
        payload = {
            "acclimated_capabilities": list(acclimation.acclimated_capabilities),
            "baselines": {
                capability_id: {
                    "count": baseline.count,
                    "mean": baseline.mean,
                    "variance": baseline.variance,
                    "stdev": baseline.stdev,
                }
                for capability_id in acclimation.acclimated_capabilities
                if (baseline := acclimation.baseline(capability_id)) is not None
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "rhythms":
        ticks = min(max(int(args.ticks), 1), 1000)
        bucket = current_time_bucket()
        model = learn_local_host_rhythms(ticks=ticks, time_bucket=bucket)
        payload = {
            "time_bucket": bucket.value,
            "co_occurring_percepts": list(model.co_occurring_percepts(bucket)),
            "baselines": {
                percept_name: {
                    "count": baseline.count,
                    "mean": baseline.mean,
                    "variance": baseline.variance,
                    "stdev": baseline.stdev,
                }
                for percept_name, learned_bucket in model.learned_contexts
                if learned_bucket == bucket
                and (baseline := model.baseline(percept_name, bucket)) is not None
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "drift":
        ticks = min(max(int(args.ticks), 1), 1000)
        baselines, tick_observations = track_local_host_drift(ticks=ticks)
        payload = {
            "ticks": [
                {
                    name: {"kind": obs.kind.value, "z_score": obs.z_score}
                    for name, obs in observations.items()
                }
                for observations in tick_observations
            ],
            "baselines": {
                name: {"is_established": baseline.is_established, "mean": baseline.mean, "stdev": baseline.stdev}
                for name, baseline in baselines.items()
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "checkpoint":
        if args.checkpoint_action == "export":
            ticks = min(max(int(args.ticks), 1), 1000)
            acclimation, _ = acclimate_local_host(ticks=ticks)
            rhythm_model = learn_local_host_rhythms(ticks=ticks)
            drift_baselines, _ = track_local_host_drift(ticks=ticks)
            payload = export_checkpoint(
                acclimation=acclimation, rhythm_model=rhythm_model, drift_baselines=drift_baselines
            )
            print(json.dumps(payload, indent=2, sort_keys=True, default=str))
            return 0
        if args.checkpoint_action == "import":
            try:
                payload = json.loads(sys.stdin.read())
            except json.JSONDecodeError as exc:
                print(f"invalid checkpoint JSON: {exc}", file=sys.stderr)
                return 1
            try:
                acclimation, rhythm_model, drift_baselines = import_checkpoint(payload)
            except CheckpointError as exc:
                print(f"invalid checkpoint: {exc}", file=sys.stderr)
                return 1
            summary = {
                "restored_acclimation_capabilities": list(acclimation.acclimated_capabilities),
                "restored_rhythm_contexts": [
                    {"percept_name": name, "time_bucket": bucket.value}
                    for name, bucket in rhythm_model.learned_contexts
                ],
                "restored_drift_percepts": {
                    name: {"count": baseline.count, "mean": baseline.mean, "stdev": baseline.stdev}
                    for name, baseline in drift_baselines.items()
                },
            }
            print(json.dumps(summary, indent=2, sort_keys=True, default=str))
            return 0
        return 1
    if args.host_action == "attend":
        ticks = min(max(int(args.ticks), 1), 1000)
        if args.budget <= 0.0:
            print("--budget must be positive", file=sys.stderr)
            return 1
        acclimation, _ = acclimate_local_host(ticks=ticks)
        allocations = attend_to_host(acclimation, budget=args.budget)
        payload = {
            "budget": args.budget,
            "known_capabilities": list(acclimation.known_capabilities),
            "allocations": [
                {"name": allocation.name, "uncertainty": allocation.uncertainty, "cost": allocation.cost}
                for allocation in allocations
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    if args.host_action == "second-look":
        ticks = min(max(int(args.ticks), 1), 1000)
        try:
            result = second_look_at_local_host(args.capability_id, max_ticks=ticks)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        payload = {
            "capability_id": result.capability_id,
            "cancelled": result.cancelled,
            "readings": [reading.as_dict() for reading in result.readings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    return 1
