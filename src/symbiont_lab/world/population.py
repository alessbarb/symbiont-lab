"""Deterministic multi-organism Genesis World runtime.\n\nThe class preserves legacy study modes, while the canonical persistent World\nenables experimental_clean: embodied actuation, mixed opaque perception and\nfail-closed semantic-contamination guards.\n\nThe experimental_clean=False (default) path is not dead: it backs the\nlocked, preregistered W03 study (experiments/world/genesis-v1/run_w03.py,\ndocs/design/symbiont-world-v2.md §11), whose regression tests\n(tests/unit/lab/world/test_w03_experiment.py) run it directly against this\nclass without ever going through WorldRuntimeState. WorldRuntimeState itself\nrefuses any experimental_clean=False population\n(assert_experimental_boundary / \"canonical World refuses\nlegacy/contaminated population\"), so this branch never reaches the\ncanonical live World -- it stays only to keep a historical study\nreproducible. Do not delete without first retiring that study and its lock\ntest.\n"""
from __future__ import annotations

from dataclasses import dataclass

from symbiont.core.physiology import VitalState

from symbiont_world.contracts import ReceivedEmission, WorldObservation
from symbiont_world.events import EventJournal, WorldEvent
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.observation import LOCAL_OCCUPANCY_SIGNAL, local_observation
from symbiont_world.rng import derive_world_rng
from symbiont_world.state import WorldState
from symbiont_world.topology import BodyPlacement, HexCoord, HexTopology

