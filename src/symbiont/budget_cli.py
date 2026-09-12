from __future__ import annotations

import argparse

from .budget import run_attention_budget_analysis


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare observer-side attention strategies at equal investigation budgets"
    )
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    args = parser.parse_args()

    analysis = run_attention_budget_analysis(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
    )

    print("SYMBIONT LAB — equal-attention budget analysis")
    print(f"hosts / steps / seed: {analysis.hosts} / {analysis.steps} / {analysis.seed}")
    print(
        f"natural policy budget: {analysis.natural_budget} investigations "
        f"({analysis.natural_budget_per_1000:.2f} / 1000 events)"
    )
    print()
    print(
        f"{'strategy':16} {'budget/1k':>10} {'recall':>9} {'precision':>10} "
        f"{'benign FPR':>10} {'stealth':>9} {'special benign':>15}"
    )
    for row in analysis.matched:
        print(
            f"{row.strategy:16} {row.investigations_per_1000:10.2f} "
            f"{_pct(row.threat_recall):>9} {_pct(row.precision):>10} "
            f"{_pct(row.benign_false_positive_rate):>10} {_pct(row.stealth_recall):>9} "
            f"{_pct(row.benign_special_share):>15}"
        )

    print("\nThreat-family recall at matched budget")
    for row in analysis.matched:
        ransomware = row.family_recall.get("pathogen:ransom_sim")
        bot = row.family_recall.get("pathogen:bot_sim")
        stealth = row.family_recall.get("pathogen:stealth_sim")
        print(
            f"  {row.strategy:14} ransom={_pct(ransomware):>7} "
            f"bot={_pct(bot):>7} stealth={_pct(stealth):>7}"
        )

    print("\nBudget curves (observer-side rankings)")
    for strategy, points in analysis.curves.items():
        print(f"  {strategy}")
        for point in points:
            print(
                f"    {point.investigations_per_1000:6.1f}/1k  "
                f"recall={_pct(point.threat_recall):>7}  "
                f"precision={_pct(point.precision):>7}  "
                f"stealth={_pct(point.stealth_recall):>7}"
            )


if __name__ == "__main__":
    main()
