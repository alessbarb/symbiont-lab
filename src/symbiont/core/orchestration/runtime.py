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
from ...genetics.genome import Genome, DevelopmentGenes, PlasticityGenes, RangeSpec
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
from ..regulation import InnateReactivity, ReactiveMemory, ReactiveState
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
from ...actuation.proposer import ActuatorEvidenceModel
from ...actuation.binding import CompetenceExecutionBindingRegistry
from ...actuation.constitution import ActuatorConstitution
from ...actuation.surface import ActuatorChannel, ActuatorSurface
from ...actuation.candidate import ActuatorCandidateState
from ...actuation.types import Actuation, MotorIntent
from ...actuation.system import ActuatorSystem
from ...actuation.action import MotorCommand
from ...actuation.commitment import ActionCommitment, CommitmentStatus
from ...actuation.competence import CompetenceLibrary, MotorCompetence
from ...actuation.evidence import CausalEvidenceLedger, SensorimotorTransition
from ...actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from ...actuation.state import SensorimotorV2Snapshot
from ...actuation.sensorimotor import CompetenceDevelopmentEngine, SensorimotorSnapshot
from ..domains.action import ActionDomain, ActionServices
from ..domains.context import TickContext
from ..domains.physiology import (
    PhysiologyDomain,
    PhysiologyPreflightServices,
    PhysiologyServices,
)
from ..domains.perception import PerceptionDomain, PerceptionServices
from ..domains.cognition import CognitionDomain, CognitionServices
from ..domains.epistemic import EpistemicDomain, EpistemicServices
from ..domains.lifecycle import LifecycleDomain
from ..domains.regulation import RegulationDomain, RegulationServices
from ..domains.embodiment import EmbodimentDomain, EmbodimentServices
from ..domains.development import DevelopmentDomain
from ..domains.memory import MemoryDomain, MemoryServices


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
        actuator_evidence: ActuatorEvidenceModel | None = None,
        motor_selection_threshold: float = 0.1,
        actuator_system: ActuatorSystem | None = None,
        competence_development: CompetenceDevelopmentEngine | None = None,
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
        self._lifecycle_domain = LifecycleDomain()
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
        # One-tick causal trace only. A restart deliberately breaks this trace;
        # established reactive associations are checkpointed separately.
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
        if self._actuation_enabled and actuator_constitution is None:
            raise ValueError(
                "actuation_enabled requires an explicit body-owned actuator_constitution"
            )
        if self._actuation_enabled and actuator_constitution is not None:
            if not self._living_body_state.structure_states:
                self._living_body_state.structure_states = {
                    slot.slot_id: BodyStructureState(
                        structure_id=slot.slot_id,
                        integrity=self._living_body_state.structural_integrity,
                    )
                    for slot in actuator_constitution.slots
                }
        if (
            isinstance(motor_selection_threshold, bool)
            or not isinstance(motor_selection_threshold, (int, float))
            or not 0.0 <= float(motor_selection_threshold) <= 1.0
        ):
            raise ValueError("motor_selection_threshold must be within [0, 1]")
        selection_threshold = float(motor_selection_threshold)
        self._action_domain = ActionDomain(
            organism_id=self._organism_id,
            enabled=self._actuation_enabled,
            surface=actuator_constitution,
            selection_threshold=selection_threshold,
            actuator_evidence=actuator_evidence,
            competence_development=competence_development,
            actuator_system=actuator_system,
        )
        self._regulation_domain = RegulationDomain()
        self._development_domain = DevelopmentDomain()
        self._physiology_domain = PhysiologyDomain()
        self._perception_domain = PerceptionDomain()
        self._cognition_domain = CognitionDomain()
        self._memory_domain = MemoryDomain()
        self._epistemic_domain = EpistemicDomain()
        self._embodiment_domain = EmbodimentDomain()
        self._pending_embodied_work = 0.0
        self._narrative_journal: list[dict[str, Any]] = []

    # Compatibility views expose the single ActionDomain state; they do not
    # create a second authority.
    @property
    def _actuator_constitution(self):
        return self._action_domain.surface

    @property

    @property

    @property
    def _active_action_commitment(self):
        return self._action_domain.active_commitment

    @_active_action_commitment.setter
    def _active_action_commitment(self, value):
        self._action_domain.active_commitment = value

    @property
    def _last_action_proposal(self):
        return self._action_domain.last_proposal

    @_last_action_proposal.setter
    def _last_action_proposal(self, value):
        self._action_domain.last_proposal = value

    @property
    def _last_action_source(self):
        return self._action_domain.last_action_source

    @_last_action_source.setter
    def _last_action_source(self, value):
        self._action_domain.last_action_source = value

    @property
    def _last_motor_command(self):
        return self._action_domain.last_motor_command

    @_last_motor_command.setter
    def _last_motor_command(self, value):
        self._action_domain.last_motor_command = value

    @property
    def _last_motor_intent(self):
        return self._action_domain.last_motor_intent

    @_last_motor_intent.setter
    def _last_motor_intent(self, value):
        self._action_domain.last_motor_intent = value

    @property
    def _last_actuation(self):
        return self._action_domain.last_actuation

    @_last_actuation.setter
    def _last_actuation(self, value):
        self._action_domain.last_actuation = value

    @property
    def _last_motor_intents(self):
        return self._action_domain.last_motor_intents

    @_last_motor_intents.setter
    def _last_motor_intents(self, value):
        self._action_domain.last_motor_intents = tuple(value)

    @property
    def _last_actuations(self):
        return self._action_domain.last_actuations

    @_last_actuations.setter
    def _last_actuations(self, value):
        self._action_domain.last_actuations = tuple(value)

    @property
    def _last_executed_primitive_id(self):
        return self._action_domain.last_executed_controller_seed_id

    @_last_executed_primitive_id.setter
    def _last_executed_primitive_id(self, value):
        self._action_domain.last_executed_controller_seed_id = value

    @property
    def _effect_space(self):
        return self._action_domain.effect_space

    @_effect_space.setter
    def _effect_space(self, value):
        self._action_domain.effect_space = value

    @property
    def _causal_evidence(self):
        return self._action_domain.causal_evidence

    @_causal_evidence.setter
    def _causal_evidence(self, value):
        self._action_domain.causal_evidence = value

    @property
    def _competence_library(self):
        return self._action_domain.competence_library

    @_competence_library.setter
    def _competence_library(self, value):
        self._action_domain.competence_library = value

    @property
    def _competence_execution_bindings(self):
        return self._action_domain.execution_bindings

    @_competence_execution_bindings.setter
    def _competence_execution_bindings(self, value):
        self._action_domain.execution_bindings = value

    @property
    def _sensorimotor_model(self):
        return self._action_domain.effect_model

    @_sensorimotor_model.setter
    def _sensorimotor_model(self, value):
        self._action_domain.effect_model = value

    @property
    def _controllability_model(self):
        return self._action_domain.controllability_model

    @_controllability_model.setter
    def _controllability_model(self, value):
        self._action_domain.controllability_model = value

    @property
    def _agency_model(self):
        return self._action_domain.agency_model

    @_agency_model.setter
    def _agency_model(self, value):
        self._action_domain.agency_model = value

    @property
    def _exploration_policy(self):
        return self._action_domain.exploration_policy

    @property
    def _exploration_strength_memory(self):
        return self._action_domain.exploration_strength_memory

    @_exploration_strength_memory.setter
    def _exploration_strength_memory(self, value):
        self._action_domain.exploration_strength_memory = dict(value)

    @property
    def _active_exploration_preference(self):
        return self._action_domain.active_exploration_preference

    @_active_exploration_preference.setter
    def _active_exploration_preference(self, value):
        self._action_domain.active_exploration_preference = tuple(value)

    @property
    def _last_exploration_signals(self):
        return self._action_domain.last_exploration_signals

    @_last_exploration_signals.setter
    def _last_exploration_signals(self, value):
        self._action_domain.last_exploration_signals = dict(value)

    @property
    def _composition_engine(self):
        return self._action_domain.composition_engine

    @_composition_engine.setter
    def _composition_engine(self, value):
        self._action_domain.composition_engine = value

    @property
    def _composition_predecessor_id(self):
        return self._action_domain.composition_predecessor_id

    @_composition_predecessor_id.setter
    def _composition_predecessor_id(self, value):
        self._action_domain.composition_predecessor_id = value

    @property
    def _active_composition_children(self):
        return self._action_domain.active_composition_children

    @_active_composition_children.setter
    def _active_composition_children(self, value):
        self._action_domain.active_composition_children = tuple(value)

    @property
    def _active_composition_index(self):
        return self._action_domain.active_composition_index

    @_active_composition_index.setter
    def _active_composition_index(self, value):
        self._action_domain.active_composition_index = int(value)

    @property
    def _effect_by_commitment(self):
        return self._action_domain.effect_by_commitment

    @property
    def _pending_sensorimotor_transition(self):
        return self._action_domain.pending_transition

    @_pending_sensorimotor_transition.setter
    def _pending_sensorimotor_transition(self, value):
        self._action_domain.pending_transition = value

    @property
    def _last_sensorimotor_transition(self):
        return self._action_domain.last_transition

    @_last_sensorimotor_transition.setter
    def _last_sensorimotor_transition(self, value):
        self._action_domain.last_transition = value

    @property
    def _pending_motor_observation(self):
        return self._action_domain.pending_motor_observation

    @_pending_motor_observation.setter
    def _pending_motor_observation(self, value):
        self._action_domain.pending_motor_observation = tuple(value)

    @property
    def _pending_proprioception(self):
        return self._action_domain.pending_proprioception

    @_pending_proprioception.setter
    def _pending_proprioception(self, value):
        self._action_domain.pending_proprioception = dict(value)

    @property
    def _pending_reactive_credit(self):
        return self._action_domain.pending_reactive_credit

    @_pending_reactive_credit.setter
    def _pending_reactive_credit(self, value):
        self._action_domain.pending_reactive_credit = value

    @property
    def _last_reactive_state(self):
        return self._action_domain.last_reactive_state

    @_last_reactive_state.setter
    def _last_reactive_state(self, value):
        self._action_domain.last_reactive_state = value

    @property
    def _pending_homeostatic_action_credit(self):
        return self._regulation_domain.pending_homeostatic_action_credit

    @_pending_homeostatic_action_credit.setter
    def _pending_homeostatic_action_credit(self, value):
        self._regulation_domain.pending_homeostatic_action_credit = list(value)

    @property
    def _last_runtime_vital_state(self):
        return self._lifecycle_domain.state.last_vital_state

    @_last_runtime_vital_state.setter
    def _last_runtime_vital_state(self, value):
        self._lifecycle_domain.state.last_vital_state = value

    @property
    def _last_runtime_development_phase(self):
        return self._lifecycle_domain.state.last_development_phase

    @_last_runtime_development_phase.setter
    def _last_runtime_development_phase(self, value):
        self._lifecycle_domain.state.last_development_phase = value

    @property
    def _first_sense_emitted(self):
        return self._lifecycle_domain.state.first_sense_emitted

    @_first_sense_emitted.setter
    def _first_sense_emitted(self, value):
        self._lifecycle_domain.state.first_sense_emitted = bool(value)

    @property
    def _first_concept_emitted(self):
        return self._lifecycle_domain.state.first_concept_emitted

    @_first_concept_emitted.setter
    def _first_concept_emitted(self, value):
        self._lifecycle_domain.state.first_concept_emitted = bool(value)

    @property
    def _first_prediction_emitted(self):
        return self._lifecycle_domain.state.first_prediction_emitted

    @_first_prediction_emitted.setter
    def _first_prediction_emitted(self, value):
        self._lifecycle_domain.state.first_prediction_emitted = bool(value)

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
        actuator_count = (
            len(self._actuator_constitution.actuator_ids)
            if self._actuator_constitution is not None
            else 0
        )
        active_count = (
            len(self._action_domain.actuator_evidence.active_repertoire)
            if self._action_domain.actuator_evidence is not None
            else 0
        )
        self._gene_expression_state = (
            self._development_domain.update_gene_expression(
                genome=self._genome,
                expression_state=self._gene_expression_state,
                expression_regulator=self._expression_regulator,
                cognitive_bridge=self._cognitive_bridge,
                cognition=cognition,
                drift_observations=drift_observations,
                metabolic_pressure=metabolic_pressure,
                actuator_count=actuator_count,
                active_actuator_count=active_count,
            )
        )


    @property
    def reacclimation_remaining(self) -> int:
        """Ticks remaining in the organism-owned post-restore reacclimation gate."""
        return int(self._reacclimation_remaining)

    @property
    def actuation_enabled(self) -> bool:
        return self._actuation_enabled

    def bind_action_embodiment(
        self,
        embodiment_id: str,
        *,
        new_episode: bool,
    ) -> None:
        """Bind physical action authority to one canonical EmbodimentEpisode.

        Restoring the same episode preserves already revalidated current-body
        bindings.  Beginning a genuinely new episode invalidates every active
        commitment and withdraws all previous execution bindings.
        """
        if not isinstance(embodiment_id, str) or not embodiment_id:
            raise ValueError("embodiment_id must be non-empty")
        if not self._actuation_enabled:
            return
        surface = self._action_domain.surface
        if surface is None:
            raise RuntimeError("cannot bind embodiment without actuator surface")

        if new_episode:
            self._action_domain.begin_embodiment(
                surface=surface,
                embodiment_id=embodiment_id,
                tick=self._tick_count,
            )
            return

        current = self._action_domain.embodiment_id
        if current is not None and current != embodiment_id:
            raise RuntimeError(
                "restored action authority belongs to another embodiment"
            )
        self._action_domain.embodiment_id = embodiment_id
        commitment = self._action_domain.active_commitment
        if (
            commitment is not None
            and commitment.active
            and commitment.embodiment_id is None
        ):
            # Explicit migration of a pre-Embodiment-id commitment.  This is
            # only legal when the surrounding physical episode itself was
            # restored rather than replaced.
            commitment.embodiment_id = embodiment_id

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
    def actuator_evidence_model(self) -> ActuatorEvidenceModel | None:
        return self._action_domain.actuator_evidence

    @property
    def active_motor_repertoire(self) -> tuple[str, ...]:
        if self._action_domain.actuator_evidence is None:
            return ()
        return self._action_domain.actuator_evidence.active_repertoire

    @property
    def competence_development(self) -> CompetenceDevelopmentEngine | None:
        return self._action_domain.competence_development

    @property
    def sensorimotor_snapshot(self) -> SensorimotorSnapshot | None:
        if self._action_domain.competence_development is None:
            return None
        return self._action_domain.competence_development.snapshot()

    @property
    def sensorimotor_exclusive_actuator_groups(
        self,
    ) -> tuple[tuple[str, ...], ...]:
        if self._action_domain.competence_development is None:
            return ()
        return self._action_domain.competence_development.exclusive_actuator_groups

    @property
    def available_motor_competence_ids(self) -> tuple[str, ...]:
        """Opaque ids of currently evidence-supported motor competences."""
        engine = self._action_domain.competence_development
        if engine is None:
            return ()
        return engine.available_cognitive_primitive_ids()

    @property
    def sensorimotor_competence_candidates(self) -> tuple[dict[str, object], ...]:
        """Passive candidate view; legacy sequence objects never cross this boundary."""
        if self._action_domain.competence_development is None:
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
            for item in self._action_domain.competence_development.primitives
        )

    @property
    def sensorimotor_competence_episodes(self) -> tuple[dict[str, object], ...]:
        """Latest evidence episodes projected into v2 competence terminology."""
        if self._action_domain.competence_development is None:
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
            for episode in self._action_domain.competence_development.last_primitive_episodes
        )

    def _sensorimotor_v2_snapshot(self) -> SensorimotorV2Snapshot | None:
        return self._action_domain.snapshot(
            body_schema_sensorimotor_relations=(
                self._body_schema.sensorimotor_dependency_evidence_count
            )
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
        if self._action_domain.actuator_evidence is None:
            return ()
        return self._action_domain.actuator_evidence.states


    def _motor_percept_snapshot(
        self,
        percepts: tuple[Percept, ...],
    ) -> dict[str, float]:
        return self._action_domain.motor_percept_snapshot(
            percepts,
            sensory_system=self._sensory_system,
        )

    def _sensorimotor_body_snapshot(
        self,
        percepts: tuple[Percept, ...],
    ) -> dict[str, float]:
        return self._action_domain.sensorimotor_body_snapshot(
            percepts,
            sensory_system=self._sensory_system,
        )

    def _complete_pending_motor_observation(
        self,
        percepts: tuple[Percept, ...],
        *,
        tick: int,
    ) -> tuple[str, ...]:
        return self._action_domain.complete_pending_motor_observation(
            percepts,
            tick=tick,
            sensory_system=self._sensory_system,
        )

    def _schedule_homeostatic_action_credit(
        self,
        *,
        family: str,
        action_id: str,
        concept_ids: tuple[str, ...],
        baseline_error: float,
        tick: int,
    ) -> None:
        self._regulation_domain.schedule_homeostatic_action_credit(
            cognitive_bridge=self._cognitive_bridge,
            family=family,
            action_id=action_id,
            concept_ids=concept_ids,
            baseline_error=baseline_error,
            tick=tick,
        )


    def _resolve_homeostatic_action_credit(self, *, tick: int) -> None:
        self._regulation_domain.resolve_homeostatic_action_credit(
            services=RegulationServices(
                cognitive_bridge=self._cognitive_bridge,
                homeostasis=self._homeostasis,
                living_body_state=self._living_body_state,
            ),
            tick=tick,
        )


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


    def _motor_step(
        self,
        cognition: CognitiveBridgeResult | None,
        percepts: tuple[Percept, ...],
        *,
        tick: int | None = None,
        context: TickContext | None = None,
        signal_references: dict[str, str] | None = None,
    ) -> None:
        if context is None:
            if tick is None:
                raise ValueError("motor step requires TickContext or tick")
            context = TickContext(
                symbiont_id=self._organism_id,
                symbiont_tick=int(tick),
                embodiment_id=self._action_domain.embodiment_id,
            )
        elif tick is not None and int(tick) != context.symbiont_tick:
            raise ValueError("motor step tick contradicts TickContext")
        self._action_domain.step(
            cognition,
            percepts,
            context=context,
            signal_references=signal_references,
            services=ActionServices(
                sensory_system=self._sensory_system,
                homeostasis=self._homeostasis,
                innate_reactivity=self._innate_reactivity,
                reactive_memory=self._reactive_memory,
                body_schema=self._body_schema,
                cognitive_bridge=self._cognitive_bridge,
                gene_expression_state=self._gene_expression_state,
                choose_acquired_competence=self._choose_acquired_competence,
                schedule_homeostatic_action_credit=self._schedule_homeostatic_action_credit,
            ),
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
                self._action_domain.selection_threshold
                if self._actuation_enabled
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
        self._epigenetic_priors = (
            self._development_domain.decay_epigenetic_priors(
                self._epigenetic_priors,
                decay=self._epigenetic_decay,
            )
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
                motor_selection_threshold=self._action_domain.selection_threshold,
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

    def tick(
        self,
        *,
        context: TickContext | None = None,
    ) -> RuntimeTickResult:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("organism is irreversibly dead")
        expected_tick = self._tick_count + 1
        if context is None:
            context = TickContext(
                symbiont_id=self._organism_id,
                symbiont_tick=expected_tick,
                embodiment_id=self._action_domain.embodiment_id,
            )
        else:
            if context.symbiont_id != self._organism_id:
                raise ValueError("tick context belongs to another Symbiont")
            if context.symbiont_tick != expected_tick:
                raise ValueError(
                    "tick context symbiont time is not the next organism tick"
                )
            if (
                self._action_domain.embodiment_id is not None
                and context.embodiment_id
                != self._action_domain.embodiment_id
            ):
                raise ValueError(
                    "tick context belongs to another EmbodimentEpisode"
                )
        tick_start = time.monotonic()
        action_result: ActionExecutionResult | None = None
        self._reacclimation_remaining = (
            self._embodiment_domain.advance_reacclimation(
                self._reacclimation_remaining
            )
        )
        physiology_preflight = self._physiology_domain.preflight(
            services=PhysiologyPreflightServices(
                metabolism=self._metabolism,
                homeostasis=self._homeostasis,
                living_body_state=self._living_body_state,
                degradation=self._degradation,
                interoception_provider=self._interoception_provider,
            )
        )
        degradation_excreted = physiology_preflight.degradation_excreted
        plasticity_gate = physiology_preflight.plasticity_enabled

        perception = self._perception_domain.step(
            services=PerceptionServices(
                lifecycle=self._lifecycle,
                adaptive_senses=self._adaptive_senses,
                self_model=self._self_model,
                signal_identity=self._signal_identity,
                signal_knowledge=self._signal_knowledge,
                sensory_system=self._sensory_system,
                acclimation=self._acclimation,
                rhythm_model=self._rhythm_model,
                drift_baselines=self._drift_baselines,
                assimilator=self._assimilator,
                resource_habitats=self._resource_habitats,
                interoception_provider=self._interoception_provider,
                reading_providers=self._reading_providers,
                charge_metabolism=self._charge_metabolism,
            ),
            context=context,
            discover_senses=self._discover_senses,
            bootstrap_semantic_senses=self._bootstrap_semantic_senses,
            attention_budget=self._attention_budget,
            sampling_selector=self._sampling_selector,
            pending_proprioception=(
                self._pending_proprioception
                if self._actuation_enabled
                else {}
            ),
        )
        snapshot = perception.snapshot
        resource_readings = perception.resource_readings
        organism_readings = perception.organism_readings
        knowledge_view = perception.knowledge_view
        sampling_plan = perception.sampling_plan
        percept_names = perception.percept_names
        developed_names = perception.developed_names
        capability_by_percept_name = perception.capability_by_percept_name
        cognitive_aliases = perception.cognitive_aliases
        selected_ids = set(perception.selected_ids)
        cognitive_readings = perception.cognitive_readings
        percepts = perception.percepts
        sensor_by_cognitive_name = perception.sensor_by_cognitive_name
        drift_observations = perception.drift_observations
        assimilation = list(perception.assimilation)
        allocations = perception.allocations
        perceptual_allocations = perception.perceptual_allocations
        availability_by_capability = perception.availability_by_capability
        if perception.pending_proprioception_consumed:
            self._pending_proprioception = {}

        action_projection = self._action_domain.prepare_cognition(
            percepts,
            context=context,
            sensory_system=self._sensory_system,
        )
        cognition_step = self._cognition_domain.step(
            services=CognitionServices(
                cognitive_bridge=self._cognitive_bridge,
                sensory_system=self._sensory_system,
                self_model=self._self_model,
                charge_metabolism=self._charge_metabolism,
            ),
            context=context,
            perception=perception,
            action_projection=action_projection,
            plasticity_enabled=plasticity_gate,
            auto_promote_predictors=self._auto_promote_predictors,
            reacclimation_remaining=self._reacclimation_remaining,
            cognitive_self_namespace_key=self._cognitive_self_namespace_key,
        )
        cognition_result = cognition_step.cognition
        cognitive_self_observation = (
            cognition_step.cognitive_self_observation
        )
        self._memory_domain.observe(
            services=MemoryServices(
                consolidator=self._memory_consolidator,
                self_model=self._self_model,
            ),
            context=context,
            perception=perception,
            cognition=cognition_step,
            reacclimation_remaining=self._reacclimation_remaining,
        )

        current_signal_references = perception.signal_references

        self._motor_step(
            cognition_result,
            percepts,
            context=context,
            signal_references=current_signal_references,
        )

        epistemic = self._epistemic_domain.investigate(
            services=EpistemicServices(
                self_model=self._self_model,
                evidence_ledger=self._evidence_ledger,
                acclimation=self._acclimation,
                reading_providers=self._reading_providers,
            ),
            context=context,
            perception=perception,
            investigate_ticks=self._investigate_ticks,
        )
        investigated_capability = epistemic.investigated_capability
        evidence_gathered = epistemic.evidence_gathered
        dissent = epistemic.dissent
        narrative = epistemic.narrative

        # The action decision consumes the current tick's bounded perception
        # and cognition.  ``action_result`` remains ``None`` here: canonical
        # cognition does not run a typed local action-selection step, and
        # this runtime tick performs no such step on its own.  The field is
        # kept on the tick result only as a passive, semantic-free reporting
        # surface: existing lab adapters and the Observatory read it when
        # present without requiring this runtime to ever populate it.

        embodiment_step = self._embodiment_domain.observe(
            services=EmbodimentServices(
                body_schema=self._body_schema,
                sensory_system=self._sensory_system,
                self_model=self._self_model,
                signal_identity=self._signal_identity,
            ),
            context=context,
            cognitive_self_observation=cognitive_self_observation,
        )
        sensory_phenotype_view = embodiment_step.sensory_phenotype
        # Cognitive/information-assimilation "success" (incorporation utility,
        # prediction accuracy) is not a physical resource and must never
        # manufacture metabolic reserve on its own: only externally acquired
        # resource (habitat consumption via ``request_resource_intake``,
        # explicit ``intake`` from an actual transfer, etc.) may grow
        # reserve. Assimilation cost is still charged elsewhere
        # (``_charge_metabolism`` above) regardless of ``_explicit_metabolism``.

        retained_units = self._memory_domain.retained_units(
            drift_baseline_count=len(self._drift_baselines),
            cognitive_node_count=(
                len(self._cognitive_bridge.graph.nodes)
                if (
                    self._cognitive_bridge is not None
                    and self._cognitive_bridge.graph is not None
                )
                else 0
            ),
        )
        embodied_work = self._pending_embodied_work
        self._pending_embodied_work = 0.0
        physiology_step = self._physiology_domain.advance(
            services=PhysiologyServices(
                metabolism=self._metabolism,
                homeostasis=self._homeostasis,
                ontogeny=self._ontogeny,
                physiology=self._physiology,
                developmental_tracker=self._developmental_tracker,
                living_body_state=self._living_body_state,
                degradation=self._degradation,
                sensory_system=self._sensory_system,
                adaptive_senses=self._adaptive_senses,
                cognitive_bridge=self._cognitive_bridge,
            ),
            retained_memory_units=retained_units,
            embodied_work=embodied_work,
            resting_requested=self._resting_requested,
            degradation_excreted=degradation_excreted,
        )
        metabolism_snapshot = physiology_step.metabolism
        homeostatic_snapshot = physiology_step.homeostasis
        physiology_snapshot = physiology_step.physiology
        ontogeny_snapshot = physiology_step.ontogeny
        development_snapshot = physiology_step.development
        repaired_amount = physiology_step.repaired_amount
        self._resting_requested = physiology_step.resting_requested
        resting_for_tick = physiology_step.resting_for_tick
        self._resolve_homeostatic_action_credit(tick=context.symbiont_tick)
        release = self._lifecycle_domain.release_on_death(
            organism_id=self._organism_id,
            physiology_snapshot=physiology_snapshot,
            habitat=self._habitat,
            habitat_released=self._habitat_released,
            resource_habitats=self._resource_habitats,
            birth_authority=self._birth_authority,
            birth_authority_released=self._birth_authority_released,
            social_habitat=self._social_habitat,
            social_habitat_released=self._social_habitat_released,
        )
        self._habitat_released = release.habitat_released
        self._birth_authority_released = release.birth_authority_released
        self._social_habitat_released = release.social_habitat_released
        self._lifecycle_domain.update_interoception_metrics(
            provider=self._interoception_provider,
            tick_start=tick_start,
            cognition_result=cognition_result,
            living_body_state=self._living_body_state,
            homeostasis=self._homeostasis,
            degradation=self._degradation,
            metabolism_snapshot=metabolism_snapshot,
        )
        runtime_events = self._lifecycle_domain.events(
            homeostatic_snapshot=homeostatic_snapshot,
            physiology_snapshot=physiology_snapshot,
            development_snapshot=development_snapshot,
            cognition_result=cognition_result,
            percepts=percepts,
            knowledge_view=knowledge_view,
            drift_observations=drift_observations,
            action_executed=bool(
                action_result is not None and action_result.executed
            ),
        )

        # Evidence from tick t regulates the operating phenotype for t+1.
        self._update_gene_expression(
            cognition=cognition_result,
            drift_observations=drift_observations,
            metabolic_pressure=metabolism_snapshot.pressure.value,
        )

        self._tick_count = context.symbiont_tick
        self._physiology_domain.advance_body_age(self._living_body_state)
        self._lifecycle_domain.record_journal(
            self._narrative_journal,
            tick=self._tick_count,
            physiology_snapshot=physiology_snapshot,
            metabolism_snapshot=metabolism_snapshot,
            resting_for_tick=resting_for_tick,
            allocations=allocations,
            investigated_capability=investigated_capability,
            drift_observations=drift_observations,
            dissent=dissent,
            assimilation_count=len(assimilation),
            narrative=narrative,
        )
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
            runtime_events=runtime_events,
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
            if self._actuator_constitution is None:
                raise CheckpointError(
                    "actuation enabled without actuator constitution"
                )
            constitution_payload = {
                "contract_fingerprint": (
                    self._actuator_constitution.contract_fingerprint
                ),
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
            payload["actuation"] = {
                "enabled": True,
                "constitution": constitution_payload,
                "action_domain": self._action_domain.checkpoint_state(),
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
        actuator_evidence = None
        motor_selection_threshold = 0.1
        competence_development = None
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
                raw_action_domain = raw_actuation.get(
                    "action_domain"
                )
                if raw_action_domain is not None:
                    if (
                        not isinstance(raw_action_domain, dict)
                        or raw_action_domain.get("schema_version") != 1
                    ):
                        raise CheckpointError(
                            "invalid canonical action_domain checkpoint"
                        )
                    raw_evidence_state = raw_action_domain.get(
                        "actuator_evidence"
                    )
                    raw_selection_threshold = raw_action_domain.get(
                        "selection_threshold", 0.1
                    )
                    raw_sensorimotor = raw_action_domain.get(
                        "competence_development"
                    )
                    if not isinstance(raw_sensorimotor, dict):
                        raise CheckpointError(
                            "canonical action domain is missing competence_development"
                        )
                    raw_pending = raw_action_domain.get(
                        "pending_motor_observation"
                    )
                    raw_proprio = raw_action_domain.get(
                        "pending_proprioception", {}
                    )
                else:
                    # Migration-only path for pre-ActionDomain checkpoints.
                    raw_evidence_state = raw_actuation.get("proposer")
                    raw_selection_threshold = raw_actuation.get(
                        "selection_threshold", 0.1
                    )
                    raw_sensorimotor = raw_actuation.get("sensorimotor")
                    raw_pending = raw_actuation.get(
                        "pending_motor_observation"
                    )
                    raw_proprio = raw_actuation.get(
                        "pending_proprioception", {}
                    )
                if not isinstance(raw_evidence_state, dict):
                    raise CheckpointError(
                        "action domain actuator evidence is missing"
                    )
                try:
                    actuator_evidence = restore_actuation_state(
                        raw_evidence_state,
                        actuator_constitution,
                        organism_id=str(normalized.get("organism_id") or ""),
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CheckpointError(f"invalid actuator evidence checkpoint: {exc}") from exc
                if (
                    isinstance(raw_selection_threshold, bool)
                    or not isinstance(raw_selection_threshold, (int, float))
                    or not 0.0 <= float(raw_selection_threshold) <= 1.0
                ):
                    raise CheckpointError("invalid motor selection threshold")
                motor_selection_threshold = float(raw_selection_threshold)
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
                        competence_development = CompetenceDevelopmentEngine.restore(
                            raw_sensorimotor_restore,
                            actuator_ids=actuator_constitution.actuator_ids,
                            organism_id=str(normalized.get("organism_id") or ""),
                            embodiment_fingerprint=actuator_constitution.contract_fingerprint,
                        )
                    except (TypeError, ValueError, KeyError) as exc:
                        raise CheckpointError(
                            f"invalid sensorimotor checkpoint: {exc}"
                        ) from exc
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
        constructor_kwargs.pop("actuator_evidence", None)
        constructor_kwargs.pop("motor_selection_threshold", None)
        constructor_kwargs.pop("actuator_system", None)
        constructor_kwargs.pop("competence_development", None)
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
            actuator_evidence=actuator_evidence,
            motor_selection_threshold=motor_selection_threshold,
            competence_development=competence_development,
        )
        runtime._pending_motor_observation = pending_motor_observation
        runtime._pending_proprioception = pending_proprioception
        if isinstance(raw_actuation, dict):
            raw_action_domain = raw_actuation.get("action_domain")
            if isinstance(raw_action_domain, dict):
                raw_commitment = raw_action_domain.get(
                    "active_commitment"
                )
            else:
                raw_commitment = raw_actuation.get("action_commitment")
            if isinstance(raw_commitment, dict):
                current_surface = (
                    runtime._actuator_constitution.contract_fingerprint
                    if runtime._actuator_constitution is not None
                    else None
                )
                restored_commitment = ActionCommitment.restore(
                    raw_commitment,
                    fallback_surface_fingerprint=current_surface,
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
            raw_v2 = (
                raw_action_domain.get("sensorimotor_v2")
                if isinstance(raw_action_domain, dict)
                else raw_actuation.get("sensorimotor_v2")
            )
            if isinstance(raw_v2, dict):
                try:
                    runtime._action_domain.restore_v2(
                        raw_v2,
                        body_schema=runtime._body_schema,
                        fingerprint_migration=fingerprint_migration,
                    )
                except (TypeError, ValueError, KeyError) as exc:
                    raise CheckpointError(
                        f"invalid sensorimotor v2 checkpoint: {exc}"
                    ) from exc

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
        raw_last_primitive = None
        if isinstance(raw_actuation, dict):
            raw_action_domain = raw_actuation.get("action_domain")
            if isinstance(raw_action_domain, dict):
                raw_last_primitive = raw_action_domain.get(
                    "last_executed_controller_seed_id"
                )
            else:
                raw_last_primitive = raw_actuation.get(
                    "last_executed_primitive_id"
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
