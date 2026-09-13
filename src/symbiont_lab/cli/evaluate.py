from __future__ import annotations

import argparse
import json
import sys

from symbiont_lab.evaluation.advisory_evaluation import (
    OperatorJudgment,
    evaluate_advisories,
    evaluate_advisories_over_time,
    record_operator_judgment,
)


def build_evaluate_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="evaluate_action", required=True)

    advisories_p = sub.add_parser(
        "advisories",
        help="Measure fired defensive advisories against real operator judgment (roadmap v0.49)",
    )
    advisories_sub = advisories_p.add_subparsers(dest="advisories_action", required=True)

    label_cmd = advisories_sub.add_parser(
        "label",
        help="Record a real operator's judgment of one specific fired advisory",
    )
    label_cmd.add_argument("--advisory-log", required=True, help="Path to the organism's advisory log")
    label_cmd.add_argument("--labels-file", required=True, help="Path to the (separate) operator labels file")
    label_cmd.add_argument("--tick", type=int, required=True, help="Tick the advisory fired on")
    label_cmd.add_argument("--capability-id", required=True, help="Capability the advisory concerned")
    label_cmd.add_argument(
        "--judgment", required=True, choices=[j.value for j in OperatorJudgment], help="Your judgment of it"
    )
    label_cmd.add_argument("--note", default=None, help="Optional free-text note")

    summary_cmd = advisories_sub.add_parser(
        "summary",
        help="Summarize labeled/unlabeled advisories: usefulness rate, false-alarm rate, label coverage",
    )
    summary_cmd.add_argument("--advisory-log", required=True, help="Path to the organism's advisory log")
    summary_cmd.add_argument("--labels-file", required=True, help="Path to the operator labels file")
    summary_cmd.add_argument(
        "--window-ticks",
        type=int,
        default=None,
        help="If given, report per-window summaries (of this many ticks each) instead of one lifetime summary",
    )


def _summary_to_dict(summary) -> dict:
    return {
        "total_fired": summary.total_fired,
        "total_labeled": summary.total_labeled,
        "useful_count": summary.useful_count,
        "false_alarm_count": summary.false_alarm_count,
        "unknown_count": summary.unknown_count,
        "usefulness_rate": summary.usefulness_rate,
        "false_alarm_rate": summary.false_alarm_rate,
        "label_coverage": summary.label_coverage,
    }


def run_evaluate_command(args: argparse.Namespace) -> int:
    if args.evaluate_action == "advisories":
        if args.advisories_action == "label":
            try:
                record_operator_judgment(
                    args.advisory_log,
                    args.labels_file,
                    tick=args.tick,
                    capability_id=args.capability_id,
                    judgment=OperatorJudgment(args.judgment),
                    note=args.note,
                )
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(json.dumps({"recorded": True, "tick": args.tick, "capability_id": args.capability_id}, indent=2))
            return 0
        if args.advisories_action == "summary":
            if args.window_ticks is not None:
                windows = evaluate_advisories_over_time(
                    args.advisory_log, args.labels_file, window_ticks=args.window_ticks
                )
                payload = {
                    "windows": [
                        {"start_tick": start, "end_tick": end, **_summary_to_dict(summary)}
                        for start, end, summary in windows
                    ]
                }
            else:
                payload = _summary_to_dict(evaluate_advisories(args.advisory_log, args.labels_file))
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        return 1
    return 1
