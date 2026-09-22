#!/usr/bin/env python3
"""Run the experimental-only K1 kernel capacity screen.

The command creates per-run manifests and never changes ``KernelLimits()``
defaults or resident checkpoints. K1-A is the cheap abstract arm; K1-B is an
explicitly headless Physics3D follow-up.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from symbiont_lab.kernel_characterization.config import KernelVariant
from symbiont_lab.kernel_characterization.protocols import DEFAULT_SEEDS
from symbiont_lab.kernel_characterization.runner import write_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("k1-a", "k1-b", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k10", "k11", "k12"), default="k1-a")
    default_nodes = [64, 96, 128, 160, 192, 256, 384, 512]
    parser.add_argument("--nodes", nargs="+", type=int, default=default_nodes)
    parser.add_argument("--edges", nargs="+", type=int, help="K2 max_edges values")
    parser.add_argument("--concepts", nargs="+", type=int, help="K3 max_concepts values")
    parser.add_argument("--mutations", nargs="+", type=int, help="K4 mutation budget values")
    parser.add_argument("--tentative", nargs="+", type=int, help="K5 tentative-edge values")
    parser.add_argument("--intervals", nargs="+", type=int, help="K6 consolidation intervals")
    parser.add_argument("--support", nargs="+", type=int, help="K7 slow-support epoch values")
    parser.add_argument("--fast-thresholds", nargs="+", type=float, help="K8 fast-gate thresholds")
    parser.add_argument("--fast-reliabilities", nargs="+", type=float, help="K8 fast-gate reliability values")
    parser.add_argument("--capacities", nargs="+", type=int, help="K9 memory capacity values")
    parser.add_argument("--norms", nargs="+", type=float, help="K10 incoming weight norms")
    parser.add_argument("--reacclimation", nargs="+", type=int, help="K11 restore reacclimation values")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--ticks-per-phase", type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/kernel-characterization/capacity/runs"))
    args = parser.parse_args()
    if args.arm == "k2":
        edge_values = args.edges or [384, 768, 1152, 1536, 2304, 3072, 4608, 6144]
        variants = [KernelVariant(max_nodes=192, max_edges=value) for value in dict.fromkeys([*edge_values, 1536])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k2")
        print(run_dir)
        return 0
    if args.arm == "k3":
        concept_values = args.concepts or [8, 16, 24, 32, 48, 64, 96, 128]
        variants = [KernelVariant(max_nodes=192, max_concepts=value) for value in dict.fromkeys([*concept_values, 32])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k3")
        print(run_dir)
        return 0
    if args.arm in {"k4", "k5"}:
        if args.arm == "k4":
            values = args.mutations or [1, 2, 4, 8, 12, 16, 24, 32]
            variants = [KernelVariant(max_nodes=192, max_structural_mutations_per_consolidation=value) for value in dict.fromkeys([*values, 8])]
        else:
            values = args.tentative or [16, 32, 64, 128, 256, 512]
            variants = [KernelVariant(max_nodes=192, max_tentative_edges=value) for value in dict.fromkeys([*values, 128])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm=args.arm)
        print(run_dir)
        return 0
    if args.arm == "k6":
        values = args.intervals or [4, 8, 16, 32, 64, 128]
        variants = [KernelVariant(max_nodes=192, consolidation_interval_ticks=value) for value in dict.fromkeys([*values, 32])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k6")
        print(run_dir)
        return 0
    if args.arm == "k7":
        values = args.support or [1, 2, 3, 4, 6, 8]
        variants = [KernelVariant(max_nodes=192, slow_support_epochs=value) for value in dict.fromkeys([*values, 4])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k7")
        print(run_dir)
        return 0
    if args.arm == "k8":
        thresholds = args.fast_thresholds or [0.6, 0.7, 0.8, 0.9, 0.95]
        reliabilities = args.fast_reliabilities or [0.4, 0.6, 0.8, 0.9]
        variants = [
            KernelVariant(max_nodes=192, fast_consolidation_threshold=threshold, fast_min_reliability=reliability)
            for threshold in thresholds for reliability in reliabilities
        ]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k8")
        print(run_dir)
        return 0
    if args.arm == "k9":
        values = args.capacities or [16, 32, 64, 128, 256, 512]
        variants = [KernelVariant(max_nodes=192, max_consolidation_candidates=value, max_salient_event_traces=value) for value in dict.fromkeys([*values, 256])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k9")
        print(run_dir)
        return 0
    if args.arm == "k10":
        values = args.norms or [2, 4, 6, 8, 12, 16, 24, 32]
        variants = [KernelVariant(max_nodes=192, max_incoming_consolidated_weight_norm=value) for value in dict.fromkeys([*values, 8])]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k10")
        print(run_dir)
        return 0
    if args.arm == "k11":
        values = args.reacclimation or [0, 4, 8, 16, 32, 64, 128]
        variants = [KernelVariant(max_nodes=192, reacclimation_ticks=value) for value in dict.fromkeys([*values, 32]) if value > 0]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k11")
        print(run_dir)
        return 0
    if args.arm == "k12":
        variants = [
            KernelVariant(max_nodes=nodes, max_edges=nodes * density, max_concepts=concepts, max_structural_mutations_per_consolidation=mutations)
            for nodes in (192, 256, 384) for density in (6, 10, 16) for concepts in (32, 64) for mutations in (4, 8, 16)
        ]
        run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm="k12")
        print(run_dir)
        return 0
    if args.arm == "k1-b" and args.nodes == default_nodes:
        args.nodes = [192, 256, 384, 512]
    elif args.arm == "k1-b" and any(value < 192 for value in args.nodes):
        parser.error("K1-B Physics3D requires node values >= 192")
    # The 192-node control is mandatory even when a caller supplies a reduced
    # exploratory list.
    node_values = list(dict.fromkeys([*args.nodes, 192]))
    variants = [KernelVariant(max_nodes=value) for value in node_values]
    run_dir = write_run(args.output_dir, variants, tuple(args.seeds), args.ticks_per_phase, arm=args.arm)
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
