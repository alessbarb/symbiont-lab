"""W3: connects the Genesis v1 kernel to a real ModeledOrganismRuntime
without modifying the frozen organism core (docs/design/symbiont-world-v1.md
§15). v1 scope only: one stationary organism, no communication, no
reproduction, no movement.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from importlib import resources
from typing import Any

import random

from symbiont.cognition.genome import Genome, GenomeCodec
from symbiont.cognition.birth import load_actuator_constitution
from symbiont.actuation.constitution import ActuatorConstitution
from symbiont.actuation.types import Actuation
from symbiont.core.body_schema import BodySchemaEngine
from symbiont.core.behavior import ActionExecutionResult, ActionKind, select_action
from symbiont.core.ecology import SharedHabitat
from symbiont.core.heredity import HeritableGenome
from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import PhysiologyController, VitalState
from symbiont.host.contracts import AccessMode, Capability, CapabilityKind, CapabilityScope
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from symbiont.modeling.runtime import ModeledOrganismRuntime

from .deferred import DeferredEffect, DeferredEffectQueue

from symbiont_world.contracts import WorldAction, WorldObservation
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.observation import local_observation, opaque_signal_id
from symbiont_world.rng import derive_world_rng
from symbiont_world.state import WorldState
from symbiont_world.topology import HexCoord, HexTopology, WorldBody

_HAZARD_DAMAGE_QUANTUM = 0.05
_OCCUPANCY_SIGNAL = opaque_signal_id("local-occupancy-density")
_RECEPTION_PRESENT_SIGNAL = opaque_signal_id("local-reception-presence")
_RECEPTION_SYMBOL_SIGNAL = opaque_signal_id("local-reception-symbol")
_RECEPTION_INTENSITY_SIGNAL = opaque_signal_id("local-reception-intensity")
_LOCAL_SURFACE_WATER_SIGNAL = opaque_signal_id("local-surface-water")
_LOCAL_DETRITUS_SIGNAL = opaque_signal_id("local-detritus")
_LOCAL_DISTURBANCE_SIGNAL = opaque_signal_id("local-disturbance")
_LOCAL_ECOLOGICAL_PRESSURE_SIGNAL = opaque_signal_id("local-ecological-pressure")
_LOCAL_EFFECTIVE_FERTILITY_SIGNAL = opaque_signal_id("local-effective-fertility")


class WorldDiscoveryProvider:
    """DiscoveryProvider (symbiont/host/contracts.py) implementation, not a
    modification: exposes a fixed set of opaque world signals as
    Capability objects."""

    def __init__(self, capabilities: tuple[Capability, ...]) -> None:
        self._capabilities = capabilities
        self._provider_id = "symbiont-world"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def discover(self) -> tuple[Capability, ...]:
        return self._capabilities


class WorldReadingProvider:
    """ReadingProvider (symbiont/host/readings.py) implementation. Holds the
    latest WorldObservation, refreshed once per tick by the orchestrator
    before runtime.tick() is called."""

    def __init__(self) -> None:
        self._provider_id = "symbiont-world"
        self._observation: WorldObservation | None = None

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def set_observation(self, observation: WorldObservation) -> None:
        self._observation = observation

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        if self._observation is None:
            return ()
        now = time.monotonic_ns()
        readings = []
        reception_values: dict[str, float] = {}
        if self._observation.reception:
            strongest = max(
                self._observation.reception,
                key=lambda item: (item.intensity, item.sequence),
            )
            reception_values = {
                _RECEPTION_PRESENT_SIGNAL: min(1.0, len(self._observation.reception) / 8.0),
                _RECEPTION_SYMBOL_SIGNAL: (
                    float(strongest.sequence[0]) / 255.0 if strongest.sequence else 0.0
                ),
                _RECEPTION_INTENSITY_SIGNAL: max(0.0, min(1.0, float(strongest.intensity))),
            }
        for capability in capabilities:
            value = self._observation.signals.get(capability.capability_id)
            if value is None:
                value = reception_values.get(capability.capability_id)
            if value is None:
                continue
            readings.append(
                SensorReading(
                    capability_id=capability.capability_id,
                    source="symbiont_world",
                    value=float(value),
                    unit=Unit.RATIO,
                    monotonic_timestamp_ns=now,
                    quality=ReadingQuality.NOMINAL,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )
        return tuple(readings)


def _capabilities_for(ground_truth: GroundTruth) -> tuple[Capability, ...]:
    signal_ids = (
        (
            _OCCUPANCY_SIGNAL,
            _RECEPTION_PRESENT_SIGNAL,
            _RECEPTION_SYMBOL_SIGNAL,
            _RECEPTION_INTENSITY_SIGNAL,
            _LOCAL_SURFACE_WATER_SIGNAL,
            _LOCAL_DETRITUS_SIGNAL,
            _LOCAL_DISTURBANCE_SIGNAL,
            _LOCAL_ECOLOGICAL_PRESSURE_SIGNAL,
            _LOCAL_EFFECTIVE_FERTILITY_SIGNAL,
        )
        + tuple(ground_truth.fields)
        + tuple(ground_truth.resources)
        + tuple(ground_truth.hazards)
    )
    return tuple(
        Capability(
            capability_id=signal_id,
            kind=CapabilityKind.SIGNAL,
            source="symbiont_world",
            access=AccessMode.READ_ONLY,
            scope=CapabilityScope.LOCAL,
        )
        for signal_id in signal_ids
    )


def _load_base_genome() -> tuple[Genome, HeritableGenome]:
    payload = json.loads(
        resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text()
    )
    genome = GenomeCodec().load(payload)
    heritable = HeritableGenome(genome_id=genome.genome_id, loci=(("behavior_exploration", 0.15),))
    return genome, heritable


@dataclass(frozen=True, slots=True)
class ActuationBinding:
    actuator_id: str
    effect: str
    argument: str


@dataclass(frozen=True, slots=True)
class ActuationBindingConstitution:
    """Apparatus-owned opaque actuator->world-effect binding."""

    bindings: tuple[ActuationBinding, ...]

    def __post_init__(self) -> None:
        ids = [item.actuator_id for item in self.bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("actuation binding actuator ids must be unique")
        if any(item.effect not in {"move", "acquire", "emit"} for item in self.bindings):
            raise ValueError("unsupported actuation binding effect")
        for item in self.bindings:
            if item.effect == "move":
                try:
                    direction = int(item.argument)
                except (TypeError, ValueError) as exc:
                    raise ValueError("move binding argument must be a hex direction") from exc
                if not 0 <= direction < 6:
                    raise ValueError("move binding direction must be within [0, 5]")
            elif item.effect == "acquire" and item.argument not in {"", "local"}:
                raise ValueError("acquire binding must use opaque local interaction")
            elif item.effect == "emit":
                try:
                    symbol = int(item.argument)
                except (TypeError, ValueError) as exc:
                    raise ValueError("emit binding argument must be an integer symbol") from exc
                if not 0 <= symbol <= 255:
                    raise ValueError("emit symbol must be within [0, 255]")

    @property
    def fingerprint(self) -> str:
        payload = [
            {"actuator_id": item.actuator_id, "effect": item.effect, "argument": item.argument}
            for item in sorted(self.bindings, key=lambda value: value.actuator_id)
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def binding_for(self, actuator_id: str) -> ActuationBinding | None:
        for item in self.bindings:
            if item.actuator_id == actuator_id:
                return item
        return None


class ActuationAdapter:
    """Translate bodily Actuation into WorldAction without choosing for it."""

    def __init__(
        self,
        constitution: ActuatorConstitution,
        binding: ActuationBindingConstitution,
    ) -> None:
        self.constitution = constitution
        self.binding = binding
        known = set(constitution.actuator_ids)
        if any(item.actuator_id not in known for item in binding.bindings):
            raise ValueError("binding references actuator outside body constitution")

    def translate(self, actuation: Actuation | None) -> WorldAction | None:
        if actuation is None:
            return None
        slot = self.constitution.slot_for(actuation.actuator_id)
        if actuation.delivered < slot.execution_threshold:
            return None
        binding = self.binding.binding_for(actuation.actuator_id)
        if binding is None:
            return None
        if binding.effect == "move":
            return WorldAction(move=binding.argument)
        if binding.effect == "acquire":
            return WorldAction(acquire=binding.argument or "local")
        if binding.effect == "emit":
            return WorldAction(emit=(int(binding.argument),))
        return None


def default_world_actuation_binding(
    constitution: ActuatorConstitution,
) -> ActuationBindingConstitution:
    """Bind the first six opaque body slots to the six hex directions.

    The mapping is apparatus/world truth and is fingerprinted; cognition sees
    only actuator ids and consequences.
    """
    bindings = tuple(
        ActuationBinding(actuator_id=actuator_id, effect="move", argument=str(direction))
        for direction, actuator_id in enumerate(constitution.actuator_ids[:6])
    )
    return ActuationBindingConstitution(bindings=bindings)


@dataclass(frozen=True, slots=True)
class WorldTickRecord:
    tick: int
    observation: WorldObservation
    action: ActionExecutionResult
    hazard_hits: tuple[str, ...]
    alive: bool


@dataclass(slots=True)
class _OrganismRig:
    """Everything one organism needs to perceive/act in a world, minus
    world-shared state (WorldState/WorldEnvironment). Factored out so
    SingleOrganismGenesisRuntime and PopulationGenesisRuntime (v2) build
    organisms identically -- one construction path, not two."""

    runtime: ModeledOrganismRuntime
    reading_provider: WorldReadingProvider
    resource_habitats: dict[str, SharedHabitat]
    policy: str
    policy_rng: random.Random
    actuation_adapter: ActuationAdapter
    actuation_binding: ActuationBindingConstitution


def _construct_organism(
    *,
    organism_id: str,
    world_id: str,
    world_seed: int,
    organism_seed: int,
    ground_truth: GroundTruth,
    policy: str,
    sensory_plasticity: bool = False,
    discover_senses: bool = False,
    actuation_binding: ActuationBindingConstitution | None = None,
    actuation_enabled: bool = False,
) -> _OrganismRig:
    if policy not in ("cognitive", "random"):
        raise ValueError("policy must be 'cognitive' or 'random'")

    reading_provider = WorldReadingProvider()
    discovery_provider = WorldDiscoveryProvider(_capabilities_for(ground_truth))
    host_lifecycle = HostLifecycle(
        discovery=HostDiscovery(providers=(discovery_provider,)),
        reading_providers=(reading_provider,),
    )

    resource_habitats: dict[str, SharedHabitat] = {
        resource_id: SharedHabitat(
            habitat_id=f"{world_id}:{organism_id}:{resource_id}",
            capacity=1,
            resources=law.initial_quantity,
        )
        for resource_id, law in ground_truth.resources.items()
    }

    genome, heritable = _load_base_genome()
    actuator_constitution = load_actuator_constitution(genome)
    actuation_binding = actuation_binding or default_world_actuation_binding(actuator_constitution)
    actuation_adapter = ActuationAdapter(actuator_constitution, actuation_binding)
    replenishment = {kind: 0.25 for kind in ("observation", "cognition", "persistence", "maintenance")}
    runtime = ModeledOrganismRuntime(
        organism_id=organism_id,
        host_lifecycle=host_lifecycle,
        resource_habitats=resource_habitats,
        genome=genome,
        heritable_genome=heritable,
        generation=0,
        metabolism=MetabolicLedger(replenishment=replenishment),
        explicit_metabolism=True,
        physiology=PhysiologyController(),
        body_schema=BodySchemaEngine(
            id_salt=hashlib.sha256(f"{world_id}:{world_seed}:{organism_id}".encode()).hexdigest()[:32]
        ),
        bootstrap_semantic_senses=True,
        discover_senses=discover_senses,
        sensory_plasticity=sensory_plasticity,
        autonomous_behavior=True,
        interoception_mode="absent",
        min_samples=1,
        mutation_seed=organism_seed,
        actuation_enabled=actuation_enabled,
        actuator_constitution=actuator_constitution,
    )
    policy_rng = derive_world_rng(world_seed, f"adapter.random-policy-control:{organism_id}")
    return _OrganismRig(
        runtime=runtime,
        reading_provider=reading_provider,
        resource_habitats=resource_habitats,
        policy=policy,
        policy_rng=policy_rng,
        actuation_adapter=actuation_adapter,
        actuation_binding=actuation_binding,
    )


def _act(rig: _OrganismRig) -> ActionExecutionResult:
    """Run the organism-local behaviour step.

    Legacy World instances without the motor apparatus retain their exact
    historical action path. When actuation is enabled, physical resource
    acquisition is exclusively the opaque local-interaction actuator, so
    ActionKind.INTAKE is excluded from this older local-action frontier.
    """
    if not rig.runtime.actuation_enabled:
        if rig.policy == "cognitive":
            return rig.runtime.autonomous_action_step()
        available = tuple(
            opportunity
            for opportunity in rig.runtime.action_opportunities()
            if opportunity.authorized and opportunity.preconditions_met
        )
        if not available:
            return ActionExecutionResult("none", False, reason="no_available_opportunity")
        chosen = rig.policy_rng.choice(available)
        return rig.runtime.execute_local_action(chosen)

    available = tuple(
        opportunity
        for opportunity in rig.runtime.action_opportunities()
        if (
            opportunity.kind is not ActionKind.INTAKE
            and opportunity.authorized
            and opportunity.preconditions_met
        )
    )
    if not available:
        return ActionExecutionResult("none", False, reason="no_available_opportunity")
    if rig.policy == "cognitive":
        selection = select_action(available, exploration=0.0)
        if selection.selected is None:
            return ActionExecutionResult("none", False, reason="no_available_opportunity")
        return rig.runtime.execute_local_action(selection.selected)

    chosen = rig.policy_rng.choice(available)
    return rig.runtime.execute_local_action(chosen)


class SingleOrganismGenesisRuntime:
    """Runs exactly one ModeledOrganismRuntime inside a Genesis v1 world.

    v1 scope only (docs/design/symbiont-world-v1.md §15): the organism
    never issues WorldAction.move; occupancy never changes after
    construction. No communication, no reproduction.
    """

    def __init__(
        self,
        *,
        organism_id: str,
        world_seed: int,
        ground_truth: GroundTruth,
        topology: HexTopology,
        start_cell: HexCoord,
        world_id: str = "genesis-v1",
        policy: str = "cognitive",
        organism_seed: int | None = None,
        sensory_plasticity: bool = False,
        discover_senses: bool = False,
        deferred_resource_delays: dict[str, int] | None = None,
        deferred_damage_amount: float = 0.1,
    ) -> None:
        self.organism_id = organism_id
        self.world_seed = world_seed
        self.organism_seed = world_seed if organism_seed is None else organism_seed
        self.topology = topology
        self._deferred_resource_delays = deferred_resource_delays or {}
        self._deferred_damage_amount = deferred_damage_amount
        self._deferred_queue = DeferredEffectQueue()
        self.environment = WorldEnvironment(ground_truth)
        self.state = WorldState(world_id=world_id)
        if not self.state.occupancy.occupy(start_cell, organism_id):
            raise ValueError("start_cell already occupied")
        self.state.bodies[organism_id] = WorldBody(organism_id=organism_id, occupied_cell=start_cell)

        self._rig = _construct_organism(
            organism_id=organism_id,
            world_id=world_id,
            world_seed=world_seed,
            organism_seed=self.organism_seed,
            ground_truth=ground_truth,
            policy=policy,
            sensory_plasticity=sensory_plasticity,
            discover_senses=discover_senses,
        )
        self.runtime = self._rig.runtime
        self._reading_provider = self._rig.reading_provider
        self._resource_habitats = self._rig.resource_habitats
        self.history: list[WorldTickRecord] = []

    def _occupied_cell(self) -> HexCoord:
        return self.state.bodies[self.organism_id].occupied_cell

    def is_alive(self) -> bool:
        return self.runtime._physiology.state is not VitalState.DEAD

    def run_tick(self) -> WorldTickRecord:
        if not self.is_alive():
            raise RuntimeError("organism is dead; the run has already ended")

        current_tick = self.state.tick
        cell = self._occupied_cell()
        hazard_hits: list[str] = []
        observation: WorldObservation | None = None
        action_result: ActionExecutionResult | None = None

        with self.state.begin_tick():
            self.environment.propagate_fields(current_tick)
            self.environment.renew_resources(cell)

            for effect in self._deferred_queue.pop_due(self.organism_id, current_tick):
                if self.is_alive():
                    self.runtime.apply_environmental_damage(effect.amount)

            pre_pool = {
                resource_id: pool_value
                for resource_id, pool_value in self.environment.resource_pool(cell).items()
            }
            for resource_id, habitat in self._resource_habitats.items():
                habitat.set_environment_resources(pre_pool.get(resource_id, 0.0))

            observation = local_observation(self.topology, self.state.occupancy, self.state.bodies[self.organism_id], self.environment)
            self._reading_provider.set_observation(observation)

            self.runtime.tick()
            action_result = _act(self._rig)

            for resource_id, habitat in self._resource_habitats.items():
                consumed = pre_pool.get(resource_id, 0.0) - habitat.snapshot().available_resources
                if consumed > 0.0:
                    self.environment.acquire(cell, resource_id, consumed)
                    delay = self._deferred_resource_delays.get(resource_id)
                    if delay is not None:
                        self._deferred_queue.schedule(DeferredEffect(
                            organism_id=self.organism_id,
                            due_tick=current_tick + delay,
                            amount=self._deferred_damage_amount,
                        ))

            density = observation.signals.get(_OCCUPANCY_SIGNAL, 0.0)
            if self.is_alive():
                for hazard_id, exposure in self.environment.hazard_exposures_at(cell, density).items():
                    rng = derive_world_rng(self.world_seed, f"hazard.{hazard_id}:{current_tick}")
                    if rng.random() < exposure:
                        self.runtime.apply_environmental_damage(_HAZARD_DAMAGE_QUANTUM)
                        hazard_hits.append(hazard_id)

        if observation is None or action_result is None:
            raise RuntimeError("tick aborted without observation or action")

        record = WorldTickRecord(
            tick=current_tick,
            observation=observation,
            action=action_result,
            hazard_hits=tuple(hazard_hits),
            alive=self.is_alive(),
        )
        self.history.append(record)
        return record

    def run(self, ticks: int) -> tuple[WorldTickRecord, ...]:
        records: list[WorldTickRecord] = []
        for _ in range(ticks):
            if not self.is_alive():
                break
            records.append(self.run_tick())
        return tuple(records)
