from __future__ import annotations

import argparse

from .evidence_noise_sweep import NOISE_METRICS, run_evidence_noise_sweep


def _parse_ints(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one seed")
    return values


def _parse_floats(raw: str) -> tuple[float, ...]:
    values = tuple(float(part.strip()) for part in raw.split(",") if part.strip())
    if not values:
        raise argparse.ArgumentTypeError("provide at least one noise level")
    return values


def _number(value: float | None, *, percent: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{value:+.1%}" if signed else f"{value:.1%}"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweep synthetic second-look sensor noise across paired validation seeds"
    )
    parser.add_argument("--seeds", type=_parse_ints, default=(211, 223, 239, 251, 269))
    parser.add_argument("--noise-levels", type=_parse_floats, default=(0.08, 0.18, 0.30, 0.45))
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--budget-per-1000", type=float, default=12.0)
    args = parser.parse_args()

    sweep = run_evidence_noise_sweep(
        seeds=args.seeds,
        noise_levels=args.noise_levels,
        hosts=args.hosts,
        steps=args.steps,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget_per_1000=args.budget_per_1000,
    )

    print("SYMBIONT LAB — second-look sensor noise sweep")
    print(f"seeds: {', '.join(map(str, sweep.seeds))}")
    print(f"noise: {', '.join(f'{value:g}' for value in sweep.noise_levels)}")
    print(f"budget: {sweep.budget} ({sweep.budget_per_1000:g}/1000)")

    for noise in sweep.noise_levels:
        print(f"\nNoise {noise:g}")
        print(f"{'strategy':18} {'Brier gain':>11} {'Brier +':>8} {'net corr':>9} {'stealth corr':>12}")
        for strategy in sweep.strategies:
            metrics = sweep.summaries[noise][strategy].metrics
            print(
                f"{strategy:18} "
                f"{_number(metrics['brier_gain'].mean, signed=True):>11} "
                f"{_number(metrics['brier_gain'].positive_fraction, percent=True):>8} "
                f"{_number(metrics['net_correction_rate'].mean, percent=True, signed=True):>9} "
                f"{_number(metrics['stealth_correction_rate'].mean, percent=True):>12}"
            )

    if len(sweep.noise_levels) > 1:
        reference = sweep.noise_levels[0]
        print(f"\nPaired degradation vs noise {reference:g}")
        for noise, strategies in sweep.paired_vs_lowest_noise.items():
            print(f"  noise {noise:g}")
            for strategy, metrics in strategies.items():
                delta = metrics['brier_gain']
                agreement = "N/A" if delta.direction_agreement is None else f"{delta.direction_agreement:.0%}"
                print(
                    f"    {strategy:18} Δ Brier gain={_number(delta.mean, signed=True)} "
                    f"direction={agreement} n={delta.pairs}"
                )

    print("\nSensor evidence remains shadow-only; no measurement changes a live agent decision.")


if __name__ == "__main__":
    main()
