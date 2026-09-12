from __future__ import annotations

import argparse

from .longitudinal import run_longitudinal_species


def _delta(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run paired synthetic generations with bounded abstract heritage"
    )
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--hosts", type=int, default=100)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--threat-rate", type=float, default=0.018)
    parser.add_argument("--poison-fraction", type=float, default=0.08)
    parser.add_argument("--heterogeneity", type=float, default=0.12)
    parser.add_argument("--drift-step", type=int, default=-1)
    parser.add_argument("--drift-fraction", type=float, default=0.35)
    parser.add_argument("--drift-magnitude", type=float, default=0.22)
    parser.add_argument("--heritage-limit", type=int, default=24)
    args = parser.parse_args()

    result = run_longitudinal_species(
        generations=args.generations,
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=None if args.drift_step < 0 else args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
        heritage_limit=args.heritage_limit,
    )

    print("SYMBIONT LAB — longitudinal species")
    print(
        f"{'gen':>3} {'seed':>6} {'in':>4} {'out':>4} {'retain':>8} "
        f"{'Δ detect':>10} {'Δ precision':>12} {'Δ FP':>9} {'Δ calib':>10} {'Δ blind':>10}"
    )
    for item in result.generations:
        print(
            f"{item.generation:3d} {item.seed:6d} {item.inherited_patterns:4d} "
            f"{item.exported_patterns:4d} {item.retention_rate:8.1%} "
            f"{_delta(item.detection_delta):>10} {_delta(item.precision_delta):>12} "
            f"{_delta(item.false_positive_delta):>9} {_delta(item.calibration_delta):>10} "
            f"{_delta(item.blind_spot_delta):>10}"
        )

    print("\nMean inherited − naive control (heritage-active generations only)")
    print(f"  generations:    {result.heritage_effect_generations}")
    print(f"  detection:      {_delta(result.mean_detection_delta)}")
    print(f"  precision:      {_delta(result.mean_precision_delta)}")
    print(f"  false positives:{_delta(result.mean_false_positive_delta)}")
    print(f"  classification recall:    {_delta(result.mean_classification_recall_delta)}")
    print(f"  classification precision: {_delta(result.mean_classification_precision_delta)}")
    print(f"  calibration:    {_delta(result.mean_calibration_delta)}")
    print(f"  blind spots:    {_delta(result.mean_blind_spot_delta)}")
    print(f"  final heritage: {len(result.final_heritage.patterns)} abstract patterns")
    print("\nHeritage contains only bounded synthetic fingerprint priors; no code, host memory or source reputation is inherited.")


if __name__ == "__main__":
    main()
