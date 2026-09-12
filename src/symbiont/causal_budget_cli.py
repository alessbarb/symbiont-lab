from __future__ import annotations

import argparse

from .causal_budget import run_causal_attention_budget


def _number(value: float | None, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare irreversible online attention selectors under one ex-ante budget"
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
    parser.add_argument("--budget-per-1000", type=float, default=12.0)
    args = parser.parse_args()

    result = run_causal_attention_budget(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget_per_1000=args.budget_per_1000,
    )

    print("SYMBIONT LAB — causal online attention budget")
    print(
        f"events={result.events} eligible={result.eligible_events} budget={result.budget} "
        f"({result.budget_per_1000:.2f}/1000) seed={result.seed}"
    )
    print(
        f"{'strategy':14} {'selected':>8} {'forced':>7} {'zero':>6} "
        f"{'warmup':>7} {'pre':>6} {'post':>6} {'recall':>8} "
        f"{'precision':>9} {'benign FPR':>10} {'stealth':>8}"
    )
    for row in result.outcomes:
        print(
            f"{row.strategy:14} {row.selected:8d} {row.forced_selections:7d} "
            f"{row.zero_score_selections:6d} "
            f"{row.selected_by_phase.get('warmup', 0):7d} "
            f"{row.selected_by_phase.get('pre_drift', 0):6d} "
            f"{row.selected_by_phase.get('post_drift', 0):6d} "
            f"{_number(row.threat_recall, percent=True):>8} "
            f"{_number(row.precision, percent=True):>9} "
            f"{_number(row.benign_false_positive_rate, percent=True):>10} "
            f"{_number(row.stealth_recall, percent=True):>8}"
        )

    print(
        "\nSelectors share startup eligibility and see only the current/past synthetic stream. "
        "They cannot rank future scores."
    )


if __name__ == "__main__":
    main()
