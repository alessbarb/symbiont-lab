from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any, Callable

from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.experiments.registry import PROTOCOLS, get_protocol
from symbiont_lab.experiments.spec import ExperimentSpec
from symbiont_lab.studies.campaigns.comparative import (
    COMPARABLE_PARAMETERS,
    METRICS,
    run_comparative_study,
)
from symbiont_lab.studies.campaigns.interpretation import interpret_study


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

    compare_cmd = sub.add_parser(
        "compare", help="Run a reproducible comparative study and record it to the study archive"
    )
    compare_cmd.add_argument("--title", default="Comparative study")
    compare_cmd.add_argument("--parameter", choices=sorted(COMPARABLE_PARAMETERS), required=True)
    compare_cmd.add_argument("--baseline", type=float, required=True)
    compare_cmd.add_argument("--variant", type=float, required=True)
    compare_cmd.add_argument("--seeds", type=_parse_seeds, default=(3, 7, 11, 17, 23))
    compare_cmd.add_argument("--hosts", type=int, default=100)
    compare_cmd.add_argument("--steps", type=int, default=300)
    compare_cmd.add_argument("--threat-rate", type=float, default=0.018)
    compare_cmd.add_argument("--poison-fraction", type=float, default=0.08)
    compare_cmd.add_argument("--heterogeneity", type=float, default=0.12)
    compare_cmd.add_argument("--drift-step", type=int, default=-1)
    compare_cmd.add_argument("--drift-fraction", type=float, default=0.35)
    compare_cmd.add_argument("--drift-magnitude", type=float, default=0.22)
    compare_cmd.add_argument("--archive", default=".symbiont/studies.jsonl")
    compare_cmd.add_argument("--parent-study-id", default=None)
    compare_cmd.add_argument("--no-record", action="store_true")


def _parse_seeds(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one seed")
    return values


def _study_number(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def _study_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0%}"


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
    elif args.study_action == "compare":
        spec = ExperimentSpec(
            title=args.title,
            hosts=args.hosts,
            steps=args.steps,
            seed=args.seeds[0],
            threat_rate=args.threat_rate,
            poison_fraction=args.poison_fraction,
            heterogeneity=args.heterogeneity,
            drift_step=None if args.drift_step < 0 else args.drift_step,
            drift_fraction=args.drift_fraction,
            drift_magnitude=args.drift_magnitude,
            delay=0.0,
        )
        study = run_comparative_study(
            spec,
            parameter=args.parameter,
            baseline_value=args.baseline,
            variant_value=args.variant,
            seeds=args.seeds,
            title=args.title,
        )
        interpretation = interpret_study(study)

        record = None
        if not args.no_record:
            archive = StudyArchive(args.archive)
            record = archive.append(
                spec,
                study,
                interpretation,
                source="cli",
                parent_record_id=args.parent_study_id,
            )

        print(f"SYMBIONT LAB — {study.title}")
        if record:
            print(f"study id:  {record.record_id}")
            if record.parent_record_id:
                print(f"parent:    {record.parent_record_id}")
        print(f"parameter: {study.parameter}")
        print(f"seeds:     {', '.join(map(str, study.seeds))}")
        print(f"baseline:  {study.baseline.parameter_value}")
        print(f"variant:   {study.variant.parameter_value}")
        print()
        print(
            f"{'metric':38} {'baseline':>11} {'variant':>11} {'delta':>11} "
            f"{'agree':>8} {'pairs':>7} {'σ Δ':>9}"
        )
        for metric in METRICS:
            base = study.baseline.metrics[metric]
            variant = study.variant.metrics[metric]
            paired = study.paired_deltas[metric]
            print(
                f"{metric:38} {_study_number(base.mean):>11} {_study_number(variant.mean):>11} "
                f"{_study_number(study.delta(metric), signed=True):>11} "
                f"{_study_percent(paired.direction_agreement):>8} {paired.pairs:7d} "
                f"{_study_number(paired.stdev):>9}"
            )

        print("\nObserver interpretation")
        print(f"  {interpretation.summary}")
        print(f"  confidence: {interpretation.confidence:.0%}")
        for finding in interpretation.findings[:6]:
            if finding.classification != "stable" or finding.evidence != "weak":
                print(f"  - [{finding.evidence}] {finding.text}")

        follow = interpretation.follow_up
        print("\nSuggested next study")
        print(
            f"  {follow.parameter}: {follow.baseline:.4f} -> {follow.variant:.4f} "
            f"with ~{follow.recommended_seed_count} paired seeds"
        )
        print(f"  {follow.rationale}")
        if record:
            print(f"  continue lineage with --parent-study-id {record.record_id}")
        return 0
    return 1
