"""Run a resident Symbiont and emit passive Observatory snapshot envelopes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys

from adapter import envelope, project_tick


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stream a resident self-discovering Symbiont to Observatory")
    parser.add_argument("--state-file", type=Path, default=Path("~/.local/state/symbiont/organism.json").expanduser())
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--display-id", default="local-symbiont")
    parser.add_argument("--max-ticks", type=int, default=None, help="optional finite budget for testing")
    args = parser.parse_args(argv)

    from symbiont.core import OrganismRuntime, ResidentConfig, ResidentOrganism

    runtime = OrganismRuntime.load_or_create(
        args.state_file,
        discover_senses=True,
        bootstrap_semantic_senses=False,
    )

    def publish(result) -> None:
        snapshot = project_tick(
            result,
            acclimation=runtime.acclimation,
            display_id=args.display_id,
            ticks_remaining=None,
        )
        active_names = set(runtime.adaptive_senses.percept_names().values())
        snapshot["organism"]["sensory_development"] = [
            {
                "name": state.percept_name,
                "samples": state.samples,
                "availability": round(state.availability, 6),
                "utility": round(state.utility, 6),
                "active": state.percept_name in active_names,
            }
            for state in runtime.adaptive_senses.states[:64]
        ]
        snapshot["organism"]["sensory_relations"] = [
            {
                "sense_a": relation.sense_a,
                "sense_b": relation.sense_b,
                "synchronous": _rounded(relation.synchronous),
                "a_to_b": _rounded(relation.a_to_b),
                "b_to_a": _rounded(relation.b_to_a),
                "samples": relation.samples,
            }
            for relation in runtime.adaptive_senses.strongest_relations(limit=24)
        ]
        print(json.dumps(envelope(snapshot), ensure_ascii=False, separators=(",", ":")), flush=True)

    resident = ResidentOrganism(
        runtime,
        state_file=args.state_file,
        config=ResidentConfig(
            interval_seconds=args.interval,
            checkpoint_every_ticks=args.checkpoint_every,
            max_ticks=args.max_ticks,
        ),
        on_tick=publish,
    )

    def stop(_signum, _frame) -> None:
        resident.stop()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    resident.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
