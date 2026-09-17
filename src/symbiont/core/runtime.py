from __future__ import annotations

import json
import platform
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
from ..host.percepts import DEFAULT_PERCEPT_NAMES, Percept, synthesize_percepts
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
from ..cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ..cognition.genome import Genome, DevelopmentGenes, PlasticityGenes, RangeSpec
from ..cognition.graph import CognitiveGraph
from ..cognition.learning import ShadowPrediction
from ..cognition.limits import KernelLimits
from .attention import AttentionAllocation, attend_to_host
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
from .heredity import HeritableGenome
from .inheritance import EpigeneticPrior, mutate_genome
from .behavior import (ActionEvidence, ActionExecutionResult, ActionKind,
                        ActionOpportunity, ExpectedOutcome, SelectionResult,
                        LocalActionModel, InteroceptiveActionModel, select_action)
from .development import DevelopmentalSnapshot, DevelopmentalTracker
from ..cognition.birth import load_base_graph


def _parse_running_version(version_string: str) -> tuple[int, int, int]:
    parts = version_string.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)


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
    # Bounded lifecycle facts emitted by the subject runtime.  The laboratory
    # may project these into its own taxonomy, but must not manufacture them
    # from snapshots after the fact.
    runtime_events: tuple[str, ...] = ()


class OrganismDeadError(RuntimeError):
    """Raised when execution is requested after irreversible death."""


