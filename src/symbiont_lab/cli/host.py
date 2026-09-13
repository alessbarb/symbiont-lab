from __future__ import annotations

import argparse
import json

from symbiont.host import (
    acclimate_local_host,
    current_time_bucket,
    discover_local_host,
    learn_local_host_rhythms,
    monitor_local_host,
    perceive_local_host,
    sample_local_host,
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
    return 1
