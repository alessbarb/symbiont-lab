"""Preregistered W01/W02 runs against the real Genesis v1 adapter
(docs/design/symbiont-world-v1.md §8, §15).

W01: does a single Symbiont's own cognitive policy beat a uniform-random
policy on the same world, same seed, across independent seeds?
W02: do two independent runs of the identical config (same genome, same
starting cell, same world_seed) diverge in behavior due to internal
stochastic history the world_seed does not control?

Preregistered metric (frozen before running): composite_score = mean(reserve
across observation/cognition/persistence/maintenance) + homeostasis.integrity,
both components in [0, 1], so composite_score is in [0, 2]. Higher is
"better physiological trajectory." This is an evaluator-side metric never
fed to the organism.

Preregistered decision rule for W01 (n=3 seeds, informal small-n test,
matching the discipline of longitudinal-population-ecology-v1): reject H0
("cognitive == random") only if the cognitive policy's composite_score
exceeds the random policy's in at least 2 of 3 seeds. Otherwise H0 stands
(default expectation per §8: convergence/no-improvement).

This script performs no fabrication: whatever it prints is the actual
result of running the real adapter.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from symbiont_lab.world.adapter import SingleOrganismGenesisRuntime
from symbiont_lab.world.genesis_v1 import build_ground_truth
from symbiont_world.topology import HexCoord, HexTopology

SEEDS = (101, 127, 149)
TICKS = 300
START_CELL = HexCoord(4, 4)
TOPOLOGY = HexTopology(width=8, height=8)


def composite_score(runtime: SingleOrganismGenesisRuntime) -> float:
    snapshot = runtime.runtime.metabolism.snapshot()
    mean_reserve = sum(snapshot.reserve.values()) / len(snapshot.reserve)
    integrity = runtime.runtime.homeostasis.integrity
    return mean_reserve + integrity


def run_one(seed: int, policy: str, *, organism_seed: int | None = None, label: str = "") -> dict:
    runtime = SingleOrganismGenesisRuntime(
        organism_id=f"w01-{policy}-{seed}-{label or organism_seed}",
        world_seed=seed,
        organism_seed=organism_seed,
        ground_truth=build_ground_truth(),
        topology=TOPOLOGY,
        start_cell=START_CELL,
        policy=policy,
    )
    records = runtime.run(TICKS)
    return {
        "seed": seed,
        "organism_seed": runtime.organism_seed,
        "policy": policy,
        "ticks_run": len(records),
        "alive": runtime.is_alive(),
        "composite_score": composite_score(runtime),
        "action_counts": dict(Counter(r.action.action_id for r in records)),
        "hazard_hits": sum(len(r.hazard_hits) for r in records),
    }


def w01() -> dict:
    results = [run_one(seed, policy) for seed in SEEDS for policy in ("cognitive", "random")]
    wins = 0
    for seed in SEEDS:
        cognitive = next(r for r in results if r["seed"] == seed and r["policy"] == "cognitive")
        random_ = next(r for r in results if r["seed"] == seed and r["policy"] == "random")
        if cognitive["composite_score"] > random_["composite_score"]:
            wins += 1
    reject_h0 = wins >= 2
    return {"results": results, "cognitive_wins": wins, "of_seeds": len(SEEDS), "reject_h0": reject_h0}


def w02(seed: int = 101) -> dict:
    """Two operationalizations, both against the same world (same seed,
    same starting cell):

    - identical_clone: both replicas also share organism_seed. This is a
      determinism check (invariant 2), not a test of divergence -- with
      every source of randomness derived from the same two seeds, identical
      behavior is guaranteed by construction, not evidence about anything.
    - distinct_history: replicas share world_seed (same world) but differ
      in organism_seed (distinct internal stochastic history: mutation_seed
      and body_schema salt). This is the actual W02 operationalization the
      spec asks for (docs/design/symbiont-world-v1.md §8).
    """
    clone_a = run_one(seed, "cognitive", organism_seed=seed, label="clone-a")
    clone_b = run_one(seed, "cognitive", organism_seed=seed, label="clone-b")
    distinct_a = run_one(seed, "cognitive", organism_seed=seed + 1000, label="distinct-a")
    distinct_b = run_one(seed, "cognitive", organism_seed=seed + 2000, label="distinct-b")
    return {
        "identical_clone": {
            "replica_a": clone_a,
            "replica_b": clone_b,
            "diverges": clone_a["action_counts"] != clone_b["action_counts"],
        },
        "distinct_history": {
            "replica_a": distinct_a,
            "replica_b": distinct_b,
            "diverges": distinct_a["action_counts"] != distinct_b["action_counts"],
        },
    }


if __name__ == "__main__":
    w01_result = w01()
    w02_result = w02()
    output = {"w01": w01_result, "w02": w02_result}
    print(json.dumps(output, indent=2))
    out_path = Path(__file__).with_name("results.json")
    out_path.write_text(json.dumps(output, indent=2))
