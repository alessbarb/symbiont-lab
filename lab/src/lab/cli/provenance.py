"""`symbiont-lab provenance`: query a causal provenance journal (apparatus only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab.observation.provenance_journal import (
    ProvenanceIndex,
    ProvenanceJournal,
    render_tree,
)
from symbiont.provenance import CausalRef


def build_provenance_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="provenance_action", required=True)
    summary = sub.add_parser("summary", help="Event counts by domain and operation")
    summary.add_argument("journal", type=Path)
    find = sub.add_parser("find", help="List events by domain / operation / subject kind")
    find.add_argument("journal", type=Path)
    find.add_argument("--domain")
    find.add_argument("--operation")
    find.add_argument("--kind")
    find.add_argument("--limit", type=int, default=20)
    why = sub.add_parser("why", help="Causal tree behind one reference")
    why.add_argument("journal", type=Path)
    why.add_argument("kind", help="Reference kind, e.g. intent, competence, footprint_version")
    why.add_argument("id", help="Reference id")
    why.add_argument("--depth", type=int, default=12)
    why.add_argument("--json", action="store_true", help="Print the tree as JSON")


def run_provenance_command(args: argparse.Namespace) -> int:
    index = ProvenanceIndex.load(ProvenanceJournal(args.journal))
    if args.provenance_action == "summary":
        for key, count in index.summary().items():
            print(f"{count:8d}  {key}")
        return 0
    if args.provenance_action == "find":
        events = index.find(domain=args.domain, operation=args.operation, kind=args.kind)
        for event in events[-args.limit :]:
            print(
                f"t{event.tick:<8d} {event.domain}.{event.operation:<14s} "
                f"{event.subject.kind}:{event.subject.id}"
            )
        print(f"({len(events)} events)")
        return 0
    tree = index.why(CausalRef(args.kind, args.id), depth=args.depth)
    if args.json:
        print(json.dumps(tree, indent=2, sort_keys=True))
    else:
        print("\n".join(render_tree(tree)))
    return 0 if "event" in tree else 1