from .adapter import (
    ActionExecutionResult,
    ActuationBindingConstitution,
    WorldTickRecord,
    _OCCUPANCY_SIGNAL,
    _act,
    _capabilities_for,
    _construct_organism,
    clean_world_observation,
    local_substrate_signals,
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
    """Run N organism runtimes inside one shared Genesis World.\n\n    Per-tick ordering is deterministic. Legacy callers may disable movement or\n    use historical action surfaces; canonical persistent World selects the\n    fail-closed experimental-clean configuration.\n    """

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
        experimental_clean: bool = False,
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
        self.experimental_clean = bool(experimental_clean)
        self._actuation_binding_override = actuation_binding
        self._emissions: dict[str, tuple[int, ...]] = {}
        self._rigs = {}
        self.history: list[PopulationTickRecord] = []

        for index, (organism_id, cell) in enumerate(sorted(zip(organism_ids, start_cells))):
            if not self.state.occupancy.occupy(cell, organism_id):
                raise ValueError(f"start_cell {cell} already occupied (organism {organism_id!r})")
            self.state.bodies[organism_id] = BodyPlacement(organism_id=organism_id, occupied_cell=cell)
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
                actuation_enabled=(movement_enabled or actuation_binding is not None),
                experimental_clean=self.experimental_clean,
            )

    def _observation_for(self, organism_id: str) -> WorldObservation:
        rig = self._rigs[organism_id]
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
        apparatus_observation = WorldObservation(
            signals=dict(base.signals),
            contact=base.contact,
            reception=tuple(reception),
            internal=base.internal,
        )
        if self.experimental_clean:
            metabolic = rig.runtime.metabolism.snapshot()
            somatic_state = {
                **{
                    f"reserve:{kind}": max(
                        0.0,
                        min(
                            1.0,
                            metabolic.reserve[kind]
                            / max(metabolic.capacity[kind], 1e-12),
                        ),
                    )
                    for kind in sorted(metabolic.capacity)
                },
                "integrity": max(0.0, min(1.0, rig.runtime.homeostasis.integrity)),
                "activity": max(0.0, min(1.0, rig.runtime.homeostasis.activity_scale)),
            }
            cleaned = clean_world_observation(
                self.ground_truth,
                apparatus_observation,
                geography=self.geography,
                cell=body.occupied_cell,
                receptor_ids=rig.receptor_ids,
                somatic_state=somatic_state,
            )
            forbidden = (
                {_OCCUPANCY_SIGNAL}
                | set(self.ground_truth.fields)
                | set(self.ground_truth.resources)
                | set(self.ground_truth.hazards)
                | set(local_substrate_signals(self.geography, body.occupied_cell))
            )
            leaked = set(cleaned.signals) & forbidden
            if leaked:
                raise RuntimeError(
                    f"experimental contamination in observation: {sorted(leaked)}"
                )
            return cleaned
        signals = dict(apparatus_observation.signals)
        signals.update(local_substrate_signals(self.geography, body.occupied_cell))
        return WorldObservation(
            signals=signals,
            contact=apparatus_observation.contact,
            reception=apparatus_observation.reception,
            internal=apparatus_observation.internal,
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
        if action is None:
            return
        if self.experimental_clean:
            if action.interact != "local":
                return
            rig = self._rigs[organism_id]
            actuation = rig.runtime.last_actuation
            delivered = max(0.0, actuation.delivered if actuation is not None else 0.0)
            if delivered <= 0.0:
                return
            impulse = self.geography.apply_directional_impulse(cell, cell, delivered)
            tx.stage_event(WorldEvent(
                event_id=f"evt-{self.state.world_id}-{current_tick}-substrate-local-{organism_id}",
                world_id=self.state.world_id,
                tick=current_tick,
                kind="SUBSTRATE_IMPULSE",
                actor=organism_id,
                position=f"{cell.q},{cell.r}",
                payload={
                    "actuator_id": actuation.actuator_id if actuation is not None else None,
                    "delivered": delivered,
                    "water_transferred": impulse.water_transferred,
                    "detritus_transferred": impulse.detritus_transferred,
                    "origin_disturbance_added": impulse.origin_disturbance_added,
                    "target_disturbance_added": impulse.target_disturbance_added,
                },
            ))
            return
        if action.acquire != "local":
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
        actuation = rig.runtime.last_actuation
        requested = min(
            0.25,
            max(0.0, actuation.delivered if actuation is not None else 0.0) * 0.25,
        )
        if requested <= 0.0:
            return

        # Legacy apparatus path retained for non-canonical historical studies.
        resource_id, _ = max(available, key=lambda item: (item[1], item[0]))
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

    def _resolve_embodied_material_exchange(
        self,
        organism_id: str,
        *,
        cell: HexCoord,
        current_tick: int,
        tx: IntegratedWorldTickTransaction,
    ) -> None:
        """Resolve passive material exchange from physical motor work.

        No actuator means intake. In clean World, any delivered bodily work may
        create bounded local exchange with material already present at the body.
        The organism sees only later somatic/perceptual consequences.
        """
        rig = self._rigs[organism_id]
        if not rig.experimental_clean:
            return
        actuation = rig.runtime.last_actuation
        if actuation is None or actuation.delivered <= 0.0:
            return
        pool = self.environment.resource_pool(cell)
        available = [
            (resource_id, amount)
            for resource_id, amount in sorted(pool.items())
            if amount > 0.0
        ]
        if not available:
            return
        total_available = sum(amount for _, amount in available)
        exchange_budget = min(0.05, float(actuation.delivered) * 0.05)
        granted = rig.runtime.absorb_metabolic_energy(exchange_budget)
        if granted > 0.0:
            # World owns material identity and depletion. The organism receives
            # only the scalar absorbed amount; no resource id crosses inward.
            for resource_id, amount in available:
                physical_share = granted * (amount / total_available)
                self.environment.acquire(cell, resource_id, physical_share)
        tx.stage_event(WorldEvent(
            event_id=f"evt-{self.state.world_id}-{current_tick}-material-exchange-{organism_id}",
            world_id=self.state.world_id,
            tick=current_tick,
            kind="ACTUATION_RESOLVED",
            actor=organism_id,
            position=f"{cell.q},{cell.r}",
            payload={
                "effect": "material_exchange",
                "outcome": "granted" if granted > 0.0 else "no_transfer",
                "amount": granted,
                "actuator_id": actuation.actuator_id,
                "delivered": actuation.delivered,
            },
        ))

    def assert_experimental_boundary(self) -> None:
        """Fail closed if canonical clean-mode assumptions are violated."""
        if not self.experimental_clean:
            return
        if not self.movement_enabled:
            raise RuntimeError(
                "experimental contamination: embodied actuation/movement disabled"
            )

        subject_capabilities = {
            item.capability_id
            for item in _capabilities_for(self.ground_truth, experimental_clean=True)
        }
        forbidden_signal_ids = (
            {_OCCUPANCY_SIGNAL}
            | set(self.ground_truth.fields)
            | set(self.ground_truth.resources)
            | set(self.ground_truth.hazards)
            | set(local_substrate_signals(self.geography, HexCoord(0, 0)))
        )
        leaked = subject_capabilities & forbidden_signal_ids
        if leaked:
            raise RuntimeError(
                f"experimental contamination: direct apparatus signals exposed: {sorted(leaked)}"
            )

        receptor_sets: list[set[str]] = []
        for organism_id, rig in self._rigs.items():
            runtime = rig.runtime
            if len(rig.receptor_ids) != 8 or len(set(rig.receptor_ids)) != 8:
                raise RuntimeError(
                    f"experimental contamination: invalid receptor body for {organism_id}"
                )
            rig_receptors = set(rig.receptor_ids)
            if rig_receptors & forbidden_signal_ids:
                raise RuntimeError(
                    f"experimental contamination: direct apparatus receptor id for {organism_id}"
                )
            capability_ids = {
                item.capability_id
                for item in _capabilities_for(
                    self.ground_truth,
                    experimental_clean=True,
                    receptor_ids=rig.receptor_ids,
                )
            }
            if capability_ids != rig_receptors:
                raise RuntimeError(
                    f"experimental contamination: capability/receptor mismatch for {organism_id}"
                )
            if any(rig_receptors & prior for prior in receptor_sets):
                raise RuntimeError(
                    f"experimental contamination: shared receptor namespace for {organism_id}"
                )
            receptor_sets.append(rig_receptors)
            if not rig.experimental_clean:
                raise RuntimeError(
                    f"experimental contamination: {organism_id} is not marked clean"
                )
            if rig.resource_habitats:
                raise RuntimeError(
                    f"experimental contamination: World resource habitats injected into {organism_id}"
                )
            if not runtime._explicit_metabolism:
                raise RuntimeError(
                    f"experimental contamination: implicit/ambient metabolic replenishment enabled for {organism_id}"
                )
            if runtime._birth_authority is not None or runtime._reproductive_pressure is not None:
                raise RuntimeError(
                    f"experimental contamination: World reproductive authority injected into {organism_id}"
                )
            if runtime._bootstrap_semantic_senses:
                raise RuntimeError(
                    f"experimental contamination: semantic bootstrap enabled for {organism_id}"
                )
            if runtime._interoception_mode != "absent":
                raise RuntimeError(
                    f"experimental contamination: privileged interoception enabled for {organism_id}"
                )
            if not runtime._discover_senses:
                raise RuntimeError(
                    f"experimental contamination: sense discovery disabled for {organism_id}"
                )
            if not runtime.sensory_system.plasticity_enabled:
                raise RuntimeError(
                    f"experimental contamination: sensory plasticity disabled for {organism_id}"
                )
            if runtime.heritable_genome is not None and runtime.heritable_genome.loci:
                raise RuntimeError(
                    f"experimental contamination: founder behavioral loci present for {organism_id}"
                )
            replenishment = runtime.metabolism.checkpoint()["replenishment"]
            if any(float(value) != 0.0 for value in replenishment.values()):
                raise RuntimeError(
                    f"experimental contamination: free metabolic replenishment for {organism_id}"
                )

            if not runtime.actuation_enabled or runtime.actuator_constitution is None:
                raise RuntimeError(
                    f"experimental contamination: motor body disabled for {organism_id}"
                )
            actuator_ids = runtime.actuator_constitution.actuator_ids
            if len(actuator_ids) < 8:
                raise RuntimeError(
                    f"experimental contamination: clean motor body has fewer than 8 slots for {organism_id}"
                )

            bindings = rig.actuation_binding.bindings
            semantic_effects = {item.effect for item in bindings} - {"move", "interact"}
            if semantic_effects:
                raise RuntimeError(
                    f"experimental contamination: unsupported clean motor effects {sorted(semantic_effects)}"
                )
            move_bindings = [item for item in bindings if item.effect == "move"]
            interaction_bindings = [item for item in bindings if item.effect == "interact"]
            if (
                len(move_bindings) != 6
                or {item.argument for item in move_bindings} != {str(i) for i in range(6)}
            ):
                raise RuntimeError(
                    f"experimental contamination: directional motor constitution changed for {organism_id}"
                )
            if len(interaction_bindings) != 1 or interaction_bindings[0].argument not in {"", "local"}:
                raise RuntimeError(
                    f"experimental contamination: local physical interaction body changed for {organism_id}"
                )
            if getattr(runtime, "_motor_exploration_mode", None) != "spontaneous":
                raise RuntimeError(
                    f"experimental contamination: structured motor probing enabled for {organism_id}"
                )
            bound_ids = {item.actuator_id for item in bindings}
            if not (set(actuator_ids) - bound_ids):
                raise RuntimeError(
                    f"experimental contamination: no unbound causal-control actuator for {organism_id}"
                )

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
        death_cells: list[HexCoord] = []

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
                renewal_factor = self.geography.resource_renewal_factor(cell)
                self.environment.renew_resources(cell, renewal_factor=renewal_factor)
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-renew-{cell.q}_{cell.r}",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="RESOURCE_RENEWED",
                    actor=None,
                    position=f"{cell.q},{cell.r}",
                    payload={"renewal_factor": renewal_factor},
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
                self._resolve_embodied_material_exchange(
                    organism_id,
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

                density = (
                    local_observation(
                        self.topology,
                        self.state.occupancy,
                        self.state.bodies[organism_id],
                        self.environment,
                    ).signals.get(LOCAL_OCCUPANCY_SIGNAL, 0.0)
                    if self.experimental_clean
                    else observation.signals.get(LOCAL_OCCUPANCY_SIGNAL, 0.0)
                )
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
                    death_cells.append(cell)
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
                [self.state.bodies[o].occupied_cell for o in self.organism_ids if self.is_alive(o)],
                death_cells=death_cells,
            )
            if death_cells:
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-ecology-death",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="ECOLOGY_CHANGED",
                    actor=None,
                    position=None,
                    payload={
                        "death_cells": [f"{cell.q},{cell.r}" for cell in death_cells],
                        "detritus_deposited": len(death_cells),
                    },
                ))

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
            impulse = self.geography.apply_directional_impulse(
                body.occupied_cell,
                target,
                delivered,
            )
            tx.stage_event(WorldEvent(
                event_id=f"evt-{self.state.world_id}-{current_tick}-substrate-{organism_id}",
                world_id=self.state.world_id,
                tick=current_tick,
                kind="SUBSTRATE_IMPULSE",
                actor=organism_id,
                position=f"{body.occupied_cell.q},{body.occupied_cell.r}",
                payload={
                    "actuator_id": actuator_id,
                    "delivered": delivered,
                    "target": f"{impulse.target.q},{impulse.target.r}",
                    "water_transferred": impulse.water_transferred,
                    "detritus_transferred": impulse.detritus_transferred,
                    "origin_disturbance_added": impulse.origin_disturbance_added,
                    "target_disturbance_added": impulse.target_disturbance_added,
                },
            ))
            # These checks are world consequence resolution, not pre-choice
            # filtering: the organism has already actuated at this point.
            if not moved:
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-act-move-{organism_id}",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="ACTUATION_RESOLVED",
                    actor=organism_id,
                    position=f"{body.occupied_cell.q},{body.occupied_cell.r}",
                    payload={
                        "effect": "move",
                        "outcome": "boundary",
                        "actuator_id": actuator_id,
                        "delivered": delivered,
                    },
                ))
                continue
            if not self.geography.can_traverse(body.occupied_cell, target):
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-act-move-{organism_id}",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="ACTUATION_RESOLVED",
                    actor=organism_id,
                    position=f"{body.occupied_cell.q},{body.occupied_cell.r}",
                    payload={
                        "effect": "move",
                        "outcome": "terrain_blocked",
                        "actuator_id": actuator_id,
                        "delivered": delivered,
                    },
                ))
                continue
            proposals.setdefault(target, []).append(organism_id)
            orig_cells[organism_id] = body.occupied_cell
            intent_meta[organism_id] = (actuator_id, delivered)

        rng = derive_world_rng(self.world_seed, f"resolution.simultaneous-intent:{current_tick}")
        for target in sorted(proposals, key=lambda c: (c.q, c.r)):
            contenders = proposals[target]
            if self.state.occupancy.is_occupied(target):
                for organism_id in sorted(contenders):
                    actuator_id, delivered = intent_meta[organism_id]
                    origin = orig_cells[organism_id]
                    tx.stage_event(WorldEvent(
                        event_id=f"evt-{self.state.world_id}-{current_tick}-act-move-{organism_id}",
                        world_id=self.state.world_id,
                        tick=current_tick,
                        kind="ACTUATION_RESOLVED",
                        actor=organism_id,
                        position=f"{origin.q},{origin.r}",
                        payload={
                            "effect": "move",
                            "outcome": "occupied",
                            "actuator_id": actuator_id,
                            "delivered": delivered,
                        },
                    ))
                continue
            winner = contenders[0] if len(contenders) == 1 else rng.choice(sorted(contenders))
            for organism_id in sorted(contenders):
                if organism_id == winner:
                    continue
                actuator_id, delivered = intent_meta[organism_id]
                origin = orig_cells[organism_id]
                tx.stage_event(WorldEvent(
                    event_id=f"evt-{self.state.world_id}-{current_tick}-act-move-{organism_id}",
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="ACTUATION_RESOLVED",
                    actor=organism_id,
                    position=f"{origin.q},{origin.r}",
                    payload={
                        "effect": "move",
                        "outcome": "contention_lost",
                        "actuator_id": actuator_id,
                        "delivered": delivered,
                    },
                ))
            origin = orig_cells[winner]
            if self.state.occupancy.move(winner, target):
                self.state.bodies[winner].occupied_cell = target
                self.state.bodies[winner].emission_origin = target
                self.geography.deposit_trace(origin, 0.40)
                actuator_id, delivered = intent_meta[winner]
                resolution_id = f"evt-{self.state.world_id}-{current_tick}-act-move-{winner}"
                tx.stage_event(WorldEvent(
                    event_id=resolution_id,
                    world_id=self.state.world_id,
                    tick=current_tick,
                    kind="ACTUATION_RESOLVED",
                    actor=winner,
                    position=f"{target.q},{target.r}",
                    payload={
                        "effect": "move",
                        "outcome": "moved",
                        "actuator_id": actuator_id,
                        "delivered": delivered,
                    },
                ))
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
                    causal_parent_ids=(resolution_id,),
                ))


