from __future__ import annotations

import argparse
from pprint import pprint

from symbiont_lab.studies.learning.prospective_agency_embodied import (
    run_prospective_embodied_study,
    run_prospective_embodied_trial,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the preregistered L8 prospective-agency Physics3D gate."
    )
    parser.add_argument("--seed", type=int, action="append")
    parser.add_argument("--warmup-ticks", type=int, default=5000)
    parser.add_argument("--horizon-ticks", type=int, default=256)
    parser.add_argument("--physics-substeps-per-tick", type=int, default=10)
    return parser


def main() -> int:
    args = _parser().parse_args()
    seeds = tuple(args.seed or (101,))

    if len(seeds) == 1:
        result = run_prospective_embodied_trial(
            seeds[0],
            warmup_ticks=args.warmup_ticks,
            horizon_ticks=args.horizon_ticks,
            physics_substeps_per_tick=args.physics_substeps_per_tick,
        )
    else:
        result = run_prospective_embodied_study(
            seeds=seeds,
            warmup_ticks=args.warmup_ticks,
            horizon_ticks=args.horizon_ticks,
            physics_substeps_per_tick=args.physics_substeps_per_tick,
        )

    pprint(result.as_dict(), sort_dicts=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
