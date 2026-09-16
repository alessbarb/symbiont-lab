from __future__ import annotations

import json
import platform
import uuid
from dataclasses import dataclass
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
from ..host.readings import HostSampler, ReadingProvider
from ..host.rhythms import RhythmModel
from ..host.second_look import SecondLookSession
from ..cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from ..cognition.genome import Genome
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
from .physiology import PhysiologyController, PhysiologySnapshot, VitalState
from .signal_knowledge_checkpoint import validate_checkpoint
from .metabolism import MetabolicLedger, MetabolicSnapshot
from .assimilation import InformationAssimilator, AssimilationDecision
from .homeostasis import HomeostaticController, HomeostaticSnapshot
from .ecology import SharedHabitat
from .social import (InteractionOutcome, RelationLedger, RelationValence,
                     SocialCompetitionRequest, SocialHabitat, SocialPresence)
from .birth_authority import BirthRecord, HabitatBirthAuthority
from .reproduction import ReproductivePressure, ReproductiveStatus, clonal_bud
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


class OrganismDeadError(RuntimeError):
    """Raised when execution is requested after irreversible death."""


class OrganismRuntime:
    """Continuous cognitive cycle over safe local perceptions.

    In developmental mode discovery remains broad inside the provider's fixed safety
    boundary, while sampling becomes selective. Cognitive learning happens only
    after attention has been allocated for the current tick, so attention and the
    self-model can constrain plastic updates instead of merely describing them.
    """

    def __init__(
        self,
        *,
        discovery_policy: DiscoveryPolicy | None = None,
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
        habitat: SharedHabitat | None = None,
        social_habitat: SocialHabitat | None = None,
        social_ledger: RelationLedger | None = None,
        explicit_metabolism: bool = False,
        auto_promote_predictors: bool = False,
        reproductive_pressure: ReproductivePressure | None = None,
        birth_authority: HabitatBirthAuthority | None = None,
        generation: int = 0,
        reproduction_cost: float = 0.1,
        social_exchange_quantum: float = 0.1,
        resting_requested: bool = False,
    ) -> None:
        if attention_budget <= 0.0:
            raise ValueError("attention_budget must be positive")
        if investigate_ticks < 0:
            raise ValueError("investigate_ticks must be non-negative (0 disables investigation)")
        if tick_count < 0 or generation < 0 or reproduction_cost < 0.0 or social_exchange_quantum <= 0.0:
            raise ValueError("invalid tick, generation, reproduction cost or social exchange quantum")

        discovery_providers: list[DiscoveryProvider] = []
        reading_providers: list[ReadingProvider] = []
        self._bootstrap_semantic_senses = bootstrap_semantic_senses
        self._adaptive_senses = adaptive_senses if adaptive_senses is not None else AdaptiveSenseModel()
        self._discover_senses = discover_senses

        if bootstrap_semantic_senses:
            discovery_providers.append(StandardLibraryProvider())
            reading_providers.append(StandardLibraryReadingProvider())

        if discover_senses and platform.system() == "Linux":
            from ..host.providers.linux_surfaces import LinuxSurfaceProvider

            linux_provider = LinuxSurfaceProvider()
            discovery_providers.append(linux_provider)
            reading_providers.append(linux_provider)

        self._reading_providers = tuple(reading_providers)
        self._lifecycle = HostLifecycle(
            discovery=HostDiscovery(providers=tuple(discovery_providers), policy=discovery_policy),
            reading_providers=self._reading_providers,
        )
        self._acclimation = acclimation if acclimation is not None else HostAcclimation(min_samples=min_samples)
        self._rhythm_model = rhythm_model if rhythm_model is not None else RhythmModel(min_samples=min_samples)
        self._drift_baselines = dict(drift_baselines) if drift_baselines is not None else {}
        self._evidence_ledger = (
            evidence_ledger if evidence_ledger is not None else EvidenceRevisionLedger(conflict_z=conflict_z)
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
        self._generation = generation
        self._reproduction_cost = float(reproduction_cost)
        self._social_exchange_quantum = float(social_exchange_quantum)
        self._resting_requested = bool(resting_requested)
        self._metabolism = metabolism if metabolism is not None else MetabolicLedger(
            replenishment=({k: 0.0 for k in ("observation", "cognition", "persistence", "maintenance")}
                           if self._explicit_metabolism else None)
        )
        self._assimilator = assimilator if assimilator is not None else InformationAssimilator()
        self._homeostasis = homeostasis if homeostasis is not None else HomeostaticController()
        self._physiology = physiology if physiology is not None else PhysiologyController()
        self._habitat = habitat
        self._social_habitat = social_habitat
        self._social_ledger = social_ledger if social_ledger is not None else RelationLedger()
        self._social_habitat_released = False
        self._habitat_released = False
        self._birth_authority_released = False
        if self._habitat is not None and not self._habitat.has_allocation(self._organism_id):
            self._habitat.admit(self._organism_id, 1.0)
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
                graph=cognitive_graph, genome=genome, kernel_limits=self._kernel_limits
            )

    @property
    def organism_id(self) -> str:
        return self._organism_id

    def _charge_metabolism(self, kind: str, amount: float) -> None:
        """Charge declared work, reducing activity while physiologically dormant."""
        factor = 0.25 if self._physiology.state is VitalState.DORMANT else 1.0
        self._metabolism.charge(kind, amount * factor)

    def effective_configuration(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "organism_id": self._organism_id,
            "attention_budget": self._attention_budget,
            "investigate_ticks": self._investigate_ticks,
            "discover_senses": self._discover_senses,
            "bootstrap_semantic_senses": self._bootstrap_semantic_senses,
            "explicit_metabolism": self._explicit_metabolism,
            "auto_promote_predictors": self._auto_promote_predictors,
            "generation": self._generation,
            "reproduction_cost": self._reproduction_cost,
            "social_exchange_quantum": self._social_exchange_quantum,
            "resting_requested": self._resting_requested,
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
            config["kernel_limits"] = {
                "max_nodes": self._kernel_limits.max_nodes,
                "max_edges": self._kernel_limits.max_edges,
                "max_concepts": self._kernel_limits.max_concepts,
                "max_structural_mutations_per_consolidation": self._kernel_limits.max_structural_mutations_per_consolidation,
            }
        return config

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
        by_target = {item.target_id: item for item in self._social_ledger.relations
                     if item.source_id == self._organism_id}

        def priority(item: SocialPresence) -> tuple[float, str]:
            relation = by_target.get(item.target_id)
            if relation is None:
                # Unknown channels receive an exploration bonus.  This is a
                # local information-seeking capability, not an evaluator
                # supplied preference or a social label.
                return (-0.25, item.target_id)
            freshness = relation.freshness(self._tick_count)
            confidence = min(1.0, relation.observations / 8.0)
            expected_net = (relation.support - relation.harm) * confidence * freshness
            exploration = 1.0 / (1.0 + relation.observations)
            # Positive evidence makes a channel worth revisiting; accumulated
            # harm lowers its priority without making it unreachable, allowing
            # later evidence to revise the relation.
            return (-(expected_net + 0.25 * exploration), item.target_id)

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
        self._social_ledger.observe(self._organism_id, target_id, benefit=outcome.granted,
                                    tick=self._tick_count)
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
        return self.request_social_exchange(
            opportunity.target_id, resources[0], self._social_exchange_quantum
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
        opportunity = self.select_social_opportunity()
        relation = next((item for item in self._social_ledger.relations
                         if item.source_id == self._organism_id
                         and opportunity is not None
                         and item.target_id == opportunity.target_id), None)
        resources = self._social_habitat.resource_tokens
        if (opportunity is None or relation is None
                or relation.valence is not RelationValence.NEGATIVE or not resources):
            return None
        return SocialCompetitionRequest(self._organism_id, resources[0], self._social_exchange_quantum)

    def suspend_social_interaction(self, target_id: str) -> None:
        """Suspend this runtime's future requests to one admitted peer."""
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot suspend social interactions")
        if self._social_habitat is None:
            raise ValueError("no social habitat is attached")
        self._social_habitat.suspend(self._organism_id, target_id)

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
        requested = {(source, resource): amount for source, resource, amount in requests}
        for outcome in outcomes:
            loss = max(0.0, requested.get((outcome.source_id, outcome.resource), outcome.granted) - outcome.granted)
            # The habitat relation records which competing peer was observed;
            # retain that target rather than collapsing scarcity onto the
            # habitat token in the runtime's local memory.
            self._social_ledger.observe(outcome.source_id, outcome.relation.target_id,
                                        cost=loss, tick=self._tick_count)
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

    def attempt_clonal_bud(self) -> BirthRecord | None:
        """Materialize one child only through the explicitly supplied authority."""
        if self._birth_authority is None or self._reproductive_pressure is None or self._genome is None:
            return None
        record = clonal_bud(parent_id=self._organism_id, genome_id=self._genome.genome_id,
                            generation=self._generation, authority=self._birth_authority,
                            pressure=self._reproductive_pressure)
        if record is not None and self._reproduction_cost:
            self._metabolism.charge("maintenance", self._reproduction_cost)
        return record

    def materialize_clonal_bud(self) -> "OrganismRuntime | None":
        """Create a fresh germinal runtime for an authorized clonal birth.

        Acquired phenotype, memory, metabolism and physiology are not copied;
        only the inherited genome and lineage identity cross the birth boundary.
        """
        record = self.attempt_clonal_bud()
        if record is None or self._genome is None or self._birth_authority is None:
            return None
        graph = load_base_graph(kernel_limits=self._kernel_limits)
        return OrganismRuntime(
            attention_budget=self._attention_budget,
            investigate_ticks=self._investigate_ticks,
            conflict_z=2.0,
            min_samples=5,
            discover_senses=self._discover_senses,
            bootstrap_semantic_senses=self._bootstrap_semantic_senses,
            genome=self._genome,
            kernel_limits=self._kernel_limits,
            cognitive_graph=graph,
            organism_id=record.organism_id,
            birth_authority=self._birth_authority,
            generation=record.generation,
            social_habitat=self._social_habitat,
            reproductive_pressure=(
                ReproductivePressure(threshold_ticks=self._reproductive_pressure.threshold_ticks)
                if self._reproductive_pressure is not None else None
            ),
            explicit_metabolism=self._explicit_metabolism,
            reproduction_cost=self._reproduction_cost,
            social_exchange_quantum=self._social_exchange_quantum,
        )

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

    def request_resource_intake(self, amount: float, *, kind: str = "maintenance") -> float:
        """Acquire bounded resource from the attached shared habitat.

        Habitat scarcity is authoritative; only the granted amount enters the
        organism's metabolic reserve. This is an explicit local request, not an
        automatic replenishment or evaluator intervention.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot acquire resources")
        if self._habitat is None:
            raise ValueError("no shared habitat is attached")
        granted = self._habitat.consume(self._organism_id, amount)
        return self._metabolism.intake(kind, granted)

    @property
    def assimilator(self) -> InformationAssimilator:
        return self._assimilator

    @property
    def homeostasis(self) -> HomeostaticController:
        return self._homeostasis

    @property
    def resting_requested(self) -> bool:
        return self._resting_requested

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
        if self._reacclimation_remaining > 0:
            self._reacclimation_remaining -= 1

        snapshot = self._lifecycle.tick(
            sampling_selector=self._sampling_selector if self._discover_senses else None
        )
        readings_by_capability = {reading.capability_id: reading for reading in snapshot.readings}
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
        # Runtime ticks are the authoritative monotonic clock; test/fixture
        # lifecycles may reuse a snapshot tick while the organism continues.
        candidate_pairs = tuple(
            (self._signal_identity.signal_id(relation.sense_a), self._signal_identity.signal_id(relation.sense_b))
            for relation in self._adaptive_senses.strongest_relations(limit=64)
            if relation.sense_a != relation.sense_b
        )
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
        self._charge_metabolism("observation", len(snapshot.readings) * 0.01)
        sampling_plan = self._adaptive_senses.last_sampling_plan if self._discover_senses else None

        self._adaptive_senses.observe(snapshot.readings)
        for outcome in snapshot.sampling_outcomes:
            self._self_model.observe(outcome=outcome, tick=self._tick_count)
        for evicted_name in self._adaptive_senses.drain_evicted_percept_names():
            self._drift_baselines.pop(evicted_name, None)

        active_learned_names = self._adaptive_senses.percept_names() if self._discover_senses else {}
        developed_names = self._adaptive_senses.developed_percept_names() if self._discover_senses else {}
        semantic_names = DEFAULT_PERCEPT_NAMES if self._bootstrap_semantic_senses else {}

        selected_names: dict[str, str] = dict(semantic_names)
        selected_names.update(active_learned_names)
        percept_names = {
            capability_id: developed_names.get(capability_id, selected_name)
            for capability_id, selected_name in selected_names.items()
        }
        cognitive_aliases = {
            capability_id: semantic_name
            for capability_id, semantic_name in semantic_names.items()
            if percept_names.get(capability_id) not in (None, semantic_name)
        }

        selected_ids = set(percept_names)
        cognitive_readings = tuple(
            reading for reading in snapshot.readings if reading.capability_id in selected_ids
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
        self._charge_metabolism("cognition", len(allocations) * 0.02)

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
            for allocation in allocations:
                candidate = allocation.name
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

        # BodySchema receives two bounded organism-owned evidence surfaces:
        # sensory SelfModel classes and opaque dynamic cognitive channels. It
        # never sees host manifest truth, CognitiveGraph nodes/edges or
        # Observatory topology.
        self._body_schema.observe_self_model(
            self._self_model.export(current_tick=self._tick_count),
            tick=self._tick_count,
        )
        retained_units = float(len(self._drift_baselines)) * 0.001
        if self._cognitive_bridge is not None and self._cognitive_bridge.graph is not None:
            retained_units += float(len(self._cognitive_bridge.graph.nodes)) * 0.0005
        metabolism_snapshot = self._metabolism.advance(retained_units=retained_units)
        homeostatic_snapshot = self._homeostasis.regulate(metabolism_snapshot.pressure)
        physiology_snapshot = self._physiology.advance(
            metabolism_snapshot, tick=self._tick_count,
            resting=self._resting_requested or homeostatic_snapshot.action.value in ("pause_plasticity", "safe_mode"),
        )
        if physiology_snapshot.state.value == "dead":
            if self._habitat is not None and not self._habitat_released:
                self._habitat.release(self._organism_id)
                self._habitat_released = True
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
        self._tick_count += 1
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
        payload["generation"] = self._generation
        payload["reproduction_cost"] = self._reproduction_cost
        payload["social_exchange_quantum"] = self._social_exchange_quantum
        payload["resting_requested"] = self._resting_requested
        payload["reproductive_pressure"] = (
            {"threshold_ticks": self._reproductive_pressure.threshold_ticks,
             "reserve": self._reproductive_pressure.reserve,
             "blocked_ticks": self._reproductive_pressure.blocked_ticks}
            if self._reproductive_pressure is not None else None
        )
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
        min_samples = int(kwargs.get("min_samples", 5))
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
        evidence_ledger = EvidenceRevisionLedger.restore_checkpoint(
            normalized.get("evidence_ledger"),
            conflict_z=float(kwargs.get("conflict_z", 2.0)),
            allowed_capability_ids=acclimation.known_capabilities,
        )
        from .. import __version__ as _symbiont_version

        kernel_limits = kwargs.get("kernel_limits") or KernelLimits()
        genome = restore_genome_checkpoint(
            normalized.get("genome"),
            kernel_limits=kernel_limits,
            running_version=_parse_running_version(_symbiont_version),
        )
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
        signal_knowledge = SignalKnowledgeEngine.from_checkpoint(validate_checkpoint(normalized.get("signal_knowledge"))) if normalized.get("signal_knowledge") else SignalKnowledgeEngine()
        metabolism = MetabolicLedger.from_checkpoint(normalized["metabolism"]) if normalized.get("metabolism") else MetabolicLedger(tick=normalized.get("saved_at_tick") or 0)
        assimilator = InformationAssimilator.from_checkpoint(normalized["assimilation"]) if normalized.get("assimilation") else InformationAssimilator()
        homeostasis = HomeostaticController.from_checkpoint(normalized["homeostasis"]) if normalized.get("homeostasis") else HomeostaticController()
        physiology = PhysiologyController.from_checkpoint(normalized["physiology"]) if normalized.get("physiology") else PhysiologyController()
        social_ledger = RelationLedger.from_checkpoint(normalized["social_ledger"]) if normalized.get("social_ledger") else RelationLedger()
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
        constructor_kwargs.pop("resting_requested", None)
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
            cognitive_bridge=cognitive_bridge,
            memory_consolidator=memory_consolidator,
            tick_count=normalized.get("saved_at_tick") or 0,
            organism_id=normalized.get("organism_id"),
            signal_knowledge=signal_knowledge,
            signal_identity=signal_identity,
            metabolism=metabolism,
            assimilator=assimilator,
            homeostasis=homeostasis,
            physiology=physiology,
            social_ledger=social_ledger,
            explicit_metabolism=bool(kwargs.get("explicit_metabolism", normalized.get("effective_config", {}).get("explicit_metabolism", False))),
            auto_promote_predictors=bool(kwargs.get("auto_promote_predictors", normalized.get("effective_config", {}).get("auto_promote_predictors", False))),
            reproductive_pressure=reproductive_pressure,
            birth_authority=kwargs.get("birth_authority"),
            generation=int(normalized.get("generation", normalized.get("effective_config", {}).get("generation", 0))),
            reproduction_cost=float(normalized.get("reproduction_cost", normalized.get("effective_config", {}).get("reproduction_cost", 0.1))),
            social_exchange_quantum=float(normalized.get("social_exchange_quantum", normalized.get("effective_config", {}).get("social_exchange_quantum", 0.1))),
            resting_requested=bool(normalized.get("resting_requested", normalized.get("effective_config", {}).get("resting_requested", False))),
        )
        runtime._reacclimation_remaining = kernel_limits.reacclimation_ticks
        return runtime

    @classmethod
    def load_or_create(cls, path: str | Path, **kwargs: Any) -> "OrganismRuntime":
        payload = load_checkpoint_file(path)
        if payload is None:
            return cls(**kwargs)
        return cls.from_checkpoint(payload, **kwargs)
