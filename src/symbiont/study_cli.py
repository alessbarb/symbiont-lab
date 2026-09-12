from __future__ import annotations

import argparse

from .experiment import ExperimentSpec
from .study import COMPARABLE_PARAMETERS, METRICS, run_comparative_study


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

    print(f"SYMBIONT LAB — {study.title}")
    print(f"parameter: {study.parameter}")
    print(f"seeds:     {', '.join(map(str, study.seeds))}")
    print(f"baseline:  {study.baseline.parameter_value}")
    print(f"variant:   {study.variant.parameter_value}")
    print()
    print(f"{'metric':34} {'baseline':>11} {'variant':>11} {'delta':>11} {'σ base':>9} {'σ var':>9}")
    for metric in METRICS:
        base = study.baseline.metrics[metric]
        variant = study.variant.metrics[metric]
        print(
            f"{metric:34} {base.mean:11.4f} {variant.mean:11.4f} "
            f"{study.delta(metric):+11.4f} {base.stdev:9.4f} {variant.stdev:9.4f}"
        )


if __name__ == "__main__":
    main()
