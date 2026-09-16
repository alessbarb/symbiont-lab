from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any, Callable

from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.experiments.registry import PROTOCOLS, get_protocol


def build_study_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="study_action", required=True)
    run_cmd = sub.add_parser("run", help="Run a scientific study protocol")
    run_cmd.add_argument("protocol", choices=sorted(PROTOCOLS.keys()), help="Protocol name")
    run_cmd.add_argument("--seeds", "--seed", dest="seeds", default="101,127,149", help="Seed or comma-separated seeds")
    run_cmd.add_argument("--hosts", type=int, default=None, help="Override synthetic host count")
    run_cmd.add_argument("--steps", type=int, default=None, help="Override simulation steps")
    run_cmd.add_argument("--generations", type=int, default=None, help="Override generation count for longitudinal protocols")

    show_cmd = sub.add_parser("show", help="Show details of an archived study run")
    show_cmd.add_argument("record_id", help="Study record identifier")


def _prepare_protocol_kwargs(
    protocol_fn: Callable[..., Any],
    seeds: list[int],
    args: argparse.Namespace,
) -> dict[str, Any]:
    sig = inspect.signature(protocol_fn)
    params = sig.parameters
    kwargs: dict[str, Any] = {}

    if "seeds" in params:
        kwargs["seeds"] = seeds
    elif "source_seeds" in params:
        kwargs["source_seeds"] = seeds
    elif "seed" in params:
        kwargs["seed"] = seeds[0] if seeds else 7
    elif "source_seed" in params:
        kwargs["source_seed"] = seeds[0] if seeds else 7
        if "target_seed" in params:
            kwargs["target_seed"] = seeds[1] if len(seeds) > 1 else (seeds[0] + 1009 if seeds else 1016)

    # Forward optional overrides if accepted by protocol
    if getattr(args, "hosts", None) is not None and "hosts" in params:
        kwargs["hosts"] = args.hosts
    if getattr(args, "steps", None) is not None and "steps" in params:
        kwargs["steps"] = args.steps
    if getattr(args, "generations", None) is not None and "generations" in params:
        kwargs["generations"] = args.generations

    return kwargs


def run_study_command(args: argparse.Namespace) -> int:
    if args.study_action == "run":
        protocol_fn = get_protocol(args.protocol)
        raw_seeds = getattr(args, "seeds", "101,127,149") or "101,127,149"
        seeds = [int(s.strip()) for s in str(raw_seeds).split(",") if s.strip()]
        kwargs = _prepare_protocol_kwargs(protocol_fn, seeds, args)
        print(f"Executing study protocol '{args.protocol}' with parameters {kwargs}...")
        result = protocol_fn(**kwargs)
        print("Study completed successfully.")
        if isinstance(result, tuple) and len(result) == 2 and hasattr(result[0], "as_dict"):
            raw = result[0].as_dict()
        elif hasattr(result, "as_dict"):
            raw = result.as_dict()
        else:
            raw = result
        print(json.dumps(raw, indent=2, sort_keys=True, default=str))
        return 0
    elif args.study_action == "show":
        archive = StudyArchive()
        records = archive.recent(100)
        found = next((r for r in records if r.record_id == args.record_id), None)
        if not found:
            print(f"Study record '{args.record_id}' not found in {archive.path}.")
            return 1
        print(json.dumps(found.as_dict(), indent=2))
        return 0
    return 1
