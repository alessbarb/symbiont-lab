from __future__ import annotations

import argparse

from .heritage_stress import run_heritage_stress_study


def _number(value: float | None, *, percent: bool = False, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{value:+.1%}" if signed else f"{value:.1%}"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stress synthetic inherited priors against a fixed target world"
    )
    parser.add_argument("--source-seed", type=int, default=7)
    parser.add_argument("--target-seed", type=int, default=1016)
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

    study = run_heritage_stress_study(
        source_seed=args.source_seed,
        target_seed=args.target_seed,
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

    print("SYMBIONT LAB — heritage stress")
    print(f"source / target seed: {study.source_seed} / {study.target_seed}")
    print(f"learned source patterns: {study.source_patterns}")
    print()
    print(
        f"{'condition':12} {'priors':>6} {'attn R':>8} {'class R':>8} {'Brier':>8} "
        f"{'prior MAE':>10} {'final MAE':>10} {'gain':>9} {'override':>9} {'reexport':>9}"
    )
    for row in study.conditions:
        print(
            f"{row.name:12} {row.inherited_patterns:6d} "
            f"{_number(row.attention_recall, percent=True):>8} "
            f"{_number(row.classification_recall, percent=True):>8} "
            f"{row.brier_score:8.4f} {_number(row.prior_mae):>10} "
            f"{_number(row.combined_mae):>10} {_number(row.correction_gain):>9} "
            f"{_number(row.live_override_rate, percent=True):>9} "
            f"{_number(row.reexport_rate, percent=True):>9}"
        )
        if row.reexported_patterns:
            print(
                f"  re-exported {row.reexported_patterns}; direction flips={row.direction_flips}; "
                f"truth-evaluable={row.evaluable_reexports}; improved={row.improved_reexports}; "
                f"worsened={row.worsened_reexports}; "
                f"mean MAE gain={_number(row.mean_reexport_mae_gain, signed=True)}"
            )

    digests = {row.world_digest for row in study.conditions}
    print(f"\nfixed target world: {'yes' if len(digests) == 1 else 'NO'}")


if __name__ == "__main__":
    main()
