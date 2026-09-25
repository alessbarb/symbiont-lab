"""Genesis World ↔ organism boundary.

Historical single-organism adapters remain for frozen studies. The canonical
persistent World uses the experimental-clean population path: mixed opaque
physical receptors, opaque motor actuation and no typed local behavior priors.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, replace
from importlib import resources
from typing import Any

import random

from symbiont.genetics.genome import Genome
from symbiont.genetics.migration import GenomeMigrationCodec as GenomeCodec
from symbiont.cognition.birth import load_base_genome
from symbiont.actuation.constitution import ActuatorConstitution
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.cognition.limits import KernelLimits
from symbiont.actuation.types import Actuation
from symbiont.core.ecology import SharedHabitat
from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import PhysiologyController, VitalState
from symbiont.core.signal_identity import SignalIdentity
from symbiont.host.contracts import AccessMode, Capability, CapabilityKind, CapabilityScope
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from symbiont.modeling.runtime import ModeledOrganismRuntime

from .deferred import DeferredEffect, DeferredEffectQueue

from symbiont_world.contracts import WorldAction, WorldObservation
from symbiont_world.genesis import GroundTruth, WorldEnvironment
from symbiont_world.observation import local_observation, opaque_signal_id
from symbiont_world.rng import derive_world_rng, derive_world_seed
from symbiont_world.state import WorldState
from symbiont_world.topology import BodyPlacement, HexCoord, HexTopology

_HAZARD_DAMAGE_QUANTUM = 0.05
_OCCUPANCY_SIGNAL = opaque_signal_id("local-occupancy-density")
_RECEPTION_PRESENT_SIGNAL = opaque_signal_id("local-reception-presence")
_RECEPTION_SYMBOL_SIGNAL = opaque_signal_id("local-reception-symbol")
_RECEPTION_INTENSITY_SIGNAL = opaque_signal_id("local-reception-intensity")
_LOCAL_SURFACE_WATER_SIGNAL = opaque_signal_id("local-surface-water")
_LOCAL_DETRITUS_SIGNAL = opaque_signal_id("local-detritus")
_LOCAL_DISTURBANCE_SIGNAL = opaque_signal_id("local-disturbance")

# Canonical clean-world sensory body. These IDs are organism-facing, but their
# apparatus meanings are not. Individual World variables never cross the
# boundary one-to-one.
_PHYSICAL_RECEPTOR_IDS = tuple(
    opaque_signal_id(f"physical-receptor-{index}") for index in range(8)
)


def physical_receptor_ids(identity_salt: str) -> tuple[str, ...]:
    return tuple(
        opaque_signal_id(f"physical-receptor:{identity_salt}:{index}")
        for index in range(8)
    )


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


def local_substrate_signals(geography: Any, cell: HexCoord) -> dict[str, float]:
    """Opaque local physical state available to organism perception.

    Apparatus names never cross the organism boundary: only stable opaque
    signal IDs and bounded numeric values are returned.
    """
    return {
        _LOCAL_SURFACE_WATER_SIGNAL: float(geography.surface_water(cell)),
        _LOCAL_DETRITUS_SIGNAL: float(geography.detritus(cell)),
        _LOCAL_DISTURBANCE_SIGNAL: float(geography.disturbance(cell)),
    }


def _capabilities_for(
    ground_truth: GroundTruth,
    *,
    experimental_clean: bool = False,
    receptor_ids: tuple[str, ...] | None = None,
) -> tuple[Capability, ...]:
    if experimental_clean:
        signal_ids = receptor_ids or _PHYSICAL_RECEPTOR_IDS
    else:
        signal_ids = (
            (
                _OCCUPANCY_SIGNAL,
                _RECEPTION_PRESENT_SIGNAL,
                _RECEPTION_SYMBOL_SIGNAL,
                _RECEPTION_INTENSITY_SIGNAL,
                _LOCAL_SURFACE_WATER_SIGNAL,
                _LOCAL_DETRITUS_SIGNAL,
                _LOCAL_DISTURBANCE_SIGNAL,
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


def _unit_interval(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        return 0.5
    # Smoothly compress arbitrary signed physical fields without creating
    # semantic thresholds.
    return 0.5 + 0.5 * math.tanh(value)


def _mix_weight(receptor_index: int, source_id: str) -> float:
    # Transfer geometry is constitutional and identical across founders.
    # Organism-facing receptor identities are private, but identity itself
    # must not alter the physical receptor response.
    digest = hashlib.sha256(
        f"physical-receptor-transfer:{receptor_index}:{source_id}".encode()
    ).digest()
    integer = int.from_bytes(digest[:8], "big")
    return (integer / float((1 << 64) - 1)) * 2.0 - 1.0


def physical_receptor_signals(
    ground_truth: GroundTruth,
    observation: WorldObservation,
    *,
    geography: Any | None = None,
    cell: HexCoord | None = None,
    receptor_ids: tuple[str, ...] | None = None,
    somatic_state: dict[str, float] | None = None,
) -> dict[str, float]:
    """Project apparatus truth into mixed opaque receptor activity.

    No resource id, hazard id, occupancy concept, fertility estimate or
    one-to-one substrate variable reaches the organism. Resources contribute
    only as normalized local material presence; hazards are deliberately
    absent and must be learned from experienced consequences.
    """
    sources: list[tuple[str, float]] = []

    for field_id in sorted(ground_truth.fields):
        if field_id in observation.signals:
            sources.append((f"field:{field_id}", _unit_interval(observation.signals[field_id])))

    material_fractions: list[float] = []
    for resource_id, law in sorted(ground_truth.resources.items()):
        amount = max(0.0, float(observation.signals.get(resource_id, 0.0)))
        material_fractions.append(
            min(1.0, amount / max(float(law.capacity), 1e-12))
        )
    if material_fractions:
        # Composition identity is deliberately unavailable. Until World gives
        # materials genuine physical properties, clean receptors perceive only
        # aggregate local material abundance.
        sources.append((
            "material:aggregate",
            sum(material_fractions) / len(material_fractions),
        ))

    if geography is not None and cell is not None:
        sources.extend((
            ("substrate:surface", max(0.0, min(1.0, float(geography.surface_water(cell))))),
            ("substrate:residual", max(0.0, min(1.0, float(geography.detritus(cell))))),
            ("substrate:change", max(0.0, min(1.0, float(geography.disturbance(cell))))),
        ))

    if observation.reception:
        strongest = max(observation.reception, key=lambda item: (item.intensity, item.sequence))
        sources.extend((
            ("reception:amplitude", max(0.0, min(1.0, float(strongest.intensity)))),
            (
                "reception:waveform",
                float(strongest.sequence[0]) / 255.0 if strongest.sequence else 0.0,
            ),
        ))

    if somatic_state:
        for source_id, value in sorted(somatic_state.items()):
            bounded = max(0.0, min(1.0, float(value))) if math.isfinite(float(value)) else 0.5
            sources.append((f"soma:{source_id}", bounded))

    active_receptors = receptor_ids or _PHYSICAL_RECEPTOR_IDS
    if not sources:
        return {receptor_id: 0.5 for receptor_id in active_receptors}

    scale = math.sqrt(float(len(sources)))
    mixed: dict[str, float] = {}
    for receptor_index, receptor_id in enumerate(active_receptors):
        activation = sum(
            _mix_weight(receptor_index, source_id) * (2.0 * value - 1.0)
            for source_id, value in sources
        ) / scale
        mixed[receptor_id] = max(0.0, min(1.0, 0.5 + 0.5 * math.tanh(activation)))
    return mixed


def clean_world_observation(
    ground_truth: GroundTruth,
    observation: WorldObservation,
    *,
    geography: Any | None = None,
    cell: HexCoord | None = None,
    receptor_ids: tuple[str, ...] | None = None,
    somatic_state: dict[str, float] | None = None,
) -> WorldObservation:
    return WorldObservation(
        signals=physical_receptor_signals(
            ground_truth,
            observation,
            geography=geography,
            cell=cell,
            receptor_ids=receptor_ids,
            somatic_state=somatic_state,
        ),
        # Structured contact/reception/internal channels are apparatus truth.
        # In clean mode their physical effects must enter only through mixed
        # receptors, never as pre-segmented subject concepts.
        contact=(),
        reception=(),
        internal={},
    )


def _load_base_genome() -> Genome:
    from symbiont import __version__ as symbiont_version

    parts = (symbiont_version.split(".") + ["0", "0"])[:3]
    running_version = tuple(int(part) for part in parts)
    return load_base_genome(
        kernel_limits=KernelLimits(),
        running_version=running_version,
    )


@dataclass(frozen=True, slots=True)
class ActuationBinding:
    actuator_id: str
    effect: str
    argument: str
    minimum_activation: float = 0.05

    def __post_init__(self) -> None:
        threshold = float(self.minimum_activation)
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("binding minimum_activation must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class ActuationBindingConstitution:
    """Apparatus-owned opaque actuator->world-effect binding."""

    bindings: tuple[ActuationBinding, ...]

    def __post_init__(self) -> None:
        ids = [item.actuator_id for item in self.bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("actuation binding actuator ids must be unique")
        if any(item.effect not in {"move", "interact", "acquire", "emit"} for item in self.bindings):
            raise ValueError("unsupported actuation binding effect")
        for item in self.bindings:
            if item.effect == "move":
                try:
                    direction = int(item.argument)
                except (TypeError, ValueError) as exc:
                    raise ValueError("move binding argument must be a hex direction") from exc
                if not 0 <= direction < 6:
                    raise ValueError("move binding direction must be within [0, 5]")
            elif item.effect in {"interact", "acquire"} and item.argument not in {"", "local"}:
                raise ValueError("local interaction binding must use opaque local interaction")
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
            {"actuator_id": item.actuator_id, "effect": item.effect, "argument": item.argument, "minimum_activation": item.minimum_activation}
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
        self.constitution.slot_for(actuation.actuator_id)
        binding = self.binding.binding_for(actuation.actuator_id)
        if binding is None or actuation.delivered < binding.minimum_activation:
            return None
        if binding.effect == "move":
            return WorldAction(move=binding.argument)
        if binding.effect == "interact":
            return WorldAction(interact=binding.argument or "local")
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
    bindings = [
        ActuationBinding(actuator_id=actuator_id, effect="move", argument=str(direction))
        for direction, actuator_id in enumerate(constitution.actuator_ids[:6])
    ]
    # A seventh inherited motor channel, when present, is only a local
    # substrate perturbation. It is deliberately not an intake/feeding organ;
    # material exchange is a body/environment consequence shared by motor work.
    if len(constitution.actuator_ids) >= 7:
        bindings.append(
            ActuationBinding(
                actuator_id=constitution.actuator_ids[6],
                effect="interact",
                argument="local",
            )
        )
    # Any further slot is intentionally left unbound: naturally occurring
    # activation provides a causal negative control without a semantic "noop".
    return ActuationBindingConstitution(bindings=tuple(bindings))


@dataclass(frozen=True, slots=True)
class ActionExecutionResult:
    """Local, apparatus-owned report of one adapter-level effector step.

    Deliberately not imported from the organism package: the World adapter
    reports its own opaque-motor outcome, never a typed local action-kind
    selection.
    """

    action_id: str
    executed: bool
    result: object | None = None
    reason: str | None = None


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

    runtime: ModeledOrganismRuntime | None
    reading_provider: WorldReadingProvider
    resource_habitats: dict[str, SharedHabitat]
    policy: str
    policy_rng: random.Random
    actuation_adapter: ActuationAdapter | None = None
    actuation_binding: ActuationBindingConstitution | None = None
    experimental_clean: bool = False
    receptor_ids: tuple[str, ...] = ()
    individual: Any | None = None


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
    experimental_clean: bool = False,
) -> _OrganismRig:
    if policy not in ("cognitive", "random"):
        raise ValueError("policy must be 'cognitive' or 'random'")

    reading_provider = WorldReadingProvider()
    receptor_ids = (
        physical_receptor_ids(f"organism:{organism_seed}:{organism_id}")
        if experimental_clean
        else ()
    )
    discovery_provider = WorldDiscoveryProvider(
        _capabilities_for(
            ground_truth,
            experimental_clean=experimental_clean,
            receptor_ids=receptor_ids or None,
        )
    )

    if experimental_clean:
        from symbiont.core.symbiont import Symbiont
        from symbiont.core.body import create_standard_body
        from symbiont.core.embodiment import implant_body
        from symbiont.core.individual import Individual
        from symbiont.genetics.germline import GermlineState

        num_rec = len(receptor_ids) if receptor_ids else 8
        num_eff = 8
        body = create_standard_body(f"body:{organism_id}", num_receptors=num_rec, num_effectors=num_eff)
        sym_genome = _load_base_genome()
        germline = GermlineState.from_genome(sym_genome)
        sym_seed = derive_world_seed(world_seed, f"symbiont.cognitive:{organism_id}")
        sym = Symbiont(organism_id, seed=sym_seed, genome=sym_genome, germline=germline)
        session = implant_body(organism_id, body, started_at=0)
        individual = Individual(symbiont=sym, body=body, session=session)
        policy_rng = derive_world_rng(world_seed, f"adapter.random-policy-control:{organism_id}")

        return _OrganismRig(
            runtime=None,
            reading_provider=reading_provider,
            resource_habitats={},
            policy=policy,
            policy_rng=policy_rng,
            actuation_adapter=None,
            actuation_binding=None,
            experimental_clean=True,
            receptor_ids=receptor_ids,
            individual=individual,
        )

    host_lifecycle = HostLifecycle(
        discovery=HostDiscovery(providers=(discovery_provider,)),
        reading_providers=(reading_provider,),
    )

    # NOTE(legacy): Canonical clean World must not inject world resource topology into the
    # organism. Legacy studies retain SharedHabitat-backed resource surfaces;
    # clean organisms receive physical energy only through the scalar body
    # absorption boundary.
    resource_habitats: dict[str, SharedHabitat] = {
        resource_id: SharedHabitat(
            habitat_id=f"{world_id}:{organism_id}:{resource_id}",
            capacity=1,
            resources=law.initial_quantity,
        )
        for resource_id, law in ground_truth.resources.items()
    }

    genome = _load_base_genome()
    actuator_constitution = derive_actuator_constitution(
        8,
        physical_contract="genesis-world-body-v3",
    )
    actuation_binding = actuation_binding or default_world_actuation_binding(actuator_constitution)
    actuation_adapter = ActuationAdapter(actuator_constitution, actuation_binding)
    replenishment_value = 0.25
    replenishment = {
        kind: replenishment_value
        for kind in ("observation", "cognition", "persistence", "maintenance")
    }
    metabolism = MetabolicLedger(replenishment=replenishment)
    physiology = PhysiologyController(body_state=metabolism.body_state)
    runtime = ModeledOrganismRuntime(
        organism_id=organism_id,
        host_lifecycle=host_lifecycle,
        resource_habitats=resource_habitats,
        genome=genome,
        generation=0,
        metabolism=metabolism,
        explicit_metabolism=False,
        physiology=physiology,
        signal_identity=None,
        bootstrap_semantic_senses=True,
        discover_senses=discover_senses,
        sensory_plasticity=sensory_plasticity,
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
        experimental_clean=False,
        receptor_ids=receptor_ids,
        individual=None,
    )


def _act(rig: _OrganismRig) -> ActionExecutionResult:
    """Run the organism-local behaviour step.

    An embodied organism (clean or legacy, actuation-enabled either way)
    resolves material exchange as a physical consequence of bodily work
    through opaque motor actuation; this report is a passive summary of
    that actuation, never a typed local action-kind selection or a scalar
    utility ranking.

    A pre-actuation legacy World instance has no motor body at all. For
    that case only, the apparatus itself drives the organism's generic
    effector calls (resource intake, repair) directly each tick, with no
    action-kind vocabulary and no scored ranking among candidates -- this
    is lab/world simulation logic standing in for a body, not organism
    cognition choosing among named actions.
    """
    if rig.experimental_clean:
        if rig.individual is not None:
            has_act = bool(
                rig.individual.history
                and rig.individual.history[-1].physical_consequences
            )
            return ActionExecutionResult(
                action_id="opaque_motor",
                executed=has_act,
                reason=None if has_act else "no_motor_actuation",
            )
        return ActionExecutionResult(
            action_id="opaque_motor",
            executed=True,
            reason=None,
        )

    if rig.runtime is not None and rig.runtime.actuation_enabled:
        actuation = rig.runtime.last_actuation
        return ActionExecutionResult(
            action_id="opaque_motor",
            executed=actuation is not None,
            reason=None if actuation is not None else "no_motor_actuation",
        )

    intake_habitats = (
        tuple(rig.resource_habitats.items())
        if rig.resource_habitats
        else ((None, rig.runtime._habitat),) if rig.runtime._habitat is not None else ()
    )
    # Bounded reserve capacity means only the first successful draw each
    # tick actually accepts anything; rotate which habitat goes first so
    # every attached resource gets an equal, deterministic turn over time
    # instead of one fixed habitat permanently starving the others.
    if intake_habitats:
        offset = rig.runtime.tick_count % len(intake_habitats)
        intake_habitats = intake_habitats[offset:] + intake_habitats[:offset]
    executed = False
    for resource_id, habitat in intake_habitats:
        if habitat is None or habitat.snapshot().available_resources <= 0.0:
            continue
        kind = rig.runtime._most_depleted_metabolic_kind()
        rig.runtime.request_resource_intake(0.1, kind=kind, resource_id=resource_id)
        executed = True

    return ActionExecutionResult(
        action_id="legacy_apparatus_effectors",
        executed=executed,
        reason=None if executed else "no_available_effector",
    )


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
        self.state.bodies[organism_id] = BodyPlacement(organism_id=organism_id, occupied_cell=start_cell)

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
