from __future__ import annotations

import argparse

from .evidence import run_second_look_study


def _value(value: float | None, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a shadow-only synthetic second-look evidence study"
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
    parser.add_argument("--budget", type=int, default=-1)
    parser.add_argument("--sensor-noise", type=float, default=0.18)
    args = parser.parse_args()

    study = run_second_look_study(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        budget=None if args.budget < 0 else args.budget,
        sensor_noise=args.sensor_noise,
    )

    print("SYMBIONT LAB — bounded synthetic second look")
    print(f"hosts / steps / seed: {study.hosts} / {study.steps} / {study.seed}")
    print(
        f"second-look budget: {study.budget} measurements "
        f"({study.budget_per_1000:.2f} / 1000 events)"
    )
    print(f"sensor noise: {study.sensor_noise:.3f}")
    print("shadow-only: measurements do not feed back into agents\n")
    print(
        f"{'selector':18} {'threat share':>12} {'pre Brier':>11} {'post Brier':>12} "
        f"{'gain':>9} {'Δ entropy':>10} {'fixed':>7} {'broken':>7} {'stealth':>8}"
    )
    for row in study.outcomes:
        print(
            f"{row.strategy:18} {_value(row.selected_threat_share, percent=True):>12} "
            f"{_value(row.pre_brier):>11} {_value(row.post_brier):>12} "
            f"{_value(row.brier_gain):>9} {_value(row.mean_entropy_reduction):>10} "
            f"{row.corrected_errors:7d} {row.introduced_errors:7d} {row.stealth_selected:8d}"
        )


if __name__ == "__main__":
    main()
