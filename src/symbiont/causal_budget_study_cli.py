from __future__ import annotations

import argparse

from .causal_budget_study import CAUSAL_METRICS, run_replicated_causal_budget_study


def _parse_ints(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one seed")
    return values


def _parse_floats(raw: str) -> tuple[float, ...]:
    values = tuple(float(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one budget")
    return values


def _number(value: float | None, *, percent: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{value:+.1%}" if signed else f"{value:.1%}"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replicate causal online attention selectors across paired seeds and budgets"
    )
    parser.add_argument("--seeds", type=_parse_ints, default=(101, 127, 149, 173, 199))
    parser.add_argument("--budgets-per-1000", type=_parse_floats, default=(5.0, 12.0, 20.0))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--reference-strategy", default="random")
    args = parser.parse_args()

    study = run_replicated_causal_budget_study(
        seeds=args.seeds,
        budgets_per_1000=args.budgets_per_1000,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        reference_strategy=args.reference_strategy,
    )

    print("SYMBIONT LAB — replicated causal attention")
    print(f"seeds: {', '.join(map(str, study.seeds))}")
    print(f"budgets / 1000: {', '.join(f'{value:g}' for value in study.budgets_per_1000)}")
    print(f"reference: {study.reference_strategy}")

    for budget in study.budgets_per_1000:
        print(f"\nBudget {budget:g} / 1000")
        print(
            f"{'strategy':14} {'recall':>8} {'precision':>9} {'benign FPR':>10} "
            f"{'stealth':>8} {'forced':>8}"
        )
        for strategy in study.strategies:
            metrics = study.summaries[budget][strategy].metrics
            print(
                f"{strategy:14} "
                f"{_number(metrics['threat_recall'].mean, percent=True):>8} "
                f"{_number(metrics['precision'].mean, percent=True):>9} "
                f"{_number(metrics['benign_false_positive_rate'].mean, percent=True):>10} "
                f"{_number(metrics['stealth_recall'].mean, percent=True):>8} "
                f"{_number(metrics['forced_share'].mean, percent=True):>8}"
            )

        print(f"  Paired deltas vs {study.reference_strategy}")
        for strategy, metrics in study.paired_vs_reference[budget].items():
            pieces: list[str] = []
            for metric in ("threat_recall", "precision", "stealth_recall", "forced_share"):
                delta = metrics[metric]
                agreement = (
                    "N/A" if delta.direction_agreement is None else f"{delta.direction_agreement:.0%}"
                )
                pieces.append(
                    f"{metric}={_number(delta.mean, signed=True)} ({agreement}, n={delta.pairs})"
                )
            print(f"    {strategy}: " + "; ".join(pieces))

    print("\nDirection agreement is descriptive, not statistical significance.")
    print("All selectors make irreversible online choices and receive equal ex-ante capacity within each world.")


if __name__ == "__main__":
    main()
