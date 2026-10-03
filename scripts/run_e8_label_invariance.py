#!/usr/bin/env python3
"""Run the preregistered E8 label-invariance protocol for exactly one seed."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _domain in ("symbiont", "environment", "modality", "embodiment", "lab"):
    sys.path.insert(0, str(ROOT / _domain / "src"))

from lab.studies.embodiment.label_invariance import run_label_invariance_study


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, action="append", required=True)
    args = parser.parse_args()
    if len(args.seed) != 1:
        parser.error("exactly one --seed is required")
    seed = args.seed[0]
    declared_seed = int(os.environ.get("SYMBIONT_SEED", seed))
    if declared_seed != seed:
        parser.error("--seed must equal the launcher-declared SYMBIONT_SEED")
    result = run_label_invariance_study(seeds=(seed,), steps=300)
    print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
