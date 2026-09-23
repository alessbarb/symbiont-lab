"""CLI entrypoints for telemetry conversion and benchmarking."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .telemetry_tools import benchmark_run, compare_runs, convert_run


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
    args = parser.parse_args(argv)
    payload = (
        compare_runs(args.run, args.compare)
        if args.compare is not None
        else benchmark_run(args.run)
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def convert_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Physics3D telemetry to lossless v4.1"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)
    report = convert_run(
        args.source,
        args.output,
        run_id=args.run_id,
    )
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


__all__ = ["benchmark_main", "convert_main"]
