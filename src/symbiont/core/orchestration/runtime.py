from __future__ import annotations

import json
import platform
import hashlib
import uuid
import math
import time
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ...host.acclimation import HostAcclimation
from ...host.adaptive import AdaptiveSenseModel, SamplingPlan
from ...host.bootstrap import current_time_bucket
from ...host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointError,
    export_checkpoint,
    import_checkpoint,
    load_checkpoint_file,
    normalize_checkpoint,
    save_checkpoint_atomic,
)
from ...host.contracts import DiscoveryPolicy, DiscoveryProvider, HostManifest
from ...host.discovery import HostDiscovery
from ...host.drift import DriftAwareBaseline, DriftObservation
from ...host.lifecycle import HostLifecycle, LifecycleSnapshot
from ...host.percepts import DEFAULT_PERCEPT_NAMES, Percept
from ...host.providers.stdlib import StandardLibraryProvider
from ...host.providers.stdlib_readings import StandardLibraryReadingProvider
from ...host.readings import (
    HostSampler,
    ReadingPrivacyClass,
    ReadingProvider,
    ReadingQuality,
    SensorReading,
    Unit,
)
from ...host.rhythms import RhythmModel
from ...host.second_look import SecondLookSession
from ...sensory import SensorySystem
from ...cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ...cognition.genome import Genome, DevelopmentGenes, PlasticityGenes, RangeSpec
from ...cognition.graph import CognitiveGraph
from ...cognition.learning import ShadowPrediction
from ...cognition.limits import KernelLimits
from ...genetics.expression import (
    ExpressionRegulator,
    GeneExpressionState,
    RegulatorySignals,
)
from ..cognition.attention import AttentionAllocation, AttentionBudget, AttentionCandidate, attend_to_host
from ..embodiment.body_schema import BodySchemaEngine
from ..cognition.bridge import CognitiveBridge, CognitiveBridgeResult
from ..cognition.self_model import derive_cognitive_self_namespace, project_cognitive_self_observation
from ..cognition.consolidation import ConsolidationSignal, MemoryConsolidator, MemoryKind, novelty_from_drift_kind, surprise_from_loss
from ..cognition.evidence import DissentRecord, EvidenceRevisionLedger
from ..foundation.narrative import NarrativeEntry, narrate_host
from ..cognition.host_self_model import LOW_HEALTH_INVESTIGATION_THRESHOLD, SelfModel
from ..signals.identity import SignalIdentity
from ..signals.knowledge import SignalKnowledgeEngine, MAX_KNOWLEDGE_CHECKPOINT_BYTES
from ..signals.knowledge_types import SignalObservation, SignalObservationBatch
from ..embodiment.degradation import DegradationQueue
from ..embodiment.physiology import (
    DEFAULT_PHYSIOLOGY_CONFIG,
    BodyStructureState,
    LivingBodyState,
    PhysiologyConfig,
    PhysiologyController,
    PhysiologySnapshot,
    VitalState,
)
from ..signals.knowledge_checkpoint import validate_checkpoint
from ..embodiment.metabolism import MetabolicLedger, MetabolicSnapshot
from ..embodiment.assimilation import InformationAssimilator, AssimilationDecision
from ..embodiment.homeostasis import HomeostaticController, HomeostaticSnapshot
from ..regulation import ActionArbitrator, InnateReactivity, ReactiveMemory, ReactiveState
from ..social.ecology import SharedHabitat
from ..social.trust import SourceTrustModel
from ..social.relations import (InteractionOutcome, RelationLedger, RelationValence,
                     SocialRelation,
                     ResourceEvidenceLedger, SocialCompetitionRequest,
                     SocialHabitat, SocialPresence)
from ..lineage.birth_authority import BirthRecord, HabitatBirthAuthority
from ..embodiment.ontogeny import OntogenyController, OntogenySnapshot
from ..lineage.inheritance import EpigeneticPrior
from ...genetics.migration import apply_legacy_heritable_payload
from ...genetics.mutation import mutate_genome
from ..embodiment.development import DevelopmentalSnapshot, DevelopmentalTracker
from ...cognition.birth import load_base_graph
from ...actuation.checkpoint import export_actuation_state, restore_actuation_state
from ...actuation.binding import CompetenceExecutionBindingRegistry
from ...actuation.constitution import ActuatorConstitution
from ...actuation.surface import ActuatorChannel, ActuatorSurface
from ...actuation.proposer import ActuatorProposer
from ...actuation.candidate import ActuatorCandidateState
from ...actuation.selector import MotorIntentSelector
from ...actuation.system import ActuatorSystem
from ...actuation.types import Actuation, MotorIntent
from ...actuation.action import (
    ActionEvaluation,
    ActionJustification,
    ActionProposal,
    ActionSource,
    MotorCommand,
)
from ...actuation.commitment import ActionCommitment, CommitmentStatus
from ...actuation.effects import EffectSpace
from ...actuation.competence import CompetenceEvidence, CompetenceLibrary, MotorCompetence
from ...actuation.evidence import (
    CausalEvidenceLedger,
    PredictionError,
    SensorimotorTransition,
)
from ...actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from ...actuation.exploration import ExplorationPolicy, ExplorationSignals
from ...actuation.composition import CompositionEngine
from ...actuation.state import SensorimotorV2Snapshot
from ...actuation.sensorimotor import (
    SensorimotorLearner,
    SensorimotorSnapshot,
)


def _parse_running_version(version_string: str) -> tuple[int, int, int]:
    parts = version_string.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


