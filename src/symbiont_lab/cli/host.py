from __future__ import annotations

import argparse
import json

from symbiont.host import discover_local_host, monitor_local_host, sample_local_host


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
    return 1
