"""W02 retry with a real divergence mechanism (docs/design/
symbiont-world-v2.md §5).

v1's audit (../genesis-v1/audit.md) found organism_seed alone has no
causal path to a lone organism's action trajectory with
exploration=0.0, discover_senses=False, no reproduction. This retry
activates sensory_plasticity=True/discover_senses=True (both already
exist in symbiont, no core change) to give divergence an actual
mechanism.

Preregistered metric (frozen before running): two replicas, same
world_seed/GroundTruth/starting cell, different organism_seed.
diverges = True if EITHER the action_counts distribution OR the set of
developed percept names differ between replicas after N ticks. This is
an honest re-run, not a guaranteed-positive rematch: whatever comes out
is reported as-is.
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

TICKS = 300
START_CELL = HexCoord(4, 4)
TOPOLOGY = HexTopology(width=8, height=8)


def run_replica(world_seed: int, organism_seed: int, label: str) -> dict:
    runtime = SingleOrganismGenesisRuntime(
        organism_id=f"w02-retry-{label}",
        world_seed=world_seed,
        organism_seed=organism_seed,
        ground_truth=build_ground_truth(),
        topology=TOPOLOGY,
        start_cell=START_CELL,
        policy="cognitive",
        sensory_plasticity=True,
        discover_senses=True,
    )
    records = runtime.run(TICKS)
    developed = set(runtime.runtime.adaptive_senses.developed_percept_names())
    return {
        "world_seed": world_seed,
        "organism_seed": organism_seed,
        "ticks_run": len(records),
        "alive": runtime.is_alive(),
        "action_counts": dict(Counter(r.action.action_id for r in records)),
        "developed_percept_names": sorted(developed),
    }


def w02_retry(world_seed: int = 101) -> dict:
    replica_a = run_replica(world_seed, world_seed + 1000, "a")
    replica_b = run_replica(world_seed, world_seed + 2000, "b")
    diverges_actions = replica_a["action_counts"] != replica_b["action_counts"]
    diverges_senses = replica_a["developed_percept_names"] != replica_b["developed_percept_names"]
    return {
        "replica_a": replica_a,
        "replica_b": replica_b,
        "diverges_actions": diverges_actions,
        "diverges_senses": diverges_senses,
        "diverges": diverges_actions or diverges_senses,
    }


if __name__ == "__main__":
    result = w02_retry()
    print(json.dumps(result, indent=2))
    Path(__file__).with_name("w02_retry_results.json").write_text(json.dumps(result, indent=2))