def _canonical_hash(payload: dict[str, Any]) -> str:
    """Content hash of a JSON-serializable payload, key order independent."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state_hash_of(checkpoint_payload: dict[str, Any]) -> str:
    """Hash organism state, excluding save-event/provenance metadata.

    ``checkpoint_lineage`` records save *events* and ``runtime_provenance``
    records what code produced the save — neither is part of what the
    organism *is*. Two checkpoints of the same underlying state must hash
    identically regardless of when or under what version they were taken.
    """
    return _canonical_hash(
        {
            key: value
            for key, value in checkpoint_payload.items()
            if key not in ("checkpoint_lineage", "runtime_provenance")
        }
    )


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
    ontogeny: OntogenySnapshot | None = None
    degradation_excreted: int = 0
    retained_items: int = 0
    action_result: ActionExecutionResult | None = None
    development: DevelopmentalSnapshot | None = None
    sensory_phenotype: dict[str, Any] | None = None
    # WARN(integrity): Bounded lifecycle facts emitted by the subject runtime.  The laboratory
    # may project these into its own taxonomy, but must not manufacture them
    # from snapshots after the fact.
    runtime_events: tuple[str, ...] = ()
    motor_intent: MotorIntent | None = None
    actuation: Actuation | None = None
    motor_intents: tuple[MotorIntent, ...] = ()
    actuations: tuple[Actuation, ...] = ()
    action_commitment: ActionCommitment | None = None
    motor_command: MotorCommand | None = None
    sensorimotor_transition: SensorimotorTransition | None = None
    sensorimotor_v2: SensorimotorV2Snapshot | None = None
    gene_expression: dict[str, object] | None = None


class OrganismDeadError(RuntimeError):
    """Raised when execution is requested after irreversible death."""


class OrganismRuntime:
    """Continuous cognitive cycle over safe local perceptions.

    In developmental mode discovery remains broad inside the provider's fixed safety
    boundary, while sampling becomes selective. Cognitive learning happens only
    after attention has been allocated for the current tick, so attention and the
    self-model can constrain plastic updates instead of merely describing them.
    """

    _SUPPORTED_EPIGENETIC_KEYS = frozenset()

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
        heritable_genome: object | None = None,
        mutation_seed: int = 0,
        epigenetic_priors: tuple[EpigeneticPrior, ...] = (),
        epigenetic_decay: float = 0.05,
        kernel_limits: KernelLimits | None = None,
        cognitive_graph: CognitiveGraph | None = None,
        cognitive_bridge: CognitiveBridge | None = None,
        gene_expression_state: GeneExpressionState | None = None,
        expression_regulator: ExpressionRegulator | None = None,
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
        birth_authority: HabitatBirthAuthority | None = None,
        generation: int = 0,
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
        motor_intent_selector: MotorIntentSelector | None = None,
        actuator_system: ActuatorSystem | None = None,
        sensorimotor_learner: SensorimotorLearner | None = None,
    ) -> None:
        if attention_budget <= 0.0:
            raise ValueError("attention_budget must be positive")
        if investigate_ticks < 0:
            raise ValueError("investigate_ticks must be non-negative (0 disables investigation)")
        if (tick_count < 0 or generation < 0
                or social_exchange_quantum <= 0.0 or social_exchange_cost < 0.0):
            raise ValueError("invalid tick, generation, social quantum or social cost")
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
            from ...host.providers.interoception import (
                InteroceptionProvider,
                ShamInteroceptionProvider,
            )
            from ...host.providers.linux_surfaces import LinuxSurfaceProvider
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
        self._birth_authority = birth_authority
        self._developmental_tracker = developmental_tracker if developmental_tracker is not None else DevelopmentalTracker()
        self._last_runtime_vital_state: str | None = None
        self._last_runtime_development_phase: str | None = None
        self._first_sense_emitted = False
        self._first_concept_emitted = False
        self._first_prediction_emitted = False
        self._generation = generation
        self._last_checkpoint_hash: str | None = None
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

        metabolic_seed_state = living_body_state
        if metabolic_seed_state is None and homeostasis is not None:
            metabolic_seed_state = homeostasis.body_state
        if metabolic_seed_state is None and physiology is not None:
            metabolic_seed_state = physiology.body_state

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
                body_state=metabolic_seed_state,
            )
        )

        if self._interoception_provider is not None:
            # The first internal percept must describe the organism's actual
            # initial state.  Starting the provider at an unconditional 1.0
            # would create a one-cycle blind spot exactly when a germinal
            # organism has to make its first local decision.
            initial_metabolism = self._metabolism.snapshot()
            initial_ratio = self._metabolism.body_state.energy_reserve / max(
                self._metabolism.body_state.max_energy,
                1e-12,
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
            source_state = (
                homeostasis.body_state
                if homeostasis is not None
                else (
                    physiology.body_state
                    if physiology is not None
                    else self._metabolism.body_state
                )
            )
            physiology_snapshot = (
                physiology.snapshot() if physiology is not None else None
            )
            living_body_state = LivingBodyState(
                energy_reserve=self._metabolism.body_state.energy_reserve,
                max_energy=self._metabolism.body_state.max_energy,
                structural_integrity=(
                    homeostasis.integrity
                    if homeostasis is not None
                    else source_state.structural_integrity
                ),
                temperature=source_state.temperature,
                fatigue=source_state.fatigue,
                growth_progress=source_state.growth_progress,
                senescence=source_state.senescence,
                age_ticks=max(tick_count, source_state.age_ticks),
                vital_state=(
                    physiology_snapshot.state
                    if physiology_snapshot is not None
                    else source_state.vital_state
                ),
                transitions=(
                    physiology_snapshot.transitions
                    if physiology_snapshot is not None
                    else source_state.transitions
                ),
                death_tick=(
                    physiology_snapshot.death_tick
                    if physiology_snapshot is not None
                    else source_state.death_tick
                ),
            )
        self._living_body_state = living_body_state
        self._metabolism.bind_body_state(self._living_body_state)

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
        self._innate_reactivity = InnateReactivity()
        self._reactive_memory = ReactiveMemory()
        self._action_arbitrator = ActionArbitrator()
        # One-tick causal trace only. A restart deliberately breaks this trace;
        # established reactive associations are checkpointed separately.
        self._pending_reactive_credit: tuple[str, str, float] | None = None
        self._last_reactive_state = None
        self._ontogeny = OntogenyController(
            config=self._physiology_config,
            body_state=self._living_body_state,
        )
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
            self._habitat.admit(self._organism_id)
        for resource in self._resource_habitats.values():
            if not resource.has_allocation(self._organism_id) and not resource.admit(self._organism_id):
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
        self._gene_expression_state = (
            gene_expression_state
            if gene_expression_state is not None
            else (GeneExpressionState.from_genome(genome) if genome is not None else None)
        )
        self._expression_regulator = expression_regulator or ExpressionRegulator()
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
        # Historical heritable_genome input is no longer an operative genetic
        # source. Reject non-null values rather than running two genomes.
        if heritable_genome is not None:
            raise ValueError("HeritableGenome is removed; pass Genome v2 via genome")
        self._heritable_genome = None
        self._mutation_seed = mutation_seed
        self._epigenetic_priors = tuple(epigenetic_priors)
        self._epigenetic_decay = float(epigenetic_decay)
        if self._birth_authority is not None and self._organism_id not in self._birth_authority.live_ids:
            genome_id = self._genome.genome_id if self._genome is not None else "runtime"
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
                graph=cognitive_graph,
                genome=genome,
                kernel_limits=self._kernel_limits,
                expression_state=self._gene_expression_state,
            )
        if self._cognitive_bridge is not None:
            if self._gene_expression_state is not None:
                self._cognitive_bridge.set_expression_state(self._gene_expression_state)
            self._cognitive_bridge.bind_contention_identity(self._organism_id)
        self._actuation_enabled = bool(actuation_enabled)
        self._actuator_constitution: ActuatorConstitution | None = None
        self._actuator_proposer: ActuatorProposer | None = None
        self._motor_intent_selector: MotorIntentSelector | None = None
        self._actuator_system: ActuatorSystem | None = None
        self._sensorimotor_learner: SensorimotorLearner | None = None
        self._last_motor_intent: MotorIntent | None = None
        self._last_actuation: Actuation | None = None
        self._last_motor_intents: tuple[MotorIntent, ...] = ()
        self._last_actuations: tuple[Actuation, ...] = ()
        self._last_action_source = "none"
        self._last_executed_primitive_id: str | None = None
        self._last_action_proposal: ActionProposal | None = None
        self._active_action_commitment: ActionCommitment | None = None
        self._last_motor_command: MotorCommand | None = None
        self._effect_space = EffectSpace()
        self._causal_evidence = CausalEvidenceLedger()
        self._competence_library = CompetenceLibrary()
        self._competence_execution_bindings = CompetenceExecutionBindingRegistry()
        self._sensorimotor_model = CompetenceEffectModel()
        self._controllability_model = ControllabilityModel()
        self._agency_model = AgencyModel()
        self._exploration_policy = ExplorationPolicy()
        self._exploration_strength_memory: dict[str, float] = {}
        self._active_exploration_preference: tuple[str, ...] = ()
        self._last_exploration_signals: dict[str, ExplorationSignals] = {}
        self._composition_engine = CompositionEngine()
        self._composition_predecessor_id: str | None = None
        self._active_composition_children: tuple[str, ...] = ()
        self._active_composition_index = 0
        self._effect_by_commitment: dict[str, str] = {}
        self._pending_sensorimotor_transition: dict[str, Any] | None = None
        self._last_sensorimotor_transition: SensorimotorTransition | None = None
        self._pending_motor_observation: tuple[
            tuple[str, float, dict[str, float] | None], ...
        ] = ()
        self._pending_proprioception: dict[str, float] = {}
        # Ephemeral delayed-credit traces. They are intentionally not
        # checkpointed: a restart breaks the causal continuity needed to assign
        # a later physiological outcome to a pre-restart action.
        self._pending_homeostatic_action_credit: list[
            tuple[int, str, str, tuple[str, ...], float, float]
        ] = []
        if self._actuation_enabled:
            if actuator_constitution is None:
                raise ValueError(
                    "actuation_enabled requires an explicit body-owned actuator_constitution"
                )
            self._actuator_constitution = actuator_constitution
            if not self._living_body_state.structure_states:
                # A body with actuation but no per-structure tracking yet —
                # either freshly created, or restored from a pre-L5.5.1
                # checkpoint — gets one BodyStructureState per actuator slot,
                # uniform at the current aggregate integrity.
                self._living_body_state.structure_states = {
                    slot.slot_id: BodyStructureState(
                        structure_id=slot.slot_id,
                        integrity=self._living_body_state.structural_integrity,
                    )
                    for slot in actuator_constitution.slots
                }
            self._actuator_proposer = (
                actuator_proposer
                if actuator_proposer is not None
                else ActuatorProposer(actuator_constitution, organism_id=self._organism_id)
            )
            self._motor_intent_selector = motor_intent_selector or MotorIntentSelector()
            self._actuator_system = actuator_system or ActuatorSystem()
            self._sensorimotor_learner = (
                sensorimotor_learner
                if sensorimotor_learner is not None
                else SensorimotorLearner(
                    actuator_constitution.actuator_ids,
                    organism_id=self._organism_id,
                    max_concurrent=None,
                    embodiment_fingerprint=actuator_constitution.contract_fingerprint,
                )
            )
        self._pending_embodied_work = 0.0
        self._narrative_journal: list[dict[str, Any]] = []

    @property
    def gene_expression_state(self) -> GeneExpressionState | None:
        return self._gene_expression_state

    def _update_gene_expression(
        self,
        *,
        cognition: CognitiveBridgeResult | None,
        drift_observations: dict[str, DriftObservation],
        metabolic_pressure: str,
    ) -> None:
        """Regulate the next tick from organism-owned evidence only."""
        if self._genome is None or self._gene_expression_state is None:
            return

        losses = (
            [float(error.loss) for error in cognition.prediction_errors]
            if cognition is not None
            else []
        )
        prediction_error = max(0.0, min(1.0, sum(losses) / len(losses))) if losses else 0.0
        novelty_values = [
            novelty_from_drift_kind(observation.kind)
            for observation in drift_observations.values()
        ]
        novelty = max(novelty_values, default=0.0)

        actuator_count = (
            len(self._actuator_constitution.actuator_ids)
            if self._actuator_constitution is not None
            else 0
        )
        active_count = (
            len(self._actuator_proposer.active_repertoire)
            if self._actuator_proposer is not None
            else 0
        )
        controllability_loss = (
            max(0.0, min(1.0, 1.0 - active_count / actuator_count))
            if actuator_count
            else 0.0
        )

        # No explicit "new body" flag enters regulation. Mismatch is inferred
        # from failed predictions and loss of controllability.
        embodiment_mismatch = max(prediction_error, controllability_loss)
        uncertainty = max(prediction_error, 0.5 * controllability_loss)
        pressure_ratio = {
            "normal": 0.0,
            "elevated": 0.33,
            "severe": 0.66,
            "unrecoverable": 1.0,
        }.get(str(metabolic_pressure), 0.0)

        signals = RegulatorySignals(
            uncertainty=uncertainty,
            novelty=max(0.0, min(1.0, novelty)),
            prediction_error=prediction_error,
            controllability_loss=controllability_loss,
            embodiment_mismatch=embodiment_mismatch,
            resource_pressure=pressure_ratio,
        )
        frozen = bool(
            self._cognitive_bridge is not None
            and getattr(self._cognitive_bridge, "_safety_state", None) is not None
            and self._cognitive_bridge._safety_state.frozen  # noqa: SLF001
        )
        self._gene_expression_state = self._expression_regulator.update(
            self._genome,
            self._gene_expression_state,
            signals,
            frozen=frozen,
        )
        if self._cognitive_bridge is not None:
            self._cognitive_bridge.set_expression_state(self._gene_expression_state)

    @property
    def reacclimation_remaining(self) -> int:
        """Ticks remaining in the organism-owned post-restore reacclimation gate."""
        return int(self._reacclimation_remaining)

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

    @property
    def sensorimotor_exclusive_actuator_groups(
        self,
    ) -> tuple[tuple[str, ...], ...]:
        if self._sensorimotor_learner is None:
            return ()
        return self._sensorimotor_learner.exclusive_actuator_groups

    @property
    def sensorimotor_competence_candidates(self) -> tuple[dict[str, object], ...]:
        """Passive candidate view; legacy sequence objects never cross this boundary."""
        if self._sensorimotor_learner is None:
            return ()
        return tuple(
            {
                "candidate_id": item.primitive_id,
                "embodiment_fingerprint": item.embodiment_fingerprint,
                "sequence": [
                    [[actuator_id, level] for actuator_id, level in pattern]
                    for pattern in item.sequence
                ],
                "samples": item.samples,
                "effect_mean": item.effect_mean,
                "effect_variance": item.effect_variance,
                "controllability": item.controllability,
                "directional_consistency": item.directional_consistency,
                "maturity": item.maturity.value,
                "established": item.established,
            }
            for item in self._sensorimotor_learner.primitives
        )

    @property
    def sensorimotor_competence_episodes(self) -> tuple[dict[str, object], ...]:
        """Latest evidence episodes projected into v2 competence terminology."""
        if self._sensorimotor_learner is None:
            return ()
        return tuple(
            {
                "candidate_id": episode.primitive_id,
                "start_tick": episode.start_tick,
                "end_tick": episode.end_tick,
                "source": episode.source,
                "evidence_blocks": episode.evidence_blocks,
                "sample_index": episode.sample_index,
                "materialized": episode.materialized,
                "established": episode.competence,
            }
            for episode in self._sensorimotor_learner.last_primitive_episodes
        )

    def _sensorimotor_v2_snapshot(self) -> SensorimotorV2Snapshot | None:
        if not self._actuation_enabled:
            return None
        legacy_snapshot = (
            self._sensorimotor_learner.snapshot()
            if self._sensorimotor_learner is not None
            else None
        )
        progress_values = [
            max(0.0, float(item.learning_progress))
            for item in self._last_exploration_signals.values()
        ]
        active = self._active_action_commitment
        return SensorimotorV2Snapshot(
            effect_count=len(self._effect_space.effects),
            causal_evidence_count=len(self._causal_evidence.evidence),
            competence_count=len(self._competence_library.items),
            established_competence_count=sum(
                1 for item in self._competence_library.items if self._competence_is_executable(item)
            ),
            competence_candidate_count=(
                legacy_snapshot.competence_candidates
                if legacy_snapshot is not None
                else 0
            ),
            controllability_estimate_count=len(
                self._controllability_model.estimates
            ),
            predictive_context_count=self._sensorimotor_model.context_count,
            agency_estimate_count=len(self._agency_model.estimates),
            composition_evidence_count=len(self._composition_engine.evidence),
            established_composition_count=len(self._composition_engine.established),
            body_schema_sensorimotor_relations=(
                self._body_schema.sensorimotor_dependency_evidence_count
            ),
            active_commitment_id=(
                active.commitment_id
                if active is not None and active.active
                else None
            ),
            active_competence_id=(
                active.competence_id
                if active is not None and active.active
                else None
            ),
            action_source=self._last_action_source,
            exploration_preference=self._active_exploration_preference,
            mean_learning_progress=(
                sum(progress_values) / len(progress_values)
                if progress_values
                else 0.0
            ),
        )

    @property
    def sensorimotor_v2_snapshot(self) -> SensorimotorV2Snapshot | None:
        return self._sensorimotor_v2_snapshot()
    @property
    def motor_competences(self) -> tuple[MotorCompetence, ...]:
        """Canonical learned competence view used outside the legacy learner."""
        return self._competence_library.items

    @property
    def effect_representations(self):
        return self._effect_space.effects

    @property
    def causal_evidence(self):
        return self._causal_evidence.evidence

    @property
    def actuator_causal_states(self) -> tuple[ActuatorCandidateState, ...]:
        """Evaluator-only read view of learned actuator/effect evidence."""
        if self._actuator_proposer is None:
            return ()
        return self._actuator_proposer.states

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
        # Direct actuator-effect learning must see the same complete
        # currently perceived non-command body surface as the temporal learner.
        # Lexicographic truncation over opaque ids would make later channels
        # causally invisible for reasons unrelated to the body or organism.
        return dict(sorted(values.items()))

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
        # Preserve the complete currently perceived bodily state.  A
        # lexicographic slice over opaque sensor ids silently changes which
        # physical consequences are learnable and biases motor discovery.
        return dict(sorted(values.items()))

    def _complete_pending_motor_observation(
        self, percepts: tuple[Percept, ...], *, tick: int
    ) -> tuple[str, ...]:
        pending = self._pending_motor_observation
        if not pending or self._actuator_proposer is None:
            return ()
        after = self._motor_percept_snapshot(percepts)
        promoted: list[str] = []
        for actuator_id, activation, before in pending:
            if before is not None:
                for percept_id in sorted(set(before) & set(after)):
                    self._actuator_proposer.record_effect(
                        actuator_id,
                        percept_id,
                        activation=activation,
                        delta_percept=after[percept_id] - before[percept_id],
                        tick=tick,
                    )
                self._actuator_proposer.consider_natural_evidence(actuator_id)
            if actuator_id in self._actuator_proposer.active_repertoire:
                promoted.append(actuator_id)
        self._pending_motor_observation = ()
        return tuple(dict.fromkeys(promoted))

    def _schedule_homeostatic_action_credit(
        self,
        *,
        family: str,
        action_id: str,
        concept_ids: tuple[str, ...],
        baseline_error: float,
        tick: int,
    ) -> None:
        if self._cognitive_bridge is None or not concept_ids:
            return
        # Multiple horizons let a costly action receive credit for a later
        # physiological recovery without handing cognition an environmental
        # target. Long delays are discounted but remain learnable.
        for horizon, discount in ((4, 1.0), (16, 0.85), (64, 0.65), (256, 0.40)):
            self._pending_homeostatic_action_credit.append(
                (
                    int(tick) + horizon,
                    family,
                    str(action_id),
                    tuple(sorted(set(concept_ids))),
                    float(baseline_error),
                    float(discount),
                )
            )
        # Hard bound: retain the nearest due traces if motor activity is dense.
        if len(self._pending_homeostatic_action_credit) > 4096:
            self._pending_homeostatic_action_credit.sort(key=lambda item: item[0])
            self._pending_homeostatic_action_credit = (
                self._pending_homeostatic_action_credit[:4096]
            )

    def _resolve_homeostatic_action_credit(self, *, tick: int) -> None:
        if not self._pending_homeostatic_action_credit:
            return
        if not self._living_body_state.alive:
            self._pending_homeostatic_action_credit.clear()
            return
        current_error = self._homeostasis.deviation()
        remaining: list[tuple[int, str, str, tuple[str, ...], float, float]] = []
        for due_tick, family, action_id, concept_ids, baseline_error, discount in (
            self._pending_homeostatic_action_credit
        ):
            if due_tick > tick:
                remaining.append(
                    (due_tick, family, action_id, concept_ids, baseline_error, discount)
                )
                continue
            if self._cognitive_bridge is None:
                continue
            intrinsic_value = max(
                -1.0,
                min(1.0, (baseline_error - current_error) * discount),
            )
            self._cognitive_bridge.observe_homeostatic_action_outcome(
                family=family,
                action_id=action_id,
                concept_ids=concept_ids,
                value=intrinsic_value,
                tick=tick,
            )
        self._pending_homeostatic_action_credit = remaining

    def _choose_acquired_competence(
        self,
        *,
        cognition: "CognitiveBridgeResult",
        percepts: "tuple[Percept, ...]",
        candidate_ids: "tuple[str, ...]",
        signal_references: dict[str, str],
        tick: int,
    ) -> str | None:
        """Hook for model-based prospective competence selection.

        The base runtime abstains. Model-enabled runtimes may return an opaque
        competence id, but this hook never executes a controller or emits a
        MotorCommand; the universal ActionArbitrator remains authoritative.
        """
        return None

    def _flatten_competence_controller(
        self,
        competence_id: str,
        *,
        seen: frozenset[str] = frozenset(),
    ) -> tuple[str, ...]:
        if competence_id in seen:
            raise RuntimeError("cyclic competence composition")
        competence = self._competence_library.get(competence_id)
        if competence is None or not competence.parent_competence_ids:
            return (competence_id,)
        next_seen = seen | {competence_id}
        flattened: list[str] = []
        for child_id in competence.parent_competence_ids:
            flattened.extend(
                self._flatten_competence_controller(
                    child_id,
                    seen=next_seen,
                )
            )
        return tuple(flattened)

    def _activate_competence_controller(self, competence_id: str) -> bool:
        if self._sensorimotor_learner is None:
            return False
        leaves = self._flatten_competence_controller(competence_id)
        if not leaves:
            return False
        first_leaf = leaves[0]
        self._active_composition_children = leaves if len(leaves) > 1 else ()
        self._active_composition_index = 0
        return self._sensorimotor_learner.activate_primitive(first_leaf)

    def _materialize_composition(
        self,
        evidence,
    ) -> MotorCompetence | None:
        if not evidence.established or self._actuator_constitution is None:
            return None
        digest = hashlib.sha256(
            (
                f"{evidence.first_competence_id}>"
                f"{evidence.second_competence_id}>"
                f"{evidence.effect_id}"
            ).encode("utf-8")
        ).hexdigest()[:24]
        competence_id = f"competence.composed.{digest}"
        existing = self._competence_library.get(competence_id)
        evidence_ref = f"composition.{digest}"
        derived = CompetenceEvidence(
            controller_seed_ref=f"sequence:{evidence.first_competence_id}>{evidence.second_competence_id}",
            effect_evidence_refs=(evidence.effect_id,),
            controllability_evidence_refs=(evidence_ref,),
            support=evidence.support,
            failures=evidence.failures,
            reproducibility=evidence.reproducibility,
            controllability=evidence.reproducibility,
            directional_consistency=1.0,
        )
        if existing is not None:
            existing.evidence = derived
            return existing
        competence = MotorCompetence(
            competence_id=competence_id,
            controller_id=f"controller.{competence_id}",
            effect_id=evidence.effect_id,
            evidence=derived,
            parent_competence_ids=(
                evidence.first_competence_id,
                evidence.second_competence_id,
            ),
            controller_strategy_ref=derived.controller_seed_ref,
        )
        self._competence_library.add(competence)
        self._competence_execution_bindings.bind_from_evidence(
            competence_id=competence.competence_id,
            surface_fingerprint=self._actuator_constitution.contract_fingerprint,
            effect_id=evidence.effect_id,
            evidence_refs=(evidence_ref,),
            reliability=evidence.reproducibility,
            controllability=evidence.reproducibility,
            tick=max(0, int(getattr(evidence, "last_tick", 0) or 0)),
        )
        return competence

    def _record_competence_completion(
        self,
        competence_id: str,
        *,
        commitment_id: str,
    ) -> None:
        effect_id = self._effect_by_commitment.pop(commitment_id, None)
        predecessor = self._composition_predecessor_id
        if predecessor is not None and predecessor != competence_id:
            if effect_id is None:
                self._composition_engine.observe_absence(
                    predecessor,
                    competence_id,
                )
            else:
                evidence = self._composition_engine.observe(
                    predecessor,
                    competence_id,
                    effect_id,
                    success=True,
                )
                self._materialize_composition(evidence)
        self._composition_predecessor_id = competence_id

    def _advance_or_complete_competence(
        self,
        *,
        tick: int,
    ) -> None:
        commitment = self._active_action_commitment
        if (
            commitment is None
            or not commitment.active
            or commitment.competence_id is None
            or self._sensorimotor_learner is None
            or self._sensorimotor_learner.active_primitive_id is not None
        ):
            return
        if (
            self._active_composition_children
            and self._active_composition_index + 1
            < len(self._active_composition_children)
        ):
            self._active_composition_index += 1
            child_id = self._active_composition_children[
                self._active_composition_index
            ]
            if self._sensorimotor_learner.activate_primitive(child_id):
                return
            commitment.terminate(
                tick=tick,
                status=CommitmentStatus.FAILED,
                reason="composed_child_unavailable",
            )
            self._active_composition_children = ()
            self._active_composition_index = 0
            return

        completed_id = commitment.competence_id
        completed_commitment_id = commitment.commitment_id
        commitment.terminate(
            tick=tick,
            status=CommitmentStatus.COMPLETED,
            reason="competence_completed",
        )
        self._record_competence_completion(
            completed_id,
            commitment_id=completed_commitment_id,
        )
        self._active_composition_children = ()
        self._active_composition_index = 0

    def _rank_exploration_opportunities(
        self,
        *,
        exploration_drive: float,
        reactive_state: ReactiveState,
    ) -> tuple[str, ...]:
        """Choose an opaque local opportunity from organism-owned evidence only."""
        if self._actuator_proposer is None:
            self._last_exploration_signals = {}
            return ()
        opportunities: list[tuple[str, ExplorationSignals]] = []
        current_strengths: dict[str, float] = {}
        physiological_cost = max(
            0.0,
            min(1.0, 1.0 - float(self._homeostasis.activity_scale)),
        )
        risk = max(0.0, min(1.0, float(reactive_state.withdrawal)))
        for state in self._actuator_proposer.states:
            activations = max(0, int(state.activations))
            strength = max(0.0, min(1.0, float(state.effect_strength)))
            previous = self._exploration_strength_memory.get(
                state.actuator_id,
                strength,
            )
            progress = max(0.0, strength - previous)
            current_strengths[state.actuator_id] = strength
            signals = ExplorationSignals(
                uncertainty=max(0.0, 1.0 - min(1.0, activations / 12.0)),
                novelty=1.0 / (1.0 + activations),
                learning_progress=progress,
                effect_relevance=max(0.0, min(1.0, exploration_drive)),
                controllability_potential=(
                    None if activations == 0 else strength
                ),
                physiological_cost=physiological_cost,
                risk=risk,
            )
            opportunities.append((state.actuator_id, signals))
        self._exploration_strength_memory.update(current_strengths)
        self._last_exploration_signals = dict(opportunities)
        chosen = self._exploration_policy.choose(tuple(opportunities))
        return (chosen,) if chosen is not None else ()

    def _refresh_competence_library(self) -> None:
        """Project sequence evidence into the v2 competence repertoire.

        A sequence supplies a controller seed and evidence only.  No effect
        binding is fabricated: that remains unresolved until EffectSpace
        correspondence is learned.
        """
        if self._sensorimotor_learner is None or self._actuator_constitution is None:
            return
        for primitive in self._sensorimotor_learner.primitives:
            if not primitive.established:
                continue
            existing = self._competence_library.get(primitive.primitive_id)
            if existing is None:
                self._competence_library.add(
                    MotorCompetence(
                        competence_id=primitive.primitive_id,
                        controller_id=f"controller.{primitive.primitive_id}",
                        effect_id=None,
                        evidence=primitive.competence_evidence,
                        controller_strategy_ref=primitive.primitive_id,
                    )
                )
            else:
                existing.evidence = primitive.competence_evidence

    def _motor_step(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        *,
        tick: int,
        signal_references: dict[str, str] | None = None,
    ) -> None:
        baseline = self._motor_percept_snapshot(percepts)
        sensorimotor_body_state = self._sensorimotor_body_snapshot(percepts)

        # Complete t-1 -> t only when the bodily consequence is actually
        # observable.  A command is never credited with a same-tick effect.
        self._last_sensorimotor_transition = None
        if self._pending_sensorimotor_transition is not None:
            previous = self._pending_sensorimotor_transition
            before_state = previous["state_before"]
            raw_changes = {
                name: float(sensorimotor_body_state[name]) - float(before_state[name])
                for name in sorted(set(before_state) & set(sensorimotor_body_state))
            }
            references = signal_references or {}
            opaque_changes: dict[str, float] = {}
            for name, delta in raw_changes.items():
                opaque = references.get(name)
                if opaque is None and name.startswith(
                    ("signal.", "latent.", "part.", "channel.", "internal.", "effect.")
                ):
                    opaque = name
                if opaque is not None:
                    opaque_changes[str(opaque)] = delta
            observed_effect = self._effect_space.observe(opaque_changes)

            predicted_effect_id = previous.get("predicted_effect_id")
            prediction_confidence = float(
                previous.get("prediction_confidence", 0.0)
            )
            observed_effect_id = (
                observed_effect.effect_id
                if observed_effect is not None
                else None
            )
            prediction_error = None
            if predicted_effect_id is not None:
                matched = predicted_effect_id == observed_effect_id
                prediction_error = PredictionError(
                    magnitude=0.0 if matched else 1.0,
                    uncertainty=max(
                        0.0,
                        min(1.0, 1.0 - prediction_confidence),
                    ),
                    novelty=0.0 if matched else 1.0,
                )

            transition = SensorimotorTransition(
                transition_id="transition." + hashlib.sha256(
                    f"{self._organism_id}:{previous['tick']}:{tick}:{previous['motor_command_ref']}".encode("utf-8")
                ).hexdigest()[:24],
                tick_start=int(previous["tick"]),
                tick_end=tick,
                context_ref=str(previous["context_ref"]),
                commitment_id=str(previous["commitment_id"]),
                controller_id=str(previous["controller_id"]),
                competence_id=(
                    str(previous["competence_id"])
                    if previous.get("competence_id") is not None
                    else None
                ),
                state_before_ref=str(previous["state_before_ref"]),
                motor_command_ref=str(previous["motor_command_ref"]),
                actuation_ref=str(previous["actuation_ref"]),
                prediction_ref=(
                    str(previous["prediction_id"])
                    if previous.get("prediction_id") is not None
                    else None
                ),
                state_after_ref="state." + _canonical_hash(
                    {"values": dict(sorted(sensorimotor_body_state.items()))}
                )[:24],
                observed_effect_id=observed_effect_id,
                prediction_error=prediction_error,
                physiological_delta_ref=None,
            )
            causal = self._causal_evidence.observe(transition)
            self._sensorimotor_model.observe(causal)
            if observed_effect is not None:
                self._effect_by_commitment[
                    transition.commitment_id
                ] = observed_effect.effect_id

            if transition.competence_id is not None and observed_effect is not None:
                self._body_schema.observe_sensorimotor_evidence(
                    competence_id=transition.competence_id,
                    effect_id=observed_effect.effect_id,
                    tick=tick,
                )
                competence = self._competence_library.get(transition.competence_id)
                if competence is not None:
                    current_surface = self._current_surface_fingerprint()
                    control_estimate = self._controllability_model.update_from_ledger(
                        self._causal_evidence,
                        effect_id=observed_effect.effect_id,
                        competence_id=transition.competence_id,
                        context_id=transition.context_ref,
                        tick=tick,
                    )
                    if competence.effect_id is None:
                        competence.effect_id = observed_effect.effect_id
                    if current_surface is not None:
                        self._competence_execution_bindings.bind_from_evidence(
                            competence_id=transition.competence_id,
                            surface_fingerprint=current_surface,
                            effect_id=observed_effect.effect_id,
                            evidence_refs=(causal.evidence_id,),
                            reliability=control_estimate.reliability,
                            controllability=max(
                                control_estimate.confidence,
                                competence.evidence.controllability,
                            ),
                            tick=tick,
                        )
                    self._agency_model.update_from_ledger(
                        self._causal_evidence,
                        effect_id=observed_effect.effect_id,
                        competence_id=transition.competence_id,
                        context_id=transition.context_ref,
                        tick=tick,
                        prediction_match=(
                            None
                            if prediction_error is None
                            else 1.0 - prediction_error.magnitude
                        ),
                    )

                    # Embodiment v2 body-boundary inference is reconstructed
                    # from organism-owned causal effects and agency only.
                    # Controllability alone never makes a channel part of Body.
                    observed_features = {
                        feature
                        for effect in self._effect_space.effects
                        for feature in effect.feature_refs
                    }
                    self_caused_features: set[str] = set()
                    for estimate in self._agency_model.estimates:
                        if estimate.confidence < 0.35:
                            continue
                        agentic_effect = self._effect_space.get(
                            estimate.effect_id
                        )
                        if agentic_effect is not None:
                            self_caused_features.update(
                                agentic_effect.feature_refs
                            )
                    if observed_features:
                        self._body_schema.observe_agency_boundary(
                            observed_channels=observed_features,
                            self_caused_channels=self_caused_features,
                            # Somatic membership requires independent evidence;
                            # correlation/controllability is not sufficient.
                            somatic_correlated_channels=(),
                            prediction_error=(
                                prediction_error.magnitude
                                if prediction_error is not None
                                else 0.0
                            ),
                        )
            self._last_sensorimotor_transition = transition
            self._pending_sensorimotor_transition = None

        homeostatic_baseline = self._homeostasis.deviation()
        reactive_state = self._innate_reactivity.evaluate(
            percepts=baseline,
            homeostatic_deviation=homeostatic_baseline,
        )
        self._last_reactive_state = reactive_state
        if self._pending_reactive_credit is not None:
            signature, primitive_id, pressure_before = self._pending_reactive_credit
            self._reactive_memory.observe(
                signature=signature,
                primitive_id=primitive_id,
                relief=pressure_before - homeostatic_baseline,
            )
            self._pending_reactive_credit = None
        active_concepts = (
            tuple(sorted(getattr(cognition, "active_concept_ids", ())))
            if cognition is not None
            else ()
        )

        # A competence may have crossed its evidence gate on the previous
        # natural exploration window. By this tick its readout can have been
        # admitted normally; record the causal context without scheduling or
        # forcing any replay.
        if (
            cognition is not None
            and self._cognitive_bridge is not None
            and self._sensorimotor_learner is not None
        ):
            for primitive_id in self._sensorimotor_learner.last_natural_competence_ids:
                self._cognitive_bridge.observe_primitive_execution(
                    primitive_id,
                    concept_ids=active_concepts,
                    tick=tick,
                )

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

        self._last_action_source = "none"
        intents: tuple[MotorIntent, ...] = ()
        pending: list[tuple[str, float, dict[str, float] | None]] = []
        primitive_selected_now = False

        if self._sensorimotor_learner is None:
            raise RuntimeError("actuation requires sensorimotor learner")

        # Advance an internal composed controller or close one completed
        # competence before opening deliberation again.
        self._advance_or_complete_competence(tick=tick)

        self._refresh_competence_library()
        candidate_ids = tuple(
            competence.competence_id
            for competence in self._competence_library.items
            if self._competence_is_executable(competence)
        )
        proposals: list[ActionProposal] = []

        # Innate reactivity contributes urgency and a learned response candidate;
        # it never writes a motor command itself.
        reactive_candidate = self._reactive_memory.best(
            signature=reactive_state.signature,
            candidates=candidate_ids,
        )
        if reactive_state.withdrawal >= 0.55 and reactive_candidate is not None:
            proposal_id = "proposal." + hashlib.sha256(
                f"{self._organism_id}:{tick}:protection:{reactive_candidate}".encode("utf-8")
            ).hexdigest()[:24]
            proposals.append(
                ActionProposal(
                    proposal_id=proposal_id,
                    source=ActionSource.PROTECTION,
                    effect_target_id=None,
                    competence_id=reactive_candidate,
                    justification=ActionJustification(
                        originating_need_id=f"internal.{reactive_state.signature}",
                        competence_id=reactive_candidate,
                    ),
                    evaluation=ActionEvaluation(
                        homeostatic_relevance=reactive_state.withdrawal,
                        protective_relevance=reactive_state.withdrawal,
                        effect_confidence=min(1.0, reactive_state.withdrawal),
                        uncertainty=max(0.0, 1.0 - reactive_state.withdrawal),
                    ),
                )
            )

        # Prospective agency proposes an already acquired competence.  It does
        # not activate it; final ownership belongs to the universal arbitrator.
        prospective_id: str | None = None
        if cognition is not None and candidate_ids:
            prospective_id = self._choose_acquired_competence(
                cognition=cognition,
                percepts=percepts,
                candidate_ids=candidate_ids,
                signal_references=signal_references or {},
                tick=tick,
            )
        if prospective_id is not None and prospective_id in candidate_ids:
            proposal_id = "proposal." + hashlib.sha256(
                f"{self._organism_id}:{tick}:prospection:{prospective_id}".encode("utf-8")
            ).hexdigest()[:24]
            proposals.append(
                ActionProposal(
                    proposal_id=proposal_id,
                    source=ActionSource.PROSPECTION,
                    effect_target_id=None,
                    competence_id=prospective_id,
                    justification=ActionJustification(
                        competence_id=prospective_id,
                    ),
                    evaluation=ActionEvaluation(
                        effect_confidence=0.75,
                        controllability=0.75,
                        uncertainty=0.25,
                    ),
                )
            )

        # Cognitive motor reuse is competence-level only.  The historical
        # cognition->individual-actuator path is intentionally gone.
        if cognition is not None and candidate_ids:
            primitive_readouts = cognition.readouts_for_family("primitive")
            for primitive_id in candidate_ids:
                raw = primitive_readouts.get(primitive_id)
                if (
                    isinstance(raw, (int, float))
                    and not isinstance(raw, bool)
                    and math.isfinite(float(raw))
                    and float(raw) >= self._motor_intent_selector.selection_threshold
                ):
                    strength = max(0.0, min(1.0, float(raw)))
                    proposal_id = "proposal." + hashlib.sha256(
                        f"{self._organism_id}:{tick}:competence:{primitive_id}".encode("utf-8")
                    ).hexdigest()[:24]
                    proposals.append(
                        ActionProposal(
                            proposal_id=proposal_id,
                            source=ActionSource.COMPETENCE,
                            effect_target_id=None,
                            competence_id=primitive_id,
                            justification=ActionJustification(
                                competence_id=primitive_id,
                            ),
                            evaluation=ActionEvaluation(
                                effect_confidence=strength,
                                controllability=strength,
                                uncertainty=1.0 - strength,
                            ),
                        )
                    )

        # Exploration is permanently available, but its pressure is organism
        # owned and can become very small.  There is no developmental mode.
        exploration_drive = (
            self._gene_expression_state.exploration_drive
            if self._gene_expression_state is not None
            else 0.25
        )
        exploration_drive = max(0.0, min(1.0, float(exploration_drive)))
        ranked_exploration = self._rank_exploration_opportunities(
            exploration_drive=exploration_drive,
            reactive_state=reactive_state,
        )
        if exploration_drive > 0.0 and ranked_exploration:
            preferred_id = ranked_exploration[0]
            signals = self._last_exploration_signals[preferred_id]
            proposal_id = "proposal." + hashlib.sha256(
                f"{self._organism_id}:{tick}:exploration:{preferred_id}".encode("utf-8")
            ).hexdigest()[:24]
            proposals.append(
                ActionProposal(
                    proposal_id=proposal_id,
                    source=ActionSource.EXPLORATION,
                    effect_target_id=None,
                    competence_id=None,
                    justification=ActionJustification(
                        originating_need_id="internal.sensorimotor-uncertainty",
                        evidence_refs=(f"channel.{preferred_id}",),
                    ),
                    evaluation=ActionEvaluation(
                        epistemic_relevance=max(
                            exploration_drive,
                            max(0.0, signals.learning_progress),
                        ),
                        effect_confidence=(
                            signals.controllability_potential
                            if signals.controllability_potential is not None
                            else 0.0
                        ),
                        controllability=signals.controllability_potential,
                        uncertainty=max(0.0, min(1.0, signals.uncertainty)),
                        estimated_cost=signals.physiological_cost,
                        estimated_risk=signals.risk,
                    ),
                )
            )

        decision = self._action_arbitrator.choose(
            proposals=tuple(proposals),
            current=self._active_action_commitment,
            tick=tick,
        )

        selected = decision.proposal
        if selected is not None:
            if self._active_action_commitment is not None and self._active_action_commitment.active:
                self._active_action_commitment.terminate(
                    tick=tick,
                    status=CommitmentStatus.INTERRUPTED,
                    reason=decision.reason,
                )
                self._sensorimotor_learner.interrupt_active_competence()
                self._active_composition_children = ()
                self._active_composition_index = 0

            controller_id = (
                f"controller.{selected.competence_id}"
                if selected.competence_id is not None
                else "controller.sensorimotor-exploration"
            )
            commitment_id = "commitment." + hashlib.sha256(
                f"{selected.proposal_id}:{tick}".encode("utf-8")
            ).hexdigest()[:24]
            self._last_action_proposal = selected
            self._active_exploration_preference = (
                ranked_exploration
                if selected.source is ActionSource.EXPLORATION
                else ()
            )
            self._active_action_commitment = ActionCommitment(
                commitment_id=commitment_id,
                proposal_id=selected.proposal_id,
                effect_target_id=selected.effect_target_id,
                competence_id=selected.competence_id,
                started_tick=tick,
                controller_id=controller_id,
                surface_fingerprint=(
                    self._actuator_constitution.contract_fingerprint
                    if self._actuator_constitution is not None
                    else None
                ),
                maximum_duration=(8 if selected.source is ActionSource.EXPLORATION else None),
            )

            if selected.competence_id is not None:
                if self._activate_competence_controller(selected.competence_id):
                    primitive_selected_now = True
                    intents = self._sensorimotor_learner.motor_intents(tick)
                    self._last_executed_primitive_id = (
                        self._sensorimotor_learner.last_output_primitive_id
                    )
                else:
                    self._active_action_commitment.terminate(
                        tick=tick,
                        status=CommitmentStatus.FAILED,
                        reason="competence_controller_unavailable",
                    )
                    intents = ()
            else:
                intents = self._sensorimotor_learner.motor_intents(
                    tick,
                    exploration_preference=self._active_exploration_preference,
                )

            self._last_action_source = selected.source.value

        elif decision.keep_current and self._active_action_commitment is not None:
            source_value = "competence" if self._active_action_commitment.competence_id else "exploration"
            if self._last_action_proposal is not None:
                source_value = self._last_action_proposal.source.value
            if self._active_action_commitment.competence_id is not None:
                if self._sensorimotor_learner.active_primitive_id is not None:
                    intents = self._sensorimotor_learner.motor_intents(tick)
                    self._last_executed_primitive_id = (
                        self._sensorimotor_learner.last_output_primitive_id
                    )
            else:
                intents = self._sensorimotor_learner.motor_intents(
                    tick,
                    exploration_preference=self._active_exploration_preference,
                )
            self._last_action_source = source_value

        if self._last_action_source == "exploration" and len(intents) == 1:
            isolated = intents[0]
            pending.append(
                (
                    isolated.actuator_id,
                    float(isolated.activation),
                    baseline,
                )
            )

        if self._sensorimotor_learner is not None and intents:
            intents = self._sensorimotor_learner.constrain_intents(intents)
            surviving_ids = {intent.actuator_id for intent in intents}
            pending = [item for item in pending if item[0] in surviving_ids]

        activity_scale = self._homeostasis.activity_scale
        if activity_scale < 1.0:
            intents = tuple(
                MotorIntent(
                    actuator_id=intent.actuator_id,
                    activation=float(intent.activation) * activity_scale,
                )
                for intent in intents
            )
            pending = [
                (
                    actuator_id,
                    float(activation) * activity_scale,
                    before,
                )
                for actuator_id, activation, before in pending
            ]

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

        # Low-level feedback/control commands inherit the selected commitment;
        # they are not new deliberative actions.
        if self._active_action_commitment is None or not self._active_action_commitment.active:
            raise RuntimeError("motor output has no active organism-owned commitment")
        self._last_motor_command = MotorCommand(
            commitment_id=self._active_action_commitment.commitment_id,
            controller_id=self._active_action_commitment.controller_id,
            competence_id=self._active_action_commitment.competence_id,
            channels=tuple(
                (intent.actuator_id, float(intent.activation))
                for intent in intents
            ),
        )

        actuations: list[Actuation] = []
        proprioception: dict[str, float] = {}
        if self._actuator_constitution is None:
            raise RuntimeError("actuation enabled without actuator surface")
        for intent in intents:
            actuation = self._actuator_system.execute(
                intent,
                self._actuator_constitution,
            )
            actuations.append(actuation)
            aid = actuation.actuator_id
            proprioception.update({
                f"motor.requested_activation.{aid}": actuation.requested,
                f"motor.delivered_activation.{aid}": actuation.delivered,
            })

        self._last_motor_intents = tuple(intents)
        self._last_actuations = tuple(actuations)
        self._last_motor_intent = self._last_motor_intents[0]
        self._last_actuation = self._last_actuations[0]
        self._pending_proprioception = proprioception

        if self._last_motor_command is not None and self._active_action_commitment is not None:
            context_ref = "context." + hashlib.sha256(
                (
                    (
                        self._actuator_constitution.contract_fingerprint
                        if self._actuator_constitution is not None
                        else "no-surface"
                    )
                    + "|"
                    + ("|".join(active_concepts) or "opaque")
                ).encode("utf-8")
            ).hexdigest()[:24]
            prediction = (
                self._sensorimotor_model.predict(
                    competence_id=self._active_action_commitment.competence_id,
                    context_id=context_ref,
                )
                if self._active_action_commitment.competence_id is not None
                else None
            )
            command_payload = {
                "channels": [
                    [actuator_id, activation]
                    for actuator_id, activation in self._last_motor_command.channels
                ]
            }
            actuation_payload = {
                "delivered": [
                    [item.actuator_id, float(item.delivered)]
                    for item in self._last_actuations
                ]
            }
            self._pending_sensorimotor_transition = {
                "tick": tick,
                "commitment_id": self._active_action_commitment.commitment_id,
                "controller_id": self._active_action_commitment.controller_id,
                "competence_id": self._active_action_commitment.competence_id,
                "context_ref": context_ref,
                "prediction_id": (
                    prediction.prediction_id if prediction is not None else None
                ),
                "predicted_effect_id": (
                    prediction.effect_id if prediction is not None else None
                ),
                "prediction_confidence": (
                    prediction.confidence if prediction is not None else 0.0
                ),
                "state_before": dict(sensorimotor_body_state),
                "state_before_ref": "state." + _canonical_hash(
                    {"values": dict(sorted(sensorimotor_body_state.items()))}
                )[:24],
                "motor_command_ref": "command." + _canonical_hash(command_payload)[:24],
                "actuation_ref": "actuation." + _canonical_hash(actuation_payload)[:24],
            }

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
            self._schedule_homeostatic_action_credit(
                family="primitive",
                action_id=self._last_executed_primitive_id,
                concept_ids=active_concepts,
                baseline_error=homeostatic_baseline,
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
                discovery_eligible=(self._last_executed_primitive_id is None),
                execution_primitive_id=self._last_executed_primitive_id,
            )

            # Natural recurrence is the missing non-circular path from a
            # learned bodily competence into cognition. No scheduler asks for
            # this movement: it must have just occurred in ordinary behavior.
            if cognition is not None and self._cognitive_bridge is not None:
                for primitive_id in self._sensorimotor_learner.last_natural_competence_ids:
                    self._cognitive_bridge.observe_primitive_execution(
                        primitive_id,
                        concept_ids=active_concepts,
                        tick=tick,
                    )
                    self._schedule_homeostatic_action_credit(
                        family="primitive",
                        action_id=primitive_id,
                        concept_ids=active_concepts,
                        baseline_error=homeostatic_baseline,
                        tick=tick,
                    )


    @property
    def last_action_source(self) -> str:
        """Passive provenance of the current organism-owned action commitment."""
        return self._last_action_source

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
            "social_exchange_quantum": self._social_exchange_quantum,
            "social_exchange_cost": self._social_exchange_cost,
            "resting_requested": self._resting_requested,
            "interoception_enabled": self._interoception_enabled,
            "interoception_mode": self._interoception_mode,
            "mutation_seed": self._mutation_seed,
            "epigenetic_decay": self._epigenetic_decay,
            "actuation_enabled": self._actuation_enabled,
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
        from symbiont.core.foundation.fingerprint import generate_runtime_fingerprint_from_runtime
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
    def sensorimotor_effect_model(self) -> CompetenceEffectModel:
        """Current embodiment's abstract competence -> effect model."""
        return self._sensorimotor_model

    @property
    def causal_evidence_ledger(self) -> CausalEvidenceLedger:
        """Current embodiment factual sensorimotor evidence ledger."""
        return self._causal_evidence

    @property
    def controllability_model(self) -> ControllabilityModel:
        return self._controllability_model

    @property
    def agency_model(self) -> AgencyModel:
        return self._agency_model

    @property
    def competence_library(self) -> CompetenceLibrary:
        return self._competence_library
    
    @property
    def competence_execution_bindings(self) -> CompetenceExecutionBindingRegistry:
        return self._competence_execution_bindings

    def _current_surface_fingerprint(self) -> str | None:
        return (
            self._actuator_constitution.contract_fingerprint
            if self._actuator_constitution is not None
            else None
        )

    def _competence_is_executable(self, competence: MotorCompetence) -> bool:
        return self._competence_execution_bindings.is_executable(
            competence,
            surface_fingerprint=self._current_surface_fingerprint(),
        )
    
    @property
    def evidence_ledger(self) -> EvidenceRevisionLedger:
        return self._evidence_ledger

    @property
    def genome(self) -> Genome | None:
        return self._genome

    @property
    def heritable_genome(self) -> None:
        """Legacy surface: Genome v2 is the only operative genetic state."""
        return None

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

    def _next_heritable_genome(self) -> Genome | None:
        """Create the next genotype through the single typed Genome v2 path."""
        if self._genome is None:
            return None
        return mutate_genome(
            self._genome,
            seed=self._mutation_seed + self._generation + 1,
        )

    def _child_genome(self, inherited: Genome) -> Genome:
        return inherited

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

    @property
    def ontogeny(self) -> OntogenyController:
        return self._ontogeny

    @property
    def reproductively_ready(self) -> bool:
        """Physical readiness derived only from canonical body state."""
        return self._ontogeny.reproductively_ready()

    def materialize_clonal_bud(self) -> "OrganismRuntime | None":
        """Materialize one asexual descendant from conserved parental energy.

        Readiness is purely physiological.  No cognitive topology, learned
        competence, blocked growth, reward or evaluator score participates.
        World/habitat authority may deny materialization, but cannot create
        readiness.
        """
        if (
            self._birth_authority is None
            or self._genome is None
            or not self._ontogeny.reproductively_ready()
            or not self._birth_surfaces_available()
        ):
            return None

        inherited = self._next_heritable_genome()
        child_genome_id = (
            inherited.genome_id if inherited is not None else self._genome.genome_id
        )
        record = self._birth_authority.birth(
            genome_id=child_genome_id,
            parent_ids=(self._organism_id,),
            generation=self._generation + 1,
        )
        if record is None:
            return None

        birth_energy = self._ontogeny.reproduction_energy()
        child_genome = (
            self._child_genome(inherited) if inherited is not None else self._genome
        )
        child_state = LivingBodyState(
            energy_reserve=birth_energy,
            max_energy=self._living_body_state.max_energy,
            growth_progress=0.0,
            senescence=0.0,
        )
        parent_metabolism = self._metabolism.snapshot()
        parent_metabolism_checkpoint = self._metabolism.checkpoint()
        child_metabolism = MetabolicLedger(
            capacity=dict(parent_metabolism.capacity),
            replenishment=dict(parent_metabolism_checkpoint["replenishment"]),
            physiology_config=self._physiology_config,
            body_state=child_state,
        )
        graph = load_base_graph(kernel_limits=self._kernel_limits)

        try:
            child = OrganismRuntime(
                attention_budget=self._attention_budget,
                investigate_ticks=self._investigate_ticks,
                conflict_z=self._conflict_z,
                min_samples=self._min_samples,
                discover_senses=self._discover_senses,
                bootstrap_semantic_senses=self._bootstrap_semantic_senses,
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
                metabolism=child_metabolism,
                living_body_state=child_state,
                organism_id=record.organism_id,
                birth_authority=self._birth_authority,
                generation=record.generation,
                social_habitat=None,
                resource_habitats=self._resource_habitats,
                explicit_metabolism=self._explicit_metabolism,
                social_exchange_quantum=self._social_exchange_quantum,
                social_exchange_cost=self._social_exchange_cost,
                interoception_enabled=self._interoception_enabled,
                interoception_mode=self._interoception_mode,
                actuation_enabled=self._actuation_enabled,
                motor_intent_selector=(
                    MotorIntentSelector(
                        selection_threshold=self._motor_intent_selector.selection_threshold
                    )
                    if self._actuation_enabled and self._motor_intent_selector is not None
                    else None
                ),
            )
        except Exception:
            self._birth_authority.death(record.organism_id)
            raise

        # Conservation boundary: the child's initial physical energy is exactly
        # the energy removed from the parent.  No birth-energy minting.
        self._metabolism.charge("maintenance", birth_energy)

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
        """Queue a scalar physical-work cost for the next physiology tick.

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
        accumulated = self._pending_embodied_work + float(amount)
        if not math.isfinite(accumulated):
            raise ValueError("embodied work accumulation overflowed")
        self._pending_embodied_work = accumulated

    def absorb_metabolic_energy(self, amount: float) -> float:
        """Absorb anonymous physical energy into the one conserved body pool."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot absorb metabolic energy")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
            raise ValueError("absorbed metabolic energy must be finite")
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("absorbed metabolic energy must be non-negative")
        return self._metabolism.intake_untyped(amount)

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
        # Physical body headroom is authoritative. The requested accounting
        # kind may receive bookkeeping credit, but it cannot gate or create
        # physical energy.
        available = max(
            0.0,
            self._living_body_state.max_energy
            - self._living_body_state.energy_reserve,
        )
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

    @property
    def homeostatic_deviation(self) -> float:
        """Passive scalar disequilibrium for observability, never evaluator control."""
        return self._homeostasis.deviation()

    @property
    def pending_homeostatic_credit_count(self) -> int:
        """Number of live delayed action-credit traces."""
        return len(self._pending_homeostatic_action_credit)

    def _birth_surfaces_available(self) -> bool:
        """Preflight external carrying-capacity surfaces only.

        Physical birth energy is transferred from the parent. Shared habitat
        resource quantities are not a second reproductive currency.
        """
        surfaces = list(self._resource_habitats.values())
        if self._habitat is not None:
            surfaces.append(self._habitat)
        return all(
            surface.snapshot().population < surface.capacity
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


    def apply_environmental_damage(self, amount: float) -> float:
        """Apply a bounded physical perturbation from the supplied habitat.

        This is deliberately not a controller or evaluator command: it only
        changes local integrity. Subsequent repair is constitutive body
        homeostasis and must pay its maintenance cost.
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
            current_ratio = self._living_body_state.energy_reserve / max(
                self._living_body_state.max_energy,
                1e-12,
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
            from ...host.providers.interoception import InteroceptionProvider
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
        # NOTE(legacy): Legacy mode retains the historical capability allocation exactly.
        # Adaptive mode allocates cognition among the percepts produced by
        # already-acquired sources; it cannot cause a new host read.
        perceptual_allocations: tuple[AttentionAllocation, ...] = ()
        if self._sensory_system.plasticity_enabled:
            allocated_sources = {
                allocation.name for allocation in allocations
            } | {reading.capability_id for reading in resource_readings}
            available_percepts = {percept.name for percept in percepts if percept.value is not None}
            perceptual_candidates: list[AttentionCandidate] = []
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
                perceptual_candidates.append(AttentionCandidate(
                    name=sensor.cognitive_name,
                    uncertainty=uncertainty,
                    cost=1.0,
                    rank_cost=max(
                        0.10,
                        (1.0 + sensor.transduction_cost * 10.0) / utility_factor,
                    ),
                    observations=sensor.utility_observations,
                ))
            if perceptual_candidates:
                # Preserve the number of cognitive slots made available by
                # source attention while allowing competing receptors over the
                # same source to occupy those slots.
                perceptual_allocations = AttentionBudget(
                    budget=max(1.0, float(len(allocations)))
                ).allocate(perceptual_candidates)
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

        current_signal_references = {
            **{
                name: self._signal_identity.signal_id(capability_id)
                for capability_id, name in percept_names.items()
            },
            **{
                percept.name: self._signal_identity.signal_id(sensor.source_ids[0])
                for percept in percepts
                if (sensor := sensor_by_cognitive_name.get(percept.name)) is not None
                and len(sensor.source_ids) == 1
            },
        }

        self._motor_step(
            cognition_result,
            percepts,
            tick=self._tick_count + 1,
            signal_references=current_signal_references,
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
            investigation_candidates: list[str] = []
            for percept_name, obs in drift_observations.items():
                if obs.kind.value == "regime_shift":
                    cap_id = capability_by_percept_name.get(percept_name)
                    if cap_id and cap_id in selected_ids and snapshot.manifest.supports(cap_id):
                        investigation_candidates.append(cap_id)
            for allocation in allocations:
                if allocation.name not in investigation_candidates:
                    investigation_candidates.append(allocation.name)

            for candidate in investigation_candidates:
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
        # Computed once and reused for RuntimeTickResult.sensory_phenotype
        # below -- nothing mutates sensory_system state in between.
        sensory_phenotype_view = self._sensory_phenotype_view()
        if self._sensory_system.plasticity_enabled:
            self._body_schema.observe_sensory_phenotype(
                sensory_phenotype_view,
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
        embodied_work = self._pending_embodied_work
        retained_units += embodied_work
        self._pending_embodied_work = 0.0
        metabolism_snapshot = self._metabolism.advance(retained_units=retained_units)
        repaired_amount = self._homeostasis.constitutive_step(
            self._metabolism,
            embodied_work=embodied_work,
            resting=self._resting_requested,
        )
        ontogeny_snapshot = self._ontogeny.constitutive_step(
            self._metabolism,
            resting=self._resting_requested,
        )
        metabolism_snapshot = self._metabolism.finalize_cycle(metabolism_snapshot)
        homeostatic_snapshot = self._homeostasis.regulate(metabolism_snapshot.pressure)
        if metabolism_snapshot.pressure.value in ("severe", "unrecoverable"):
            self._resting_requested = True
        elif (metabolism_snapshot.pressure.value == "normal" and self._resting_requested
              and (action_result is None or action_result.action_id != "rest")):
            self._resting_requested = False
        resting_for_tick = self._resting_requested
        physiology_snapshot = self._physiology.advance(
            metabolism_snapshot, tick=self._living_body_state.age_ticks,
            resting=resting_for_tick or homeostatic_snapshot.action.value in ("pause_plasticity", "safe_mode"),
        )
        self._resolve_homeostatic_action_credit(tick=self._tick_count + 1)
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
            repaired=repaired_amount > 0.0,
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
            metabolic_ratio = self._living_body_state.energy_reserve / max(
                1e-9,
                self._living_body_state.max_energy,
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
            # Canonical core names no action kind here (High E): the raw,
            # opaque action_id is already a passive Observatory display
            # field via RuntimeTickResult.action_result. Re-deriving a
            # semantic category (rest/interaction/reproduction/...) from it
            # would be reconstructing the removed typed action vocabulary
            # inside cognition-adjacent core code.
            runtime_events.append("action_executed")
        if current_state == "dead":
            runtime_events.extend(("death", "resource_release"))
        self._last_runtime_vital_state = current_state
        self._last_runtime_development_phase = current_phase

        # Evidence from tick t regulates the operating phenotype for t+1.
        self._update_gene_expression(
            cognition=cognition_result,
            drift_observations=drift_observations,
            metabolic_pressure=metabolism_snapshot.pressure.value,
        )

        self._tick_count += 1
        self._living_body_state.advance_age()
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
            signal_knowledge=knowledge_view,
            knowledge_events=self._signal_knowledge.drain_events(),
            signal_references=current_signal_references,
            metabolism=metabolism_snapshot,
            assimilation=tuple(assimilation),
            homeostasis=homeostatic_snapshot,
            physiology=physiology_snapshot,
            ontogeny=ontogeny_snapshot,
            degradation_excreted=degradation_excreted,
            retained_items=len(self._degradation.items),
            action_result=action_result,
            development=development_snapshot,
            sensory_phenotype=sensory_phenotype_view,
            runtime_events=tuple(dict.fromkeys(runtime_events)),
            motor_intent=self._last_motor_intent,
            actuation=self._last_actuation,
            motor_intents=self._last_motor_intents,
            actuations=self._last_actuations,
            action_commitment=self._active_action_commitment,
            motor_command=self._last_motor_command,
            sensorimotor_transition=self._last_sensorimotor_transition,
            sensorimotor_v2=self._sensorimotor_v2_snapshot(),
            gene_expression=(
                self._gene_expression_state.as_dict()
                if self._gene_expression_state is not None
                else None
            ),
        )

    def run(self, ticks: int) -> tuple[RuntimeTickResult, ...]:
        if ticks < 1:
            raise ValueError("ticks must be at least 1")
        return tuple(self.tick() for _ in range(ticks))

    def _build_checkpoint_payload(self) -> dict[str, Any]:
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
        payload["gene_expression"] = (
            self._gene_expression_state.as_dict()
            if self._gene_expression_state is not None
            else None
        )
        payload["heritable_genome"] = None
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
                "contract_fingerprint": self._actuator_constitution.contract_fingerprint,
                "slots": [
                    {
                        "slot_id": slot.slot_id,
                        "actuator_id": slot.actuator_id,
                        "command_min": slot.command_min,
                        "command_max": slot.command_max,
                        "neutral": slot.neutral,
                        "available": slot.available,
                    }
                    for slot in self._actuator_constitution.slots
                ],
            }
            pending_motor = [
                {
                    "actuator_id": actuator_id,
                    "activation": activation,
                }
                for actuator_id, activation, _baseline
                in self._pending_motor_observation
            ]
            payload["actuation"] = {
                "enabled": True,
                "constitution": constitution_payload,
                "proposer": export_actuation_state(self._actuator_proposer),
                "selection_threshold": (
                    self._motor_intent_selector.selection_threshold
                    if self._motor_intent_selector is not None
                    else 0.1
                ),
                "pending_motor_observation": pending_motor,
                "pending_proprioception": dict(sorted(self._pending_proprioception.items())),
                "sensorimotor": (
                    self._sensorimotor_learner.checkpoint()
                    if self._sensorimotor_learner is not None
                    else None
                ),
                "last_executed_primitive_id": self._last_executed_primitive_id,
                "action_commitment": (
                    self._active_action_commitment.checkpoint()
                    if self._active_action_commitment is not None
                    else None
                ),
                "sensorimotor_v2": {
                    "schema_version": 2,
                    "surface_binding": {
                        "contract_fingerprint": self._actuator_constitution.contract_fingerprint,
                        "known_channel_ids": list(self._actuator_constitution.actuator_ids),
                    },
                    "effect_space": self._effect_space.checkpoint(),
                    "causal_evidence": self._causal_evidence.checkpoint(),
                    "exploration": {
                        "strength_memory": dict(
                            sorted(self._exploration_strength_memory.items())
                        ),
                        "active_preference": list(
                            self._active_exploration_preference
                        ),
                    },
                    "competences": [
                        {
                            "competence_id": item.competence_id,
                            "controller_id": item.controller_id,
                            "effect_id": item.effect_id,
                            "controller_strategy_ref": item.controller_strategy_ref,
                            "parent_competence_ids": list(
                                item.parent_competence_ids
                            ),
                            "support": item.evidence.support,
                            "failures": item.evidence.failures,
                            "reproducibility": item.evidence.reproducibility,
                            "controllability": item.evidence.controllability,
                            "directional_consistency": item.evidence.directional_consistency,
                        }
                        for item in self._competence_library.items
                    ],
                    "execution_bindings": self._competence_execution_bindings.checkpoint(),
                    "composition": {
                        "engine": self._composition_engine.checkpoint(),
                        "predecessor_id": self._composition_predecessor_id,
                        "active_children": list(
                            self._active_composition_children
                        ),
                        "active_index": self._active_composition_index,
                    },
                },
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
        payload["innate_reactivity"] = {
            "schema_version": 1,
            "reactivity": self._innate_reactivity.checkpoint(),
            "memory": self._reactive_memory.checkpoint(),
        }
        payload["physiology"] = self._physiology.checkpoint()
        payload["social_ledger"] = self._social_ledger.checkpoint()
        payload["social_resource_ledger"] = self._social_resource_ledger.checkpoint()
        payload["source_trust"] = self._source_trust.export_checkpoint()
        payload["generation"] = self._generation
        payload["social_exchange_quantum"] = self._social_exchange_quantum
        payload["social_exchange_cost"] = self._social_exchange_cost
        payload["resting_requested"] = self._resting_requested
        payload["pending_embodied_work"] = self._pending_embodied_work
        payload["degradation"] = self._degradation.checkpoint()
        payload["narrative_journal"] = list(self._narrative_journal[-50:])
        payload["development"] = self._developmental_tracker.checkpoint()
        payload["last_runtime_vital_state"] = self._last_runtime_vital_state
        payload["last_runtime_development_phase"] = self._last_runtime_development_phase
        payload["first_life_history_events"] = {
            "sense": self._first_sense_emitted,
            "concept": self._first_concept_emitted,
            "prediction": self._first_prediction_emitted,
        }

        from ... import __version__ as _symbiont_version

        genome_data = payload.get("genome")
        payload["constitution_fingerprint"] = {
            "schema_version": 1,
            "genome_hash": _canonical_hash(cast(dict[str, Any], genome_data)) if genome_data is not None else None,
        }
        payload["runtime_provenance"] = {
            "software_version": _symbiont_version,
            "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        }
        return payload

    def state_hash(self) -> str:
        """Content hash of current organism state (spec: save/load neutrality).

        Excludes ``checkpoint_lineage`` (which records save *events*, not
        state) and ``runtime_provenance`` (which records what code produced
        the save, not what the organism is). A read-only query: unlike
        ``checkpoint()``, it never advances ``checkpoint_lineage``.
        """
        return _state_hash_of(self._build_checkpoint_payload())

    def checkpoint(self) -> dict[str, Any]:
        payload = self._build_checkpoint_payload()
        state_hash = _state_hash_of(payload)
        payload["checkpoint_lineage"] = {
            "checkpoint_id": state_hash,
            "parent_checkpoint_hash": self._last_checkpoint_hash,
        }
        self._last_checkpoint_hash = state_hash
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
        actuator_constitution_override = kwargs.pop(
            "actuator_constitution_override",
            None,
        )
        if (
            actuator_constitution_override is not None
            and not isinstance(actuator_constitution_override, ActuatorSurface)
        ):
            raise CheckpointError(
                "actuator_constitution_override must be an ActuatorSurface"
            )
        fingerprint_migration: tuple[str, str] | None = None
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
        from ... import __version__ as _symbiont_version

        kernel_limits = kwargs.get("kernel_limits") or KernelLimits()
        genome = restore_genome_checkpoint(
            normalized.get("genome"),
            kernel_limits=kernel_limits,
            running_version=_parse_running_version(_symbiont_version),
        )

        raw_heritable = normalized.get("heritable_genome")
        if genome is not None and raw_heritable not in (None, {}):
            if not isinstance(raw_heritable, dict):
                raise CheckpointError("invalid legacy HeritableGenome checkpoint")
            try:
                genome = apply_legacy_heritable_payload(
                    genome,
                    raw_heritable,
                    kernel_limits=kernel_limits,
                )
            except ValueError as exc:
                raise CheckpointError(
                    f"invalid legacy HeritableGenome checkpoint: {exc}"
                ) from exc
        heritable_genome = None

        gene_expression_state = None
        raw_expression = normalized.get("gene_expression")
        if genome is not None:
            if raw_expression is None:
                gene_expression_state = GeneExpressionState.from_genome(genome)
            else:
                if not isinstance(raw_expression, dict):
                    raise CheckpointError("invalid gene expression checkpoint")
                try:
                    from ...genetics.expression import restore_expression_state
                    gene_expression_state = restore_expression_state(
                        raw_expression,
                        genome,
                    )
                except ValueError as exc:
                    raise CheckpointError(
                        f"invalid gene expression checkpoint: {exc}"
                    ) from exc
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
        motor_intent_selector = None
        sensorimotor_learner = None
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
            raw_mode = raw_actuation.get("exploration_mode")
            if raw_mode == "structured_probe":
                raise CheckpointError(
                    "checkpoint carries removed scheduled motor probing state"
                )
            # Legacy spontaneous/exploration mode is read only for migration;
            # Sensorimotor v2 has no runtime motor mode.
            if enabled:
                raw_constitution = raw_actuation.get("constitution")
                if not isinstance(raw_constitution, dict):
                    raise CheckpointError("actuation constitution is missing")
                raw_slots = raw_constitution.get("slots")
                if not isinstance(raw_slots, list):
                    raise CheckpointError("actuation constitution slots must be a list")
                try:
                    channels = tuple(
                        ActuatorChannel(
                            slot_id=str(item["slot_id"]),
                            actuator_id=str(item["actuator_id"]),
                            command_min=float(item.get("command_min", 0.0)),
                            command_max=float(item.get("command_max", 1.0)),
                            neutral=float(item.get("neutral", 0.0)),
                            available=bool(item.get("available", True)),
                        )
                        for item in raw_slots
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CheckpointError(f"invalid body-owned actuator constitution: {exc}") from exc
                stored_fingerprint = raw_constitution.get("contract_fingerprint")
                if stored_fingerprint is None:
                    legacy_material = {
                        "slots": raw_slots,
                    }
                    fingerprint_material = json.dumps(
                        legacy_material,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    stored_fingerprint = hashlib.sha256(
                        fingerprint_material.encode("utf-8")
                    ).hexdigest()
                if not isinstance(stored_fingerprint, str) or not stored_fingerprint:
                    raise CheckpointError("invalid actuator contract fingerprint")
                restored_constitution = ActuatorSurface(
                    channels=channels,
                    contract_fingerprint=stored_fingerprint,
                )
                if actuator_constitution_override is not None:
                    if (
                        restored_constitution.channels
                        != actuator_constitution_override.channels
                    ):
                        raise CheckpointError(
                            "actuator constitution override changes legal channels"
                        )
                    actuator_constitution = actuator_constitution_override
                    if (
                        restored_constitution.contract_fingerprint
                        != actuator_constitution.contract_fingerprint
                    ):
                        fingerprint_migration = (
                            restored_constitution.contract_fingerprint,
                            actuator_constitution.contract_fingerprint,
                        )
                else:
                    actuator_constitution = restored_constitution
                try:
                    actuator_proposer = restore_actuation_state(
                        raw_actuation["proposer"],
                        actuator_constitution,
                        organism_id=str(normalized.get("organism_id") or ""),
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CheckpointError(f"invalid actuator proposer checkpoint: {exc}") from exc
                try:
                    motor_intent_selector = MotorIntentSelector(
                        selection_threshold=raw_actuation.get("selection_threshold", 0.1)
                    )
                except ValueError as exc:
                    raise CheckpointError(f"invalid motor selector checkpoint: {exc}") from exc
                raw_sensorimotor = raw_actuation.get("sensorimotor")
                if raw_sensorimotor is not None:
                    if not isinstance(raw_sensorimotor, dict):
                        raise CheckpointError("invalid canonical sensorimotor state")
                    raw_sensorimotor_restore = deepcopy(raw_sensorimotor)
                    if fingerprint_migration is not None:
                        old_fp, new_fp = fingerprint_migration
                        if (
                            raw_sensorimotor_restore.get("embodiment_fingerprint")
                            == old_fp
                        ):
                            raw_sensorimotor_restore["embodiment_fingerprint"] = new_fp
                        for key in ("primitives", "historical_candidates"):
                            raw_items = raw_sensorimotor_restore.get(key)
                            if isinstance(raw_items, list):
                                for item in raw_items:
                                    if (
                                        isinstance(item, dict)
                                        and item.get("embodiment_fingerprint")
                                        == old_fp
                                    ):
                                        item["embodiment_fingerprint"] = new_fp
                    try:
                        sensorimotor_learner = SensorimotorLearner.restore(
                            raw_sensorimotor_restore,
                            actuator_ids=actuator_constitution.actuator_ids,
                            organism_id=str(normalized.get("organism_id") or ""),
                            embodiment_fingerprint=actuator_constitution.contract_fingerprint,
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
                        if actuator_id not in set(actuator_constitution.actuator_ids):
                            raise CheckpointError("pending motor observation references unknown actuator")
                        if (
                            isinstance(activation, bool)
                            or not isinstance(activation, (int, float))
                            or not math.isfinite(float(activation))
                            or not 0.0 <= float(activation) <= 1.0
                        ):
                            raise CheckpointError("invalid pending motor activation")
                        if "baseline" in item:
                            raise CheckpointError("raw motor percept baselines must not be persisted")
                        restored_pending.append(
                            (str(actuator_id), float(activation), None)
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
        if raw_living_body is None:
            raise CheckpointError(
                "Living Body L5 requires canonical living_body checkpoint state"
            )
        try:
            living_body_state = LivingBodyState.from_checkpoint(raw_living_body)
        except (KeyError, TypeError, ValueError) as exc:
            raise CheckpointError(f"invalid living body checkpoint: {exc}") from exc

        metabolism.bind_body_state(living_body_state)

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
        if physiology.state is VitalState.DEAD:
            raise CheckpointError("dead organism checkpoints cannot be restored")
        raw_identity_key = normalized.get("signal_identity_key")
        signal_identity = SignalIdentity(bytes.fromhex(raw_identity_key)) if isinstance(raw_identity_key, str) else None
        constructor_kwargs = dict(kwargs)
        constructor_kwargs.pop("birth_authority", None)
        constructor_kwargs.pop("generation", None)
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
            gene_expression_state=gene_expression_state,
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
            birth_authority=kwargs.get("birth_authority"),
            generation=int(normalized.get("generation", normalized.get("effective_config", {}).get("generation", 0))),
            social_exchange_quantum=float(normalized.get("social_exchange_quantum", normalized.get("effective_config", {}).get("social_exchange_quantum", 0.1))),
            social_exchange_cost=float(normalized.get("social_exchange_cost", normalized.get("effective_config", {}).get("social_exchange_cost", 0.01))),
            resting_requested=bool(normalized.get("resting_requested", normalized.get("effective_config", {}).get("resting_requested", False))),
            degradation_queue=degradation_queue,
            source_trust=source_trust,
            developmental_tracker=developmental_tracker,
            actuation_enabled=actuation_enabled,
            actuator_constitution=actuator_constitution,
            actuator_proposer=actuator_proposer,
            motor_intent_selector=motor_intent_selector,
            sensorimotor_learner=sensorimotor_learner,
        )
        runtime._pending_motor_observation = pending_motor_observation
        runtime._pending_proprioception = pending_proprioception
        if isinstance(raw_actuation, dict):
            raw_commitment = raw_actuation.get("action_commitment")
            if isinstance(raw_commitment, dict):
                restored_commitment = ActionCommitment.restore(raw_commitment)
                current_surface = (
                    runtime._actuator_constitution.contract_fingerprint
                    if runtime._actuator_constitution is not None
                    else None
                )
                if restored_commitment.compatible_with(current_surface):
                    runtime._active_action_commitment = restored_commitment
                else:
                    restored_commitment.terminate(
                        tick=runtime._tick_count,
                        status=CommitmentStatus.INCOMPATIBLE,
                        reason="surface_contract_changed",
                    )
                    runtime._active_action_commitment = restored_commitment
            raw_v2 = raw_actuation.get("sensorimotor_v2")
            if isinstance(raw_v2, dict):
                try:
                    v2_schema = int(raw_v2.get("schema_version") or 0)
                    if v2_schema not in {1, 2}:
                        raise ValueError(
                            "unsupported sensorimotor v2 checkpoint schema"
                        )
                    raw_effects = raw_v2.get("effect_space")
                    raw_evidence = raw_v2.get("causal_evidence")
                    if isinstance(raw_effects, dict):
                        runtime._effect_space = EffectSpace.restore(raw_effects)
                    if isinstance(raw_evidence, dict):
                        runtime._causal_evidence = CausalEvidenceLedger.restore(raw_evidence)
                        runtime._body_schema.rebuild_sensorimotor_view(
                            runtime._causal_evidence.evidence
                        )
                        runtime._sensorimotor_model.rebuild(
                            runtime._causal_evidence
                        )
                        runtime._controllability_model.rebuild(
                            runtime._causal_evidence
                        )
                        runtime._agency_model.rebuild(
                            runtime._causal_evidence
                        )
                    raw_exploration = raw_v2.get("exploration")
                    if isinstance(raw_exploration, dict):
                        raw_strength = raw_exploration.get("strength_memory", {})
                        if isinstance(raw_strength, dict):
                            runtime._exploration_strength_memory = {
                                str(key): max(0.0, min(1.0, float(value)))
                                for key, value in raw_strength.items()
                                if str(key) in set(
                                    runtime._actuator_constitution.actuator_ids
                                    if runtime._actuator_constitution is not None
                                    else ()
                                )
                            }
                        raw_preference = raw_exploration.get(
                            "active_preference",
                            [],
                        )
                        if isinstance(raw_preference, list):
                            known = set(
                                runtime._actuator_constitution.actuator_ids
                                if runtime._actuator_constitution is not None
                                else ()
                            )
                            runtime._active_exploration_preference = tuple(
                                str(value)
                                for value in raw_preference
                                if str(value) in known
                            )
                    raw_competences = raw_v2.get("competences", [])
                    if isinstance(raw_competences, list):
                        restored_library = CompetenceLibrary()
                        for item in raw_competences:
                            if not isinstance(item, dict):
                                raise ValueError("invalid competence checkpoint item")
                            competence_id = item.get("competence_id")
                            controller_id = item.get("controller_id")
                            if not isinstance(competence_id, str) or not isinstance(controller_id, str):
                                raise ValueError("invalid competence checkpoint identifiers")
                            restored_library.add(
                                MotorCompetence(
                                    competence_id=competence_id,
                                    controller_id=controller_id,
                                    effect_id=(
                                        str(item["effect_id"])
                                        if item.get("effect_id") is not None
                                        else None
                                    ),
                                    evidence=CompetenceEvidence(
                                        controller_seed_ref=str(
                                            item.get("controller_strategy_ref")
                                            or competence_id
                                        ),
                                        support=int(item.get("support", 0)),
                                        failures=int(item.get("failures", 0)),
                                        reproducibility=float(item.get("reproducibility", 0.0)),
                                        controllability=float(item.get("controllability", 0.0)),
                                        directional_consistency=float(
                                            item.get("directional_consistency", 0.0)
                                        ),
                                    ),
                                    controller_strategy_ref=(
                                        str(item["controller_strategy_ref"])
                                        if item.get("controller_strategy_ref") is not None
                                        else None
                                    ),
                                    parent_competence_ids=tuple(
                                        str(value)
                                        for value in item.get(
                                            "parent_competence_ids",
                                            [],
                                        )
                                    ),
                                )
                            )
                        runtime._competence_library = restored_library
                        if v2_schema == 2:
                            raw_bindings = raw_v2.get("execution_bindings")
                            binding_payload = (
                                deepcopy(raw_bindings)
                                if isinstance(raw_bindings, dict)
                                else None
                            )
                            if (
                                binding_payload is not None
                                and fingerprint_migration is not None
                            ):
                                old_fp, new_fp = fingerprint_migration
                                raw_items = binding_payload.get("items")
                                if isinstance(raw_items, list):
                                    for item in raw_items:
                                        if (
                                            isinstance(item, dict)
                                            and item.get("surface_fingerprint")
                                            == old_fp
                                        ):
                                            item["surface_fingerprint"] = new_fp
                            runtime._competence_execution_bindings = (
                                CompetenceExecutionBindingRegistry.restore(
                                    binding_payload
                                )
                            )
                        else:
                            migrated = CompetenceExecutionBindingRegistry()
                            for legacy_item in raw_competences:
                                if not isinstance(legacy_item, dict):
                                    continue
                                competence_id = str(
                                    legacy_item.get("competence_id") or ""
                                )
                                surface = legacy_item.get("surface_binding")
                                if (
                                    isinstance(surface, str)
                                    and fingerprint_migration is not None
                                    and surface == fingerprint_migration[0]
                                ):
                                    surface = fingerprint_migration[1]
                                effect_id = legacy_item.get("effect_id")
                                matching = tuple(
                                    evidence
                                    for evidence in runtime._causal_evidence.evidence
                                    if evidence.competence_id == competence_id
                                    and evidence.effect_id == effect_id
                                )
                                refs = tuple(
                                    evidence.evidence_id
                                    for evidence in matching
                                )
                                if (
                                    competence_id
                                    and isinstance(surface, str)
                                    and surface
                                    and isinstance(effect_id, str)
                                    and effect_id
                                    and refs
                                ):
                                    competence = restored_library.get(competence_id)
                                    migrated.bind_from_evidence(
                                        competence_id=competence_id,
                                        surface_fingerprint=surface,
                                        effect_id=effect_id,
                                        evidence_refs=refs,
                                        reliability=(
                                            competence.evidence.reproducibility
                                            if competence is not None
                                            else 0.0
                                        ),
                                        controllability=(
                                            competence.evidence.controllability
                                            if competence is not None
                                            else 0.0
                                        ),
                                        tick=max(
                                            (
                                                evidence.observation_tick
                                                for evidence in matching
                                            ),
                                            default=0,
                                        ),
                                    )
                            runtime._competence_execution_bindings = migrated
                    raw_composition = raw_v2.get("composition")
                    if isinstance(raw_composition, dict):
                        raw_engine = raw_composition.get("engine")
                        if isinstance(raw_engine, dict):
                            runtime._composition_engine = CompositionEngine.restore(
                                raw_engine
                            )
                        predecessor = raw_composition.get("predecessor_id")
                        runtime._composition_predecessor_id = (
                            str(predecessor)
                            if predecessor is not None
                            else None
                        )
                        children = raw_composition.get("active_children", [])
                        if isinstance(children, list):
                            runtime._active_composition_children = tuple(
                                str(value) for value in children
                            )
                        runtime._active_composition_index = int(
                            raw_composition.get("active_index", 0)
                        )
                        known_competences = {
                            item.competence_id
                            for item in runtime._competence_library.items
                        }
                        if (
                            runtime._active_action_commitment is None
                            or not runtime._active_action_commitment.active
                            or not runtime._active_composition_children
                            or any(
                                child not in known_competences
                                for child in runtime._active_composition_children
                            )
                            or runtime._active_composition_index < 0
                            or runtime._active_composition_index
                            >= len(runtime._active_composition_children)
                        ):
                            runtime._active_composition_children = ()
                            runtime._active_composition_index = 0
                        if (
                            runtime._composition_predecessor_id is not None
                            and runtime._composition_predecessor_id
                            not in known_competences
                        ):
                            runtime._composition_predecessor_id = None
                except (TypeError, ValueError, KeyError) as exc:
                    raise CheckpointError(f"invalid sensorimotor v2 checkpoint: {exc}") from exc
        raw_reactivity = normalized.get("innate_reactivity")
        if raw_reactivity is not None:
            if (
                not isinstance(raw_reactivity, dict)
                or raw_reactivity.get("schema_version") != 1
            ):
                raise CheckpointError("invalid innate reactivity checkpoint")
            try:
                runtime._innate_reactivity = InnateReactivity.restore(
                    raw_reactivity.get("reactivity")
                )
                runtime._reactive_memory = ReactiveMemory.restore(
                    raw_reactivity.get("memory")
                )
            except (TypeError, ValueError, KeyError) as exc:
                raise CheckpointError(
                    f"invalid innate reactivity checkpoint: {exc}"
                ) from exc
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
            raise CheckpointError(
                "checkpoint carries removed primitive verification state; "
                "start from a current checkpoint or fresh embodiment"
            )
        raw_embodied_work = normalized.get("pending_embodied_work", 0.0)
        if (
            isinstance(raw_embodied_work, bool)
            or not isinstance(raw_embodied_work, (int, float))
            or not math.isfinite(float(raw_embodied_work))
            or float(raw_embodied_work) < 0.0
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

        raw_lineage = normalized.get("checkpoint_lineage")
        if raw_lineage is not None:
            if (
                not isinstance(raw_lineage, dict)
                or not isinstance(raw_lineage.get("checkpoint_id"), str)
            ):
                raise CheckpointError("invalid checkpoint_lineage")
            # The restored organism's next save chains from the checkpoint
            # it was just loaded from. A payload with no lineage block
            # predates this tracking — it honestly starts a new root rather
            # than inventing a history it never recorded.
            runtime._last_checkpoint_hash = raw_lineage["checkpoint_id"]
        return runtime

    @classmethod
    def load_or_create(cls, path: str | Path, **kwargs: Any) -> "OrganismRuntime":
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
