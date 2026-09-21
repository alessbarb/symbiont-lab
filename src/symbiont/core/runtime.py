from __future__ import annotations

import json
import platform
import hashlib
import uuid
import math
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ..host.acclimation import HostAcclimation
from ..host.adaptive import AdaptiveSenseModel, SamplingPlan
from ..host.bootstrap import current_time_bucket
from ..host.checkpoint import (
    CheckpointError,
    export_checkpoint,
    import_checkpoint,
    load_checkpoint_file,
    normalize_checkpoint,
    save_checkpoint_atomic,
)
from ..host.contracts import DiscoveryPolicy, DiscoveryProvider, HostManifest
from ..host.discovery import HostDiscovery
from ..host.drift import DriftAwareBaseline, DriftObservation
from ..host.lifecycle import HostLifecycle, LifecycleSnapshot
from ..host.percepts import DEFAULT_PERCEPT_NAMES, Percept
from ..host.providers.stdlib import StandardLibraryProvider
from ..host.providers.stdlib_readings import StandardLibraryReadingProvider
from ..host.readings import (
    HostSampler,
    ReadingPrivacyClass,
    ReadingProvider,
    ReadingQuality,
    SensorReading,
    Unit,
)
from ..host.rhythms import RhythmModel
from ..host.second_look import SecondLookSession
from ..sensory import SensorySystem
from ..cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ..cognition.genome import Genome, DevelopmentGenes, PlasticityGenes, RangeSpec
from ..cognition.graph import CognitiveGraph
from ..cognition.learning import ShadowPrediction
from ..cognition.limits import KernelLimits
from .attention import AttentionAllocation, AttentionBudget, AttentionCandidate, attend_to_host
from .body_schema import BodySchemaEngine
from .cognition_bridge import CognitiveBridge, CognitiveBridgeResult
from .cognitive_self import derive_cognitive_self_namespace, project_cognitive_self_observation
from .consolidation import ConsolidationSignal, MemoryConsolidator, MemoryKind, novelty_from_drift_kind, surprise_from_loss
from .evidence import DissentRecord, EvidenceRevisionLedger
from .narrative import NarrativeEntry, narrate_host
from .selfmodel import LOW_HEALTH_INVESTIGATION_THRESHOLD, SelfModel
from .signal_identity import SignalIdentity
from .signal_knowledge import SignalKnowledgeEngine, MAX_KNOWLEDGE_CHECKPOINT_BYTES
from .signal_knowledge_types import SignalObservation, SignalObservationBatch
from .degradation import DegradationQueue
from .physiology import (
    DEFAULT_PHYSIOLOGY_CONFIG,
    LivingBodyState,
    PhysiologyConfig,
    PhysiologyController,
    PhysiologySnapshot,
    VitalState,
)
from .signal_knowledge_checkpoint import validate_checkpoint
from .metabolism import MetabolicLedger, MetabolicSnapshot
from .assimilation import InformationAssimilator, AssimilationDecision
from .homeostasis import HomeostaticController, HomeostaticSnapshot
from .ecology import SharedHabitat
from .trust import SourceTrustModel
from .social import (InteractionOutcome, RelationLedger, RelationValence,
                     SocialRelation,
                     ResourceEvidenceLedger, SocialCompetitionRequest,
                     SocialHabitat, SocialPresence)
from .birth_authority import BirthRecord, HabitatBirthAuthority
from .reproduction import ReproductivePressure, ReproductiveStatus, clonal_bud
from .heredity import HeritableGenome, _ALLOWED_LOCI
from .inheritance import EpigeneticPrior, mutate_genome
from .development import DevelopmentalSnapshot, DevelopmentalTracker
from ..cognition.birth import load_base_graph, load_actuator_constitution
from ..actuation.checkpoint import export_actuation_state, restore_actuation_state
from ..actuation.constitution import ActuatorConstitution
from ..actuation.health import ActuatorState
from ..actuation.proposer import ActuatorProposer
from ..actuation.selector import MotorIntentSelector
from ..actuation.system import ActuatorSystem
from ..actuation.types import Actuation, MotorIntent
from ..actuation.sensorimotor import SensorimotorLearner, SensorimotorSnapshot


def _parse_running_version(version_string: str) -> tuple[int, int, int]:
    parts = version_string.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


@dataclass(frozen=True, slots=True)
class ActionExecutionResult:
    """Result of one explicit organism-local effector call.

    Generic and semantic-free: it names no action kind and computes no
    utility. ``result`` is intentionally opaque; callers own its shape.
    Retained on :class:`RuntimeTickResult` as a passive reporting surface
    for the Observatory and lab modeling adapters, even though canonical
    cognition no longer runs a typed action-selection step that populates it.
    """

    action_id: str
    executed: bool
    result: object | None = None
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class RuntimeTickResult:
    tick: int
    snapshot: LifecycleSnapshot
    percepts: tuple[Percept, ...]
    drift_observations: dict[str, DriftObservation]
    allocations: tuple[AttentionAllocation, ...]
    investigated_capability: str | None
    evidence_gathered: int
    dissent: DissentRecord | None
    narrative: tuple[NarrativeEntry, ...]
    sampling_plan: SamplingPlan | None = None
    perceptual_allocations: tuple[AttentionAllocation, ...] = ()
    cognition: CognitiveBridgeResult | None = None
    signal_knowledge: tuple[dict[str, Any], ...] = ()
    knowledge_events: tuple[dict[str, Any], ...] = ()
    signal_references: dict[str, str] | None = None
    metabolism: MetabolicSnapshot | None = None
    assimilation: tuple[AssimilationDecision, ...] = ()
    homeostasis: HomeostaticSnapshot | None = None
    physiology: PhysiologySnapshot | None = None
    degradation_excreted: int = 0
    retained_items: int = 0
    action_result: ActionExecutionResult | None = None
    development: DevelopmentalSnapshot | None = None
    sensory_phenotype: dict[str, Any] | None = None
    # Bounded lifecycle facts emitted by the subject runtime.  The laboratory
    # may project these into its own taxonomy, but must not manufacture them
    # from snapshots after the fact.
    runtime_events: tuple[str, ...] = ()
    motor_intent: MotorIntent | None = None
    actuation: Actuation | None = None
    motor_intents: tuple[MotorIntent, ...] = ()
    actuations: tuple[Actuation, ...] = ()


class OrganismDeadError(RuntimeError):
    """Raised when execution is requested after irreversible death."""


