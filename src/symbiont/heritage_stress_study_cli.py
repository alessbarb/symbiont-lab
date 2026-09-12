from __future__ import annotations

import argparse

from .heritage_stress_study import (
    HERITAGE_DIAGNOSTICS,
    PERFORMANCE_METRICS,
    run_replicated_heritage_stress_study,
)


def _parse_seeds(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one source seed")
    return values


def _number(value: float | None, *, percent: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{value:+.1%}" if signed else f"{value:.1%}"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired multi-world Symbiont heritage stress studies"
    )
    parser.add_argument("--source-seeds", type=_parse_seeds, default=(3, 7, 11, 17, 23))
    parser.add_argument("--target-offset", type=int, default=1009)
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--heritage-limit", type=int, default=24)
    args = parser.parse_args()

    study = run_replicated_heritage_stress_study(
        source_seeds=args.source_seeds,
        target_offset=args.target_offset,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        heritage_limit=args.heritage_limit,
    )

    print("SYMBIONT LAB — replicated heritage stress")
    print(f"source seeds: {', '.join(map(str, study.source_seeds))}")
    print(f"target seeds: {', '.join(map(str, study.target_seeds))}")
    print(f"target offset: {study.target_offset}")
    print(f"source pattern counts: {', '.join(map(str, study.source_pattern_counts))}")
    print()

    print(
        f"{'condition':12} {'attn R':>8} {'class R':>8} {'Brier':>8} "
        f"{'prior MAE':>10} {'final MAE':>10} {'gain':>9} {'reexport':>9}"
    )
    for name in study.conditions:
        metrics = study.summaries[name].metrics
        print(
            f"{name:12} "
            f"{_number(metrics['attention_recall'].mean, percent=True):>8} "
            f"{_number(metrics['classification_recall'].mean, percent=True):>8} "
            f"{_number(metrics['brier_score'].mean):>8} "
            f"{_number(metrics['prior_mae'].mean):>10} "
            f"{_number(metrics['combined_mae'].mean):>10} "
            f"{_number(metrics['correction_gain'].mean):>9} "
            f"{_number(metrics['reexport_rate'].mean, percent=True):>9}"
        )

    print("\nPaired performance deltas vs naive")
    for name, metrics in study.paired_vs_naive.items():
        print(f"  {name}")
        for metric in PERFORMANCE_METRICS:
            if metric not in {
                "attention_recall",
                "attention_precision",
                "classification_recall",
                "classification_precision",
                "brier_score",
                "high_confidence_miss_rate",
            }:
                continue
            delta = metrics[metric]
            agreement = (
                "N/A"
                if delta.direction_agreement is None
                else f"{delta.direction_agreement:.0%}"
            )
            print(
                f"    {metric:34} Δ={_number(delta.mean, signed=True):>9} "
                f"agree={agreement:>5} pairs={delta.pairs}"
            )

    print("\nHeritage diagnostics are summarized separately from performance deltas")
    for name in ("learned", "inverted", "misaligned"):
        metrics = study.summaries[name].metrics
        print(f"  {name}")
        for metric in HERITAGE_DIAGNOSTICS:
            if metric not in {
                "prior_mae",
                "live_mae",
                "combined_mae",
                "correction_gain",
                "live_override_rate",
                "reexport_rate",
                "direction_flips",
                "evaluable_reexports",
                "improved_reexports",
                "worsened_reexports",
                "mean_reexport_mae_gain",
            }:
                continue
            percent = metric in {"live_override_rate", "reexport_rate"}
            signed = metric in {"correction_gain", "mean_reexport_mae_gain"}
            print(
                f"    {metric:24} "
                f"{_number(metrics[metric].mean, percent=percent, signed=signed)}"
            )


if __name__ == "__main__":
    main()
