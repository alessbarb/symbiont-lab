from __future__ import annotations

import argparse
import json

from symbiont.core import (
    ConsentRevokedError,
    DefensiveAdvisor,
    GovernedOrganism,
    OrganismRuntime,
    RateLimitedError,
    TickBudgetExhaustedError,
    append_advisories_to_log,
)


def build_organism_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="organism_action", required=True)

    run_cmd = sub.add_parser(
        "run",
        help="Run the organism's continuous cognitive cycle for N ticks: discover, observe, "
        "acclimate, perceive, track drift, attend, investigate, revise, explain",
    )
    run_cmd.add_argument("--ticks", type=int, default=5, help="Number of cycles to run (1-1000, default 5)")
    run_cmd.add_argument(
        "--attention-budget",
        type=float,
        default=1.0,
        help="Attention budget allocated each tick (must be positive, default 1.0)",
    )
    run_cmd.add_argument(
        "--investigate-ticks",
        type=int,
        default=2,
        help="Second-look ticks spent on the top-attended capability each cycle; 0 disables investigation (default 2)",
    )
    run_cmd.add_argument(
        "--conflict-z",
        type=float,
        default=2.0,
        help="Minimum |z-score| between investigation evidence and prior belief to record dissent (default 2.0)",
    )
    run_cmd.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Samples required before a capability/context counts as learned (default 5)",
    )
    run_cmd.add_argument(
        "--min-seconds-between-ticks",
        type=float,
        default=0.0,
        help="Minimum wall-clock seconds required between ticks; a tick attempted sooner is refused, "
        "not delayed (non-negative, default 0.0)",
    )
    run_cmd.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Hard cap on total ticks this run may perform, independent of --ticks requested (default: unbounded)",
    )
    run_cmd.add_argument(
        "--state-file",
        help="Path to persist/resume organism state across invocations (atomic save, crash/restart recovery). "
        "Omit for an ephemeral, in-process-only run.",
    )
    run_cmd.add_argument(
        "--advisory-consent",
        action="store_true",
        help="Grant independent, separate consent to receive defensive advisories (default: not granted; "
        "consenting to be sensed does not imply consenting to advisories)",
    )
    run_cmd.add_argument(
        "--advisory-uncertainty-threshold",
        type=float,
        default=1.0,
        help="Relative uncertainty above which a capability counts as 'unusual activity' (must be positive, default 1.0)",
    )
    run_cmd.add_argument(
        "--advisory-log",
        help="Path to a durable, atomically-written advisory log; new advisories are appended. "
        "Omit to keep advisories ephemeral (printed only, not persisted).",
    )


def run_organism_command(args: argparse.Namespace) -> int:
    if args.organism_action == "run":
        ticks = min(max(int(args.ticks), 1), 1000)
        if args.state_file is not None:
            runtime = OrganismRuntime.load_or_create(
                args.state_file,
                attention_budget=args.attention_budget,
                investigate_ticks=args.investigate_ticks,
                conflict_z=args.conflict_z,
                min_samples=args.min_samples,
            )
        else:
            runtime = OrganismRuntime(
                attention_budget=args.attention_budget,
                investigate_ticks=args.investigate_ticks,
                conflict_z=args.conflict_z,
                min_samples=args.min_samples,
            )
        governed = GovernedOrganism(
            runtime,
            min_seconds_between_ticks=args.min_seconds_between_ticks,
            max_ticks=args.max_ticks,
        )

        advisor = DefensiveAdvisor(
            consented=args.advisory_consent, uncertainty_threshold=args.advisory_uncertainty_threshold
        )

        results = []
        all_advisories = []
        stopped_reason: str | None = None
        for _ in range(ticks):
            try:
                result = governed.tick()
            except (ConsentRevokedError, RateLimitedError, TickBudgetExhaustedError) as exc:
                stopped_reason = str(exc)
                break
            results.append(result)
            if advisor.is_consented:
                tick_advisories = advisor.evaluate(result)
                all_advisories.extend(tick_advisories)
                if args.advisory_log is not None:
                    append_advisories_to_log(tick_advisories, args.advisory_log)

        if args.state_file is not None:
            runtime.save(args.state_file)

        payload = {
            "ticks": [
                {
                    "tick": result.tick,
                    "allocations": [
                        {"name": allocation.name, "uncertainty": allocation.uncertainty, "cost": allocation.cost}
                        for allocation in result.allocations
                    ],
                    "investigated_capability": result.investigated_capability,
                    "evidence_gathered": result.evidence_gathered,
                    "contested": result.dissent is not None,
                    "narrative": [entry.summary for entry in result.narrative],
                }
                for result in results
            ],
            "advisories": [
                {
                    "tick": advisory.tick,
                    "capability_id": advisory.capability_id,
                    "signals": [{"kind": s.kind, "detail": s.detail} for s in advisory.signals],
                    "summary": advisory.summary,
                }
                for advisory in all_advisories
            ],
            "governor": {
                "ticks_run": governed.ticks_run,
                "ticks_remaining": governed.ticks_remaining,
                "is_consented": governed.is_consented,
                "stopped_early": stopped_reason,
            },
            "checkpoint": governed.checkpoint(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return 0
    return 1