class OrganismRuntime:
    """Continuous cognitive cycle over safe local perceptions.

    In developmental mode discovery remains broad inside the provider's fixed safety
    boundary, while sampling becomes selective. Cognitive learning happens only
    after attention has been allocated for the current tick, so attention and the
    self-model can constrain plastic updates instead of merely describing them.
    """

    _SUPPORTED_EPIGENETIC_KEYS = frozenset(_ALLOWED_LOCI | {"exploration_bias"})

    def __init__(
        self,
        *,
        discovery_policy: DiscoveryPolicy | None = None,
        host_lifecycle: HostLifecycle | None = None,
        host_reading_providers: tuple[ReadingProvider, ...] | None = None,
        attention_budget: float = 1.0,
        investigate_ticks: int = 2,
        conflict_z: float = 2.0,
        min_samples: int = 5,
        acclimation: HostAcclimation | None = None,
        rhythm_model: RhythmModel | None = None,
        drift_baselines: dict[str, DriftAwareBaseline] | None = None,
        tick_count: int = 0,
        discover_senses: bool = False,
        bootstrap_semantic_senses: bool = True,
        adaptive_senses: AdaptiveSenseModel | None = None,
        sensory_system: SensorySystem | None = None,
        sensory_plasticity: bool = False,
        self_model: SelfModel | None = None,
        body_schema: BodySchemaEngine | None = None,
        evidence_ledger: EvidenceRevisionLedger | None = None,
        genome: Genome | None = None,
        heritable_genome: HeritableGenome | None = None,
        mutation_seed: int = 0,
        epigenetic_priors: tuple[EpigeneticPrior, ...] = (),
        epigenetic_decay: float = 0.05,
        kernel_limits: KernelLimits | None = None,
        cognitive_graph: CognitiveGraph | None = None,
        cognitive_bridge: CognitiveBridge | None = None,
        memory_consolidator: MemoryConsolidator | None = None,
        organism_id: str | None = None,
        signal_identity: SignalIdentity | None = None,
        signal_knowledge: SignalKnowledgeEngine | None = None,
        metabolism: MetabolicLedger | None = None,
        assimilator: InformationAssimilator | None = None,
        homeostasis: HomeostaticController | None = None,
        physiology: PhysiologyController | None = None,
        living_body_state: LivingBodyState | None = None,
        physiology_config: PhysiologyConfig | None = None,
        habitat: SharedHabitat | None = None,
        resource_habitats: dict[str, SharedHabitat] | None = None,
        social_habitat: SocialHabitat | None = None,
        social_ledger: RelationLedger | None = None,
        social_resource_ledger: ResourceEvidenceLedger | None = None,
        explicit_metabolism: bool = False,
        auto_promote_predictors: bool = False,
        reproductive_pressure: ReproductivePressure | None = None,
        birth_authority: HabitatBirthAuthority | None = None,
        generation: int = 0,
        reproduction_cost: float = 0.1,
        social_exchange_quantum: float = 0.1,
        social_exchange_cost: float = 0.01,
        resting_requested: bool = False,
        degradation_queue: DegradationQueue | None = None,
        source_trust: SourceTrustModel | None = None,
        interoception_enabled: bool = True,
        interoception_mode: str | None = None,
        developmental_tracker: DevelopmentalTracker | None = None,
        actuation_enabled: bool = False,
        actuator_constitution: ActuatorConstitution | None = None,
        actuator_proposer: ActuatorProposer | None = None,
        actuator_states: dict[str, ActuatorState] | None = None,
        motor_intent_selector: MotorIntentSelector | None = None,
        actuator_system: ActuatorSystem | None = None,
        sensorimotor_learner: SensorimotorLearner | None = None,
        motor_exploration_mode: str = "structured_probe",
    ) -> None:
        if attention_budget <= 0.0:
            raise ValueError("attention_budget must be positive")
        if investigate_ticks < 0:
            raise ValueError("investigate_ticks must be non-negative (0 disables investigation)")
        if (tick_count < 0 or generation < 0 or reproduction_cost < 0.0
                or social_exchange_quantum <= 0.0 or social_exchange_cost < 0.0):
            raise ValueError("invalid tick, generation, reproduction cost, social quantum or social cost")
        if motor_exploration_mode not in {"structured_probe", "spontaneous", "babbling"}:
            raise ValueError(
                "motor_exploration_mode must be structured_probe, spontaneous or babbling"
            )

        discovery_providers: list[DiscoveryProvider] = []
        reading_providers: list[ReadingProvider] = []
        self._bootstrap_semantic_senses = bootstrap_semantic_senses
        self._adaptive_senses = adaptive_senses if adaptive_senses is not None else AdaptiveSenseModel()
        self._sensory_system = (
            sensory_system if sensory_system is not None
            else SensorySystem(plasticity_enabled=sensory_plasticity)
        )
        self._discover_senses = discover_senses
        if interoception_mode is None:
            interoception_mode = "enabled" if interoception_enabled else "absent"
        if interoception_mode not in {"enabled", "sham", "absent"}:
            raise ValueError("interoception_mode must be enabled, sham or absent")
        if interoception_mode == "absent" and interoception_enabled:
            interoception_enabled = False
        self._interoception_mode = interoception_mode
        self._interoception_enabled = interoception_mode != "absent"

        if bootstrap_semantic_senses:
            discovery_providers.append(StandardLibraryProvider())
            reading_providers.append(StandardLibraryReadingProvider())

        # The interoceptive surface is only offered alongside Linux host-sense
        # discovery, so gaining it never gives the research subject platform
        # topology on its own.
        if discover_senses and platform.system() == "Linux":
            from ..host.providers.interoception import (
                InteroceptionProvider,
                ShamInteroceptionProvider,
            )
            from ..host.providers.linux_surfaces import LinuxSurfaceProvider
            linux_provider = LinuxSurfaceProvider()
            discovery_providers.append(linux_provider)
            reading_providers.append(linux_provider)

            provider_type = (ShamInteroceptionProvider
                             if interoception_mode == "sham"
                             else InteroceptionProvider)
            self._interoception_provider = provider_type() if self._interoception_enabled else None
            if self._interoception_provider is not None:
                discovery_providers.append(self._interoception_provider)
                reading_providers.append(self._interoception_provider)
        else:
            self._interoception_provider = None

        self._reading_providers = tuple(reading_providers)
        if host_lifecycle is not None:
            if not isinstance(host_lifecycle, HostLifecycle):
                raise TypeError("host_lifecycle must be a HostLifecycle")
            self._lifecycle = host_lifecycle
            self._reading_providers = tuple(host_reading_providers or ())
        else:
            self._lifecycle = HostLifecycle(
                discovery=HostDiscovery(providers=tuple(discovery_providers), policy=discovery_policy),
                reading_providers=self._reading_providers,
            )
        provided_min_samples: list[int] = []
        if acclimation is not None and hasattr(acclimation, "_min_samples"):
            provided_min_samples.append(int(acclimation._min_samples))
        if rhythm_model is not None and hasattr(rhythm_model, "_min_samples"):
            provided_min_samples.append(int(rhythm_model._min_samples))

        if provided_min_samples:
            first_min = provided_min_samples[0]
            if any(s != first_min for s in provided_min_samples[1:]):
                raise ValueError("contradictory min_samples in prebuilt subsystems")
            self._min_samples = first_min
        else:
            self._min_samples = int(min_samples)

        self._acclimation = acclimation if acclimation is not None else HostAcclimation(min_samples=self._min_samples)
        self._rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel(min_samples=self._min_samples)
        self._drift_baselines = dict(drift_baselines) if drift_baselines is not None else {}
        if evidence_ledger is not None and hasattr(evidence_ledger, "_conflict_z"):
            self._conflict_z = float(evidence_ledger._conflict_z)
        else:
            self._conflict_z = float(conflict_z)
        self._evidence_ledger = (
            evidence_ledger if evidence_ledger is not None else EvidenceRevisionLedger(conflict_z=self._conflict_z)
        )
        self._attention_budget = attention_budget
        self._investigate_ticks = investigate_ticks
        self._tick_count = tick_count
        self._organism_id = str(organism_id) if organism_id is not None else f"org_{uuid.uuid4().hex[:16]}"
        self._signal_identity = signal_identity if signal_identity is not None else SignalIdentity(b"symbiont-signal-knowledge-key-32")
        self._signal_knowledge = signal_knowledge if signal_knowledge is not None else SignalKnowledgeEngine()
        self._explicit_metabolism = bool(explicit_metabolism)
        self._auto_promote_predictors = bool(auto_promote_predictors)
        self._reproductive_pressure = reproductive_pressure
        self._birth_authority = birth_authority
        self._developmental_tracker = developmental_tracker if developmental_tracker is not None else DevelopmentalTracker()
        self._last_runtime_vital_state: str | None = None
        self._last_runtime_development_phase: str | None = None
        self._first_sense_emitted = False
        self._first_concept_emitted = False
        self._first_prediction_emitted = False
        self._generation = generation
        self._reproduction_cost = float(reproduction_cost)
        self._social_exchange_quantum = float(social_exchange_quantum)
        self._social_exchange_cost = float(social_exchange_cost)
        self._resting_requested = bool(resting_requested)
        if physiology_config is not None:
            self._physiology_config = physiology_config
            if degradation_queue is not None:
                if (
                    degradation_queue.aging_ticks != self._physiology_config.aging_ticks
                    or degradation_queue.waste_ticks != self._physiology_config.waste_ticks
                ):
                    raise ValueError("incompatible degradation_queue ticks with physiology_config")
            if metabolism is not None and getattr(metabolism, "physiology_config", None) is not None:
                if metabolism.physiology_config != self._physiology_config:
                    raise ValueError("incompatible metabolism physiology_config with runtime physiology_config")
            if homeostasis is not None and getattr(homeostasis, "config", None) is not None:
                if homeostasis.config != self._physiology_config:
                    raise ValueError("incompatible homeostasis config with runtime physiology_config")
        else:
            provided_configs: list[PhysiologyConfig] = []
            if homeostasis is not None and getattr(homeostasis, "config", None) is not None:
                provided_configs.append(homeostasis.config)
            if metabolism is not None and getattr(metabolism, "physiology_config", None) is not None:
                provided_configs.append(metabolism.physiology_config)

            if provided_configs:
                first = provided_configs[0]
                if any(cfg != first for cfg in provided_configs[1:]):
                    raise ValueError("contradictory physiology configs in prebuilt subsystems")
                base_config = first
            else:
                base_config = DEFAULT_PHYSIOLOGY_CONFIG

            if degradation_queue is not None:
                if provided_configs:
                    if (
                        degradation_queue.aging_ticks != base_config.aging_ticks
                        or degradation_queue.waste_ticks != base_config.waste_ticks
                    ):
                        raise ValueError("incompatible degradation_queue ticks with subsystem physiology config")
                    self._physiology_config = base_config
                else:
                    aging = degradation_queue.aging_ticks
                    waste = degradation_queue.waste_ticks
                    if aging != base_config.aging_ticks or waste != base_config.waste_ticks:
                        from dataclasses import replace
                        self._physiology_config = replace(
                            base_config, aging_ticks=aging, waste_ticks=waste
                        )
                    else:
                        self._physiology_config = base_config
            else:
                self._physiology_config = base_config

        self._degradation = (
            degradation_queue
            if degradation_queue is not None
            else DegradationQueue(
                aging_ticks=self._physiology_config.aging_ticks,
                waste_ticks=self._physiology_config.waste_ticks,
            )
        )

        self._metabolism = (
            metabolism
            if metabolism is not None
            else MetabolicLedger(
                replenishment=(
                    {k: 0.0 for k in ("observation", "cognition", "persistence", "maintenance")}
                    if self._explicit_metabolism
                    else None
                ),
                physiology_config=self._physiology_config,
            )
        )

        if self._interoception_provider is not None:
            # The first internal percept must describe the organism's actual
            # initial state.  Starting the provider at an unconditional 1.0
            # would create a one-cycle blind spot exactly when a germinal
            # organism has to make its first local decision.
            initial_metabolism = self._metabolism.snapshot()
            initial_ratio = min(
                initial_metabolism.reserve[k] / max(initial_metabolism.capacity[k], 1e-12)
                for k in initial_metabolism.capacity
            )
            self._interoception_provider.update_metrics(
                tick_latency=0.0,
                epistemic_surprise=0.0,
                metabolic_reserve=max(0.0, min(1.0, initial_ratio)),
                integrity=1.0,
            )
        self._assimilator = assimilator if assimilator is not None else InformationAssimilator()

        if homeostasis is not None and getattr(homeostasis, "config", None) is not None:
            if homeostasis.config != self._physiology_config:
                raise ValueError("incompatible homeostasis config with runtime physiology_config")

        if living_body_state is None:
            if homeostasis is not None:
                living_body_state = homeostasis.body_state
            elif physiology is not None:
                living_body_state = physiology.body_state
            else:
                living_body_state = LivingBodyState(age_ticks=tick_count)
        self._living_body_state = living_body_state

        if homeostasis is not None:
            if homeostasis.integrity != self._living_body_state.structural_integrity:
                raise ValueError("homeostasis contradicts living body integrity")
            self._homeostasis = HomeostaticController(
                integrity=self._living_body_state.structural_integrity,
                activity_scale=homeostasis.activity_scale,
                plasticity_enabled=homeostasis.plasticity_enabled,
                config=self._physiology_config,
                body_state=self._living_body_state,
            )
        else:
            self._homeostasis = HomeostaticController(
                config=self._physiology_config,
                body_state=self._living_body_state,
            )

        if physiology is not None:
            snapshot = physiology.snapshot()
            if (
                snapshot.state is not self._living_body_state.vital_state
                or snapshot.transitions != self._living_body_state.transitions
                or snapshot.death_tick != self._living_body_state.death_tick
            ):
                raise ValueError("physiology contradicts living body vital state")
        self._physiology = PhysiologyController(body_state=self._living_body_state)
        self._habitat = habitat
        self._resource_habitats = dict(resource_habitats or {})
        if len(self._resource_habitats) > 16 or any(
            not isinstance(resource_id, str) or not resource_id or len(resource_id) > 64
            or not isinstance(resource, SharedHabitat)
            for resource_id, resource in self._resource_habitats.items()
        ):
            raise ValueError("resource_habitats must contain bounded opaque habitat IDs")
        self._social_habitat = social_habitat
        self._social_ledger = social_ledger if social_ledger is not None else RelationLedger()
        self._social_resource_ledger = (
            social_resource_ledger if social_resource_ledger is not None else ResourceEvidenceLedger()
        )
        self._source_trust = source_trust if source_trust is not None else SourceTrustModel()
        self._social_habitat_released = False
        self._habitat_released = False
        self._birth_authority_released = False
        if self._habitat is not None and not self._habitat.has_allocation(self._organism_id):
            self._habitat.admit(self._organism_id, 1.0)
        for resource in self._resource_habitats.values():
            if not resource.has_allocation(self._organism_id) and not resource.admit(self._organism_id, 1.0):
                raise ValueError("resource habitat cannot register runtime")
        self._self_model = self_model if self_model is not None else SelfModel()
        if body_schema is not None:
            self._body_schema = body_schema
        else:
            salt_input = f"organism-body:{mutation_seed}:{self._organism_id}".encode()
            schema_salt = hashlib.sha256(salt_input).hexdigest()[:32]
            self._body_schema = BodySchemaEngine(id_salt=schema_salt)
        # The runtime may use BodySchema's private checkpoint surface internally.
        # Derive the cognitive-token namespace once; it is stable through
        # checkpoint restore but never appears in export_representation().
        private_body_schema = self._body_schema.export(current_tick=self._tick_count)
        self._cognitive_self_namespace_key = derive_cognitive_self_namespace(
            private_body_schema["id_salt"]
        )
        self._genome = genome
        if isinstance(mutation_seed, bool) or not isinstance(mutation_seed, int):
            raise ValueError("mutation_seed must be an integer")
        if (not isinstance(epigenetic_decay, (int, float)) or isinstance(epigenetic_decay, bool)
                or not math.isfinite(float(epigenetic_decay)) or not 0.0 <= epigenetic_decay <= 1.0):
            raise ValueError("epigenetic_decay must be within [0, 1]")
        if (len(epigenetic_priors) > 16
                or any(not isinstance(item, EpigeneticPrior) for item in epigenetic_priors)
                or len({item.key for item in epigenetic_priors}) != len(epigenetic_priors)
                or any(item.key not in self._SUPPORTED_EPIGENETIC_KEYS for item in epigenetic_priors)):
            raise ValueError("epigenetic_priors exceed bounded capacity")
        self._heritable_genome = heritable_genome
        self._mutation_seed = mutation_seed
        self._epigenetic_priors = tuple(epigenetic_priors)
        self._epigenetic_decay = float(epigenetic_decay)
        if self._birth_authority is not None and self._organism_id not in self._birth_authority.live_ids:
            genome_id = (
                self._heritable_genome.identity if self._heritable_genome is not None
                else self._genome.genome_id if self._genome is not None else "runtime"
            )
            if self._birth_authority.register_existing(organism_id=self._organism_id,
                                                       genome_id=genome_id,
                                                       generation=self._generation) is None:
                raise ValueError("birth authority cannot register runtime")
        self._kernel_limits = kernel_limits if kernel_limits is not None else KernelLimits()
        self._memory_consolidator = (
            memory_consolidator if memory_consolidator is not None else MemoryConsolidator(kernel_limits=self._kernel_limits)
        )
        self._reacclimation_remaining = 0  # matches CognitiveBridge's own §16a semantics
        self._cognitive_bridge: CognitiveBridge | None = cognitive_bridge
        if self._cognitive_bridge is None and genome is not None and cognitive_graph is not None:
            self._cognitive_bridge = CognitiveBridge(
                graph=cognitive_graph, genome=genome, kernel_limits=self._kernel_limits
            )
        if self._cognitive_bridge is not None:
            self._cognitive_bridge.bind_contention_identity(self._organism_id)
        self._actuation_enabled = bool(actuation_enabled)
        self._motor_exploration_mode = motor_exploration_mode
        self._actuator_constitution: ActuatorConstitution | None = None
        self._actuator_proposer: ActuatorProposer | None = None
        self._actuator_states: dict[str, ActuatorState] = {}
        self._motor_intent_selector: MotorIntentSelector | None = None
        self._actuator_system: ActuatorSystem | None = None
        self._sensorimotor_learner: SensorimotorLearner | None = None
        self._last_motor_intent: MotorIntent | None = None
        self._last_actuation: Actuation | None = None
        self._last_motor_intents: tuple[MotorIntent, ...] = ()
        self._last_actuations: tuple[Actuation, ...] = ()
        self._last_motor_origin = "none"
        self._last_motor_origin_detail = "none"
        self._last_executed_primitive_id: str | None = None
        self._pending_primitive_choice_context: tuple[
            str, tuple[str, ...], int, int
        ] | None = None
        self._pending_motor_observation: tuple[
            tuple[str, float, dict[str, float] | None, bool], ...
        ] = ()
        self._pending_proprioception: dict[str, float] = {}
        if self._actuation_enabled:
            if actuator_constitution is None:
                if genome is None:
                    raise ValueError("actuation_enabled requires genome or actuator_constitution")
                actuator_constitution = load_actuator_constitution(genome)
            self._actuator_constitution = actuator_constitution
            self._actuator_proposer = (
                actuator_proposer
                if actuator_proposer is not None
                else ActuatorProposer(actuator_constitution, organism_id=self._organism_id)
            )
            expected_ids = set(actuator_constitution.actuator_ids)
            if actuator_states is None:
                self._actuator_states = {
                    slot.actuator_id: ActuatorState.from_slot(slot) for slot in actuator_constitution.slots
                }
            else:
                if set(actuator_states) != expected_ids:
                    raise ValueError("actuator_states must exactly match ActuatorConstitution")
                self._actuator_states = dict(actuator_states)
            self._motor_intent_selector = motor_intent_selector or MotorIntentSelector()
            self._actuator_system = actuator_system or ActuatorSystem()
            if motor_exploration_mode == "babbling":
                self._sensorimotor_learner = (
                    sensorimotor_learner
                    if sensorimotor_learner is not None
                    else SensorimotorLearner(
                        actuator_constitution.actuator_ids,
                        organism_id=self._organism_id,
                        max_concurrent=None,
                    )
                )
        self._pending_embodied_work = 0.0
        self._narrative_journal: list[dict[str, Any]] = []

    @property
    def actuation_enabled(self) -> bool:
        return self._actuation_enabled

    @property
    def last_motor_intent(self) -> MotorIntent | None:
        return self._last_motor_intent

    @property
    def last_actuation(self) -> Actuation | None:
        return self._last_actuation

    @property
    def last_motor_intents(self) -> tuple[MotorIntent, ...]:
        return self._last_motor_intents

    @property
    def last_actuations(self) -> tuple[Actuation, ...]:
        return self._last_actuations

    @property
    def actuator_constitution(self) -> ActuatorConstitution | None:
        return self._actuator_constitution

    @property
    def active_motor_repertoire(self) -> tuple[str, ...]:
        if self._actuator_proposer is None:
            return ()
        return self._actuator_proposer.active_repertoire

    @property
    def sensorimotor_snapshot(self) -> SensorimotorSnapshot | None:
        if self._sensorimotor_learner is None:
            return None
        return self._sensorimotor_learner.snapshot()

    def _motor_percept_snapshot(self, percepts: tuple[Percept, ...]) -> dict[str, float]:
        # Never let the motor-discovery statistic "discover" an actuator
        # merely because requested/delivered proprioception echoes the command
        # itself. Those channels are for body/cognition, not controllability.
        proprioceptive_names = {
            sensor.cognitive_name
            for sensor in self._sensory_system.sensors
            if any(source_id.startswith("motor.") for source_id in sensor.source_ids)
        }
        values = {
            percept.name: float(percept.value)
            for percept in percepts
            if (
                percept.name not in proprioceptive_names
                and percept.value is not None
                and math.isfinite(float(percept.value))
            )
        }
        return dict(sorted(values.items())[:32])

    def _sensorimotor_body_snapshot(
        self,
        percepts: tuple[Percept, ...],
    ) -> dict[str, float]:
        """Richer opaque state for learned body dynamics.

        Motor command echoes remain excluded so the learner must model bodily
        consequences rather than trivially reading its own requested vector.
        """
        proprioceptive_names = {
            sensor.cognitive_name
            for sensor in self._sensory_system.sensors
            if any(source_id.startswith("motor.") for source_id in sensor.source_ids)
        }
        values = {
            percept.name: float(percept.value)
            for percept in percepts
            if (
                percept.name not in proprioceptive_names
                and percept.value is not None
                and math.isfinite(float(percept.value))
            )
        }
        return dict(sorted(values.items())[:64])

    def _complete_pending_motor_observation(
        self, percepts: tuple[Percept, ...], *, tick: int
    ) -> tuple[str, ...]:
        pending = self._pending_motor_observation
        if not pending or self._actuator_proposer is None:
            return ()
        after = self._motor_percept_snapshot(percepts)
        promoted: list[str] = []
        for actuator_id, activation, before, advance_probe in pending:
            if before is not None:
                for percept_id in sorted(set(before) & set(after)):
                    self._actuator_proposer.record_effect(
                        actuator_id,
                        percept_id,
                        activation=activation,
                        delta_percept=after[percept_id] - before[percept_id],
                        tick=tick,
                    )
                if self._motor_exploration_mode in {"spontaneous", "babbling"}:
                    self._actuator_proposer.consider_natural_evidence(actuator_id)
            if advance_probe:
                self._actuator_proposer.advance_tick(actuator_id)
            if actuator_id in self._actuator_proposer.active_repertoire:
                promoted.append(actuator_id)
        self._pending_motor_observation = ()
        return tuple(dict.fromkeys(promoted))

    def _motor_step(
        self, cognition: CognitiveBridgeResult | None, percepts: tuple[Percept, ...], *, tick: int
    ) -> None:
        baseline = self._motor_percept_snapshot(percepts)
        sensorimotor_body_state = self._sensorimotor_body_snapshot(percepts)

        self._last_motor_intent = None
        self._last_actuation = None
        self._last_motor_intents = ()
        self._last_actuations = ()
        self._last_executed_primitive_id = None
        if (
            not self._actuation_enabled
            or self._actuator_proposer is None
            or self._motor_intent_selector is None
            or self._actuator_system is None
        ):
            return

        active_repertoire = self._actuator_proposer.active_repertoire
        self._last_motor_origin = "none"
        self._last_motor_origin_detail = "none"
        intents: tuple[MotorIntent, ...] = ()
        pending: list[tuple[str, float, dict[str, float] | None, bool]] = []

        cognitive_intents: tuple[MotorIntent, ...] = ()
        if cognition is not None and active_repertoire:
            readouts = cognition.readouts_for_family("motor")
            eligible = {
                actuator_id: value
                for actuator_id, value in readouts.items()
                if actuator_id in active_repertoire
            }
            cognitive_intents = self._motor_intent_selector.select_many(
                eligible,
                max_concurrent=len(active_repertoire),
            )

        primitive_execution: tuple[MotorIntent, ...] = ()
        primitive_selected_now = False
        if self._sensorimotor_learner is not None:
            # An already-started learned skill is an atomic temporal action:
            # continue it before considering a new cognitive primitive.
            if self._sensorimotor_learner.active_primitive_id is not None:
                primitive_execution = self._sensorimotor_learner.motor_intents(tick)
            elif cognition is not None:
                primitive_readouts = cognition.readouts_for_family("primitive")
                eligible_primitives = [
                    (float(value), str(primitive_id))
                    for primitive_id, value in primitive_readouts.items()
                    if (
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(float(value))
                        and float(value)
                        >= self._motor_intent_selector.selection_threshold
                    )
                ]
                if eligible_primitives:
                    _, primitive_id = sorted(
                        eligible_primitives,
                        key=lambda item: (-item[0], item[1]),
                    )[0]
                    if self._sensorimotor_learner.activate_primitive(
                        primitive_id,
                        source="cognition",
                    ):
                        primitive_selected_now = True
                        primitive_execution = (
                            self._sensorimotor_learner.motor_intents(tick)
                        )

        if primitive_execution:
            intents = primitive_execution
            self._last_executed_primitive_id = (
                self._sensorimotor_learner.last_output_primitive_id
                if self._sensorimotor_learner is not None
                else None
            )
            self._last_motor_origin = "primitive"
            primitive_source = (
                self._sensorimotor_learner.last_output_source
                if self._sensorimotor_learner is not None
                else "primitive"
            )
            self._last_motor_origin_detail = (
                "primitive_cognition"
                if primitive_source == "primitive"
                else "primitive_verification"
            )

        elif self._motor_exploration_mode == "babbling":
            if self._sensorimotor_learner is None:
                raise RuntimeError("babbling mode requires sensorimotor learner")

            had_active_primitive = (
                self._sensorimotor_learner.active_primitive_id is not None
            )
            # Sensorimotor learning is independent from cognitive admission.
            # A full CognitiveGraph or delayed state->action association must
            # never freeze causal investigation of the body.
            developmental_intents = self._sensorimotor_learner.motor_intents(
                tick,
                allow_verification=True,
            )
            output_source = self._sensorimotor_learner.last_output_source

            if output_source == "passive":
                # Null-action probes estimate passive body dynamics. They must
                # remain isolated from cognitive motor commands or the baseline
                # would no longer represent f(state, action=0).
                intents = ()
                self._last_motor_origin = "none"
                self._last_motor_origin_detail = "none"

            elif output_source in {"primitive", "verification"}:
                self._last_executed_primitive_id = (
                    self._sensorimotor_learner.last_output_primitive_id
                )
                if output_source == "verification" and not had_active_primitive:
                    if (
                        cognition is not None
                        and self._last_executed_primitive_id is not None
                    ):
                        primitive = next(
                            (
                                item
                                for item in self._sensorimotor_learner.primitives
                                if item.primitive_id
                                == self._last_executed_primitive_id
                            ),
                            None,
                        )
                        if primitive is not None:
                            new_context = (
                                primitive.primitive_id,
                                tuple(sorted(cognition.active_concept_ids)),
                                # Four action frames t..t+3 are only
                                # causally closed by the pre-action body state
                                # observed at t+4.
                                tick + primitive.duration_ticks,
                                primitive.samples,
                            )
                            current_context = self._pending_primitive_choice_context
                            # Pending association credit is opportunistic, not a
                            # global lock. Preserve a useful existing context;
                            # replace an empty-context wait if a later probe has
                            # actual active concepts.
                            if (
                                current_context is None
                                or (
                                    not current_context[1]
                                    and bool(new_context[1])
                                )
                            ):
                                self._pending_primitive_choice_context = new_context
                # Primitive verification/execution is isolated or its measured
                # consequence would be confounded by unrelated cognitive output.
                intents = developmental_intents
                self._last_motor_origin = "primitive" if intents else "none"
                self._last_motor_origin_detail = (
                    "primitive_verification" if intents else "none"
                )
            else:
                # A one-channel babbling episode is a clean natural causal
                # probe for the direct actuator proposer. Multi-channel
                # synergies stay exclusively in the sensorimotor learner
                # because their effects cannot be attributed to one actuator.
                if len(developmental_intents) == 1:
                    isolated = developmental_intents[0]
                    pending.append(
                        (
                            isolated.actuator_id,
                            float(isolated.activation),
                            baseline,
                            False,
                        )
                    )

                merged: list[MotorIntent] = []
                seen: set[str] = set()

                # During sensorimotor development, cognition receives one slot
                # while the remaining capacity stays available for body-wide
                # exploration. This prevents an early repetitive readout from
                # monopolizing the body before its dynamics are learned.
                if cognitive_intents:
                    intent = cognitive_intents[0]
                    merged.append(intent)
                    seen.add(intent.actuator_id)

                for intent in developmental_intents:
                    if intent.actuator_id in seen:
                        continue
                    merged.append(intent)
                    seen.add(intent.actuator_id)

                intents = tuple(merged)
                if cognitive_intents and developmental_intents:
                    self._last_motor_origin = "mixed"
                    self._last_motor_origin_detail = "mixed"
                elif cognitive_intents:
                    self._last_motor_origin = "cognition"
                    self._last_motor_origin_detail = "cognition"
                elif developmental_intents:
                    self._last_motor_origin = "babbling"
                    self._last_motor_origin_detail = "babbling"

        elif cognitive_intents:
            intents = cognitive_intents
            self._last_motor_origin = "cognition"
            self._last_motor_origin_detail = "cognition"

        if not intents and self._motor_exploration_mode == "structured_probe":
            probe_turn = True
            if active_repertoire:
                digest = hashlib.sha256(
                    f"motor-probe:{self._organism_id}:{tick}".encode("utf-8")
                ).digest()
                probe_turn = (int.from_bytes(digest[:4], "big") % 4) == 0
            plan = self._actuator_proposer.probing_plan(tick=tick) if probe_turn else {}
            if plan:
                pending_id = sorted(plan)[0]
                pending_activation = 1.0 if plan[pending_id] else 0.0
                pending.append((pending_id, pending_activation, baseline, True))
                if pending_activation > 0.0:
                    intents = (
                        MotorIntent(
                            actuator_id=pending_id,
                            activation=pending_activation,
                        ),
                    )
                    self._last_motor_origin = "probe"
                    self._last_motor_origin_detail = "probe"

        if not intents and self._motor_exploration_mode == "spontaneous":
            digest = hashlib.sha256(
                f"basal-motor-noise:{self._organism_id}:{tick}".encode("utf-8")
            ).digest()
            if digest[0] < 64 and self._actuator_constitution is not None:
                ids = self._actuator_constitution.actuator_ids
                pending_id = ids[int.from_bytes(digest[1:5], "big") % len(ids)]
                pending_activation = 0.25 + (
                    int.from_bytes(digest[5:9], "big")
                    / float((1 << 32) - 1)
                ) * 0.75
                intents = (
                    MotorIntent(
                        actuator_id=pending_id,
                        activation=pending_activation,
                    ),
                )
                pending.append((pending_id, pending_activation, baseline, False))
                self._last_motor_origin = "spontaneous"
                self._last_motor_origin_detail = "spontaneous"

        self._pending_motor_observation = tuple(pending)
        if not intents:
            self._pending_proprioception = {}
            if self._sensorimotor_learner is not None:
                self._sensorimotor_learner.observe(
                    tick=tick,
                    body_state=sensorimotor_body_state,
                    motor_vector={},
                    discovery_eligible=False,
                    execution_primitive_id=None,
                )
            return

        actuations: list[Actuation] = []
        proprioception: dict[str, float] = {}
        total_cost = 0.0
        for intent in intents:
            state = self._actuator_states.get(intent.actuator_id)
            if state is None:
                raise ValueError(
                    f"motor intent references unknown actuator {intent.actuator_id!r}"
                )
            actuation = self._actuator_system.execute(intent, state)
            actuations.append(actuation)
            total_cost += actuation.cost
            aid = actuation.actuator_id
            proprioception.update({
                f"motor.requested_activation.{aid}": actuation.requested,
                f"motor.delivered_activation.{aid}": actuation.delivered,
                f"motor.load.{aid}": actuation.cost,
            })

        self._last_motor_intents = tuple(intents)
        self._last_actuations = tuple(actuations)
        self._last_motor_intent = self._last_motor_intents[0]
        self._last_actuation = self._last_actuations[0]
        self._charge_metabolism("maintenance", total_cost)
        self._pending_proprioception = proprioception

        if (
            primitive_selected_now
            and self._last_executed_primitive_id is not None
            and cognition is not None
            and self._cognitive_bridge is not None
            and self._sensorimotor_learner is not None
            and any(
                primitive.primitive_id == self._last_executed_primitive_id
                for primitive in self._sensorimotor_learner.cognitive_primitives
            )
        ):
            self._cognitive_bridge.observe_primitive_execution(
                self._last_executed_primitive_id,
                concept_ids=cognition.active_concept_ids,
                tick=tick,
            )
        if self._sensorimotor_learner is not None:
            self._sensorimotor_learner.observe(
                tick=tick,
                body_state=sensorimotor_body_state,
                motor_vector={
                    actuation.actuator_id: float(actuation.delivered)
                    for actuation in self._last_actuations
                    if actuation.delivered > 0.0
                },
                discovery_eligible=(
                    self._last_motor_origin != "primitive"
                ),
                execution_primitive_id=(
                    self._last_executed_primitive_id
                    if self._last_motor_origin == "primitive"
                    else None
                ),
            )

            pending_context = self._pending_primitive_choice_context
            if (
                pending_context is not None
                and tick >= pending_context[2]
                and self._sensorimotor_learner.active_primitive_id is None
            ):
                (
                    primitive_id,
                    concept_ids,
                    _complete_tick,
                    samples_before,
                ) = pending_context
                verified = next(
                    (
                        primitive
                        for primitive in self._sensorimotor_learner.cognitive_primitives
                        if (
                            primitive.primitive_id == primitive_id
                            and primitive.samples > samples_before
                        )
                    ),
                    None,
                )
                if self._cognitive_bridge is None or verified is None:
                    self._pending_primitive_choice_context = None
                elif self._cognitive_bridge.observe_primitive_execution(
                    primitive_id,
                    concept_ids=concept_ids,
                    tick=tick,
                ):
                    # The normal cognition tick has admitted the readout and
                    # the association evidence is now recorded exactly once.
                    self._pending_primitive_choice_context = None
                # Otherwise keep the context until a later cognition tick
                # admits the readout within the normal mutation budget.
                # This pending association never gates further sensorimotor
                # investigation; the competence exists independently of its
                # cognitive consolidation state.

    @property
    def last_motor_origin(self) -> str:
        """Evaluator-only provenance of the latest motor intent."""
        return self._last_motor_origin

    @property
    def last_motor_origin_detail(self) -> str:
        """Evaluator-only detailed provenance for learned primitive execution."""
        return self._last_motor_origin_detail

    @property
    def narrative_journal(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._narrative_journal)

    @property
    def organism_id(self) -> str:
        return self._organism_id

    def _charge_metabolism(self, kind: str, amount: float) -> None:
        """Charge declared work, reducing activity while physiologically dormant."""
        factor = (
            self._physiology_config.dormant_metabolic_factor
            if self._physiology.state is VitalState.DORMANT
            else 1.0
        )
        self._metabolism.charge(kind, amount * factor)

    @property
    def min_samples(self) -> int:
        return self._min_samples

    @property
    def conflict_z(self) -> float:
        return self._conflict_z

    def effective_configuration(self) -> dict[str, Any]:
        from dataclasses import asdict
        config: dict[str, Any] = {
            "organism_id": self._organism_id,
            "attention_budget": self._attention_budget,
            "investigate_ticks": self._investigate_ticks,
            "conflict_z": self._conflict_z,
            "min_samples": self._min_samples,
            "discover_senses": self._discover_senses,
            "bootstrap_semantic_senses": self._bootstrap_semantic_senses,
            "sensory_plasticity": self._sensory_system.plasticity_enabled,
            "sensory_constitution": self._sensory_system.constitution(),
            "explicit_metabolism": self._explicit_metabolism,
            "auto_promote_predictors": self._auto_promote_predictors,
            "generation": self._generation,
            "reproduction_cost": self._reproduction_cost,
            "social_exchange_quantum": self._social_exchange_quantum,
            "social_exchange_cost": self._social_exchange_cost,
            "resting_requested": self._resting_requested,
            "interoception_enabled": self._interoception_enabled,
            "interoception_mode": self._interoception_mode,
            "mutation_seed": self._mutation_seed,
            "epigenetic_decay": self._epigenetic_decay,
            "actuation_enabled": self._actuation_enabled,
            "motor_exploration_mode": self._motor_exploration_mode,
            "motor_selection_threshold": (
                self._motor_intent_selector.selection_threshold
                if self._motor_intent_selector is not None
                else None
            ),
            "physiology": asdict(self._physiology_config),
        }
        if self._epigenetic_priors:
            config["epigenetic_priors"] = [
                {"key": prior.key, "value": prior.value} for prior in self._epigenetic_priors
            ]
        if self._heritable_genome is not None:
            config["heritable_genome"] = {
                "genome_id": self._heritable_genome.genome_id,
                "identity": self._heritable_genome.identity,
                "loci": [[key, value] for key, value in self._heritable_genome.loci],
            }
        if self._genome is not None:
            config["genome"] = {
                "genome_id": self._genome.genome_id,
                "schema_version": self._genome.schema_version,
                "kernel_compatibility": self._genome.kernel_compatibility,
                "development": {
                    "initial_concepts": self._genome.development.initial_concepts,
                    "soft_node_budget": self._genome.development.soft_node_budget,
                    "soft_edge_budget": self._genome.development.soft_edge_budget,
                    "consolidation_interval_ticks": self._genome.development.consolidation_interval_ticks,
                    "sense_node_budget": self._genome.development.sense_node_budget,
                    "sense_retention_ticks": self._genome.development.sense_retention_ticks,
                },
                "structure": {
                    "grow_threshold": self._genome.structure.grow_threshold,
                    "prune_threshold": self._genome.structure.prune_threshold,
                    "minimum_support": self._genome.structure.minimum_support,
                    "tentative_lifetime_ticks": self._genome.structure.tentative_lifetime_ticks,
                },
                "plasticity": {
                    "learning_rate": {
                        "initial": self._genome.plasticity.learning_rate.initial,
                        "min": self._genome.plasticity.learning_rate.minimum,
                        "max": self._genome.plasticity.learning_rate.maximum,
                    },
                    "forgetting_rate": {
                        "initial": self._genome.plasticity.forgetting_rate.initial,
                        "min": self._genome.plasticity.forgetting_rate.minimum,
                        "max": self._genome.plasticity.forgetting_rate.maximum,
                    },
                    "eligibility_decay": self._genome.plasticity.eligibility_decay,
                },
            }
        if self._kernel_limits is not None:
            config["kernel_limits"] = asdict(self._kernel_limits)
        return config

    @property
    def physiology_config(self) -> PhysiologyConfig:
        return self._physiology_config

    def runtime_fingerprint(
        self,
        *,
        software_version: str | None = None,
        build_identity: str | None = None,
    ) -> str:
        """Derive a canonical configuration fingerprint for this organism runtime."""
        from .fingerprint import generate_runtime_fingerprint_from_runtime
        return generate_runtime_fingerprint_from_runtime(
            self,
            software_version=software_version,
            build_identity=build_identity,
        )

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def acclimation(self) -> HostAcclimation:
        return self._acclimation

    @property
    def rhythm_model(self) -> RhythmModel:
        return self._rhythm_model

    @property
    def adaptive_senses(self) -> AdaptiveSenseModel:
        return self._adaptive_senses

    @property
    def sensory_system(self) -> SensorySystem:
        return self._sensory_system

    def _sensory_phenotype_view(self) -> dict[str, Any]:
        source_ids = {
            source_id
            for sensor in self._sensory_system.sensors
            for source_id in sensor.source_ids
        }
        return self._sensory_system.phenotype_view(
            signal_ids_by_source={
                source_id: self._signal_identity.signal_id(source_id)
                for source_id in sorted(source_ids)
            }
        )

    @property
    def self_model(self) -> SelfModel:
        return self._self_model

    @property
    def body_schema(self) -> BodySchemaEngine:
        return self._body_schema

    @property
    def evidence_ledger(self) -> EvidenceRevisionLedger:
        return self._evidence_ledger

    @property
    def genome(self) -> Genome | None:
        return self._genome

    @property
    def heritable_genome(self) -> HeritableGenome | None:
        """Genetic state, kept separate from acquired phenotype and memory."""
        return self._heritable_genome

    @property
    def epigenetic_priors(self) -> tuple[EpigeneticPrior, ...]:
        """Coarse, non-semantic developmental biases; never lifetime knowledge."""
        return self._epigenetic_priors

    def _decay_epigenetic_priors(self) -> None:
        if not self._epigenetic_priors or self._epigenetic_decay <= 0.0:
            return
        factor = 1.0 - self._epigenetic_decay
        self._epigenetic_priors = tuple(
            EpigeneticPrior(item.key, round(item.value * factor, 12))
            for item in self._epigenetic_priors
            if item.value * factor > 1e-12
        )

    def _next_heritable_genome(self) -> HeritableGenome | None:
        if self._heritable_genome is None or self._genome is None:
            return None
        return mutate_genome(
            self._heritable_genome,
            sigma=self._genome.mutation_policy.continuous_sigma,
            max_fields=self._genome.mutation_policy.max_fields_per_generation,
            seed=self._mutation_seed + self._generation + 1,
        )

    def _child_genome(self, inherited: HeritableGenome) -> Genome:
        """Project bounded loci into a fresh validated operational genome."""
        if self._genome is None:
            raise RuntimeError("heritable projection requires an operational genome")
        loci = dict(inherited.loci)
        development = self._genome.development
        node_budget = max(1, min(self._kernel_limits.max_nodes, round(loci.get("soft_node_budget", development.soft_node_budget))))
        edge_budget = max(1, min(self._kernel_limits.max_edges, round(loci.get("soft_edge_budget", development.soft_edge_budget))))
        initial_concepts = max(0, min(self._kernel_limits.max_concepts, round(loci.get("initial_concepts", development.initial_concepts))))
        development = replace(
            development,
            initial_concepts=initial_concepts,
            soft_node_budget=node_budget,
            soft_edge_budget=edge_budget,
            sense_node_budget=min(development.sense_node_budget, node_budget),
        )
        plasticity = self._genome.plasticity
        learning = plasticity.learning_rate
        forgetting = plasticity.forgetting_rate
        if "learning_rate" in loci:
            learning = replace(learning, initial=max(learning.minimum, min(learning.maximum, loci["learning_rate"])))
        if "forgetting_rate" in loci:
            forgetting = replace(forgetting, initial=max(forgetting.minimum, min(forgetting.maximum, loci["forgetting_rate"])))
        plasticity = replace(plasticity, learning_rate=learning, forgetting_rate=forgetting)
        return replace(self._genome, genome_id=inherited.identity, parent_ids=(self._genome.genome_id,),
                       development=development, plasticity=plasticity)

    @property
    def reproductive_pressure(self) -> ReproductivePressure | None:
        return self._reproductive_pressure

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def social_habitat(self) -> SocialHabitat | None:
        """Return the explicitly authorized social boundary, if attached."""
        return self._social_habitat

    @property
    def social_ledger(self) -> RelationLedger:
        """Local, organism-owned aggregate memory of social outcomes."""
        return self._social_ledger

    @property
    def social_resource_ledger(self) -> ResourceEvidenceLedger:
        """Local evidence about opaque resource availability."""
        return self._social_resource_ledger

    @property
    def degradation_queue(self) -> DegradationQueue:
        """Bounded organism-owned retention queue for aging low-value state."""
        return self._degradation

    def join_social_habitat(self, habitat: SocialHabitat) -> bool:
        """Join an explicitly supplied bounded social habitat.

        Joining is an organism-side action: the habitat remains the authority
        for admission and capacity, and no peer is discovered implicitly.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot join a social habitat")
        if self._social_habitat is not None and self._social_habitat is not habitat:
            raise ValueError("a different social habitat is already attached")
        if self._social_habitat is habitat and self._organism_id in habitat.members:
            return True
        if not habitat.admit(self._organism_id):
            return False
        self._social_habitat = habitat
        self._social_habitat_released = False
        return True

    def observe_social_presence(self) -> tuple[SocialPresence, ...]:
        """Read bounded opaque presence from the explicitly attached habitat."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot observe social presence")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        return self._social_habitat.observe_presence(self._organism_id)

    def select_social_opportunity(self) -> SocialPresence | None:
        """Select one local opportunity for cognition to consider.

        This is deliberately not an interaction: no resource is moved and no
        peer is scheduled. Selection uses only the organism's own bounded
        relation observations, preferring a fresh/unknown channel so that the
        runtime can decide what evidence to seek next.
        """
        candidates = tuple(item for item in self.observe_social_presence() if item.available)
        if not candidates:
            return None
        by_target: dict[str, tuple[SocialRelation, ...]] = {}
        for relation in self._social_ledger.relations:
            if relation.source_id == self._organism_id:
                by_target.setdefault(relation.target_id, ())
                by_target[relation.target_id] += (relation,)

        def priority(item: SocialPresence) -> tuple[float, str]:
            relations = by_target.get(item.target_id, ())
            if not relations:
                # Unknown channels receive an exploration bonus.  This is a
                # local information-seeking capability, not an evaluator
                # supplied preference or a social label.
                return (-0.25, item.target_id)
            expected_net = max(
                (relation.support - relation.harm)
                * min(1.0, relation.observations / 8.0)
                * relation.reliability(self._tick_count)
                + 0.25 / (1.0 + relation.observations)
                for relation in relations
            )
            # Positive evidence makes a channel worth revisiting; accumulated
            # harm lowers its priority without making it unreachable, allowing
            # later evidence to revise the relation.
            return (-expected_net, item.target_id)

        return min(candidates, key=priority)

    def request_social_exchange(self, target_id: str, resource: str, amount: float) -> InteractionOutcome:
        """Issue one explicit social exchange request.

        The runtime never schedules peers or chooses a social objective; the
        caller supplies the target and bounded habitat mediates the result.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot interact")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        outcome = self._social_habitat.exchange(self._organism_id, target_id, resource, amount)
        self._charge_metabolism("cognition", self._social_exchange_cost)
        self._social_ledger.observe(
            self._organism_id, target_id, benefit=outcome.granted,
            reciprocal=outcome.relation.reciprocal_observations > 0,
            tick=self._tick_count, channel=resource,
        )
        self._social_resource_ledger.observe(
            resource, requested=amount, granted=outcome.granted, tick=self._tick_count
        )
        return outcome

    def autonomous_social_step(self) -> InteractionOutcome | None:
        """Take one bounded social opportunity using only local evidence.

        The runtime chooses the target from opaque presence and its own
        relation ledger, and chooses the first bounded resource token exposed
        by the authorized habitat.  No caller supplies a peer, role, label or
        social objective; an unavailable opportunity simply yields ``None``.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot interact")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        opportunity = self.select_social_opportunity()
        resources = self._social_habitat.resource_tokens
        if opportunity is None or not resources:
            return None
        resource = self._social_resource_ledger.choose(resources, current_tick=self._tick_count)
        if resource is None:
            return None
        return self.request_social_exchange(
            opportunity.target_id, resource, self._social_exchange_quantum
        )

    def propose_social_competition(self) -> SocialCompetitionRequest | None:
        """Propose a finite-resource contest from local negative evidence.

        The proposal does not execute or target a peer. The authorized
        habitat adjudicates a batch of proposals, allowing simultaneous
        requests to contend without a social planner choosing winners.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot compete")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        opportunities = tuple(item for item in self.observe_social_presence() if item.available)
        negative = tuple(
            item for item in self._social_ledger.relations
            if item.source_id == self._organism_id
            and item.valence is RelationValence.NEGATIVE
            and any(item.target_id == opportunity.target_id for opportunity in opportunities)
        )
        resources = self._social_habitat.resource_tokens
        if not negative or not resources:
            return None
        relation = max(
            negative,
            key=lambda item: (
                item.harm * item.freshness(self._tick_count),
                item.observations,
                item.target_id,
                item.channel,
            ),
        )
        resource = relation.channel if relation.channel in resources else self._social_resource_ledger.choose(
            resources, current_tick=self._tick_count
        )
        if resource is None:
            return None
        return SocialCompetitionRequest(self._organism_id, resource, self._social_exchange_quantum)

    def suspend_social_interaction(self, target_id: str) -> None:
        """Suspend this runtime's future requests to one admitted peer."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot suspend social interactions")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        self._social_habitat.suspend(self._organism_id, target_id)

    def reject_social_interaction(self, target_id: str) -> None:
        """Refuse a future request and retain that refusal as local evidence."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot reject social interactions")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        self._social_habitat.reject(self._organism_id, target_id)
        self._social_ledger.observe(
            self._organism_id, target_id, rejected=True, tick=self._tick_count
        )

    def resume_social_interaction(self, target_id: str) -> bool:
        """Resume this runtime's suspended channel to one admitted peer."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot resume social interactions")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        return self._social_habitat.resume(self._organism_id, target_id)

    def request_social_competition(self, requests: list[tuple[str, str, float]]) -> tuple[InteractionOutcome, ...]:
        """Submit an explicit finite-resource competition request batch."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot interact")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        if any(source_id != self._organism_id for source_id, _, _ in requests):
            raise ValueError("competition requests must originate from this runtime")
        outcomes = self._social_habitat.compete(requests)
        self._charge_metabolism("cognition", self._social_exchange_cost * len(requests))
        requested = {(source, resource): amount for source, resource, amount in requests}
        for outcome in outcomes:
            loss = max(0.0, requested.get((outcome.source_id, outcome.resource), outcome.granted) - outcome.granted)
            # The habitat relation records which competing peer was observed;
            # retain that target rather than collapsing scarcity onto the
            # habitat token in the runtime's local memory.
            self._social_ledger.observe(
                outcome.source_id, outcome.relation.target_id, cost=loss,
                tick=self._tick_count, channel=outcome.resource,
            )
            requested_amount = requested.get((outcome.source_id, outcome.resource), outcome.granted)
            if requested_amount > 0.0:
                self._social_resource_ledger.observe(
                    outcome.resource, requested=requested_amount,
                    granted=outcome.granted, tick=self._tick_count
                )
        return outcomes

    def observe_reproductive_pressure(self, *, adaptive: bool, capacity_exhausted: bool,
                                      blocked_growth: bool) -> ReproductiveStatus:
        """Record endogenous developmental pressure without evaluator input."""
        if self._reproductive_pressure is None:
            raise RuntimeError("reproductive pressure is not configured")
        return self._reproductive_pressure.observe(
            viable=self._physiology.state is not VitalState.DEAD,
            adaptive=adaptive,
            capacity_exhausted=capacity_exhausted,
            blocked_growth=blocked_growth,
        )

    def _attempt_clonal_bud_with_inherited(
        self, inherited: HeritableGenome | None,
    ) -> BirthRecord | None:
        """Reserve one child using one already-selected inherited genome."""
        if self._birth_authority is None or self._reproductive_pressure is None or self._genome is None:
            return None
        if not self._birth_surfaces_available():
            return None
        child_genome_id = inherited.identity if inherited is not None else self._genome.genome_id
        record = clonal_bud(parent_id=self._organism_id, genome_id=child_genome_id,
                            generation=self._generation, authority=self._birth_authority,
                            pressure=self._reproductive_pressure)
        if record is not None and self._reproduction_cost:
            self._metabolism.charge("maintenance", self._reproduction_cost)
        return record

    def attempt_clonal_bud(self) -> BirthRecord | None:
        """Materialize one child only through the explicitly supplied authority."""
        return self._attempt_clonal_bud_with_inherited(self._next_heritable_genome())

    def materialize_clonal_bud(self) -> "OrganismRuntime | None":
        """Create a fresh germinal runtime for an authorized clonal birth.

        Acquired phenotype, memory, metabolism and physiology are not copied;
        only the inherited genome and lineage identity cross the birth boundary.
        """
        # Select the heritable mutation once.  Recomputing it after the
        # authority transaction could make the lineage record and the
        # materialized child's genome disagree.
        inherited = self._next_heritable_genome()
        record = self._attempt_clonal_bud_with_inherited(inherited)
        if record is None or self._genome is None or self._birth_authority is None:
            return None
        child_genome = self._child_genome(inherited) if inherited is not None else self._genome
        graph = load_base_graph(kernel_limits=self._kernel_limits)
        child = OrganismRuntime(
            attention_budget=self._attention_budget,
            investigate_ticks=self._investigate_ticks,
            conflict_z=self._conflict_z,
            min_samples=self._min_samples,
            discover_senses=self._discover_senses,
            bootstrap_semantic_senses=self._bootstrap_semantic_senses,
            # Heritability boundary: the complete sensory constitution
            # crosses birth, acquired SensorState and mutation history do not.
            sensory_system=self._sensory_system.germinal_copy(),
            genome=child_genome,
            heritable_genome=inherited,
            mutation_seed=self._mutation_seed + self._generation + 1,
            epigenetic_priors=self._epigenetic_priors,
            epigenetic_decay=self._epigenetic_decay,
            kernel_limits=self._kernel_limits,
            cognitive_graph=graph,
            host_lifecycle=self._lifecycle.fork_for_child(),
            physiology_config=self._physiology_config,
            organism_id=record.organism_id,
            birth_authority=self._birth_authority,
            generation=record.generation,
            # Admission is an explicit habitat transaction.  Do not attach a
            # social boundary to a child that was not admitted, otherwise its
            # first tick would hold an unusable boundary and fail closed only
            # through an exception.
            social_habitat=None,
            resource_habitats=self._resource_habitats,
            reproductive_pressure=(
                ReproductivePressure(threshold_ticks=self._reproductive_pressure.threshold_ticks)
                if self._reproductive_pressure is not None else None
            ),
            explicit_metabolism=self._explicit_metabolism,
            reproduction_cost=self._reproduction_cost,
            social_exchange_quantum=self._social_exchange_quantum,
            social_exchange_cost=self._social_exchange_cost,
            interoception_enabled=self._interoception_enabled,
            interoception_mode=self._interoception_mode,
            # The motor body is constitutional: descendants derive their own
            # ActuatorConstitution from the child's (possibly mutated) genome.
            # Acquired actuator state/repertoire is not copied from the parent.
            actuation_enabled=self._actuation_enabled,
            motor_intent_selector=(
                MotorIntentSelector(
                    selection_threshold=self._motor_intent_selector.selection_threshold
                )
                if self._actuation_enabled and self._motor_intent_selector is not None
                else None
            ),
        )
        if self._social_habitat is not None:
            child.join_social_habitat(self._social_habitat)
        return child

    @property
    def cognitive_bridge(self) -> CognitiveBridge | None:
        return self._cognitive_bridge

    @property
    def shadow_predictions(self) -> tuple[ShadowPrediction, ...]:
        """Expose bounded shadow evidence without exposing evaluator state."""
        if self._cognitive_bridge is None:
            return ()
        return self._cognitive_bridge.shadow_predictions

    def promote_shadow_prediction(self, source_id: str, target_id: str) -> bool:
        """Register one validated shadow predictor for structural contention."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot promote predictions")
        if self._cognitive_bridge is None:
            return False
        # Some callers drive the bridge directly (for example a scientific
        # study) rather than through ``Runtime.tick``. Use the bridge clock
        # when it is ahead so structural proposals receive the correct
        # eligibility tick instead of silently being stamped at zero.
        bridge_tick = getattr(self._cognitive_bridge, "_tick", self._tick_count)
        return self._cognitive_bridge.promote_shadow_prediction(
            source_id, target_id, tick=max(self._tick_count, bridge_tick)
        )

    @property
    def memory_consolidator(self) -> MemoryConsolidator:
        return self._memory_consolidator

    @property
    def signal_knowledge(self) -> SignalKnowledgeEngine:
        return self._signal_knowledge

    @property
    def metabolism(self) -> MetabolicLedger:
        return self._metabolism

    @property
    def living_body_state(self) -> LivingBodyState:
        return self._living_body_state

    def register_embodied_work(self, amount: float) -> None:
        """Queue a bounded scalar physical-work cost for the next physiology tick.

        The apparatus may report measured physical work, but it may not choose
        an internal resource compartment or attach anatomical/action semantics.
        The queued scalar is charged as maintenance after normal replenishment,
        so it contributes to the next canonical metabolic/physiology snapshot.
        """
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(float(amount))
            or amount < 0.0
        ):
            raise ValueError("embodied work must be finite and non-negative")
        self._pending_embodied_work = min(
            0.25,
            self._pending_embodied_work + float(amount),
        )

    def absorb_metabolic_energy(self, amount: float) -> float:
        """Absorb an untyped scalar amount through the organism boundary.

        The caller may provide physical energy/material magnitude, but it may
        not select an internal metabolic compartment or attach an external
        resource identity. Distribution across the body's finite reserves is
        organism-owned physiology.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot absorb metabolic energy")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
            raise ValueError("absorbed metabolic energy must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("absorbed metabolic energy must be non-negative")
        if amount == 0.0:
            return 0.0
        snapshot = self._metabolism.snapshot()
        deficits = {
            kind: max(0.0, snapshot.capacity[kind] - snapshot.reserve[kind])
            for kind in snapshot.capacity
        }
        total_deficit = sum(deficits.values())
        accepted = min(amount, total_deficit)
        if accepted <= 0.0:
            return 0.0
        absorbed = 0.0
        for kind in sorted(deficits):
            if deficits[kind] <= 0.0:
                continue
            share = accepted * (deficits[kind] / total_deficit)
            absorbed += self._metabolism.intake(kind, share)
        return absorbed

    def request_resource_intake(self, amount: float, *, kind: str = "maintenance",
                                resource_id: str | None = None) -> float:
        """Acquire bounded resource from the attached shared habitat.

        Habitat scarcity is authoritative; only the granted amount enters the
        organism's metabolic reserve. This is an explicit local request, not an
        automatic replenishment or evaluator intervention.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot acquire resources")
        habitat = self._resource_habitats.get(resource_id) if resource_id is not None else self._habitat
        if habitat is None:
            raise ValueError("no shared habitat is attached")
        if kind not in {"observation", "cognition", "persistence", "maintenance"} or isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0.0:
            raise ValueError("invalid resource intake")
        # Validate destination capacity before consuming the shared pool. If
        # intake is partial, consume only what the organism can accept.
        available = max(0.0, self._metabolism.snapshot().capacity[kind] - self._metabolism.snapshot().reserve[kind])
        accepted_request = min(float(amount), available)
        if accepted_request <= 0.0:
            return 0.0
        granted = habitat.consume(self._organism_id, accepted_request)
        return self._metabolism.intake(kind, granted)

    def _most_depleted_metabolic_kind(self) -> str:
        """Choose the locally scarcest metabolic compartment for intake."""
        snapshot = self._metabolism.snapshot()
        return min(
            snapshot.capacity,
            key=lambda kind: snapshot.reserve[kind] / max(snapshot.capacity[kind], 1e-12),
        )

    @property
    def assimilator(self) -> InformationAssimilator:
        return self._assimilator

    @property
    def homeostasis(self) -> HomeostaticController:
        return self._homeostasis

    @property
    def resting_requested(self) -> bool:
        return self._resting_requested

    def _birth_surfaces_available(self) -> bool:
        """Preflight every external allocation before reserving lineage state."""
        surfaces = list(self._resource_habitats.values())
        if self._habitat is not None:
            surfaces.append(self._habitat)
        return all(
            surface.snapshot().population < surface.capacity
            and surface.snapshot().available_resources >= 1.0
            for surface in surfaces
        )

    @property
    def source_trust(self) -> SourceTrustModel:
        return self._source_trust

    def request_rest(self) -> None:
        """Enter a bounded rest request; reserves are not replenished."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot request rest")
        self._resting_requested = True

    def resume_activity(self) -> None:
        """Clear a rest request without creating resources or integrity."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot resume activity")
        self._resting_requested = False

    def repair(self, requested: float) -> float:
        """Perform bounded, resource-backed repair outside the tick loop.

        Repair is an explicit organism action: it consumes maintenance reserve,
        never exceeds the controller's per-cycle bound, and is unavailable
        after irreversible death.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot repair")
        repaired = self._homeostasis.repair_with_resources(self._metabolism, requested)
        return repaired

    def apply_environmental_damage(self, amount: float) -> float:
        """Apply a bounded physical perturbation from the supplied habitat.

        This is deliberately not a controller or evaluator command: it only
        changes local integrity.  The subsequent repair decision remains the
        organism's own action and must pay its maintenance cost.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot receive damage")
        if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                or not math.isfinite(float(amount)) or not 0.0 < amount <= 0.25):
            raise ValueError("environmental damage must be within (0, 0.25]")
        before = self._homeostasis.integrity
        self._homeostasis.integrity = max(0.0, before - float(amount))
        return before - self._homeostasis.integrity

    def _sampling_selector(self, manifest: HostManifest) -> tuple[str, ...] | None:
        if not self._discover_senses:
            return None
        plan = self._adaptive_senses.sampling_plan(
            capability.capability_id for capability in manifest.available
        )
        requested = set(plan.requested_ids)
        if self._bootstrap_semantic_senses:
            requested.update(
                capability_id
                for capability_id in DEFAULT_PERCEPT_NAMES
                if manifest.supports(capability_id)
            )
        return tuple(sorted(requested))

    def tick(self) -> RuntimeTickResult:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("organism is irreversibly dead")
        tick_start = time.monotonic()
        action_result: ActionExecutionResult | None = None
        if self._interoception_provider is not None:
            # Environmental damage and external depletion may occur between
            # ticks.  Refresh body channels before the local decision so the
            # organism can learn from the current state rather than a stale
            # end-of-previous-tick sample.
            current_metabolism = self._metabolism.snapshot()
            current_pressure = current_metabolism.pressure.value
            current_pressure_ratio = {
                "normal": 0.0, "elevated": 0.33,
                "severe": 0.66, "unrecoverable": 1.0,
            }.get(current_pressure, 1.0)
            current_ratio = min(
                current_metabolism.reserve[k]
                / max(current_metabolism.capacity[k], 1e-12)
                for k in current_metabolism.capacity
            )
            self._interoception_provider.update_physiological_state(
                metabolic_reserve=max(0.0, min(1.0, current_ratio)),
                integrity=self._homeostasis.integrity,
                metabolic_pressure=current_pressure_ratio,
                repair_pressure=1.0 - self._homeostasis.integrity,
                waste_pressure=min(1.0, len(self._degradation.items) / 64.0),
            )
        if self._reacclimation_remaining > 0:
            self._reacclimation_remaining -= 1
        degradation_excreted = self._degradation.age_tick()
        # Gate learning before any cognitive mutation. The end-of-tick
        # physiology report is descriptive; this preflight is authoritative.
        plasticity_gate = self._homeostasis.regulate(self._metabolism.pressure()).plasticity_enabled

        snapshot = self._lifecycle.tick(
            sampling_selector=self._sampling_selector if self._discover_senses else None
        )
        # Explicitly attached finite habitats are bounded organism surfaces,
        # not host discovery.  Expose only their current aggregate quantity as
        # an opaque signal so a germinal runtime can have a real first sense
        # without receiving a semantic resource name or apparatus profile.
        resource_readings = tuple(
            SensorReading(
                capability_id=f"habitat_surface.{resource_id}",
                source="shared_habitat",
                value=resource.snapshot().available_resources,
                unit=Unit.COUNT,
                monotonic_timestamp_ns=time.monotonic_ns(),
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for resource_id, resource in sorted(self._resource_habitats.items())
        )
        raw_organism_readings = (*snapshot.readings, *resource_readings)
        if self._interoception_provider is not None:
            # Keep computational host measurements in the apparatus snapshot,
            # but do not spend organism attention or plasticity on RSS and
            # scheduler timing.  The physiological channels remain a real
            # sense and are still sampled through the same provider boundary.
            from ..host.providers.interoception import InteroceptionProvider
            raw_organism_readings = tuple(
                reading for reading in raw_organism_readings
                if reading.source != "interoception"
                or InteroceptionProvider.organism_facing(reading.capability_id)
            )
        organism_readings = tuple(
            self._interoception_provider.normalize_for_organism(reading)
            if self._interoception_provider is not None
            else reading
            for reading in raw_organism_readings
        )
        readings_by_capability = {reading.capability_id: reading for reading in organism_readings}
        observations = []
        for capability in snapshot.manifest.available:
            reading = readings_by_capability.get(capability.capability_id)
            observations.append(SignalObservation(
                signal_id=self._signal_identity.signal_id(capability.capability_id),
                available=True,
                selected=capability.capability_id in snapshot.sampled_capability_ids,
                value=None if reading is None else reading.value,
                quality="unavailable" if reading is None else reading.quality.value,
            ))
        for reading in resource_readings:
            observations.append(SignalObservation(
                signal_id=self._signal_identity.signal_id(reading.capability_id),
                available=True,
                selected=True,
                value=reading.value,
                quality=reading.quality.value,
            ))
        # Runtime ticks are the authoritative monotonic clock; test/fixture
        # lifecycles may reuse a snapshot tick while the organism continues.
        relation_percept_names = self._adaptive_senses.percept_names() if self._discover_senses else {}
        name_to_capability = {name: capability for capability, name in relation_percept_names.items()}
        def opaque_sense_id(value: str) -> str:
            # Adaptive relations are expressed in percept names, while the
            # knowledge engine is keyed only by canonical capability-derived
            # opaque IDs. Convert explicitly at this boundary.
            capability = name_to_capability.get(value, value)
            return self._signal_identity.signal_id(capability)
        candidate_pairs = tuple(
            (opaque_sense_id(relation.sense_a), opaque_sense_id(relation.sense_b))
            for relation in self._adaptive_senses.strongest_relations(limit=64)
            if relation.sense_a != relation.sense_b
        )
        resource_signal_ids = tuple(
            self._signal_identity.signal_id(reading.capability_id)
            for reading in resource_readings
        )
        candidate_pairs += tuple(
            (left, right)
            for index, left in enumerate(resource_signal_ids)
            for right in resource_signal_ids[index + 1:]
        )[:64 - len(candidate_pairs)]
        # Only explicit acquisition attempts become endogenous binary targets.
        # Provider identity is used here solely to remove the trivial case in
        # which source and outcome are one shared acquisition group; it never
        # crosses the opaque engine boundary.
        attempted = {}
        for outcome in snapshot.sampling_outcomes:
            if outcome.capability_id not in readings_by_capability and outcome.kind.value in {"missing", "unavailable", "provider_failed"}:
                favorable = False
            elif outcome.kind.value == "succeeded" and outcome.quality is not None and outcome.quality.value == "nominal":
                favorable = True
            elif outcome.kind.value in {"succeeded", "missing", "unavailable", "provider_failed"}:
                favorable = False
            else:
                continue
            attempted[outcome.capability_id] = (outcome.provider_id, favorable)
        outcomes = tuple(
            (self._signal_identity.signal_id(capability_id), favorable)
            for capability_id, (provider_id, favorable) in attempted.items()
            if not any(
                provider_id == other_provider and capability_id != other_id
                for other_id, (other_provider, _) in attempted.items()
            )
        )
        self._signal_knowledge.observe(
            SignalObservationBatch(self._tick_count + 1, tuple(observations)),
            candidate_pairs=candidate_pairs,
            outcomes=outcomes,
        )
        # Signal knowledge issues bounded one-step predictions from local
        # opaque histories.  This is a genuine runtime milestone even when
        # the structural cognitive graph has not yet produced a prediction
        # error of its own; the Observatory may observe the resulting event,
        # but it must not infer it from evaluator state.
        knowledge_view = self._signal_knowledge.view()
        interoceptive_reading_count = sum(
            reading.source == "interoception" for reading in snapshot.readings
        )
        external_reading_count = max(0, len(snapshot.readings) - interoceptive_reading_count)
        # Bounded internal channels are a body surface, not a full host
        # observation.  They still consume resources, but their aggregate
        # processing cost is lower than external discovery work.
        observation_cost = (
            min(0.02, external_reading_count * 0.01)
            + interoceptive_reading_count * 0.002
        )
        self._charge_metabolism("observation", observation_cost)
        sampling_plan = self._adaptive_senses.last_sampling_plan if self._discover_senses else None

        self._adaptive_senses.observe(organism_readings)
        for outcome in snapshot.sampling_outcomes:
            self._self_model.observe(outcome=outcome, tick=self._tick_count)
        for evicted_name in self._adaptive_senses.drain_evicted_percept_names():
            self._drift_baselines.pop(evicted_name, None)

        active_learned_names = self._adaptive_senses.percept_names() if self._discover_senses else {}
        developed_names = self._adaptive_senses.developed_percept_names() if self._discover_senses else {}
        semantic_names = (
            DEFAULT_PERCEPT_NAMES
            if self._bootstrap_semantic_senses and not self._sensory_system.plasticity_enabled
            else {}
        )
        opaque_source_names = (
            {
                reading.capability_id: self._signal_identity.signal_id(reading.capability_id)
                for reading in organism_readings
            }
            if self._sensory_system.plasticity_enabled
            else {}
        )
        habitat_names = {
            capability_id: self._signal_identity.signal_id(capability_id)
            for resource_id in self._resource_habitats
            for capability_id in (f"habitat_surface.{resource_id}",)
        }
        # Interoceptive readings are an explicit runtime surface, not host
        # discovery.  Keep their capability names out of cognition by
        # projecting them to the same opaque identity namespace used by the
        # endogenous signal learner.  This also makes the interoception
        # ablation causal: with the provider absent these channels simply do
        # not enter the local cognitive input.
        interoceptive_names = {
            reading.capability_id: self._signal_identity.signal_id(reading.capability_id)
            for reading in organism_readings
            if reading.source == "interoception"
        }

        selected_names: dict[str, str] = dict(semantic_names)
        selected_names.update(opaque_source_names)
        selected_names.update(active_learned_names)
        selected_names.update(habitat_names)
        selected_names.update(interoceptive_names)
        percept_names = {
            capability_id: developed_names.get(capability_id, selected_name)
            for capability_id, selected_name in selected_names.items()
        }
        capability_by_percept_name = {name: capability_id for capability_id, name in percept_names.items()}
        cognitive_aliases = {
            capability_id: semantic_name
            for capability_id, semantic_name in semantic_names.items()
            if percept_names.get(capability_id) not in (None, semantic_name)
        }

        selected_ids = set(percept_names)
        cognitive_readings = tuple(
            reading for reading in organism_readings if reading.capability_id in selected_ids
        )
        if self._actuation_enabled and self._pending_proprioception:
            now = time.monotonic_ns()
            proprio_names = {
                capability_id: self._signal_identity.signal_id(capability_id)
                for capability_id in self._pending_proprioception
            }
            proprio_readings = tuple(
                SensorReading(
                    capability_id=capability_id,
                    source="actuation",
                    value=value,
                    unit=Unit.RATIO,
                    monotonic_timestamp_ns=now,
                    quality=ReadingQuality.NOMINAL,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
                for capability_id, value in sorted(self._pending_proprioception.items())
            )
            percept_names.update(proprio_names)
            cognitive_readings = (*cognitive_readings, *proprio_readings)
            self._pending_proprioception = {}

        percepts = self._sensory_system.transduce(
            cognitive_readings,
            percept_names=percept_names,
            tick=self._tick_count + 1,
        )
        newly_confirmed_motor_effect_ids = self._complete_pending_motor_observation(
            percepts, tick=self._tick_count + 1
        )
        # Once an actuator's controllability is established, that bodily fact
        # remains available while cognition learns *when* to use it.  Requiring
        # a fresh actuation to supply every association sample would deadlock:
        # an isolated motor readout cannot actuate until it first gains an
        # incoming edge, but the edge itself may require minimum_support > 1.
        established_motor_effect_ids = (
            self._actuator_proposer.active_repertoire
            if self._actuator_proposer is not None
            else ()
        )
        motor_effect_actuator_ids = tuple(sorted(set(
            (*newly_confirmed_motor_effect_ids, *established_motor_effect_ids)
        )))
        cognitive_primitives = (
            self._sensorimotor_learner.cognitive_primitives
            if self._sensorimotor_learner is not None
            else ()
        )
        # transduce() may create identity receptors for sources encountered on
        # this very tick; build the lookup only after that developmental step.
        sensor_by_cognitive_name = {
            sensor.cognitive_name: sensor for sensor in self._sensory_system.sensors
        }
        acquisition_costs: dict[str, float] = {}
        for outcome in snapshot.sampling_outcomes:
            acquisition_costs[outcome.capability_id] = (
                acquisition_costs.get(outcome.capability_id, 0.0)
                + outcome.attributed_elapsed_s
            )
        self._sensory_system.update_acquisition_costs(acquisition_costs)
        self._acclimation.observe(cognitive_readings)
        self._rhythm_model.observe(percepts, time_bucket=current_time_bucket())
        # Source genealogy stays in SensorState, outside Percept/cognition.
        for percept in percepts:
            sensor = sensor_by_cognitive_name.get(percept.name)
            if (
                percept.name not in capability_by_percept_name
                and sensor is not None
                and len(sensor.source_ids) == 1
            ):
                capability_by_percept_name[percept.name] = sensor.source_ids[0]

        drift_observations: dict[str, DriftObservation] = {}
        for percept in percepts:
            if percept.value is None:
                continue
            baseline = self._drift_baselines.get(percept.name)
            if baseline is None:
                baseline = DriftAwareBaseline()
                self._drift_baselines[percept.name] = baseline
            drift_observations[percept.name] = baseline.observe(percept.value)

        assimilation: list[AssimilationDecision] = []
        for observation in drift_observations.values():
            decision = self._assimilator.evaluate(
                novelty=novelty_from_drift_kind(observation.kind),
                surprise=0.0,
                attention=0.0,
                reliability=1.0,
                cost=0.0,
            )
            assimilation.append(decision)
            self._charge_metabolism("persistence", 0.005 if decision.action.value == "incorporate" else 0.001)

        currently_available_ids = {
            capability.capability_id for capability in snapshot.manifest.available
        }
        eligible_ids = selected_ids & currently_available_ids
        self._self_model.reconcile(eligible_ids)
        rank_costs = {
            capability_id: self._self_model.relative_cost(
                capability_id, reference_ids=eligible_ids
            )
            for capability_id in eligible_ids
        }
        allocations = attend_to_host(
            self._acclimation,
            budget=self._attention_budget,
            eligible_capability_ids=eligible_ids,
            rank_costs=rank_costs,
        )

        # Source acquisition and perceptual attention are separate decisions.
        # Legacy mode retains the historical capability allocation exactly.
        # Adaptive mode allocates cognition among the percepts produced by
        # already-acquired sources; it cannot cause a new host read.
        perceptual_allocations: tuple[AttentionAllocation, ...] = ()
        if self._sensory_system.plasticity_enabled:
            allocated_sources = {
                allocation.name for allocation in allocations
            } | {reading.capability_id for reading in resource_readings}
            available_percepts = {percept.name for percept in percepts if percept.value is not None}
            candidates: list[AttentionCandidate] = []
            for sensor in self._sensory_system.sensors:
                if sensor.cognitive_name not in available_percepts:
                    continue
                if not allocated_sources.intersection(sensor.source_ids):
                    continue
                # Young receptors receive an epistemic exploration bonus.
                developmental_uncertainty = 1.0 / (1.0 + max(0, sensor.age_ticks) / 8.0)
                uncertainty = max(1.0 - sensor.confidence, developmental_uncertainty)
                # Before enough evidence exists, all receptors compete on
                # exploration/uncertainty. Once evaluated, demonstrated utility
                # lowers ranking cost and therefore earns cognitive attention.
                utility_factor = (
                    1.0 + 4.0 * sensor.utility
                    if sensor.utility_observations >= 8
                    else 1.0
                )
                candidates.append(AttentionCandidate(
                    name=sensor.cognitive_name,
                    uncertainty=uncertainty,
                    cost=1.0,
                    rank_cost=max(
                        0.10,
                        (1.0 + sensor.transduction_cost * 10.0) / utility_factor,
                    ),
                    observations=sensor.utility_observations,
                ))
            if candidates:
                # Preserve the number of cognitive slots made available by
                # source attention while allowing competing receptors over the
                # same source to occupy those slots.
                perceptual_allocations = AttentionBudget(
                    budget=max(1.0, float(len(allocations)))
                ).allocate(candidates)
        interoceptive_capability_ids = {
            capability.capability_id
            for capability in snapshot.manifest.available
            if capability.source == "interoception"
        }
        interoceptive_allocations = sum(
            allocation.name in interoceptive_capability_ids
            for allocation in allocations
        )
        self._charge_metabolism(
            "cognition",
            (len(allocations) - interoceptive_allocations) * 0.02
            + interoceptive_allocations * 0.005,
        )

        availability_by_capability = {
            state.capability_id: state.availability for state in self._adaptive_senses.states
        }

        cognition_result: CognitiveBridgeResult | None = None
        cognitive_self_observation: dict[str, Any] | None = None
        if self._cognitive_bridge is not None:
            sense_values = {
                percept.name: percept.value for percept in percepts if percept.value is not None
            }
            raw_values = {
                reading.capability_id: float(reading.value)
                for reading in cognitive_readings
                if reading.value is not None
            }
            for capability_id, alias in cognitive_aliases.items():
                raw_value = raw_values.get(capability_id)
                if raw_value is not None:
                    sense_values.setdefault(alias, raw_value)

            attended_sense_ids: set[str] = set()
            sense_modulation: dict[str, float] = {}
            if self._sensory_system.plasticity_enabled:
                sensor_by_name = {
                    sensor.cognitive_name: sensor for sensor in self._sensory_system.sensors
                }
                for allocation in perceptual_allocations:
                    sensor = sensor_by_name.get(allocation.name)
                    if sensor is None:
                        continue
                    attended_sense_ids.add(sensor.cognitive_name)
                    sense_modulation[sensor.cognitive_name] = max(
                        0.0, min(1.0, sensor.health * sensor.confidence)
                    )
            else:
                for allocation in allocations:
                    capability_id = allocation.name
                    node_names = {
                        name
                        for name in (percept_names.get(capability_id), cognitive_aliases.get(capability_id))
                        if name is not None
                    }
                    availability = availability_by_capability.get(capability_id, 1.0)
                    health = self._self_model.health(capability_id, current_tick=self._tick_count)
                    modulation = max(0.0, min(1.0, availability * health))
                    for node_name in node_names:
                        attended_sense_ids.add(node_name)
                        sense_modulation[node_name] = modulation

            cognition_result = self._cognitive_bridge.tick(
                sense_values,
                tick=self._tick_count + 1,
                attended_sense_ids=attended_sense_ids,
                sense_modulation=sense_modulation,
                plasticity_enabled=plasticity_gate,
                active_motor_actuator_ids=(
                    self._actuator_proposer.active_repertoire
                    if self._actuator_proposer is not None
                    else ()
                ),
                motor_effect_actuator_ids=motor_effect_actuator_ids,
                active_primitive_ids=tuple(
                    primitive.primitive_id
                    for primitive in cognitive_primitives
                ),
            )
            if self._auto_promote_predictors:
                self._cognitive_bridge.nominate_shadow_prediction(
                    tick=self._tick_count + 1
                )
            cognitive_activations = getattr(cognition_result, "activations", None)
            if (
                isinstance(cognitive_activations, dict)
                and getattr(cognition_result, "consecutive_failures", 0) == 0
                and self._reacclimation_remaining <= 0
            ):
                known_sensory_nodes = (
                    set(percept_names.values())
                    | set(developed_names.values())
                    | set(cognitive_aliases.values())
                )
                cognitive_self_observation = project_cognitive_self_observation(
                    cognitive_activations,
                    sensory_ids=known_sensory_nodes,
                    namespace_key=self._cognitive_self_namespace_key,
                )

        self._motor_step(
            cognition_result,
            percepts,
            tick=self._tick_count + 1,
        )

        predictive_gain_by_name: dict[str, float] = {}
        if self._cognitive_bridge is not None:
            for candidate in getattr(self._cognitive_bridge, "shadow_predictions", ()):
                # ShadowPrediction(source, target) measures whether the prior
                # source value predicts the target better than persistence.
                # Credit therefore belongs to the sensory source that supplied
                # useful predictive information, not to the predicted target.
                predictive_gain_by_name[candidate.source_id] = max(
                    predictive_gain_by_name.get(candidate.source_id, 0.0),
                    max(0.0, candidate.predictive_gain),
                )
        self._sensory_system.update_downstream_utility(predictive_gain_by_name)
        sensory_mutations = self._sensory_system.plastic_step(tick=self._tick_count + 1)
        if sensory_mutations:
            self._charge_metabolism(
                "cognition",
                sum(min(0.01, mutation.cost * 0.01) for mutation in sensory_mutations),
            )

        if not self._reacclimation_remaining:
            attended_capability_ids = {allocation.name for allocation in allocations}
            capability_by_percept_name = {name: capability_id for capability_id, name in percept_names.items()}
            prediction_loss_by_node: dict[str, float] = {}
            if cognition_result is not None:
                for error in cognition_result.prediction_errors:
                    prediction_loss_by_node[error.target_id] = error.loss

            for percept_name, observation in drift_observations.items():
                capability_id = capability_by_percept_name.get(percept_name)
                novelty = novelty_from_drift_kind(observation.kind)
                surprise = surprise_from_loss(prediction_loss_by_node.get(percept_name))
                attention = 1.0 if capability_id in attended_capability_ids else 0.0
                availability = availability_by_capability.get(capability_id, 1.0) if capability_id else 1.0
                health = (
                    self._self_model.health(capability_id, current_tick=self._tick_count)
                    if capability_id is not None
                    else 0.5
                )
                reliability = max(0.0, min(1.0, availability * health))
                signal = ConsolidationSignal(
                    novelty=novelty, surprise=surprise, attention=attention, reliability=reliability, coherence=0.0
                )
                self._memory_consolidator.observe(
                    percept_name, MemoryKind.SALIENT_EVENT, signal, tick=self._tick_count + 1
                )

        investigated_capability: str | None = None
        evidence_gathered = 0
        dissent: DissentRecord | None = None
        evidence_counts: dict[str, int] = {}
        dissent_by_capability: dict[str, DissentRecord] = {}

        if self._investigate_ticks > 0:
            candidates: list[str] = []
            for percept_name, obs in drift_observations.items():
                if obs.kind.value == "regime_shift":
                    cap_id = capability_by_percept_name.get(percept_name)
                    if cap_id and cap_id in selected_ids and snapshot.manifest.supports(cap_id):
                        candidates.append(cap_id)
            for allocation in allocations:
                if allocation.name not in candidates:
                    candidates.append(allocation.name)

            for candidate in candidates:
                if candidate not in selected_ids or not snapshot.manifest.supports(candidate):
                    continue
                if (
                    self._self_model.is_established(candidate)
                    and self._self_model.health(candidate, current_tick=self._tick_count)
                    < LOW_HEALTH_INVESTIGATION_THRESHOLD
                ):
                    continue
                session = SecondLookSession(
                    manifest=snapshot.manifest,
                    capability_id=candidate,
                    max_ticks=self._investigate_ticks,
                    sampler=HostSampler(self._reading_providers),
                )
                result = session.run_to_completion()
                investigated_capability = candidate
                evidence_gathered = len(result.readings)
                evidence_counts[candidate] = evidence_gathered
                for outcome in result.outcomes:
                    self._self_model.observe(outcome=outcome, tick=self._tick_count)
                revision = self._evidence_ledger.revise(
                    acclimation=self._acclimation,
                    capability_id=candidate,
                    evidence=result.readings,
                )
                dissent = revision.dissent
                if dissent is not None:
                    dissent_by_capability[candidate] = dissent
                break

        # The action decision consumes the current tick's bounded perception
        # and cognition.  ``action_result`` remains ``None`` here: canonical
        # cognition does not run a typed local action-selection step, and
        # this runtime tick performs no such step on its own.  The field is
        # kept on the tick result only as a passive, semantic-free reporting
        # surface: existing lab adapters and the Observatory read it when
        # present without requiring this runtime to ever populate it.

        # BodySchema receives two bounded organism-owned evidence surfaces:
        # sensory SelfModel classes and opaque dynamic cognitive channels. It
        # never sees host manifest truth, CognitiveGraph nodes/edges or
        # Observatory topology.
        if self._sensory_system.plasticity_enabled:
            self._body_schema.observe_sensory_phenotype(
                self._sensory_phenotype_view(),
                tick=self._tick_count,
            )
        else:
            self._body_schema.observe_self_model(
                self._self_model.export(current_tick=self._tick_count),
                tick=self._tick_count,
            )
        # Cognitive/information-assimilation "success" (incorporation utility,
        # prediction accuracy) is not a physical resource and must never
        # manufacture metabolic reserve on its own: only externally acquired
        # resource (habitat consumption via ``request_resource_intake``,
        # explicit ``intake`` from an actual transfer, etc.) may grow
        # reserve. Assimilation cost is still charged elsewhere
        # (``_charge_metabolism`` above) regardless of ``_explicit_metabolism``.

        retained_units = float(len(self._drift_baselines)) * 0.001
        if self._cognitive_bridge is not None and self._cognitive_bridge.graph is not None:
            retained_units += float(len(self._cognitive_bridge.graph.nodes)) * 0.0005
        retained_units += self._pending_embodied_work
        self._pending_embodied_work = 0.0
        metabolism_snapshot = self._metabolism.advance(retained_units=retained_units)
        homeostatic_snapshot = self._homeostasis.regulate(metabolism_snapshot.pressure)
        if metabolism_snapshot.pressure.value in ("severe", "unrecoverable"):
            self._resting_requested = True
        elif (metabolism_snapshot.pressure.value == "normal" and self._resting_requested
              and (action_result is None or action_result.action_id != "rest")):
            self._resting_requested = False
        resting_for_tick = self._resting_requested
        physiology_snapshot = self._physiology.advance(
            metabolism_snapshot, tick=self._tick_count,
            resting=resting_for_tick or homeostatic_snapshot.action.value in ("pause_plasticity", "safe_mode"),
        )
        topology = getattr(self._cognitive_bridge, "topology_health", None)
        topology_health = (
            getattr(topology, "value", str(topology))
            if topology is not None else ("developing" if self._cognitive_bridge is not None else "germinal")
        )
        development_snapshot = self._developmental_tracker.observe(
            state=physiology_snapshot.state.value,
            integrity=self._homeostasis.integrity,
            topology_health=topology_health,
            sensory_count=(
                len(self._sensory_system.sensors)
                if self._sensory_system.plasticity_enabled
                else len(self._adaptive_senses.developed_percept_names())
            ),
            # Local action-selection experience is not part of canonical
            # cognition; this runtime supplies no such count any more.
            action_attempts=0,
            maintenance_ratio=min(
                1.0,
                metabolism_snapshot.spent["maintenance"]
                / max(0.000001, metabolism_snapshot.capacity["maintenance"]),
            ),
            retained_items=len(self._degradation.items),
            degradation_excreted=degradation_excreted,
            repaired=homeostatic_snapshot.action.value == "repair",
            plasticity_enabled=homeostatic_snapshot.plasticity_enabled,
        )
        if physiology_snapshot.state.value == "dead":
            if self._habitat is not None and not self._habitat_released:
                self._habitat.release(self._organism_id)
                self._habitat_released = True
            for resource in self._resource_habitats.values():
                resource.release(self._organism_id)
            if self._birth_authority is not None and not self._birth_authority_released:
                self._birth_authority.death(self._organism_id)
                self._birth_authority_released = True
            if self._social_habitat is not None and not self._social_habitat_released:
                self._social_habitat.release(self._organism_id)
                self._social_habitat_released = True
        if cognitive_self_observation is not None:
            self._body_schema.observe_cognition(
                cognitive_self_observation,
                tick=self._tick_count,
            )

        narrative = narrate_host(
            self._acclimation,
            allocations=allocations,
            evidence_counts=evidence_counts,
            dissent_by_capability=dissent_by_capability,
        )
        if self._interoception_provider is not None:
            tick_latency = time.monotonic() - tick_start
            surprise = 0.0
            if cognition_result is not None and getattr(cognition_result, "prediction_errors", None):
                errors = cognition_result.prediction_errors
                surprise = min(1.0, sum(abs(e.error) for e in errors) / len(errors)) if errors else 0.0
            metabolic_ratio = min(
                self._metabolism.snapshot().reserve[k] / max(1e-9, self._metabolism.snapshot().capacity[k])
                for k in ("observation", "cognition", "persistence", "maintenance")
            )
            pressure_value = metabolism_snapshot.pressure.value
            pressure_ratio = {
                "normal": 0.0,
                "elevated": 0.33,
                "severe": 0.66,
                "unrecoverable": 1.0,
            }.get(pressure_value, 1.0)
            self._interoception_provider.update_metrics(
                tick_latency=tick_latency,
                epistemic_surprise=surprise,
                metabolic_reserve=max(0.0, min(1.0, metabolic_ratio)),
                integrity=self._homeostasis.integrity,
                metabolic_pressure=pressure_ratio,
                repair_pressure=1.0 - self._homeostasis.integrity,
                waste_pressure=min(1.0, len(self._degradation.items) / 64.0),
            )
        runtime_events: list[str] = []
        if homeostatic_snapshot.action.value != "maintain":
            # Evaluator-facing evidence only; this kernel intervention does
            # not enter cognition or alter the organism's decision.
            runtime_events.append("homeostatic_rescue")
        current_state = physiology_snapshot.state.value
        current_phase = development_snapshot.phase.value
        if current_phase != self._last_runtime_development_phase:
            runtime_events.append("development")
        if current_state in {"stressed", "agonizing", "dormant"}:
            runtime_events.append("stress")
        if self._last_runtime_vital_state in {"stressed", "agonizing", "dormant"} and current_state == "active":
            runtime_events.append("recovery")
        if current_state == "active":
            runtime_events.append("regulation")
        if cognition_result is not None:
            runtime_events.append("learning")
        if not self._first_sense_emitted and percepts:
            runtime_events.append("first_sense")
            self._first_sense_emitted = True
        if (not self._first_concept_emitted and cognition_result is not None
                and getattr(cognition_result, "readouts", ())):
            runtime_events.append("first_concept")
            self._first_concept_emitted = True
        knowledge_has_prediction = any(
            claim.get("kind") == "lead_prediction"
            for profile in knowledge_view
            for claim in profile.get("claims", ())
        )
        if (not self._first_prediction_emitted and (
                (cognition_result is not None and getattr(cognition_result, "prediction_errors", ()))
                or knowledge_has_prediction)):
            runtime_events.append("first_prediction")
            self._first_prediction_emitted = True
        if any(getattr(item, "kind", None) and
               getattr(item.kind, "value", item.kind) == "regime_shift"
               for item in drift_observations.values()):
            runtime_events.append("regime_shift")
        if current_phase == "terminal" and self._last_runtime_development_phase != "terminal":
            runtime_events.append("terminal")
        if action_result is not None and action_result.executed:
            action_id = action_result.action_id
            if action_id == "rest":
                runtime_events.append("rest")
            elif action_id == "repair":
                runtime_events.append("repair")
            elif action_id == "social_exchange":
                runtime_events.append("interaction")
            elif action_id == "compete":
                runtime_events.append("interaction")
            elif action_id == "reproduce":
                runtime_events.append("reproduction")
            elif action_id == "observe":
                runtime_events.append("observation")
            elif action_id == "intake" or action_id.startswith("intake:"):
                if isinstance(action_result.result, (int, float)) and action_result.result > 0.0:
                    runtime_events.append("resource_acquisition")
        if current_state == "dead":
            runtime_events.extend(("death", "resource_release"))
        self._last_runtime_vital_state = current_state
        self._last_runtime_development_phase = current_phase
        self._tick_count += 1
        if self._living_body_state.alive:
            self._living_body_state.age_ticks = self._tick_count
        journal_entry = {
            "tick": self._tick_count,
            "vital_state": physiology_snapshot.state.value if physiology_snapshot else "active",
            "pressure": metabolism_snapshot.pressure.value if metabolism_snapshot else "normal",
            "reserve": {k: round(v, 4) for k, v in metabolism_snapshot.reserve.items()} if metabolism_snapshot else {},
            "resting": bool(resting_for_tick or (physiology_snapshot is not None and physiology_snapshot.state.value == "dormant")),
            "attended": [a.name for a in allocations],
            "investigated": investigated_capability,
            "regime_shifts": [name for name, obs in drift_observations.items() if getattr(obs, "kind", None) and obs.kind.value == "regime_shift"],
            "dissent": dissent.capability_id if dissent is not None else None,
            "assimilated_count": len(assimilation),
            "narrative": [entry.summary for entry in narrative if entry.attended][:3],
        }
        self._narrative_journal.append(journal_entry)
        if len(self._narrative_journal) > 50:
            self._narrative_journal = self._narrative_journal[-50:]
        self._decay_epigenetic_priors()
        return RuntimeTickResult(
            tick=self._tick_count,
            snapshot=snapshot,
            percepts=percepts,
            drift_observations=drift_observations,
            allocations=allocations,
            investigated_capability=investigated_capability,
            evidence_gathered=evidence_gathered,
            dissent=dissent,
            narrative=narrative,
            sampling_plan=sampling_plan,
            perceptual_allocations=perceptual_allocations,
            cognition=cognition_result,
            signal_knowledge=self._signal_knowledge.view(),
            knowledge_events=self._signal_knowledge.drain_events(),
            signal_references={
                **{name: self._signal_identity.signal_id(capability_id) for capability_id, name in percept_names.items()},
                **{
                    percept.name: self._signal_identity.signal_id(sensor.source_ids[0])
                    for percept in percepts
                    if (sensor := sensor_by_cognitive_name.get(percept.name)) is not None
                    and len(sensor.source_ids) == 1
                },
            },
            metabolism=metabolism_snapshot,
            assimilation=tuple(assimilation),
            homeostasis=homeostatic_snapshot,
            physiology=physiology_snapshot,
            degradation_excreted=degradation_excreted,
            retained_items=len(self._degradation.items),
            action_result=action_result,
            development=development_snapshot,
            sensory_phenotype=self._sensory_phenotype_view(),
            runtime_events=tuple(dict.fromkeys(runtime_events)),
            motor_intent=self._last_motor_intent,
            actuation=self._last_actuation,
            motor_intents=self._last_motor_intents,
            actuations=self._last_actuations,
        )

    def run(self, ticks: int) -> tuple[RuntimeTickResult, ...]:
        if ticks < 1:
            raise ValueError("ticks must be at least 1")
        return tuple(self.tick() for _ in range(ticks))

    def checkpoint(self) -> dict[str, Any]:
        payload = export_checkpoint(
            acclimation=self._acclimation,
            rhythm_model=self._rhythm_model,
            drift_baselines=self._drift_baselines,
            saved_at_tick=self._tick_count,
        )
        payload["organism_id"] = self._organism_id
        payload["effective_config"] = self.effective_configuration()
        payload["sensory_development"] = self._adaptive_senses.export()
        payload["sensory_system"] = self._sensory_system.checkpoint()
        payload["self_model"] = self._self_model.export(current_tick=self._tick_count)
        payload["body_schema"] = self._body_schema.export(current_tick=self._tick_count)
        payload["evidence_ledger"] = self._evidence_ledger.export_checkpoint()
        payload["genome"] = export_genome_checkpoint(self._genome)
        payload["heritable_genome"] = (
            {"genome_id": self._heritable_genome.genome_id,
             "loci": [[key, value] for key, value in self._heritable_genome.loci],
             "identity": self._heritable_genome.identity}
            if self._heritable_genome is not None else None
        )
        payload["mutation_seed"] = self._mutation_seed
        payload["epigenetic_priors"] = [
            {"key": prior.key, "value": prior.value} for prior in self._epigenetic_priors
        ]
        payload["epigenetic_decay"] = self._epigenetic_decay
        payload["cognitive_bridge"] = (
            self._cognitive_bridge.export_checkpoint()
            if self._cognitive_bridge is not None
            else None
        )
        if self._actuation_enabled:
            if self._actuator_constitution is None or self._actuator_proposer is None:
                raise CheckpointError("actuation enabled without motor constitution/proposer")
            constitution_payload = {
                "slots": [
                    {
                        "slot_id": slot.slot_id,
                        "actuator_id": slot.actuator_id,
                        "basal_cost": slot.basal_cost,
                        "initial_health": slot.initial_health,
                        "execution_threshold": slot.execution_threshold,
                    }
                    for slot in self._actuator_constitution.slots
                ]
            }
            pending_motor = [
                {
                    "actuator_id": actuator_id,
                    "activation": activation,
                    "advance_probe": advance_probe,
                }
                for actuator_id, activation, _baseline, advance_probe
                in self._pending_motor_observation
            ]
            payload["actuation"] = {
                "enabled": True,
                "constitution": constitution_payload,
                "proposer": export_actuation_state(self._actuator_proposer),
                "states": {
                    actuator_id: state.to_payload()
                    for actuator_id, state in sorted(self._actuator_states.items())
                },
                "selection_threshold": (
                    self._motor_intent_selector.selection_threshold
                    if self._motor_intent_selector is not None
                    else 0.1
                ),
                "exploration_mode": self._motor_exploration_mode,
                "pending_motor_observation": pending_motor,
                "pending_proprioception": dict(sorted(self._pending_proprioception.items())),
                "sensorimotor": (
                    self._sensorimotor_learner.checkpoint()
                    if self._sensorimotor_learner is not None
                    else None
                ),
                "last_executed_primitive_id": self._last_executed_primitive_id,
                "pending_primitive_choice_context": (
                    {
                        "primitive_id": self._pending_primitive_choice_context[0],
                        "concept_ids": list(self._pending_primitive_choice_context[1]),
                        "complete_tick": self._pending_primitive_choice_context[2],
                        "samples_before": self._pending_primitive_choice_context[3],
                    }
                    if self._pending_primitive_choice_context is not None
                    else None
                ),
            }
        else:
            payload["actuation"] = {"enabled": False}
        payload["memory"] = self._memory_consolidator.export_checkpoint()
        knowledge_payload = self._signal_knowledge.checkpoint()
        knowledge_size = len(json.dumps(knowledge_payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        if knowledge_size > MAX_KNOWLEDGE_CHECKPOINT_BYTES:
            raise CheckpointError("signal knowledge checkpoint exceeds 256 KiB")
        payload["signal_knowledge"] = knowledge_payload
        payload["signal_identity_key"] = self._signal_identity.key.hex()
        payload["metabolism"] = self._metabolism.checkpoint()
        payload["assimilation"] = self._assimilator.checkpoint()
        payload["living_body"] = self._living_body_state.checkpoint()
        payload["homeostasis"] = self._homeostasis.checkpoint()
        payload["physiology"] = self._physiology.checkpoint()
        payload["social_ledger"] = self._social_ledger.checkpoint()
        payload["social_resource_ledger"] = self._social_resource_ledger.checkpoint()
        payload["source_trust"] = self._source_trust.export_checkpoint()
        payload["generation"] = self._generation
        payload["reproduction_cost"] = self._reproduction_cost
        payload["social_exchange_quantum"] = self._social_exchange_quantum
        payload["social_exchange_cost"] = self._social_exchange_cost
        payload["resting_requested"] = self._resting_requested
        payload["pending_embodied_work"] = self._pending_embodied_work
        payload["degradation"] = self._degradation.checkpoint()
        payload["reproductive_pressure"] = (
            {"threshold_ticks": self._reproductive_pressure.threshold_ticks,
             "reserve": self._reproductive_pressure.reserve,
             "blocked_ticks": self._reproductive_pressure.blocked_ticks}
            if self._reproductive_pressure is not None else None
        )
        payload["narrative_journal"] = list(self._narrative_journal[-50:])
        payload["development"] = self._developmental_tracker.checkpoint()
        payload["last_runtime_vital_state"] = self._last_runtime_vital_state
        payload["last_runtime_development_phase"] = self._last_runtime_development_phase
        payload["first_life_history_events"] = {
            "sense": self._first_sense_emitted,
            "concept": self._first_concept_emitted,
            "prediction": self._first_prediction_emitted,
        }
        return payload

    def save(self, path: str | Path) -> None:
        payload = self.checkpoint()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self._kernel_limits.max_plastic_checkpoint_bytes:
            raise CheckpointError(
                "checkpoint exceeds kernel_limits.max_plastic_checkpoint_bytes "
                f"({len(encoded)} > {self._kernel_limits.max_plastic_checkpoint_bytes})"
            )
        save_checkpoint_atomic(payload, path)

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any], **kwargs: Any) -> "OrganismRuntime":
        normalized = normalize_checkpoint(payload)
        effective = normalized.get("effective_config", {})
        min_samples = int(kwargs.get("min_samples", effective.get("min_samples", 5)))
        acclimation, rhythm_model, drift_baselines = import_checkpoint(
            normalized,
            acclimation=HostAcclimation(min_samples=min_samples),
            rhythm_model=RhythmModel(min_samples=min_samples),
        )
        adaptive_senses = AdaptiveSenseModel.restore(normalized.get("sensory_development"))
        raw_sensory_system = normalized.get("sensory_system")
        explicit_sensory_override = (
            kwargs["sensory_plasticity"] if "sensory_plasticity" in kwargs else None
        )
        if explicit_sensory_override is not None and not isinstance(explicit_sensory_override, bool):
            raise CheckpointError("sensory_plasticity override must be boolean")
        effective_sensory_plasticity = effective.get("sensory_plasticity", False)
        if not isinstance(effective_sensory_plasticity, bool):
            raise CheckpointError("invalid sensory_plasticity in effective_config")
        try:
            sensory_system = SensorySystem.restore(
                raw_sensory_system,
                plasticity_enabled=(
                    explicit_sensory_override
                    if explicit_sensory_override is not None
                    else (None if raw_sensory_system is not None else effective_sensory_plasticity)
                ),
            )
        except ValueError as exc:
            raise CheckpointError(f"invalid sensory system checkpoint: {exc}") from exc
        if (
            raw_sensory_system is not None
            and explicit_sensory_override is None
            and sensory_system.plasticity_enabled != effective_sensory_plasticity
        ):
            raise CheckpointError(
                "sensory constitution contradicts effective_config.sensory_plasticity"
            )
        allowed_sense_ids = set(adaptive_senses.developed_percept_names())
        if kwargs.get("bootstrap_semantic_senses", True):
            allowed_sense_ids.update(DEFAULT_PERCEPT_NAMES)
        # Self-model entries are established local state, including internal
        # senses that are not host-discovered percepts.  They must remain
        # restorable; silently dropping them changes the organism after a
        # checkpoint and breaks deterministic replay.
        raw_self_model = normalized.get("self_model")
        if raw_self_model is not None:
            if not isinstance(raw_self_model, dict):
                raise CheckpointError("invalid self-model checkpoint")
            allowed_sense_ids.update(raw_self_model)
        self_model = SelfModel.restore(
            raw_self_model,
            allowed_sense_ids=allowed_sense_ids,
            current_tick=normalized.get("saved_at_tick") or 0,
        )
        body_schema = BodySchemaEngine.restore(
            normalized.get("body_schema"),
            current_tick=normalized.get("saved_at_tick") or 0,
        )
        conflict_z = float(kwargs.get("conflict_z", effective.get("conflict_z", 2.0)))
        evidence_ledger = EvidenceRevisionLedger.restore_checkpoint(
            normalized.get("evidence_ledger"),
            conflict_z=conflict_z,
            allowed_capability_ids=acclimation.known_capabilities,
        )
        from .. import __version__ as _symbiont_version

        kernel_limits = kwargs.get("kernel_limits") or KernelLimits()
        genome = restore_genome_checkpoint(
            normalized.get("genome"),
            kernel_limits=kernel_limits,
            running_version=_parse_running_version(_symbiont_version),
        )
        heritable_genome = None
        raw_heritable = normalized.get("heritable_genome")
        if raw_heritable is not None:
            if not isinstance(raw_heritable, dict) or not isinstance(raw_heritable.get("genome_id"), str):
                raise CheckpointError("invalid heritable genome checkpoint")
            try:
                heritable_genome = HeritableGenome(
                    raw_heritable["genome_id"],
                    tuple((str(item[0]), float(item[1])) for item in raw_heritable.get("loci", ())),
                )
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise CheckpointError("invalid heritable genome checkpoint") from exc
            if raw_heritable.get("identity") not in (None, heritable_genome.identity):
                raise CheckpointError("heritable genome identity mismatch")
        raw_priors = normalized.get("epigenetic_priors")
        if raw_priors is None:
            raw_priors = []
        if not isinstance(raw_priors, list) or len(raw_priors) > 16:
            raise CheckpointError("invalid epigenetic priors checkpoint")
        try:
            epigenetic_priors = tuple(
                EpigeneticPrior(str(item["key"]), float(item["value"])) for item in raw_priors
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CheckpointError("invalid epigenetic priors checkpoint") from exc
        cognitive_bridge = None
        if genome is not None:
            cognitive_bridge = CognitiveBridge.restore(
                normalized.get("cognitive_bridge"),
                genome=genome,
                kernel_limits=kernel_limits,
            )
        memory_consolidator = MemoryConsolidator.restore_checkpoint(
            normalized.get("memory"), kernel_limits=kernel_limits
        )
        actuation_enabled = False
        actuator_constitution = None
        actuator_proposer = None
        actuator_states = None
        motor_intent_selector = None
        sensorimotor_learner = None
        motor_exploration_mode = "structured_probe"
        pending_motor_observation = ()
        pending_proprioception: dict[str, float] = {}
        raw_actuation = normalized.get("actuation")
        if raw_actuation is not None:
            if not isinstance(raw_actuation, dict):
                raise CheckpointError("invalid actuation checkpoint")
            enabled = raw_actuation.get("enabled", False)
            if not isinstance(enabled, bool):
                raise CheckpointError("actuation.enabled must be boolean")
            actuation_enabled = enabled
            raw_mode = raw_actuation.get("exploration_mode", "structured_probe")
            if raw_mode not in {"structured_probe", "spontaneous", "babbling"}:
                raise CheckpointError("invalid motor exploration mode")
            motor_exploration_mode = str(raw_mode)
            if enabled:
                if genome is None:
                    raise CheckpointError("actuation checkpoint requires genome")
                actuator_constitution = load_actuator_constitution(genome)
                expected_constitution = {
                    "slots": [
                        {
                            "slot_id": slot.slot_id,
                            "actuator_id": slot.actuator_id,
                            "basal_cost": slot.basal_cost,
                            "initial_health": slot.initial_health,
                            "execution_threshold": slot.execution_threshold,
                        }
                        for slot in actuator_constitution.slots
                    ]
                }
                if raw_actuation.get("constitution") != expected_constitution:
                    raise CheckpointError("actuation constitution does not match restored genome")
                try:
                    actuator_proposer = restore_actuation_state(
                        raw_actuation["proposer"],
                        actuator_constitution,
                        organism_id=str(normalized.get("organism_id") or ""),
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CheckpointError(f"invalid actuator proposer checkpoint: {exc}") from exc
                raw_states = raw_actuation.get("states")
                if not isinstance(raw_states, dict) or set(raw_states) != set(actuator_constitution.actuator_ids):
                    raise CheckpointError("actuator states must exactly match constitution")
                try:
                    actuator_states = {
                        actuator_id: ActuatorState.from_payload(raw_states[actuator_id])
                        for actuator_id in actuator_constitution.actuator_ids
                    }
                except (KeyError, TypeError, ValueError) as exc:
                    raise CheckpointError(f"invalid actuator state checkpoint: {exc}") from exc
                for actuator_id, state in actuator_states.items():
                    if state.actuator_id != actuator_id:
                        raise CheckpointError("actuator state key/id mismatch")
                try:
                    motor_intent_selector = MotorIntentSelector(
                        selection_threshold=raw_actuation.get("selection_threshold", 0.1)
                    )
                except ValueError as exc:
                    raise CheckpointError(f"invalid motor selector checkpoint: {exc}") from exc
                raw_sensorimotor = raw_actuation.get("sensorimotor")
                if motor_exploration_mode == "babbling":
                    try:
                        sensorimotor_learner = (
                            SensorimotorLearner.restore(
                                raw_sensorimotor,
                                actuator_ids=actuator_constitution.actuator_ids,
                                organism_id=str(normalized.get("organism_id") or ""),
                            )
                            if isinstance(raw_sensorimotor, dict)
                            else SensorimotorLearner(
                                actuator_constitution.actuator_ids,
                                organism_id=str(normalized.get("organism_id") or ""),
                                max_concurrent=None,
                            )
                        )
                    except (TypeError, ValueError, KeyError) as exc:
                        raise CheckpointError(
                            f"invalid sensorimotor checkpoint: {exc}"
                        ) from exc
                raw_pending = raw_actuation.get("pending_motor_observation")
                if raw_pending is not None:
                    if isinstance(raw_pending, dict):
                        raw_pending_items = [raw_pending]
                    elif isinstance(raw_pending, list):
                        raw_pending_items = raw_pending
                    else:
                        raise CheckpointError("invalid pending motor observation")
                    if len(raw_pending_items) > len(actuator_constitution.actuator_ids):
                        raise CheckpointError("too many pending motor observations")
                    restored_pending = []
                    for item in raw_pending_items:
                        if not isinstance(item, dict):
                            raise CheckpointError("invalid pending motor observation item")
                        actuator_id = item.get("actuator_id")
                        activation = item.get("activation")
                        advance_probe = item.get("advance_probe")
                        if actuator_id not in set(actuator_constitution.actuator_ids):
                            raise CheckpointError("pending motor observation references unknown actuator")
                        if (
                            isinstance(activation, bool)
                            or not isinstance(activation, (int, float))
                            or not math.isfinite(float(activation))
                            or not 0.0 <= float(activation) <= 1.0
                        ):
                            raise CheckpointError("invalid pending motor activation")
                        if not isinstance(advance_probe, bool):
                            raise CheckpointError("invalid pending motor observation payload")
                        if "baseline" in item:
                            raise CheckpointError("raw motor percept baselines must not be persisted")
                        restored_pending.append(
                            (str(actuator_id), float(activation), None, advance_probe)
                        )
                    pending_motor_observation = tuple(restored_pending)
                raw_proprio = raw_actuation.get("pending_proprioception", {})
                max_proprioception = 3 * len(actuator_constitution.actuator_ids)
                if (
                    not isinstance(raw_proprio, dict)
                    or len(raw_proprio) > max_proprioception
                ):
                    raise CheckpointError("invalid pending proprioception")
                for key, value in raw_proprio.items():
                    if (
                        not isinstance(key, str)
                        or not key
                        or isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                    ):
                        raise CheckpointError("invalid pending proprioception")
                    pending_proprioception[key] = float(value)
        resolved_physiology_config = kwargs.get("physiology_config")
        if resolved_physiology_config is None:
            if "physiology" in effective:
                raw_phys = effective["physiology"]
                if not isinstance(raw_phys, dict):
                    raise CheckpointError("invalid physiology config in checkpoint: must be a dict")
                try:
                    resolved_physiology_config = PhysiologyConfig(**raw_phys)
                except Exception as exc:
                    raise CheckpointError(f"invalid physiology config in checkpoint: {exc}") from exc
            else:
                raw_deg = normalized.get("degradation")
                if isinstance(raw_deg, dict) and "aging_ticks" in raw_deg and "waste_ticks" in raw_deg:
                    from dataclasses import replace
                    try:
                        resolved_physiology_config = replace(
                            DEFAULT_PHYSIOLOGY_CONFIG,
                            aging_ticks=int(raw_deg["aging_ticks"]),
                            waste_ticks=int(raw_deg["waste_ticks"]),
                        )
                    except Exception as exc:
                        raise CheckpointError(f"failed to migrate degradation ticks into physiology config: {exc}") from exc
                else:
                    resolved_physiology_config = DEFAULT_PHYSIOLOGY_CONFIG

        signal_knowledge = SignalKnowledgeEngine.from_checkpoint(validate_checkpoint(normalized.get("signal_knowledge"))) if normalized.get("signal_knowledge") else SignalKnowledgeEngine()
        metabolism = (
            MetabolicLedger.from_checkpoint(normalized["metabolism"], physiology_config=resolved_physiology_config)
            if normalized.get("metabolism")
            else MetabolicLedger(tick=normalized.get("saved_at_tick") or 0, physiology_config=resolved_physiology_config)
        )
        assimilator = InformationAssimilator.from_checkpoint(normalized["assimilation"]) if normalized.get("assimilation") else InformationAssimilator()
        raw_living_body = normalized.get("living_body")
        if raw_living_body is not None:
            try:
                living_body_state = LivingBodyState.from_checkpoint(raw_living_body)
            except (KeyError, TypeError, ValueError) as exc:
                raise CheckpointError(f"invalid living body checkpoint: {exc}") from exc
        else:
            raw_homeostasis = normalized.get("homeostasis") or {}
            raw_physiology = normalized.get("physiology") or {}
            try:
                living_body_state = LivingBodyState(
                    structural_integrity=float(raw_homeostasis.get("integrity", 1.0)),
                    age_ticks=int(normalized.get("saved_at_tick") or 0),
                    vital_state=VitalState(str(raw_physiology.get("state", "active"))),
                    transitions=int(raw_physiology.get("transitions", 0)),
                    death_tick=raw_physiology.get("death_tick"),
                )
            except (TypeError, ValueError) as exc:
                raise CheckpointError(f"cannot migrate living body state: {exc}") from exc

        homeostasis = (
            HomeostaticController.from_checkpoint(
                normalized["homeostasis"],
                config=resolved_physiology_config,
                body_state=living_body_state,
            )
            if normalized.get("homeostasis")
            else HomeostaticController(
                config=resolved_physiology_config,
                body_state=living_body_state,
            )
        )
        physiology = (
            PhysiologyController.from_checkpoint(
                normalized["physiology"],
                body_state=living_body_state,
            )
            if normalized.get("physiology")
            else PhysiologyController(body_state=living_body_state)
        )
        social_ledger = RelationLedger.from_checkpoint(normalized["social_ledger"]) if normalized.get("social_ledger") else RelationLedger()
        social_resource_ledger = ResourceEvidenceLedger.from_checkpoint(
            normalized["social_resource_ledger"]
        ) if normalized.get("social_resource_ledger") else ResourceEvidenceLedger()
        degradation_queue = DegradationQueue.from_checkpoint(
            normalized["degradation"]
        ) if normalized.get("degradation") else DegradationQueue()
        source_trust = SourceTrustModel.from_checkpoint(
            normalized["source_trust"]
        ) if normalized.get("source_trust") else SourceTrustModel()
        developmental_tracker = DevelopmentalTracker.from_checkpoint(
            normalized["development"]
        ) if normalized.get("development") else DevelopmentalTracker()
        reproductive_pressure = None
        raw_pressure = normalized.get("reproductive_pressure")
        if isinstance(raw_pressure, dict):
            reproductive_pressure = ReproductivePressure(
                threshold_ticks=int(raw_pressure["threshold_ticks"]),
                reserve=float(raw_pressure["reserve"]),
            )
            reproductive_pressure.blocked_ticks = int(raw_pressure.get("blocked_ticks", 0))
        if physiology.state is VitalState.DEAD:
            raise CheckpointError("dead organism checkpoints cannot be restored")
        raw_identity_key = normalized.get("signal_identity_key")
        signal_identity = SignalIdentity(bytes.fromhex(raw_identity_key)) if isinstance(raw_identity_key, str) else None
        constructor_kwargs = dict(kwargs)
        constructor_kwargs.pop("birth_authority", None)
        constructor_kwargs.pop("generation", None)
        constructor_kwargs.pop("reproduction_cost", None)
        constructor_kwargs.pop("social_exchange_quantum", None)
        constructor_kwargs.pop("social_exchange_cost", None)
        constructor_kwargs.pop("social_resource_ledger", None)
        constructor_kwargs.pop("resting_requested", None)
        constructor_kwargs.pop("degradation_queue", None)
        constructor_kwargs.pop("sensory_system", None)
        constructor_kwargs.pop("sensory_plasticity", None)
        constructor_kwargs.pop("actuation_enabled", None)
        constructor_kwargs.pop("actuator_constitution", None)
        constructor_kwargs.pop("actuator_proposer", None)
        constructor_kwargs.pop("actuator_states", None)
        constructor_kwargs.pop("motor_intent_selector", None)
        constructor_kwargs.pop("actuator_system", None)
        constructor_kwargs.pop("sensorimotor_learner", None)
        effective = normalized.get("effective_config", {})
        for name in ("attention_budget", "investigate_ticks", "discover_senses", "bootstrap_semantic_senses",
                     "interoception_enabled", "interoception_mode", "conflict_z", "min_samples"):
            if name not in constructor_kwargs and name in effective:
                constructor_kwargs[name] = effective[name]
        if "min_samples" not in constructor_kwargs:
            constructor_kwargs["min_samples"] = min_samples
        if "conflict_z" not in constructor_kwargs:
            constructor_kwargs["conflict_z"] = conflict_z
        constructor_kwargs.pop("explicit_metabolism", None)
        constructor_kwargs.pop("auto_promote_predictors", None)
        runtime = cls(
            **constructor_kwargs,
            acclimation=acclimation,
            rhythm_model=rhythm_model,
            drift_baselines=drift_baselines,
            adaptive_senses=adaptive_senses,
            sensory_system=sensory_system,
            sensory_plasticity=sensory_system.plasticity_enabled,
            self_model=self_model,
            body_schema=body_schema,
            evidence_ledger=evidence_ledger,
            genome=genome,
            heritable_genome=heritable_genome,
            mutation_seed=int(normalized.get("mutation_seed", 0)),
            epigenetic_priors=epigenetic_priors,
            epigenetic_decay=float(normalized.get("epigenetic_decay", 0.05)),
            cognitive_bridge=cognitive_bridge,
            memory_consolidator=memory_consolidator,
            tick_count=max(int(normalized.get("saved_at_tick") or 0), int(getattr(signal_knowledge, "_last_tick", 0) or 0)),
            organism_id=normalized.get("organism_id"),
            signal_knowledge=signal_knowledge,
            signal_identity=signal_identity,
            metabolism=metabolism,
            assimilator=assimilator,
            homeostasis=homeostasis,
            physiology=physiology,
            living_body_state=living_body_state,
            physiology_config=resolved_physiology_config,
            social_ledger=social_ledger,
            social_resource_ledger=social_resource_ledger,
            explicit_metabolism=bool(kwargs.get("explicit_metabolism", effective.get("explicit_metabolism", False))),
            auto_promote_predictors=bool(kwargs.get("auto_promote_predictors", effective.get("auto_promote_predictors", False))),
            reproductive_pressure=reproductive_pressure,
            birth_authority=kwargs.get("birth_authority"),
            generation=int(normalized.get("generation", normalized.get("effective_config", {}).get("generation", 0))),
            reproduction_cost=float(normalized.get("reproduction_cost", normalized.get("effective_config", {}).get("reproduction_cost", 0.1))),
            social_exchange_quantum=float(normalized.get("social_exchange_quantum", normalized.get("effective_config", {}).get("social_exchange_quantum", 0.1))),
            social_exchange_cost=float(normalized.get("social_exchange_cost", normalized.get("effective_config", {}).get("social_exchange_cost", 0.01))),
            resting_requested=bool(normalized.get("resting_requested", normalized.get("effective_config", {}).get("resting_requested", False))),
            degradation_queue=degradation_queue,
            source_trust=source_trust,
            developmental_tracker=developmental_tracker,
            actuation_enabled=actuation_enabled,
            actuator_constitution=actuator_constitution,
            actuator_proposer=actuator_proposer,
            actuator_states=actuator_states,
            motor_intent_selector=motor_intent_selector,
            sensorimotor_learner=sensorimotor_learner,
            motor_exploration_mode=motor_exploration_mode,
        )
        runtime._pending_motor_observation = pending_motor_observation
        runtime._pending_proprioception = pending_proprioception
        raw_last_primitive = (
            raw_actuation.get("last_executed_primitive_id")
            if isinstance(raw_actuation, dict)
            else None
        )
        if raw_last_primitive is not None and not isinstance(raw_last_primitive, str):
            raise CheckpointError("invalid last executed primitive id")
        runtime._last_executed_primitive_id = raw_last_primitive
        raw_pending_primitive_context = (
            raw_actuation.get("pending_primitive_choice_context")
            if isinstance(raw_actuation, dict)
            else None
        )
        if raw_pending_primitive_context is not None:
            if not isinstance(raw_pending_primitive_context, dict):
                raise CheckpointError("invalid pending primitive choice context")
            primitive_id = raw_pending_primitive_context.get("primitive_id")
            concept_ids = raw_pending_primitive_context.get("concept_ids")
            complete_tick = raw_pending_primitive_context.get("complete_tick")
            samples_before = raw_pending_primitive_context.get("samples_before", 0)
            if not isinstance(primitive_id, str) or not primitive_id:
                raise CheckpointError("invalid pending primitive id")
            if (
                not isinstance(concept_ids, list)
                or len(concept_ids) > 256
                or any(
                    not isinstance(value, str) or not value or len(value) > 256
                    for value in concept_ids
                )
            ):
                raise CheckpointError("invalid pending primitive concept ids")
            if (
                isinstance(complete_tick, bool)
                or not isinstance(complete_tick, int)
                or complete_tick < 0
            ):
                raise CheckpointError("invalid pending primitive completion tick")
            if (
                isinstance(samples_before, bool)
                or not isinstance(samples_before, int)
                or samples_before < 0
            ):
                raise CheckpointError("invalid pending primitive sample count")
            runtime._pending_primitive_choice_context = (
                primitive_id,
                tuple(sorted(set(concept_ids))),
                complete_tick,
                samples_before,
            )
        raw_embodied_work = normalized.get("pending_embodied_work", 0.0)
        if (
            isinstance(raw_embodied_work, bool)
            or not isinstance(raw_embodied_work, (int, float))
            or not math.isfinite(float(raw_embodied_work))
            or not 0.0 <= float(raw_embodied_work) <= 0.25
        ):
            raise CheckpointError("invalid pending_embodied_work checkpoint")
        runtime._pending_embodied_work = float(raw_embodied_work)
        runtime._reacclimation_remaining = kernel_limits.reacclimation_ticks
        runtime._narrative_journal = list(normalized.get("narrative_journal", []))
        raw_last_state = normalized.get("last_runtime_vital_state")
        raw_last_phase = normalized.get("last_runtime_development_phase")
        if raw_last_state is not None and (not isinstance(raw_last_state, str) or len(raw_last_state) > 32):
            raise ValueError("invalid last runtime vital state")
        if raw_last_phase is not None and (not isinstance(raw_last_phase, str) or len(raw_last_phase) > 32):
            raise ValueError("invalid last runtime development phase")
        runtime._last_runtime_vital_state = raw_last_state
        runtime._last_runtime_development_phase = raw_last_phase
        raw_first_events = normalized.get("first_life_history_events", {})
        if not isinstance(raw_first_events, dict) or any(
            not isinstance(raw_first_events.get(key, False), bool)
            for key in ("sense", "concept", "prediction")
        ):
            raise ValueError("invalid first life-history event state")
        runtime._first_sense_emitted = raw_first_events.get("sense", False)
        runtime._first_concept_emitted = raw_first_events.get("concept", False)
        runtime._first_prediction_emitted = raw_first_events.get("prediction", False)
        return runtime

    @classmethod
    def load_or_create(cls, path: str | Path, **kwargs: Any) -> "OrganismRuntime":
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
