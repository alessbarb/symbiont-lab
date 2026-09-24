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
            if rig.individual is not None:
                phys = rig.individual.body.physiology
                somatic_state = {
                    "reserve:maintenance": max(
                        0.0,
                        min(
                            1.0,
                            phys.energy_reserve / max(phys.max_energy, 1e-12),
                        ),
                    ),
                    "integrity": max(0.0, min(1.0, phys.structural_integrity)),
                    "activity": 1.0,
                }
            elif rig.runtime is not None:
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
            else:
                somatic_state = {
                    "reserve:maintenance": 1.0,
                    "integrity": 1.0,
                    "activity": 1.0,
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
        rig = self._rigs[organism_id]
        if self.experimental_clean:
            if rig.individual is not None or action.interact != "local" or rig.runtime is None:
                return
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

        # NOTE(legacy): Legacy apparatus path retained for non-canonical historical studies.
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
        if not rig.experimental_clean or rig.individual is not None or rig.runtime is None:
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
        exchange_budget = min(0.05, float(actuation.delivered) * 0.05, total_available)
        if exchange_budget <= 0.0:
            return
        # 1. World withdraws physical material first (NEW-AUD-001)
        withdrawn_per_res: dict[str, float] = {}
        actual_withdrawn = 0.0
        for resource_id, amount in available:
            physical_share = exchange_budget * (amount / total_available)
            withdrawn = self.environment.acquire(cell, resource_id, physical_share)
            withdrawn_per_res[resource_id] = withdrawn
            actual_withdrawn += withdrawn

        if actual_withdrawn <= 0.0:
            return

        # 2. Runtime absorbs from actual withdrawn material
        granted = rig.runtime.absorb_metabolic_energy(actual_withdrawn)

        # 3. Refund any unabsorbed remainder back to environment
        unabsorbed = actual_withdrawn - granted
        if unabsorbed > 0.0:
            for resource_id, withdrawn in withdrawn_per_res.items():
                if actual_withdrawn > 0.0:
                    self.environment.deposit(cell, resource_id, unabsorbed * (withdrawn / actual_withdrawn))
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
        pass

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
            if rig.individual is not None:
                if rig.runtime is not None:
                    raise RuntimeError(
                        f"experimental contamination: legacy runtime coexists with clean Individual for {organism_id}"
                    )
                if rig.actuation_adapter is not None:
                    raise RuntimeError(
                        f"experimental contamination: legacy actuation adapter present in clean Individual for {organism_id}"
                    )
                if len(rig.individual.body.effector_ids) < 8:
                    raise RuntimeError(
                        f"experimental contamination: clean motor body has fewer than 8 effectors for {organism_id}"
                    )
                continue
            if not runtime._explicit_metabolism:
                raise RuntimeError(
                    f"experimental contamination: implicit/ambient metabolic replenishment enabled for {organism_id}"
                )
            if runtime._birth_authority is not None:
                raise RuntimeError(
                    f"experimental contamination: World birth authority injected into {organism_id}"
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
            bound_ids = {item.actuator_id for item in bindings}
            if not (set(actuator_ids) - bound_ids):
                raise RuntimeError(
                    f"experimental contamination: no unbound causal-control actuator for {organism_id}"
                )

    @property
    def organism_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._rigs))

    def is_alive(self, organism_id: str) -> bool:
        rig = self._rigs[organism_id]
        if rig.experimental_clean and rig.individual is not None:
            return rig.individual.is_alive
        if rig.runtime is not None:
            return rig.runtime._physiology.state is not VitalState.DEAD
        return False

    def any_alive(self) -> bool:
        return any(self.is_alive(organism_id) for organism_id in self._rigs)

    def _living_density(self, organism_id: str) -> float:
        """Fraction of in-bounds neighboring cells occupied by living organisms.

        Dead placements may remain available to apparatus/history, but never
        contribute to density-dependent biological risk.
        """
        body = self.state.bodies[organism_id]
        visited: set[HexCoord] = {body.occupied_cell}
        frontier: set[HexCoord] = {body.occupied_cell}
        living_neighbors = 0
        total_neighbors = 0

        for _ in range(max(body.interaction_radius, 0)):
            next_frontier: set[HexCoord] = set()
            for cell in frontier:
                for direction in range(6):
                    neighbor = cell.neighbor(direction)
                    if neighbor in visited or not self.topology.in_bounds(neighbor):
                        continue
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
                    total_neighbors += 1
                    occupant = self.state.occupancy.occupant(neighbor)
                    if occupant is not None and self.is_alive(occupant):
                        living_neighbors += 1
            frontier = next_frontier

        return living_neighbors / total_neighbors if total_neighbors else 0.0

    def run_tick(self) -> PopulationTickRecord | None:
        current_tick = self.state.tick
        per_organism: dict[str, WorldTickRecord] = {}
        next_emissions: dict[str, tuple[int, ...]] = {}
        death_cells: list[HexCoord] = []
        death_ids: list[str] = []

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

            # Ecology advances on the World clock, not on organism presence.
            # Every world cell receives exactly one renewal step per tick,
            # whether occupied, empty, densely visited, or never visited.
            renewal_cell_count = self.topology.width * self.topology.height
            renewal_factor_sum = 0.0
            renewal_factor_min = None
            renewal_factor_max = None
            for q in range(self.topology.width):
                for r in range(self.topology.height):
                    renewal_cell = HexCoord(q, r)
                    renewal_factor = self.geography.resource_renewal_factor(renewal_cell)
                    self.environment.renew_resources(
                        renewal_cell,
                        renewal_factor=renewal_factor,
                    )
                    renewal_factor_sum += renewal_factor
                    renewal_factor_min = (
                        renewal_factor
                        if renewal_factor_min is None
                        else min(renewal_factor_min, renewal_factor)
                    )
                    renewal_factor_max = (
                        renewal_factor
                        if renewal_factor_max is None
                        else max(renewal_factor_max, renewal_factor)
                    )
            tx.stage_event(WorldEvent(
                event_id=f"evt-{self.state.world_id}-{current_tick}-renewal",
                world_id=self.state.world_id,
                tick=current_tick,
                kind="RESOURCE_RENEWED",
                actor=None,
                position=None,
                payload={
                    "cell_count": renewal_cell_count,
                    "mean_renewal_factor": (
                        renewal_factor_sum / renewal_cell_count
                        if renewal_cell_count
                        else 0.0
                    ),
                    "min_renewal_factor": renewal_factor_min,
                    "max_renewal_factor": renewal_factor_max,
                },
            ))

            for organism_id in self.organism_ids:
                rig = self._rigs[organism_id]
                was_alive = self.is_alive(organism_id)
                if not was_alive:
                    continue

                cell = self.state.bodies[organism_id].occupied_cell

                diagnostic_energy_start = None
                diagnostic_integrity_start = None
                diagnostic_deferred_damage = 0.0
                diagnostic_hazard_damage = 0.0
                diagnostic_motor_cost = 0.0
                diagnostic_basal_cost = 0.0
                diagnostic_basal_wear = 0.0
                diagnostic_absorbed = 0.0
                if rig.experimental_clean and rig.individual is not None:
                    diagnostic_energy_start = rig.individual.body.physiology.energy_reserve
                    diagnostic_integrity_start = rig.individual.body.physiology.structural_integrity

                if self.deferred_queue is not None:
                    due_effects = self.deferred_queue.pop_due(organism_id, current_tick)
                    for effect_index, effect in enumerate(due_effects):
                        if self.is_alive(organism_id):
                            if rig.experimental_clean and rig.individual is not None:
                                before_integrity = rig.individual.body.physiology.structural_integrity
                                rig.individual.body.apply_damage(effect.amount)
                                diagnostic_deferred_damage += max(
                                    0.0,
                                    before_integrity
                                    - rig.individual.body.physiology.structural_integrity,
                                )
                            elif rig.runtime is not None:
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

                if rig.experimental_clean and rig.individual is not None:
                    energy_before_step = rig.individual.body.physiology.energy_reserve
                    integrity_before_step = rig.individual.body.physiology.structural_integrity
                    step_rec = rig.individual.step(external_stimuli=observation.signals)
                    diagnostic_motor_cost = sum(
                        consequence.energy_cost
                        for consequence in step_rec.physical_consequences.values()
                    )
                    energy_after_step = rig.individual.body.physiology.energy_reserve
                    integrity_after_step = rig.individual.body.physiology.structural_integrity
                    diagnostic_basal_cost = max(
                        0.0,
                        energy_before_step - diagnostic_motor_cost - energy_after_step,
                    )
                    diagnostic_basal_wear = max(
                        0.0,
                        integrity_before_step - integrity_after_step,
                    )
                    delivered = max(
                        (
                            c.physical_effect
                            for c in step_rec.physical_consequences.values()
                            if c.physical_effect > 0.0
                        ),
                        default=0.0,
                    )
                    if delivered > 0.0:
                        impulse = self.geography.apply_directional_impulse(cell, cell, delivered)
                        tx.stage_event(WorldEvent(
                            event_id=f"evt-{self.state.world_id}-{current_tick}-substrate-local-{organism_id}",
                            world_id=self.state.world_id,
                            tick=current_tick,
                            kind="SUBSTRATE_IMPULSE",
                            actor=organism_id,
                            position=f"{cell.q},{cell.r}",
                            payload={
                                "actuator_id": "body_effector",
                                "delivered": delivered,
                                "water_transferred": impulse.water_transferred,
                                "detritus_transferred": impulse.detritus_transferred,
                                "origin_disturbance_added": impulse.origin_disturbance_added,
                                "target_disturbance_added": impulse.target_disturbance_added,
                            },
                        ))
                    pool = self.environment.resource_pool(cell)
                    available = [
                        (resource_id, amount)
                        for resource_id, amount in sorted(pool.items())
                        if amount > 0.0
                    ]
                    if available and delivered > 0.0:
                        total_available = sum(amount for _, amount in available)
                        requested = min(0.05, float(delivered) * 0.05, total_available)
                        if requested > 0.0:
                            # 1. World withdraws physical material from environment first (NEW-AUD-001)
                            withdrawn_per_resource: dict[str, float] = {}
                            actual_withdrawn = 0.0
                            for resource_id, amount in available:
                                physical_share = requested * (amount / total_available)
                                withdrawn = self.environment.acquire(cell, resource_id, physical_share)
                                withdrawn_per_resource[resource_id] = withdrawn
                                actual_withdrawn += withdrawn

                            if actual_withdrawn > 0.0:
                                # 2. World issues MaterialTransfer for actually granted physical matter
                                from symbiont.core.body import MaterialTransfer
                                transfer = MaterialTransfer(
                                    source_id=f"world:{cell.q},{cell.r}",
                                    target_body_id=rig.individual.body_id,
                                    amount=actual_withdrawn,
                                )
                                # 3. Body absorbs from the transfer up to its physiological capacity
                                absorbed = rig.individual.body.absorb_material(transfer)
                                diagnostic_absorbed += absorbed

                                # 4. Any unabsorbed matter is strictly refunded back to the cell pool
                                unabsorbed = actual_withdrawn - absorbed
                                if unabsorbed > 0.0:
                                    for resource_id, withdrawn in withdrawn_per_resource.items():
                                        if actual_withdrawn > 0.0:
                                            refund = unabsorbed * (withdrawn / actual_withdrawn)
                                            self.environment.deposit(cell, resource_id, refund)

                                tx.stage_event(WorldEvent(
                                    event_id=f"evt-{self.state.world_id}-{current_tick}-material-exchange-{organism_id}",
                                    world_id=self.state.world_id,
                                    tick=current_tick,
                                    kind="ACTUATION_RESOLVED",
                                    actor=organism_id,
                                    position=f"{cell.q},{cell.r}",
                                    payload={
                                        "effect": "material_exchange",
                                        "outcome": "granted" if absorbed > 0.0 else "no_transfer",
                                        "amount": absorbed,
                                        "actuator_id": "body_effector",
                                        "delivered": delivered,
                                    },
                                ))
                    action_result = _act(rig)
                else:
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
                    self._living_density(organism_id)
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
                                payload={
                                    "hazard_id": hazard_id,
                                    "exposure": exposure,
                                    "living_density": density,
                                },
                            ))
                            if rig.experimental_clean and rig.individual is not None:
                                before_integrity = rig.individual.body.physiology.structural_integrity
                                rig.individual.body.apply_damage(0.05)
                                diagnostic_hazard_damage += max(
                                    0.0,
                                    before_integrity
                                    - rig.individual.body.physiology.structural_integrity,
                                )
                            elif rig.runtime is not None:
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

                if rig.experimental_clean and rig.individual is not None:
                    phys = rig.individual.body.physiology
                    death_cause = None
                    if not is_now_alive:
                        if phys.energy_reserve <= 0.0:
                            death_cause = "energy_depletion"
                        elif phys.structural_integrity <= 0.0:
                            death_cause = "structural_failure"
                        else:
                            death_cause = "nonviable"
                    tx.stage_event(WorldEvent(
                        event_id=f"evt-{self.state.world_id}-{current_tick}-physiology-{organism_id}",
                        world_id=self.state.world_id,
                        tick=current_tick,
                        kind="PHYSIOLOGY_BALANCE",
                        actor=organism_id,
                        position=f"{cell.q},{cell.r}",
                        payload={
                            "energy_start": diagnostic_energy_start,
                            "energy_end": phys.energy_reserve,
                            "absorbed": diagnostic_absorbed,
                            "motor_cost": diagnostic_motor_cost,
                            "basal_cost": diagnostic_basal_cost,
                            "integrity_start": diagnostic_integrity_start,
                            "integrity_end": phys.structural_integrity,
                            "basal_wear": diagnostic_basal_wear,
                            "deferred_damage": diagnostic_deferred_damage,
                            "hazard_damage": diagnostic_hazard_damage,
                            "alive": is_now_alive,
                            "death_cause": death_cause,
                        },
                    ))

                if was_alive and not is_now_alive:
                    death_cells.append(cell)
                    death_ids.append(organism_id)
                    death_payload = {}
                    if rig.experimental_clean and rig.individual is not None:
                        phys = rig.individual.body.physiology
                        death_payload = {
                            "cause": (
                                "energy_depletion"
                                if phys.energy_reserve <= 0.0
                                else "structural_failure"
                                if phys.structural_integrity <= 0.0
                                else "nonviable"
                            )
                        }
                    tx.stage_event(WorldEvent(
                        event_id=f"evt-{self.state.world_id}-{current_tick}-death-{organism_id}",
                        world_id=self.state.world_id,
                        tick=current_tick,
                        kind="DEATH",
                        actor=organism_id,
                        position=f"{cell.q},{cell.r}",
                        payload=death_payload,
                    ))

                per_organism[organism_id] = WorldTickRecord(
                    tick=current_tick,
                    observation=observation,
                    action=action_result,
                    hazard_hits=tuple(hazard_hits),
                    alive=is_now_alive,
                )

            # OccupancyGrid represents living occupancy. Dead bodies leave
            # ecological detritus through DynamicGeography, but no longer
            # inflate living-density risk or block a cell as a live organism.
            for dead_id in death_ids:
                self.state.occupancy.vacate(dead_id)

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
            if rig.experimental_clean and rig.individual is not None:
                if rig.individual.history:
                    last_rec = rig.individual.history[-1]
                    best_move = None
                    max_effect = 0.0
                    for port_id, c in last_rec.physical_consequences.items():
                        eff = rig.individual.body.get_effector(port_id)
                        if eff is not None and eff.direction is not None and c.physical_effect > max_effect:
                            max_effect = c.physical_effect
                            best_move = (eff.direction, port_id, c.physical_effect)
                    movement_intents[organism_id] = best_move
                else:
                    movement_intents[organism_id] = None
                continue

            if rig.runtime is None or rig.actuation_adapter is None:
                movement_intents[organism_id] = None
                continue

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


