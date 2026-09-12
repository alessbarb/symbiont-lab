from __future__ import annotations

import argparse

from .evidence_study import EVIDENCE_METRICS, run_replicated_evidence_study


def _parse_seeds(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one seed")
    return values


def _number(value: float | None, *, percent: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{value:+.1%}" if signed else f"{value:.1%}"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired multi-seed Symbiont Lab second-look studies"
    )
    parser.add_argument("--seeds", type=_parse_seeds, default=(3, 7, 11, 17, 23))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--budget", type=int, default=-1)
    parser.add_argument("--sensor-noise", type=float, default=0.18)
    parser.add_argument("--reference", default="random")
    args = parser.parse_args()

    study = run_replicated_evidence_study(
        seeds=args.seeds,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget=None if args.budget < 0 else args.budget,
        sensor_noise=args.sensor_noise,
        reference_strategy=args.reference,
    )

    print("SYMBIONT LAB — replicated bounded-evidence study")
    print(f"seeds:      {', '.join(map(str, study.seeds))}")
    print(f"reference:  {study.reference_strategy}")
    print(f"budgets:    {', '.join(map(str, study.budgets))}")
    print()
    print(
        f"{'selector':18} {'Brier gain':>11} {'entropy Δ':>11} {'net fixes':>10} "
        f"{'threat share':>13} {'stealth share':>13}"
    )
    for strategy in study.strategies:
        summary = study.summaries[strategy].metrics
        print(
            f"{strategy:18} {_number(summary['brier_gain'].mean):>11} "
            f"{_number(summary['mean_entropy_reduction'].mean):>11} "
            f"{_number(summary['net_correction_rate'].mean, percent=True):>10} "
            f"{_number(summary['selected_threat_share'].mean, percent=True):>13} "
            f"{_number(summary['stealth_share'].mean, percent=True):>13}"
        )

    print(f"\nPaired deltas vs {study.reference_strategy}")
    for strategy, metrics in study.paired_vs_reference.items():
        print(f"  {strategy}")
        for metric in EVIDENCE_METRICS:
            delta = metrics[metric]
            if metric not in {
                "brier_gain",
                "mean_entropy_reduction",
                "net_correction_rate",
                "stealth_share",
            }:
                continue
            agreement = "N/A" if delta.direction_agreement is None else f"{delta.direction_agreement:.0%}"
            print(
                f"    {metric:28} Δ={_number(delta.mean, signed=True):>9} "
                f"agree={agreement:>5} pairs={delta.pairs}"
            )


if __name__ == "__main__":
    main()
