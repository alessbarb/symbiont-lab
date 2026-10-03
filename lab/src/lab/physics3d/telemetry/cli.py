"""CLI entrypoints for telemetry conversion and benchmarking."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab.physics3d.telemetry.tools import (
    benchmark_run,
    compare_runs,
    evaluate_acceptance_gates,
)


def benchmark_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark Physics3D telemetry storage and reconstruction"
    )
    parser.add_argument("run", type=Path)
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="compare RUN against a second telemetry run",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="evaluate canonical v4.1 acceptance gates for RUN",
    )
    parser.add_argument(
        "--expected-ticks",
        type=int,
        default=None,
        help="require an exact tick count when --gate is used",
    )
    args = parser.parse_args(argv)
    payload = (
        compare_runs(args.run, args.compare)
        if args.compare is not None
        else benchmark_run(args.run)
    )
    exit_code = 0
    if args.gate:
        if args.compare is not None:
            parser.error("--gate cannot be combined with --compare")
        gate = evaluate_acceptance_gates(
            payload,
            expected_ticks=args.expected_ticks,
        )
        payload = {"benchmark": payload, "gate": gate}
        exit_code = 0 if gate["passed"] else 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


__all__ = ["benchmark_main"]