class OrganismRuntime:
    """Continuous cognitive cycle over safe local perceptions.

    In developmental mode discovery remains broad inside the provider's fixed safety
    boundary, while sampling becomes selective. Cognitive learning happens only
    after attention has been allocated for the current tick, so attention and the
    self-model can constrain plastic updates instead of merely describing them.
    """

    _SUPPORTED_EPIGENETIC_KEYS = frozenset({"exploration_bias"})

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
        autonomous_behavior: bool = False,
        behavior_exploration: float = 0.25,
        action_model: LocalActionModel | None = None,
        interoceptive_action_model: InteroceptiveActionModel | None = None,
        interoception_enabled: bool = True,
        interoception_mode: str | None = None,
        developmental_tracker: DevelopmentalTracker | None = None,
    ) -> None:
        if attention_budget <= 0.0:
            raise ValueError("attention_budget must be positive")
        if investigate_ticks < 0:
            raise ValueError("investigate_ticks must be non-negative (0 disables investigation)")
        if (tick_count < 0 or generation < 0 or reproduction_cost < 0.0
                or social_exchange_quantum <= 0.0 or social_exchange_cost < 0.0):
            raise ValueError("invalid tick, generation, reproduction cost, social quantum or social cost")
        if (isinstance(behavior_exploration, bool)
                or not math.isfinite(float(behavior_exploration))
                or not 0.0 <= behavior_exploration <= 1.0):
            raise ValueError("behavior_exploration must be within [0, 1]")

        discovery_providers: list[DiscoveryProvider] = []
        reading_providers: list[ReadingProvider] = []
        self._bootstrap_semantic_senses = bootstrap_semantic_senses
        self._adaptive_senses = adaptive_senses if adaptive_senses is not None else AdaptiveSenseModel()
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

        # Autonomous organisms receive their own bounded interoceptive surface
        # even when host-sense discovery is disabled.  Keeping this surface
        # separate from Linux discovery prevents the research subject from
        # gaining platform topology merely by being given a body.
        if ((discover_senses and platform.system() == "Linux")
                or (autonomous_behavior and interoception_enabled)):
            from ..host.providers.interoception import (
                InteroceptionProvider,
                ShamInteroceptionProvider,
            )

            if discover_senses and platform.system() == "Linux":
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
        self._action_evidence: list[ActionEvidence] = []
        # One-step delayed observation keeps learning causal: the model is
        # updated from the state after the action's next biological cycle,
        # not from the decision point that produced the action.
        self._pending_action_observation: tuple[ActionKind, str, tuple[float, float], ExpectedOutcome, float] | None = None
        self._autonomous_behavior = bool(autonomous_behavior)
        self._behavior_exploration = float(behavior_exploration)
        self._action_model = action_model if action_model is not None else LocalActionModel()
        self._interoceptive_action_model = (
            interoceptive_action_model if interoceptive_action_model is not None
            else InteroceptiveActionModel()
        )
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
        self._homeostasis = (
            homeostasis
            if homeostasis is not None
            else HomeostaticController(config=self._physiology_config)
        )
        self._physiology = physiology if physiology is not None else PhysiologyController()
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
        self._body_schema = body_schema if body_schema is not None else BodySchemaEngine()
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
        self._narrative_journal: list[dict[str, Any]] = []

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
            "explicit_metabolism": self._explicit_metabolism,
            "auto_promote_predictors": self._auto_promote_predictors,
            "generation": self._generation,
            "reproduction_cost": self._reproduction_cost,
            "social_exchange_quantum": self._social_exchange_quantum,
            "social_exchange_cost": self._social_exchange_cost,
            "resting_requested": self._resting_requested,
            "autonomous_behavior": self._autonomous_behavior,
            "behavior_exploration": self._behavior_exploration,
            "interoception_enabled": self._interoception_enabled,
            "interoception_mode": self._interoception_mode,
            "mutation_seed": self._mutation_seed,
            "epigenetic_decay": self._epigenetic_decay,
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

    def _exploration_with_prior(self) -> float:
        bias = sum(item.value for item in self._epigenetic_priors if item.key == "exploration_bias")
        exploration = self._behavior_exploration + 0.25 * bias
        # Interoception is supplied to the contextual action model in
        # ``action_opportunities``.  Do not also hard-code pressure as a
        # second exploration policy here: that would make the enabled arm
        # less exploratory by construction rather than letting experience
        # establish which actions work in each internal state.
        return max(0.0, min(1.0, exploration))

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

    def _observe_endogenous_reproductive_pressure(self) -> None:
        """Advance reproductive pressure from organism/environment state only.

        The evaluator may provide the habitat and its finite capacity, but it
        does not request reproduction.  This automatic path is enabled only
        for autonomous behavior and keeps the existing explicit study API
        available for controlled compatibility studies.
        """
        if self._reproductive_pressure is None or self._birth_authority is None:
            return
        graph = self._cognitive_bridge.graph if self._cognitive_bridge is not None else None
        reserve, integrity = self._behavior_state()
        # This pressure is developmental, not a report that the habitat is
        # already full.  Requiring a full birth authority here would make the
        # autonomous action impossible exactly when a slot is available.
        developmental_capacity_pressure = (
            reserve < 0.75 or integrity < 1.0
            or (graph is not None and len(graph.nodes) >= self._kernel_limits.max_nodes)
        )
        self.observe_reproductive_pressure(
            adaptive=bool(self._adaptive_senses.developed_percept_names()) or self._tick_count > 0,
            capacity_exhausted=developmental_capacity_pressure,
            blocked_growth=developmental_capacity_pressure,
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
            genome=child_genome,
            heritable_genome=inherited,
            mutation_seed=self._mutation_seed + self._generation + 1,
            epigenetic_priors=self._epigenetic_priors,
            epigenetic_decay=self._epigenetic_decay,
            kernel_limits=self._kernel_limits,
            cognitive_graph=graph,
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
            autonomous_behavior=self._autonomous_behavior,
            behavior_exploration=max(0.0, min(1.0, float(
                (dict(inherited.loci) if inherited is not None else {}).get(
                    "behavior_exploration", self._behavior_exploration)))),
            interoception_enabled=self._interoception_enabled,
            interoception_mode=self._interoception_mode,
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
        """Explicitly promote one validated shadow candidate, if eligible."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot promote predictions")
        if self._cognitive_bridge is None:
            return False
        return self._cognitive_bridge.promote_shadow_prediction(
            source_id, target_id, tick=self._tick_count
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

    def action_opportunities(self) -> tuple[ActionOpportunity, ...]:
        """Expose bounded local possibilities without choosing or executing one.

        This is the first bridge from biological state to endogenous behaviour.
        It contains only state already available to the organism and local
        authorization checks; it never includes evaluator fitness or a target
        selected by the laboratory.  The ordinary tick remains unchanged until
        an execution contract for these opportunities is closed.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms have no action opportunities")
        metabolic = self._metabolism.snapshot()
        reserve = min(
            metabolic.reserve[k] / max(metabolic.capacity[k], 1e-12)
            for k in metabolic.capacity
        )
        opportunities: list[ActionOpportunity] = [
            ActionOpportunity(
                action_id="wait", kind=ActionKind.WAIT, authorized=True,
                preconditions_met=True,
                expected=ExpectedOutcome(
                    viability=0.0, integrity=0.0,
                    resource_change=0.0, information_gain=0.0,
                    uncertainty_reduction=0.0, reproductive_feasibility=0.0,
                    social_expectation=0.0,
                ), cost=0.0,
            ),
            ActionOpportunity(
                action_id="rest", kind=ActionKind.REST, authorized=True,
                # Pressure changes the locally predicted consequence, not the
                # available action set.  Blocking rest/observation/intake from
                # a threshold here would turn interoception into a hidden
                # policy instead of a learned sense.  Only hard viability and
                # authorization guards may remove an opportunity.
                preconditions_met=True,
                expected=ExpectedOutcome(
                    viability=0.1, integrity=0.05,
                    resource_change=0.0, information_gain=0.0,
                    uncertainty_reduction=0.0, reproductive_feasibility=0.0,
                    social_expectation=0.0,
                ), cost=0.02,
            ),
        ]
        # Observation is an endogenous opportunity as well as a passive input
        # to the ordinary tick. Keeping it in the same local frontier lets
        # the organism trade information-seeking against intake, repair and
        # rest without introducing a planner or an external objective.
        opportunities.append(ActionOpportunity(
            action_id="observe", kind=ActionKind.OBSERVE,
            authorized=True, preconditions_met=True,
            expected=ExpectedOutcome(
                viability=0.0, integrity=0.0, resource_change=-0.01,
                information_gain=0.2, uncertainty_reduction=0.1,
                reproductive_feasibility=0.0, social_expectation=0.0,
            ), cost=0.05, novelty=0.5, uncertainty=0.5,
        ))
        intake_habitats = (
            tuple(self._resource_habitats.items())
            if self._resource_habitats else
            ((None, self._habitat),) if self._habitat is not None else ()
        )
        for resource_id, intake_habitat in intake_habitats:
            if intake_habitat is None:
                continue
            habitat_snapshot = intake_habitat.snapshot()
            action_id = "intake" if resource_id is None else f"intake:{resource_id}"
            opportunities.append(ActionOpportunity(
                action_id=action_id, kind=ActionKind.INTAKE,
                authorized=True, preconditions_met=(habitat_snapshot.available_resources > 0.0
                                                    and reserve < 1.0),
                expected=ExpectedOutcome(
                    viability=0.05,
                    # Predict the bounded intake quantum, not the entire free
                    # pool exposed by the habitat.
                    integrity=0.05,
                    resource_change=(min(0.1, habitat_snapshot.available_resources
                                         / intake_habitat.acquisition_cost)
                                     * intake_habitat.physiological_usefulness),
                    information_gain=intake_habitat.information_content,
                    uncertainty_reduction=0.0,
                    reproductive_feasibility=0.1 if reserve < 0.5 else 0.0,
                    social_expectation=0.0,
                ), cost=0.01,
            ))
        # Do not expose integrity as an action-availability oracle.  In the
        # absent-interoception arm, making ``repair`` disappear when the body
        # is intact would itself be an internal-state sensor.  The action is
        # therefore always available when maintenance reserve permits it;
        # executing it against an intact body is a valid local no-op and the
        # outcome learner can discover that consequence.
        expected_repair = min(0.1, max(0.0, 1.0 - self._homeostasis.integrity))
        opportunities.append(ActionOpportunity(
            action_id="repair", kind=ActionKind.REPAIR, authorized=True,
            preconditions_met=metabolic.reserve["maintenance"] > 0.0,
            expected=ExpectedOutcome(
                viability=0.25,
                # Predict only the bounded local recovery quantum.  This is
                # an expected consequence, not an availability predicate:
                # the same action remains exposed when intact and can be
                # learned as a maintenance no-op.
                integrity=expected_repair,
                resource_change=-0.1,
                information_gain=0.0, uncertainty_reduction=0.0,
                reproductive_feasibility=0.0, social_expectation=0.0,
            ),
            # Repair is an endogenous but initially unlearned option.  Giving
            # it bounded uncertainty lets exploration test its consequences;
            # the learned contextual model can subsequently retain or reject
            # it.  This is not a reserve threshold or rescue command.
            novelty=1.0, uncertainty=1.0, cost=0.1,
        ))
        if self._reproductive_pressure is not None:
            ready = self._reproductive_pressure.blocked_ticks >= self._reproductive_pressure.threshold_ticks
            birth_available = (
                self._birth_authority is not None
                and len(self._birth_authority.live_ids) < self._birth_authority.capacity
                and self._birth_authority.resource_budget >= 1.0
                and self._birth_surfaces_available()
            )
            opportunities.append(ActionOpportunity(
                action_id="reproduce", kind=ActionKind.REPRODUCE, authorized=birth_available,
                # A damaged body cannot spend reproductive reserve while its
                # local integrity is below the maintenance threshold.  This
                # is an endogenous safety precondition, not an evaluator
                # fitness rule; repair remains a competing local action.
                preconditions_met=(ready and self._reproductive_pressure.reserve > 0.0
                                   and self._homeostasis.integrity >= 0.9),
                expected=ExpectedOutcome(
                    viability=-min(1.0, self._reproduction_cost), integrity=-min(1.0, self._reproduction_cost),
                    resource_change=-min(1.0, self._reproduction_cost), information_gain=0.0,
                    uncertainty_reduction=0.0, reproductive_feasibility=1.0,
                    social_expectation=0.0,
                ), cost=min(1.0, self._reproduction_cost),
            ))
        if self._social_habitat is not None:
            presence = tuple(item for item in self.observe_social_presence() if item.available)
            opportunities.append(ActionOpportunity(
            action_id="social_exchange", kind=ActionKind.SOCIAL_EXCHANGE,
                authorized=True, preconditions_met=bool(presence and self._social_habitat.resource_tokens),
                expected=ExpectedOutcome(
                    viability=0.0, integrity=0.0, resource_change=0.0,
                    information_gain=0.2 if presence else 0.0,
                    uncertainty_reduction=0.1 if presence else 0.0,
                    reproductive_feasibility=0.0, social_expectation=0.1 if presence else 0.0,
                ), cost=min(1.0, self._social_exchange_cost), novelty=1.0 if presence else 0.0,
                uncertainty=1.0 if presence else 0.0,
            ))
            # Competition is exposed only when the organism's own relation
            # ledger contains negative evidence and the habitat can adjudicate
            # a bounded request.  The evaluator does not choose a target or
            # inject a competition label.
            competition = self.propose_social_competition()
            if competition is not None:
                opportunities.append(ActionOpportunity(
                    action_id="compete", kind=ActionKind.COMPETE,
                    authorized=True, preconditions_met=True,
                    expected=ExpectedOutcome(
                        viability=0.0, integrity=0.0, resource_change=0.0,
                        information_gain=0.15, uncertainty_reduction=0.1,
                        reproductive_feasibility=0.0, social_expectation=-0.1,
                    ), cost=min(1.0, self._social_exchange_cost),
                    novelty=0.5, uncertainty=0.75,
                ))
        adjusted = tuple(self._action_model.adjust(item) for item in opportunities)
        if self._interoception_provider is None:
            return adjusted
        signal = self._interoception_provider.local_action_pressure()
        return tuple(self._interoceptive_action_model.adjust(item, signal=signal)
                     for item in adjusted)

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

    def select_local_action(self, *, exploration: float = 0.0) -> SelectionResult:
        """Select, but do not execute, one organism-local opportunity."""
        return select_action(self.action_opportunities(), exploration=exploration)

    def autonomous_action_step(self, *, exploration: float = 0.0,
                               intake_amount: float = 0.1,
                               repair_amount: float = 0.1) -> ActionExecutionResult:
        """Perform one complete local perceive-select-execute step.

        This is intentionally a separate bounded step rather than an implicit
        addition to ``tick``.  A longitudinal harness can place it at an
        explicit causal point and record the resulting observation before the
        next decision; existing host observation semantics remain unchanged.
        """
        selection = self.select_local_action(exploration=exploration)
        if selection.selected is None:
            return ActionExecutionResult("none", False, reason="no_available_opportunity")
        return self.execute_local_action(
            selection.selected,
            intake_amount=intake_amount,
            repair_amount=repair_amount,
        )

    def execute_local_action(self, opportunity: ActionOpportunity, *,
                             intake_amount: float = 0.1, repair_amount: float = 0.1) -> ActionExecutionResult:
        """Execute one freshly validated local opportunity through runtime APIs.

        The opportunity is revalidated immediately before effects are applied;
        a stale choice cannot bypass a changed habitat or physiology state.
        Unsupported observation actions remain explicit no-ops until their
        causal execution contract is specified.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot execute actions")
        if not isinstance(opportunity, ActionOpportunity):
            raise TypeError("opportunity must be an ActionOpportunity")
        self._settle_pending_action_observation()
        current = {item.action_id: item for item in self.action_opportunities()}
        fresh = current.get(opportunity.action_id)
        if (fresh is None or fresh.kind is not opportunity.kind or
                not opportunity.authorized or not opportunity.preconditions_met or
                not fresh.authorized or not fresh.preconditions_met):
            return self._finish_action(opportunity, ActionExecutionResult(
                opportunity.action_id, False, reason="stale_or_unavailable"
            ), "rejected")
        before_state = self._behavior_state()
        decision_signal = (
            self._interoception_provider.local_action_pressure()
            if self._interoception_provider is not None else 0.0
        )
        if fresh.kind is ActionKind.WAIT:
            return self._finish_action(fresh, ActionExecutionResult(fresh.action_id, True), "wait", before_state, decision_signal)
        if fresh.kind is ActionKind.REST:
            self.request_rest()
            return self._finish_action(fresh, ActionExecutionResult(fresh.action_id, True), "rest_requested", before_state, decision_signal)
        if fresh.kind is ActionKind.OBSERVE:
            # The current tick's observation has already crossed the host
            # boundary above. This records the local information-seeking
            # choice without performing a second unbounded read.
            return self._finish_action(fresh, ActionExecutionResult(
                fresh.action_id, True
            ), "observation", before_state, decision_signal)
        if fresh.kind is ActionKind.INTAKE:
            resource_id = None
            if fresh.action_id.startswith("intake:"):
                resource_id = fresh.action_id.split(":", 1)[1]
            # Intake is a local resource-allocation act: the organism fills
            # the most depleted compartment rather than receiving a fixed
            # apparatus-selected destination.
            intake_kind = self._most_depleted_metabolic_kind()
            return self._finish_action(fresh, ActionExecutionResult(
                fresh.action_id, True, self.request_resource_intake(
                    intake_amount, kind=intake_kind, resource_id=resource_id
                )
            ), "intake", before_state, decision_signal)
        if fresh.kind is ActionKind.REPAIR:
            return self._finish_action(fresh, ActionExecutionResult(fresh.action_id, True, self.repair(repair_amount)), "repair", before_state, decision_signal)
        if fresh.kind is ActionKind.SOCIAL_EXCHANGE:
            outcome = self.autonomous_social_step()
            if outcome is None:
                return self._finish_action(fresh, ActionExecutionResult(
                    fresh.action_id, False, reason="social_opportunity_unavailable"
                ), "social_exchange_unavailable", before_state, decision_signal)
            return self._finish_action(fresh, ActionExecutionResult(
                fresh.action_id, True, outcome
            ), "social_exchange", before_state, decision_signal)
        if fresh.kind is ActionKind.COMPETE:
            proposal = self.propose_social_competition()
            if proposal is None:
                return self._finish_action(fresh, ActionExecutionResult(
                    fresh.action_id, False, reason="competition_opportunity_unavailable"
                ), "competition_unavailable", before_state, decision_signal)
            outcome = self.request_social_competition([(
                proposal.source_id, proposal.resource, proposal.amount
            )])
            return self._finish_action(fresh, ActionExecutionResult(
                fresh.action_id, True, outcome
            ), "competition", before_state, decision_signal)
        if fresh.kind is ActionKind.REPRODUCE:
            child = self.materialize_clonal_bud()
            if child is None:
                return self._finish_action(fresh, ActionExecutionResult(
                    fresh.action_id, False, reason="birth_denied"
                ), "reproduction_denied", before_state, decision_signal)
            return self._finish_action(fresh, ActionExecutionResult(
                fresh.action_id, True, child
            ), "reproduction", before_state, decision_signal)
        return self._finish_action(fresh, ActionExecutionResult(
            fresh.action_id, False, reason="execution_contract_pending"
        ), "pending", before_state, decision_signal)

    def _finish_action(self, opportunity: ActionOpportunity,
                       result: ActionExecutionResult, outcome: str,
                       before_state: tuple[float, float] | None = None,
                       decision_signal: float | None = None) -> ActionExecutionResult:
        self._action_evidence.append(ActionEvidence(
            tick=self._tick_count, action_id=opportunity.action_id,
            kind=opportunity.kind, executed=result.executed,
            outcome=outcome, reason=result.reason,
        ))
        del self._action_evidence[:-128]
        if before_state is not None:
            if result.executed:
                signal = decision_signal if decision_signal is not None else 0.0
                self._pending_action_observation = (
                    opportunity.kind, opportunity.action_id, before_state, opportunity.expected, signal
                )
            else:
                self._action_model.observe(opportunity.kind, executed=False, action_id=opportunity.action_id)
        return result

    def _settle_pending_action_observation(self) -> None:
        pending = self._pending_action_observation
        if pending is None:
            return
        self._pending_action_observation = None
        kind, action_id, before_state, expected, signal = pending
        reserve, integrity = self._behavior_state()
        self._action_model.observe(
            kind, executed=True,
            resource_delta=reserve - before_state[0],
            integrity_delta=integrity - before_state[1],
            expected=expected,
            action_id=action_id,
        )
        if self._interoception_provider is not None:
            self._interoceptive_action_model.observe(
                signal, kind, executed=True,
                resource_delta=reserve - before_state[0],
                integrity_delta=integrity - before_state[1],
                expected=expected,
                action_id=action_id,
            )

    def _behavior_state(self) -> tuple[float, float]:
        metabolic = self._metabolism.snapshot()
        reserve = min(
            metabolic.reserve[k] / max(metabolic.capacity[k], 1e-12)
            for k in metabolic.capacity
        )
        return (max(0.0, min(1.0, reserve)), max(0.0, min(1.0, self._homeostasis.integrity)))

    @property
    def action_evidence(self) -> tuple[ActionEvidence, ...]:
        return tuple(self._action_evidence)

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
        self._settle_pending_action_observation()
        # Rest is a biological episode, not a permanent administrative mode.
        # Autonomous rest therefore applies to the cycle in which it was
        # selected and is cleared before the next local decision.  Explicit
        # callers retain the existing persistent request semantics.
        if self._autonomous_behavior and self._resting_requested:
            self._resting_requested = False
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
        semantic_names = DEFAULT_PERCEPT_NAMES if self._bootstrap_semantic_senses else {}
        habitat_names = {
            f"habitat_surface.{resource_id}": self._signal_identity.signal_id(resource_id)
            for resource_id in self._resource_habitats
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
            if self._autonomous_behavior and reading.source == "interoception"
        }

        selected_names: dict[str, str] = dict(semantic_names)
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

        percepts = synthesize_percepts(cognitive_readings, percept_names=percept_names)
        self._acclimation.observe(cognitive_readings)
        self._rhythm_model.observe(percepts, time_bucket=current_time_bucket())

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
            )
            if self._auto_promote_predictors:
                for candidate in self._cognitive_bridge.shadow_predictions:
                    self._cognitive_bridge.promote_shadow_prediction(
                        candidate.source_id, candidate.target_id, tick=self._tick_count + 1
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
        # and cognition.  The pending action evidence was settled at entry, so
        # this placement preserves the one-tick causal delay without allowing
        # an outcome to retroactively affect the decision that produced it.
        if self._autonomous_behavior:
            self._observe_endogenous_reproductive_pressure()
            action_result = self.autonomous_action_step(
                exploration=self._exploration_with_prior()
            )
            # A live autonomous cycle has a bounded basal cost even when no
            # host percept or graph mutation occurs. Without this floor an
            # empty germinal graph could survive indefinitely without resource
            # exchange, making mortality an artifact of workload.
            self._charge_metabolism("maintenance", 0.01)

        # BodySchema receives two bounded organism-owned evidence surfaces:
        # sensory SelfModel classes and opaque dynamic cognitive channels. It
        # never sees host manifest truth, CognitiveGraph nodes/edges or
        # Observatory topology.
        self._body_schema.observe_self_model(
            self._self_model.export(current_tick=self._tick_count),
            tick=self._tick_count,
        )
        if self._explicit_metabolism:
            for decision in assimilation:
                if decision.action.value == "incorporate":
                    intake_amount = float(decision.utility) * 0.02
                    self._metabolism.intake("persistence", intake_amount)
                    self._metabolism.intake("observation", intake_amount * 0.5)

            if cognition_result is not None and getattr(cognition_result, "prediction_errors", None):
                mean_err = sum(abs(e.error) for e in cognition_result.prediction_errors) / len(cognition_result.prediction_errors)
                accuracy = max(0.0, 1.0 - mean_err)
                if accuracy > 0.5:
                    self._metabolism.intake("cognition", accuracy * 0.02)
                    self._metabolism.intake("maintenance", accuracy * 0.01)

        retained_units = float(len(self._drift_baselines)) * 0.001
        if self._cognitive_bridge is not None and self._cognitive_bridge.graph is not None:
            retained_units += float(len(self._cognitive_bridge.graph.nodes)) * 0.0005
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
        if self._autonomous_behavior:
            self._resting_requested = False
        topology = getattr(self._cognitive_bridge, "topology_health", None)
        topology_health = (
            getattr(topology, "value", str(topology))
            if topology is not None else ("developing" if self._cognitive_bridge is not None else "germinal")
        )
        development_snapshot = self._developmental_tracker.observe(
            state=physiology_snapshot.state.value,
            integrity=self._homeostasis.integrity,
            topology_health=topology_health,
            sensory_count=len(self._adaptive_senses.developed_percept_names()),
            action_attempts=self._action_model.attempts,
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
            cognition=cognition_result,
            signal_knowledge=self._signal_knowledge.view(),
            knowledge_events=self._signal_knowledge.drain_events(),
            signal_references={name: self._signal_identity.signal_id(capability_id) for capability_id, name in percept_names.items()},
            metabolism=metabolism_snapshot,
            assimilation=tuple(assimilation),
            homeostasis=homeostatic_snapshot,
            physiology=physiology_snapshot,
            degradation_excreted=degradation_excreted,
            retained_items=len(self._degradation.items),
            action_result=action_result,
            development=development_snapshot,
            runtime_events=tuple(dict.fromkeys(runtime_events)),
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
        payload["memory"] = self._memory_consolidator.export_checkpoint()
        knowledge_payload = self._signal_knowledge.checkpoint()
        knowledge_size = len(json.dumps(knowledge_payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        if knowledge_size > MAX_KNOWLEDGE_CHECKPOINT_BYTES:
            raise CheckpointError("signal knowledge checkpoint exceeds 256 KiB")
        payload["signal_knowledge"] = knowledge_payload
        payload["signal_identity_key"] = self._signal_identity.key.hex()
        payload["metabolism"] = self._metabolism.checkpoint()
        payload["assimilation"] = self._assimilator.checkpoint()
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
        payload["degradation"] = self._degradation.checkpoint()
        payload["reproductive_pressure"] = (
            {"threshold_ticks": self._reproductive_pressure.threshold_ticks,
             "reserve": self._reproductive_pressure.reserve,
             "blocked_ticks": self._reproductive_pressure.blocked_ticks}
            if self._reproductive_pressure is not None else None
        )
        payload["narrative_journal"] = list(self._narrative_journal[-50:])
        payload["action_evidence"] = [item.checkpoint() for item in self._action_evidence]
        payload["action_model"] = self._action_model.checkpoint()
        payload["interoceptive_action_model"] = self._interoceptive_action_model.checkpoint()
        payload["development"] = self._developmental_tracker.checkpoint()
        payload["last_runtime_vital_state"] = self._last_runtime_vital_state
        payload["last_runtime_development_phase"] = self._last_runtime_development_phase
        payload["first_life_history_events"] = {
            "sense": self._first_sense_emitted,
            "concept": self._first_concept_emitted,
            "prediction": self._first_prediction_emitted,
        }
        pending = self._pending_action_observation
        if pending is not None:
            kind, action_id, before, expected, signal = pending
            payload["pending_action_observation"] = {
                "kind": kind.value, "action_id": action_id,
                "before_reserve": before[0], "before_integrity": before[1],
                "signal": signal,
                "expected": {
                    "viability": expected.viability,
                    "integrity": expected.integrity,
                    "resource_change": expected.resource_change,
                },
            }
        else:
            payload["pending_action_observation"] = None
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
        allowed_sense_ids = set(adaptive_senses.developed_percept_names())
        if kwargs.get("bootstrap_semantic_senses", True):
            allowed_sense_ids.update(DEFAULT_PERCEPT_NAMES)
        self_model = SelfModel.restore(
            normalized.get("self_model"),
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
        homeostasis = (
            HomeostaticController.from_checkpoint(normalized["homeostasis"], config=resolved_physiology_config)
            if normalized.get("homeostasis")
            else HomeostaticController(config=resolved_physiology_config)
        )
        physiology = PhysiologyController.from_checkpoint(normalized["physiology"]) if normalized.get("physiology") else PhysiologyController()
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
        effective = normalized.get("effective_config", {})
        for name in ("attention_budget", "investigate_ticks", "discover_senses", "bootstrap_semantic_senses",
                     "autonomous_behavior", "behavior_exploration", "interoception_enabled",
                     "interoception_mode", "conflict_z", "min_samples"):
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
        )
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
        try:
            runtime._action_evidence = ActionEvidence.restore_many(normalized.get("action_evidence"))
            runtime._action_model = LocalActionModel.from_checkpoint(normalized.get("action_model"))
            runtime._interoceptive_action_model = InteroceptiveActionModel.from_checkpoint(
                normalized.get("interoceptive_action_model")
            )
            raw_pending = normalized.get("pending_action_observation")
            if raw_pending is not None:
                if not isinstance(raw_pending, dict):
                    raise ValueError("pending action observation must be an object")
                kind = ActionKind(raw_pending["kind"])
                before_reserve = raw_pending["before_reserve"]
                before_integrity = raw_pending["before_integrity"]
                raw_expected = raw_pending["expected"]
                signal = raw_pending.get("signal", 0.0)
                action_id = raw_pending.get("action_id", kind.value)
                if (not isinstance(action_id, str) or not action_id or len(action_id) > 96):
                    raise ValueError("invalid pending action identifier")
                if not isinstance(raw_expected, dict):
                    raise ValueError("pending action expected outcome must be an object")
                expected = ExpectedOutcome(
                    viability=raw_expected["viability"], integrity=raw_expected["integrity"],
                    resource_change=raw_expected["resource_change"], information_gain=0.0,
                    uncertainty_reduction=0.0, reproductive_feasibility=0.0,
                    social_expectation=0.0,
                )
                if any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0
                    for value in (before_reserve, before_integrity)
                ):
                    raise ValueError("invalid pending action observation state")
                if (isinstance(signal, bool) or not isinstance(signal, (int, float))
                        or not math.isfinite(float(signal)) or not 0.0 <= float(signal) <= 1.0):
                    raise ValueError("invalid pending interoceptive signal")
                runtime._pending_action_observation = (
                    kind, action_id,
                    (float(before_reserve), float(before_integrity)), expected, float(signal)
                )
        except ValueError as exc:
            raise CheckpointError(str(exc)) from exc
        return runtime

    @classmethod
    def load_or_create(cls, path: str | Path, **kwargs: Any) -> "OrganismRuntime":
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
