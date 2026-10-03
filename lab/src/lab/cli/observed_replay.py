"""Record a bounded run of a real Symbiont as a passive Observatory replay.

This module owns the organism it records. The ``observatory`` package only
projects the ticks it is handed; it never constructs a runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lab.integration.organism import create_canonical_organism, load_or_create_canonical_organism
from lab.observatory.adapter import MAX_TICKS, envelope, project_tick, write_replay
from symbiont.core.orchestration.governor import GovernedOrganism


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Record bounded real Symbiont ticks for the passive Observatory"
    )
    parser.add_argument(
        "--ticks", type=int, default=20, help="finite tick budget (1-10000; default 20)"
    )
    parser.add_argument("--output", type=Path, default=Path("symbiont-replay.json"))
    parser.add_argument(
        "--display-id", default="local-symbiont", help="non-identifying display label"
    )
    parser.add_argument(
        "--checkpoint", type=Path, help="optional durable abstract runtime checkpoint"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="also emit one postMessage-compatible JSON envelope per line",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.ticks <= MAX_TICKS:
        parser.error(f"--ticks must be between 1 and {MAX_TICKS}")

    runtime = (
        load_or_create_canonical_organism(args.checkpoint)
        if args.checkpoint
        else create_canonical_organism()
    )
    organism = GovernedOrganism(runtime, max_ticks=args.ticks)
    revision_counts: dict[str, int] = {}
    snapshots = []
    for _ in range(args.ticks):
        result = organism.tick()
        snapshot = project_tick(
            result,
            acclimation=runtime.acclimation,
            display_id=args.display_id,
            ticks_remaining=organism.ticks_remaining,
            revision_counts=revision_counts,
            body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
            signal_knowledge=result.signal_knowledge,
            knowledge_events=result.knowledge_events,
            signal_references=result.signal_references,
            social_relations=runtime.social_ledger.relations,
            social_resource_evidence=runtime.social_resource_ledger.evidence,
            cultural_observations=(
                runtime.cultural_observations()
                if hasattr(runtime, "cultural_observations")
                else None
            ),
        )
        snapshots.append(snapshot)
        if args.stdout:
            print(
                json.dumps(envelope(snapshot), ensure_ascii=False, separators=(",", ":")),
                flush=True,
            )
    write_replay(args.output, snapshots)
    if args.checkpoint:
        runtime.save(args.checkpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())
