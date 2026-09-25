from __future__ import annotations

import argparse

from symbiont.simulation import run_simulation


def build_simulate_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--hosts", type=int, default=100, help="Number of synthetic hosts")
    parser.add_argument("--steps", type=int, default=300, help="Simulation steps")
    parser.add_argument("--seed", type=int, default=7, help="Simulation master seed")
    parser.add_argument("--threat-rate", type=float, default=0.018, help="Pathogen injection rate")
    parser.add_argument(
        "--poison-fraction", type=float, default=0.08, help="Fraction of inverted reporters"
    )
    parser.add_argument("--heterogeneity", type=float, default=0.12, help="Host trait diversity")
    parser.add_argument(
        "--drift-step", type=int, default=None, help="Step at which benign drift occurs"
    )
    parser.add_argument(
        "--drift-fraction", type=float, default=0.35, help="Fraction of hosts shifted"
    )
    parser.add_argument(
        "--drift-magnitude", type=float, default=0.22, help="Drift baseline shift magnitude"
    )


def run_simulate_command(args: argparse.Namespace) -> int:
    result, _ = run_simulation(
        hosts=args.hosts,
        steps=args.steps,
        seed=args.seed,
        threat_rate=args.threat_rate,
        poison_fraction=args.poison_fraction,
        heterogeneity=args.heterogeneity,
        drift_step=args.drift_step,
        drift_fraction=args.drift_fraction,
        drift_magnitude=args.drift_magnitude,
    )
    print("=== Symbiont Simulation Result ===")
    print(f"Hosts: {result.hosts}, Steps: {result.steps}, Seed: {args.seed}")
    print(f"Pathogen events: {result.pathogen_events}, Benign events: {result.benign_events}")
    print(
        f"Attention Recall: {result.attention_recall:.3f}"
        if result.attention_recall is not None
        else "Attention Recall: N/A"
    )
    print(
        f"Attention Precision: {result.attention_precision:.3f}"
        if result.attention_precision is not None
        else "Attention Precision: N/A"
    )
    print(
        f"Classification Precision: {result.classification_precision:.3f}"
        if result.classification_precision is not None
        else "Classification Precision: N/A"
    )
    print(f"Calibration Error (ECE): {result.calibration_error:.4f}")
    print(f"Brier Score: {result.brier_score:.4f}")
    return 0
