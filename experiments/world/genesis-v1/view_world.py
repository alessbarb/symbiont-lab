"""Thin CLI launcher: run a Genesis v1 population for N ticks and print the
read-only world view (docs/design/symbiont-world-v2.md §8). All logic lives
in symbiont_lab.world.cli_view.render_world (a pure function); this script
only calls it and prints.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from symbiont_lab.world.cli_view import render_world
from symbiont_lab.world.genesis_v1 import GENESIS_V1_METADATA, build_ground_truth
from symbiont_lab.world.population import PopulationGenesisRuntime, founder_placement
from symbiont_world.topology import HexTopology

WORLD_SEED = 101
FOUNDERS = 8
TICKS = 50


def main() -> None:
    topology = HexTopology(width=8, height=8)
    ground_truth = build_ground_truth()
    cells = founder_placement(WORLD_SEED, topology, FOUNDERS)
    population = PopulationGenesisRuntime(
        organism_ids=tuple(f"founder-{i}" for i in range(FOUNDERS)),
        world_seed=WORLD_SEED,
        ground_truth=ground_truth,
        topology=topology,
        start_cells=cells,
    )
    population.run(TICKS)
    print(render_world(population.state, population.environment, ground_truth, GENESIS_V1_METADATA, topology))


if __name__ == "__main__":
    main()
