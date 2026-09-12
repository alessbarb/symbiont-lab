from __future__ import annotations

import argparse
import json

from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive


def build_archive_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="archive_action", required=True)
    list_cmd = sub.add_parser("list", help="List recent archived experiment runs and studies")
    list_cmd.add_argument("--limit", type=int, default=10, help="Max records to list")


def run_archive_command(args: argparse.Namespace) -> int:
    if args.archive_action == "list":
        runs = ExperimentArchive().recent(args.limit)
        studies = StudyArchive().recent(args.limit)
        print(f"=== Experiment Runs ({len(runs)}) ===")
        for r in runs:
            print(f"[{r.record_id}] {r.created_at} — {r.spec.get('title', 'Untitled')} (source: {r.source})")

        print(f"\n=== Comparative Studies ({len(studies)}) ===")
        for s in studies:
            print(f"[{s.record_id}] {s.created_at} — {s.base_spec.get('title', 'Untitled')} (source: {s.source})")
        return 0
    return 1
