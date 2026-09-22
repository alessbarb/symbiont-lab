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
    parser.add_argument("--arm", choices=("k1-a", "k1-b", "k2"), default="k1-a")
    default_nodes = [64, 96, 128, 160, 192, 256, 384, 512]
    parser.add_argument("--nodes", nargs="+", type=int, default=default_nodes)
    parser.add_argument("--edges", nargs="+", type=int, help="K2 max_edges values")
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
