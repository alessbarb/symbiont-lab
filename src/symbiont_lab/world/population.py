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

from symbiont_world.contracts import ReceivedEmission, WorldObservation
from symbiont_world.events import EventJournal, WorldEvent
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.observation import LOCAL_OCCUPANCY_SIGNAL, local_observation
from symbiont_world.rng import derive_world_rng
from symbiont_world.state import WorldState
from symbiont_world.topology import HexCoord, HexTopology, WorldBody

from .adapter import (
    ActuationBindingConstitution,
    WorldTickRecord,
    _act,
    _construct_organism,
)
from .deferred import DeferredEffectQueue
from .terrain import DynamicGeography
from .transaction import IntegratedWorldTickTransaction


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
        journal: EventJournal | None = None,
        deferred_queue: DeferredEffectQueue | None = None,
        geography: DynamicGeography | None = None,
        movement_enabled: bool = False,
        actuation_binding: ActuationBindingConstitution | None = None,
    ) -> None:
        if len(organism_ids) != len(start_cells):
            raise ValueError("organism_ids and start_cells must be the same length")
        if len(set(organism_ids)) != len(organism_ids):
            raise ValueError("organism_ids must be unique")

        self.world_seed = world_seed
        self.topology = topology
        self.ground_truth = ground_truth
        self.environment = WorldEnvironment(ground_truth)
        self.state = WorldState(world_id=world_id)
        self.journal = journal if journal is not None else EventJournal()
        self.deferred_queue = deferred_queue if deferred_queue is not None else DeferredEffectQueue()
        self.geography = (
            geography if geography is not None else DynamicGeography(topology, world_seed)
        )
        self.movement_enabled = movement_enabled
        self._actuation_binding_override = actuation_binding
        self._emissions: dict[str, tuple[int, ...]] = {}
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
                actuation_binding=actuation_binding,
            )

    def _observation_for(self, organism_id: str) -> WorldObservation:
        body = self.state.bodies[organism_id]
        base = local_observation(
            self.topology, self.state.occupancy, body, self.environment
        )
        reception: list[ReceivedEmission] = []
        for emitter_id, sequence in sorted(self._emissions.items()):
            if emitter_id == organism_id or emitter_id not in self.state.bodies:
                continue
            emitter_cell = self.state.bodies[emitter_id].occupied_cell
            distance = body.occupied_cell.distance(emitter_cell)
            if 0 < distance <= max(0, body.interaction_radius):
                reception.append(
                    ReceivedEmission(
                        sequence=sequence,
                        intensity=1.0 / float(distance),
                    )
                )
        return WorldObservation(
            signals=base.signals,
            contact=base.contact,
            reception=tuple(reception),
            internal=base.internal,
        )

    def _resolve_local_interaction(
        self,
        organism_id: str,
        action,
        *,
        cell: HexCoord,
        current_tick: int,
        tx: IntegratedWorldTickTransaction,
    ) -> None:
        if action is None or action.acquire != "local":
            return
        rig = self._rigs[organism_id]
        pool = self.environment.resource_pool(cell)
        available = [
            (resource_id, amount)
            for resource_id, amount in sorted(pool.items())
            if amount > 0.0 and resource_id in rig.resource_habitats
        ]
        if not available:
            tx.stage_event(WorldEvent(
                event_id=f"evt-{self.state.world_id}-{current_tick}-act-acq-{organism_id}",
                world_id=self.state.world_id,
                tick=current_tick,
                kind="ACTUATION_RESOLVED",
                actor=organism_id,
                position=f"{cell.q},{cell.r}",
                payload={"effect": "acquire", "outcome": "no_local_resource"},
            ))
            return
        # World/apparatus resolves the local physical surface; cognition never
        # receives the resource id through the motor command.
        resource_id, _ = max(available, key=lambda item: (item[1], item[0]))
        actuation = rig.runtime.last_actuation
        requested = min(0.25, max(0.0, actuation.delivered if actuation is not None else 0.0) * 0.25)
        if requested <= 0.0:
            return
        granted = rig.runtime.request_resource_intake(
            requested,
            kind="maintenance",
            resource_id=resource_id,
        )
        tx.stage_event(WorldEvent(
            event_id=f"evt-{self.state.world_id}-{current_tick}-act-acq-{organism_id}",
            world_id=self.state.world_id,
            tick=current_tick,
            kind="ACTUATION_RESOLVED",
            actor=organism_id,
            position=f"{cell.q},{cell.r}",
            payload={
                "effect": "acquire",
                "outcome": "granted" if granted > 0.0 else "no_transfer",
                "amount": granted,
            },
        ))

    @property
    def organism_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._rigs))

    def is_alive(self, organism_id: str) -> bool:
        return self._rigs[organism_id].runtime._physiology.state is not VitalState.DEAD

    def any_alive(self) -> bool:
        return any(self.is_alive(organism_id) for organism_id in self._rigs)

    def run_tick(self) -> PopulationTickRecord | None:
        current_tick = self.state.tick
        per_organism: dict[str, WorldTickRecord] = {}
        next_emissions: dict[str, tuple[int, ...]] = {}

        tx = IntegratedWorldTickTransaction(
            state=self.state,
            environment=self.environment,
            rigs=self._rigs,
            deferred_queue=self.deferred_queue,
            journal=self.journal,
            geography=self.geography,
        )
        with tx:
            self.environment.propagate_fields(current_tick)
            tx.stage_event(WorldEvent(
                event_id=f"evt-{self.state.world_id}-{current_tick}-fields",
                world_id=self.state.world_id,
                tick=current_tick,
                kind="WORLD_FIELD_CHANGED",
                actor=None,
                position=None,
                payload=dict(self.environment.field_values()),
            ))

            for organism_id in self.organism_ids:
                rig = self._rigs[organism_id]
                was_alive = self.is_alive(organism_id)
                if not was_alive:
                    continue

                cell = self.state.bodies[organism_id].occupied_cell
                self.environment.renew_resources(cell)
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-renew-{cell.q}_{cell.r}",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="RESOURCE_RENEWED",
                    actor=None,
                    position=f"{cell.q},{cell.r}",
                ))

                if self.deferred_queue is not None:
                    due_effects = self.deferred_queue.pop_due(organism_id, current_tick)
                    for effect_index, effect in enumerate(due_effects):
                        if self.is_alive(organism_id):
                            rig.runtime.apply_environmental_damage(effect.amount)
                            tx.stage_event(WorldEvent(
                                event_id=(
                                    f"evt-{self.state.world_id}-{current_tick}-defdmg-"
                                    f"{organism_id}-{effect_index}"
                                ),
                                world_id=self.state.world_id,
                                tick=current_tick,
                                kind="PHYSIOLOGICAL_DAMAGE",
                                actor=organism_id,
                                position=f"{cell.q},{cell.r}",
                                payload={
                                    "damage": effect.amount,
                                    "source": "deferred_effect",
                                    "due_tick": effect.due_tick,
                                    "effect_index": effect_index,
                                },
                            ))

                pre_pool = dict(self.environment.resource_pool(cell))
                for resource_id, habitat in rig.resource_habitats.items():
                    habitat.set_environment_resources(pre_pool.get(resource_id, 0.0))

                observation = self._observation_for(organism_id)
                rig.reading_provider.set_observation(observation)

                rig.runtime.tick()
                world_action = rig.actuation_adapter.translate(rig.runtime.last_actuation)
                self._resolve_local_interaction(
                    organism_id,
                    world_action,
                    cell=cell,
                    current_tick=current_tick,
                    tx=tx,
                )
                if world_action is not None and world_action.emit is not None:
                    next_emissions[organism_id] = tuple(world_action.emit)
                    tx.stage_event(WorldEvent(
                        event_id=f"evt-{self.state.world_id}-{current_tick}-emit-{organism_id}",
                        world_id=self.state.world_id,
                        tick=current_tick,
                        kind="ORGANISM_EMITTED",
                        actor=organism_id,
                        position=f"{cell.q},{cell.r}",
                        payload={"sequence": list(world_action.emit)},
                    ))
                action_result = _act(rig)
                if action_result.executed and "repair" in action_result.action_id.lower():
                    tx.stage_event(WorldEvent(
                        event_id=f"evt-{self.state.world_id}-{current_tick}-repair-{organism_id}",
                        world_id=self.state.world_id,
                        tick=current_tick,
                        kind="REPAIR",
                        actor=organism_id,
                        position=f"{cell.q},{cell.r}",
                        payload={"action_id": action_result.action_id},
                    ))


                for resource_id, habitat in rig.resource_habitats.items():
                    consumed = pre_pool.get(resource_id, 0.0) - habitat.snapshot().available_resources
                    if consumed > 0.0:
                        self.environment.acquire(cell, resource_id, consumed)
                        tx.stage_event(WorldEvent(
                            event_id=f"evt-{self.state.world_id}-{current_tick}-acq-{organism_id}-{resource_id}",
                            world_id=self.state.world_id,
                            tick=current_tick,
                            kind="RESOURCE_ACQUIRED",
                            actor=organism_id,
                            position=f"{cell.q},{cell.r}",
                            payload={"resource_id": resource_id, "amount": consumed},
                        ))

                density = observation.signals.get(LOCAL_OCCUPANCY_SIGNAL, 0.0)
                hazard_hits: list[str] = []
                if self.is_alive(organism_id):
                    for hazard_id, exposure in self.environment.hazard_exposures_at(cell, density).items():
                        rng = derive_world_rng(self.world_seed, f"hazard.{hazard_id}:{organism_id}:{current_tick}")
                        if rng.random() < exposure:
                            haz_evt_id = f"evt-{self.state.world_id}-{current_tick}-haz-{hazard_id}-{organism_id}"
                            tx.stage_event(WorldEvent(
                                event_id=haz_evt_id,
                                world_id=self.state.world_id,
                                tick=current_tick,
                                kind="HAZARD_EXPOSURE",
                                actor=organism_id,
                                position=f"{cell.q},{cell.r}",
                                payload={"hazard_id": hazard_id, "exposure": exposure},
                            ))
                            rig.runtime.apply_environmental_damage(0.05)
                            tx.stage_event(WorldEvent(
                                event_id=f"evt-{self.state.world_id}-{current_tick}-dmg-{hazard_id}-{organism_id}",
                                world_id=self.state.world_id,
                                tick=current_tick,
                                kind="PHYSIOLOGICAL_DAMAGE",
                                actor=organism_id,
                                position=f"{cell.q},{cell.r}",
                                payload={"damage": 0.05, "source": hazard_id},
                                causal_parent_ids=(haz_evt_id,),
                            ))
                            hazard_hits.append(hazard_id)

                is_now_alive = self.is_alive(organism_id)
                if was_alive and not is_now_alive:
                    tx.stage_event(WorldEvent(
                        event_id=f"evt-{self.state.world_id}-{current_tick}-death-{organism_id}",
                        world_id=self.state.world_id,
                        tick=current_tick,
                        kind="DEATH",
                        actor=organism_id,
                        position=f"{cell.q},{cell.r}",
                    ))

                per_organism[organism_id] = WorldTickRecord(
                    tick=current_tick,
                    observation=observation,
                    action=action_result,
                    hazard_hits=tuple(hazard_hits),
                    alive=is_now_alive,
                )

            if self.movement_enabled:
                self._resolve_spatial_movement(tx, current_tick)

            # Step geography (traces decay, disturbance decay, deposit on current cells)
            self.geography.step(
                [self.state.bodies[o].occupied_cell for o in self.organism_ids if self.is_alive(o)]
            )

        if not tx.committed:
            return None

        self._emissions = next_emissions
        record = PopulationTickRecord(tick=current_tick, per_organism=per_organism)
        self.history.append(record)
        return record

    def run(self, ticks: int) -> tuple[PopulationTickRecord, ...]:
        records: list[PopulationTickRecord] = []
        for _ in range(ticks):
            if not self.any_alive():
                break
            rec = self.run_tick()
            if rec is not None:
                records.append(rec)
        return tuple(records)

    def _resolve_spatial_movement(
        self, tx: IntegratedWorldTickTransaction, current_tick: int
    ) -> None:
        """Resolve organism-owned actuation; Lab never chooses a direction."""
        movement_intents: dict[str, tuple[int, str, float] | None] = {}
        for organism_id in self.organism_ids:
            if not self.is_alive(organism_id):
                continue
            rig = self._rigs[organism_id]
            actuation = rig.runtime.last_actuation
            world_action = rig.actuation_adapter.translate(actuation)
            if world_action is None or world_action.move is None or actuation is None:
                movement_intents[organism_id] = None
                continue
            try:
                direction = int(world_action.move)
            except (TypeError, ValueError) as exc:
                raise ValueError("ActuationAdapter produced invalid movement binding") from exc
            movement_intents[organism_id] = (
                direction,
                actuation.actuator_id,
                actuation.delivered,
            )

        proposals: dict[HexCoord, list[str]] = {}
        orig_cells: dict[str, HexCoord] = {}
        intent_meta: dict[str, tuple[str, float]] = {}
        for organism_id, intent in movement_intents.items():
            if intent is None:
                continue
            direction, actuator_id, delivered = intent
            body = self.state.bodies[organism_id]
            target, moved = self.topology.resolve_move(body.occupied_cell, direction)
            # These checks are world consequence resolution, not pre-choice
            # filtering: the organism has already actuated at this point.
            if not moved or not self.geography.can_traverse(body.occupied_cell, target):
                continue
            proposals.setdefault(target, []).append(organism_id)
            orig_cells[organism_id] = body.occupied_cell
            intent_meta[organism_id] = (actuator_id, delivered)

        rng = derive_world_rng(self.world_seed, f"resolution.simultaneous-intent:{current_tick}")
        for target in sorted(proposals, key=lambda c: (c.q, c.r)):
            contenders = proposals[target]
            if self.state.occupancy.is_occupied(target):
                continue
            winner = contenders[0] if len(contenders) == 1 else rng.choice(sorted(contenders))
            origin = orig_cells[winner]
            if self.state.occupancy.move(winner, target):
                self.state.bodies[winner].occupied_cell = target
                self.state.bodies[winner].emission_origin = target
                self.geography.deposit_trace(origin, 0.40)
                actuator_id, delivered = intent_meta[winner]
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-move-{winner}",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="MOVE",
                    actor=winner,
                    position=f"{target.q},{target.r}",
                    payload={
                        "from": f"{origin.q},{origin.r}",
                        "to": f"{target.q},{target.r}",
                        "actuator_id": actuator_id,
                        "delivered": delivered,
                    },
                ))


