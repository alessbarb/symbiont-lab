from __future__ import annotations

import argparse
import json
from pathlib import Path

from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.experiments.registry import PROTOCOLS, get_protocol


def build_study_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="study_action", required=True)
    run_cmd = sub.add_parser("run", help="Run a scientific study protocol")
    run_cmd.add_argument("protocol", choices=sorted(PROTOCOLS.keys()), help="Protocol name")
    run_cmd.add_argument("--seeds", default="101,127,149", help="Comma-separated seeds")

    show_cmd = sub.add_parser("show", help="Show details of an archived study run")
    show_cmd.add_argument("record_id", help="Study record identifier")


def run_study_command(args: argparse.Namespace) -> int:
    if args.study_action == "run":
        protocol_fn = get_protocol(args.protocol)
        seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
        print(f"Executing study protocol '{args.protocol}' across seeds {seeds}...")
        result = protocol_fn(seeds=seeds)
        print("Study completed successfully.")
        raw = result.as_dict() if hasattr(result, "as_dict") else result
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
