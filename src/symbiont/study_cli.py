from __future__ import annotations

import argparse

from .experiment import ExperimentSpec
from .interpretation import interpret_study
from .study import COMPARABLE_PARAMETERS, METRICS, run_comparative_study
from .study_archive import StudyArchive


def _parse_seeds(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one seed")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a reproducible Symbiont Lab comparative study")
    parser.add_argument("--title", default="Comparative study")
    parser.add_argument("--parameter", choices=sorted(COMPARABLE_PARAMETERS), required=True)
    parser.add_argument("--baseline", type=float, required=True)
    parser.add_argument("--variant", type=float, required=True)
    parser.add_argument("--seeds", type=_parse_seeds, default=(3, 7, 11, 17, 23))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--archive", default=".symbiont/studies.jsonl")
    parser.add_argument("--parent-study-id", default=None)
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()

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
        f"{'metric':34} {'baseline':>11} {'variant':>11} {'delta':>11} "
        f"{'agree':>8} {'σ Δ':>9}"
    )
    for metric in METRICS:
        base = study.baseline.metrics[metric]
        variant = study.variant.metrics[metric]
        paired = study.paired_deltas[metric]
        print(
            f"{metric:34} {base.mean:11.4f} {variant.mean:11.4f} "
            f"{study.delta(metric):+11.4f} {paired.direction_agreement:8.0%} {paired.stdev:9.4f}"
        )

    print("\nObserver interpretation")
    print(f"  {interpretation.summary}")
    print(f"  confidence: {interpretation.confidence:.0%}")
    for finding in interpretation.findings[:5]:
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


if __name__ == "__main__":
    main()
