"""Deterministic founder placement and the multi-organism Genesis v1
runtime (docs/design/symbiont-world-v2.md §4).

Occupancy/simultaneous-intent resolution were built in W1 and never
exercised with more than one occupant -- this is the first real test of
that machinery under load.
"""
from __future__ import annotations

from dataclasses import dataclass

from symbiont.core.behavior import ActionExecutionResult
from symbiont.core.physiology import VitalState

from symbiont_world.contracts import WorldObservation
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.observation import LOCAL_OCCUPANCY_SIGNAL, local_observation
from symbiont_world.rng import derive_world_rng
from symbiont_world.state import WorldState
from symbiont_world.topology import HexCoord, HexTopology, WorldBody

from .adapter import WorldTickRecord, _act, _construct_organism


def founder_placement(world_seed: int, topology: HexTopology, count: int) -> tuple[HexCoord, ...]:
    """Deterministic seed -> distinct starting cells (docs/design/
    symbiont-world-v2.md §4). No minimum dispersion guarantee in v2."""
    if count < 1:
        raise ValueError("count must be at least 1")
    total_cells = topology.width * topology.height
    if count > total_cells:
        raise ValueError("count exceeds available cells in topology")

    rng = derive_world_rng(world_seed, "genesis.founder-placement")
    all_cells = [HexCoord(q, r) for q in range(topology.width) for r in range(topology.height)]
    chosen: list[HexCoord] = []
    pool = list(all_cells)
    for _ in range(count):
        index = rng.randrange(len(pool))
        chosen.append(pool.pop(index))
    return tuple(chosen)


@dataclass(frozen=True, slots=True)
class PopulationTickRecord:
    tick: int
    per_organism: dict[str, WorldTickRecord]


class PopulationGenesisRuntime:
    """Runs N ModeledOrganismRuntime instances inside one shared Genesis
    v1 world. v2 scope only (docs/design/symbiont-world-v2.md §4): no
    movement, no communication, no reproduction -- each organism is
    stationary at its founder cell. Per-tick order is deterministic
    (sorted organism_id), never dict iteration order (v1 §5)."""

    def __init__(
        self,
        *,
        organism_ids: tuple[str, ...],
        world_seed: int,
        ground_truth: GroundTruth,
        topology: HexTopology,
        start_cells: tuple[HexCoord, ...],
        world_id: str = "genesis-v1-population",
        policy: str = "cognitive",
        sensory_plasticity: bool = False,
        discover_senses: bool = False,
    ) -> None:
        if len(organism_ids) != len(start_cells):
            raise ValueError("organism_ids and start_cells must be the same length")
        if len(set(organism_ids)) != len(organism_ids):
            raise ValueError("organism_ids must be unique")

        self.world_seed = world_seed
        self.topology = topology
        self.environment = WorldEnvironment(ground_truth)
        self.state = WorldState(world_id=world_id)
        self._rigs = {}
        self.history: list[PopulationTickRecord] = []

        for index, (organism_id, cell) in enumerate(sorted(zip(organism_ids, start_cells))):
            if not self.state.occupancy.occupy(cell, organism_id):
                raise ValueError(f"start_cell {cell} already occupied (organism {organism_id!r})")
            self.state.bodies[organism_id] = WorldBody(organism_id=organism_id, occupied_cell=cell)
            self._rigs[organism_id] = _construct_organism(
                organism_id=organism_id,
                world_id=world_id,
                world_seed=world_seed,
                organism_seed=world_seed + index,
                ground_truth=ground_truth,
                policy=policy,
                sensory_plasticity=sensory_plasticity,
                discover_senses=discover_senses,
            )

    @property
    def organism_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._rigs))

    def is_alive(self, organism_id: str) -> bool:
        return self._rigs[organism_id].runtime._physiology.state is not VitalState.DEAD

    def any_alive(self) -> bool:
        return any(self.is_alive(organism_id) for organism_id in self._rigs)

    def run_tick(self) -> PopulationTickRecord:
        current_tick = self.state.tick
        per_organism: dict[str, WorldTickRecord] = {}

        with self.state.begin_tick():
            self.environment.propagate_fields(current_tick)

            for organism_id in self.organism_ids:
                rig = self._rigs[organism_id]
                if self.is_alive(organism_id) is False:
                    continue

                cell = self.state.bodies[organism_id].occupied_cell
                self.environment.renew_resources(cell)

                pre_pool = dict(self.environment.resource_pool(cell))
                for resource_id, habitat in rig.resource_habitats.items():
                    habitat.set_environment_resources(pre_pool.get(resource_id, 0.0))

                observation = local_observation(
                    self.topology, self.state.occupancy, self.state.bodies[organism_id], self.environment
                )
                rig.reading_provider.set_observation(observation)

                rig.runtime.tick()
                action_result = _act(rig)

                for resource_id, habitat in rig.resource_habitats.items():
                    consumed = pre_pool.get(resource_id, 0.0) - habitat.snapshot().available_resources
                    if consumed > 0.0:
                        self.environment.acquire(cell, resource_id, consumed)

                density = observation.signals.get(LOCAL_OCCUPANCY_SIGNAL, 0.0)
                hazard_hits: list[str] = []
                if self.is_alive(organism_id):
                    for hazard_id, exposure in self.environment.hazard_exposures_at(cell, density).items():
                        rng = derive_world_rng(self.world_seed, f"hazard.{hazard_id}:{organism_id}:{current_tick}")
                        if rng.random() < exposure:
                            rig.runtime.apply_environmental_damage(0.05)
                            hazard_hits.append(hazard_id)

                per_organism[organism_id] = WorldTickRecord(
                    tick=current_tick,
                    observation=observation,
                    action=action_result,
                    hazard_hits=tuple(hazard_hits),
                    alive=self.is_alive(organism_id),
                )

        record = PopulationTickRecord(tick=current_tick, per_organism=per_organism)
        self.history.append(record)
        return record

    def run(self, ticks: int) -> tuple[PopulationTickRecord, ...]:
        records: list[PopulationTickRecord] = []
        for _ in range(ticks):
            if not self.any_alive():
                break
            records.append(self.run_tick())
        return tuple(records)
