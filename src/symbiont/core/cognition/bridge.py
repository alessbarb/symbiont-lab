from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Collection, Mapping

from ...cognition.activation import SensoryNormalizer
from ...genetics.genome import Genome
from ...cognition.graph import CognitiveGraph, GraphError, PlasticNode, TickContext
from ...cognition.learning import PredictionError, ShadowPrediction, compute_prediction_errors
from ...cognition.limits import KernelLimits
from ...genetics.expression import GeneExpressionState
from ...cognition.metaplasticity import SafetyState
from ...cognition.structure import (
    Mutation,
    StructuralPlasticity,
    apply_mutations,
)
from ...cognition.types import NodeKind
from .plasticity_state import PlasticityEngine
from .predictors import PredictorLifecycle
from .sense_concept_lifecycle import (
    ConceptLineage,
    RepresentationMaturity,
    RepresentationTracker,
    SenseConceptLifecycle,
)
from .structural_candidates import StructuralContention
from .structural_planner import AdaptiveStructuralBudgets, StructuralPlanner
from .bridge_checkpoint import export_bridge_state, restore_bridge_state
from .bridge_compat import CognitiveBridgeCompatibility

_ACTIVITY_THRESHOLD = 0.1
_MOTOR_READOUT_PREFIX = "readout_motor:"
_PRIMITIVE_READOUT_PREFIX = "readout_primitive:"
_MAX_SHADOW_PREDICTIONS = 16384


class TopologyHealth(StrEnum):
    GERMINAL = "germinal"
    DEVELOPING = "developing"
    CONNECTED = "connected"
    ADAPTIVE = "adaptive"
    DEGENERATE = "degenerate"
    RECOVERING = "recovering"


@dataclass(slots=True, frozen=True)
class CognitiveBridgeResult:
    tick: int
    activations: Mapping[str, float]
    readouts: Mapping[str, float]
    prediction_errors: tuple[PredictionError, ...]
    structural_mutations_applied: int
    frozen: bool
    topology_revision: int
    consecutive_failures: int = 0
    mutations: tuple[Mutation, ...] = ()
    topology_health: TopologyHealth = TopologyHealth.GERMINAL
    recovering: bool = False
    recycling_events: tuple[dict[str, object], ...] = ()
    stranded_concepts: tuple[str, ...] = ()
    predictive_gain: float = 0.0
    motor_readouts: Mapping[str, float] | None = None
    primitive_readouts: Mapping[str, float] | None = None
    active_concept_ids: tuple[str, ...] = ()
    retiring_predictors: tuple[str, ...] = ()
    retirement_edges: int = 0
    structural_candidates: int = 0
    structural_producers: int = 0
    oldest_structural_wait_ticks: int = 0
    representation_maturity: Mapping[str, int] | None = None
    max_contention_losses: int = 0
    node_budget: int = 0
    edge_budget: int = 0
    sense_budget: int = 0

    def readouts_for_family(self, family: str) -> Mapping[str, float]:
        if family == "core":
            return self.readouts
        if family == "motor":
            return self.motor_readouts or {}
        if family == "primitive":
            return self.primitive_readouts or {}
        return {}


class CognitiveBridge(CognitiveBridgeCompatibility):
    """Wire a CognitiveGraph into the organism's resident tick loop.

    Germinal cognition follows a reversible homeostatic cycle: observe and
    learn, maintain weak/obsolete structure, reclaim node capacity, then grow
    new structure, with the entire structural batch committed atomically.
    Structural validity is complemented by a derived topology-health state so
    a syntactically valid but developmentally trapped graph can enter recovery.

    Owner-authored non-empty graphs remain outside automatic sense admission,
    node GC, sensory eviction and topology recovery unless they explicitly opt
    into ``develop_senses``.
    """

    def __init__(
        self,
        *,
        graph: CognitiveGraph,
        genome: Genome,
        kernel_limits: KernelLimits,
        structural_plasticity: StructuralPlasticity | None = None,
        safety_state: SafetyState | None = None,
        develop_senses: bool | None = None,
        expression_state: GeneExpressionState | None = None,
    ) -> None:
        self._graph = graph
        self._genome = genome
        self._expression_state = expression_state or GeneExpressionState.from_genome(genome)
        self._kernel_limits = kernel_limits
        self._structural_plasticity = (
            structural_plasticity
            if structural_plasticity is not None
            else StructuralPlasticity(
                min_candidate_support=genome.structure.minimum_support,
                tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
                cooldown_ticks=genome.structure.tentative_lifetime_ticks,
            )
        )
        self._safety_state = safety_state if safety_state is not None else SafetyState()
        self._normalizers: dict[str, SensoryNormalizer] = {}
        self._previous_frame: dict[str, float] = {}
        self._lifecycle = SenseConceptLifecycle()
        self._representations = RepresentationTracker(graph)
        self._tick = 0
        self._predictors = PredictorLifecycle()
        self._contention = StructuralContention(
            kernel_limits=kernel_limits,
            identity=genome.genome_id,
        )
        self._topology_revision = 0
        self._budgets = AdaptiveStructuralBudgets.from_graph(
            graph,
            kernel_limits=kernel_limits,
            soft_node_budget=genome.development.soft_node_budget,
            soft_edge_budget=genome.development.soft_edge_budget,
            sense_node_budget=genome.development.sense_node_budget,
            sensitivity=genome.development.capacity_growth_sensitivity,
        )
        self._planner = StructuralPlanner(
            kernel_limits=kernel_limits,
            structural_plasticity=self._structural_plasticity,
            budgets=self._budgets,
        )
        self._develop_senses = (not graph.nodes) if develop_senses is None else bool(develop_senses)
        self._recovery_pending = False
        self._plasticity = PlasticityEngine(kernel_limits=kernel_limits)
        self._plasticity.seed_new_edges(self._graph)
        self._reacclimation_remaining = 0
        self._cached_topology_revision = -1
        self._cached_graph: CognitiveGraph | None = None
        self._cached_node_kinds: dict[str, NodeKind] = {}
        self._cached_relation_pairs: set[tuple[str, str]] = set()
        self._cached_node_ids_by_kind: dict[NodeKind, tuple[str, ...]] = {}
        self._cached_topology_health_key: tuple[int, bool] | None = None
        self._cached_topology_health: TopologyHealth | None = None

    def set_expression_state(self, state: GeneExpressionState) -> None:
        """Install the expression snapshot that becomes effective this tick."""
        self._expression_state = state

    @property
    def expression_state(self) -> GeneExpressionState:
        return self._expression_state

    def _topology_cache(self) -> tuple[dict[str, NodeKind], set[tuple[str, str]]]:
        if (
            self._cached_topology_revision != self._topology_revision
            or self._cached_graph is not self._graph
        ):
            self._cached_node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
            self._cached_relation_pairs = {
                (edge.source_id, edge.target_id) for edge in self._graph.edges
            }
            by_kind: dict[NodeKind, list[str]] = {}
            for node in self._graph.nodes:
                by_kind.setdefault(node.kind, []).append(node.node_id)
            self._cached_node_ids_by_kind = {
                kind: tuple(node_ids) for kind, node_ids in by_kind.items()
            }
            self._cached_topology_revision = self._topology_revision
            self._cached_graph = self._graph
        return self._cached_node_kinds, self._cached_relation_pairs

    def _topology_node_ids(self, kind: NodeKind) -> tuple[str, ...]:
        """Return stable node IDs for a kind, rebuilding only on topology change."""
        self._topology_cache()
        return self._cached_node_ids_by_kind.get(kind, ())

    @property
    def graph(self) -> CognitiveGraph:
        return self._graph

    @property
    def safety_state(self) -> SafetyState:
        return self._safety_state

    @property
    def topology_revision(self) -> int:
        return self._topology_revision

    @property
    def develop_senses(self) -> bool:
        return self._develop_senses

    @property
    def recovery_pending(self) -> bool:
        return self._recovery_pending

    @property
    def concept_lineage(self) -> tuple[ConceptLineage, ...]:
        return self._lifecycle.concept_lineage

    @property
    def unrouted_since_tick(self) -> dict[str, int]:
        return dict(self._lifecycle.unrouted_since_tick)

    @property
    def next_concept_index(self) -> int:
        return self._lifecycle.next_concept_index

    @property
    def topology_health(self) -> TopologyHealth:
        cache_key = (self._topology_revision, self._recovery_pending)
        if self._cached_topology_health_key != cache_key:
            self._cached_topology_health = self._classify_topology_health()
            self._cached_topology_health_key = cache_key
        # _classify_topology_health always returns a value; keep the explicit
        # fallback defensive for type checkers and malformed test doubles.
        return self._cached_topology_health or TopologyHealth.GERMINAL

    def bind_contention_identity(self, identity: str) -> None:
        self._contention.bind_identity(identity)

    def _representation_maturity(
        self,
        node_id: str,
        *,
        graph: CognitiveGraph | None = None,
    ) -> RepresentationMaturity:
        return self._representations.maturity(
            node_id,
            graph=self._graph if graph is None else graph,
            tick=self._tick,
            orphan_since_tick=self._lifecycle.orphan_since_tick,
            retiring_predictor_ids=self._predictors.retirement,
            predictor_utility=self._predictors.utility,
            tentative_lifetime_ticks=(
                self._genome.structure.tentative_lifetime_ticks
            ),
            minimum_support=self._genome.structure.minimum_support,
        )

    def _representation_mature_enough_as_target(
        self,
        node_id: str,
        *,
        graph: CognitiveGraph | None = None,
    ) -> bool:
        return self._representation_maturity(
            node_id,
            graph=graph,
        ) in {RepresentationMaturity.MATURE, RepresentationMaturity.STABLE}

    @staticmethod
    def _motor_readout_id(actuator_id: str) -> str:
        return f"{_MOTOR_READOUT_PREFIX}{actuator_id}"

    @staticmethod
    def _actuator_id_from_motor_readout(node_id: str) -> str | None:
        if not node_id.startswith(_MOTOR_READOUT_PREFIX):
            return None
        return node_id[len(_MOTOR_READOUT_PREFIX):]

    @staticmethod
    def _primitive_readout_id(primitive_id: str) -> str:
        return f"{_PRIMITIVE_READOUT_PREFIX}{primitive_id}"

    @staticmethod
    def _primitive_id_from_readout(node_id: str) -> str | None:
        if not node_id.startswith(_PRIMITIVE_READOUT_PREFIX):
            return None
        return node_id[len(_PRIMITIVE_READOUT_PREFIX):]

    def _oldest_blocked_structural_wait(self, *, tick: int) -> int:
        return self._planner.oldest_blocked_wait(
            graph=self._graph,
            contention=self._contention,
            tick=tick,
        )

    def _update_predictor_retirement_state(self, *, tick: int) -> None:
        self._predictors.update_retirement(
            graph=self._graph,
            tick=tick,
            soft_node_limit=self._soft_node_limit,
            structural_wait=self._oldest_blocked_structural_wait(tick=tick),
            minimum_support=self._genome.structure.minimum_support,
            tentative_lifetime_ticks=(
                self._genome.structure.tentative_lifetime_ticks
            ),
        )

    def _sync_motor_readouts(
        self,
        actuator_ids: Collection[str],
    ) -> None:
        self._planner.sync_motor_readouts(
            graph=self._graph,
            contention=self._contention,
            actuator_ids=actuator_ids,
            tick=self._tick,
        )

    def _sync_primitive_readouts(
        self,
        primitive_ids: Collection[str],
    ) -> None:
        graph, mutations = self._planner.sync_primitive_readouts(
            graph=self._graph,
            contention=self._contention,
            primitive_ids=primitive_ids,
            tick=self._tick,
            frozen=self._safety_state.frozen,
        )
        if mutations and graph is not self._graph:
            self._graph = graph
            self._record_applied_metadata(
                mutations,
                tick=self._tick,
            )
            self._plasticity.seed_new_edges(self._graph)
            self._reconcile_node_metadata()
            self._topology_revision += 1

    def observe_primitive_execution(
        self,
        primitive_id: str,
        *,
        concept_ids: Collection[str],
        tick: int,
    ) -> bool:
        """Record state→primitive evidence after normal readout admission.

        Returns False only while the verified primitive has not yet been
        admitted by the normal tick-time skill synchronization.
        """
        readout_id = self._primitive_readout_id(str(primitive_id))
        readout_node = self._graph.node_by_id(readout_id)
        if readout_node is None or readout_node.kind is not NodeKind.READOUT:
            return False

        node_kinds, _ = self._topology_cache()
        recorded = False
        for concept_id in sorted({str(value) for value in concept_ids if str(value)}):
            if node_kinds.get(concept_id) is not NodeKind.CONCEPT:
                continue
            self._structural_plasticity.observe_motor_association_evidence(
                source_id=concept_id,
                motor_readout_id=readout_id,
                source_active=True,
                actuator_has_effect_evidence=True,
                tick=tick,
            )
            recorded = True

        # Admission of the primitive readout is not itself association
        # evidence. Keep the pending verification context alive until at least
        # one real concept->primitive observation has been recorded. A later
        # verification with an active concept context may then replace an empty
        # pending context without blocking sensorimotor investigation.
        return recorded

    def observe_homeostatic_action_outcome(
        self,
        *,
        family: str,
        action_id: str,
        concept_ids: Collection[str],
        value: float,
        tick: int,
    ) -> bool:
        """Apply delayed intrinsic value to an actually executed opaque action.

        value is semantic-free physiological improvement: positive values
        mean internally owned disequilibrium later decreased, negative values
        mean it increased. No environmental target, distance or resource
        identity enters this method.
        """
        if family not in {"motor", "primitive"}:
            raise ValueError("homeostatic action family must be motor or primitive")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("homeostatic action value must be numeric")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("homeostatic action value must be finite")
        value = max(-1.0, min(1.0, value))
        if abs(value) <= 1e-9:
            return False

        readout_id = (
            self._motor_readout_id(str(action_id))
            if family == "motor"
            else self._primitive_readout_id(str(action_id))
        )
        node_kinds, _ = self._topology_cache()
        if node_kinds.get(readout_id) is not NodeKind.READOUT:
            return False

        concept_set = {
            str(concept_id)
            for concept_id in concept_ids
            if str(concept_id)
            and node_kinds.get(str(concept_id)) is NodeKind.CONCEPT
        }
        if not concept_set:
            return False

        # Preserve ordinary causal association evidence first. Intrinsic value
        # modulates a relation actually experienced in this concept context;
        # it never invents an environmental objective or target direction.
        for concept_id in sorted(concept_set):
            self._structural_plasticity.observe_motor_association_evidence(
                source_id=concept_id,
                motor_readout_id=readout_id,
                source_active=True,
                actuator_has_effect_evidence=True,
                tick=tick,
            )

        return self._plasticity.apply_homeostatic_value(
            self._graph,
            concept_ids=concept_set,
            readout_id=readout_id,
            value=value,
            tick=tick,
        )

    @property
    def _soft_node_limit(self) -> int:
        return self._budgets.node_budget

    @property
    def _sense_node_limit(self) -> int:
        return self._budgets.sense_limit

    @property
    def _soft_edge_limit(self) -> int:
        return self._budgets.edge_budget

    def _expand_resource_budgets(
        self,
        *,
        need_nodes: bool = False,
        need_edges: bool = False,
        need_senses: bool = False,
    ) -> bool:
        return self._budgets.expand(
            need_nodes=need_nodes,
            need_edges=need_edges,
            need_senses=need_senses,
        )

    def _admit_senses(
        self,
        sense_values: Mapping[str, float],
        *,
        tick: int,
    ) -> None:
        if not isinstance(self._graph, CognitiveGraph):
            return
        graph, admitted = self._planner.admit_senses(
            graph=self._graph,
            sense_values=sense_values,
            lifecycle=self._lifecycle,
            tick=tick,
            develop_senses=self._develop_senses,
        )
        if admitted:
            self._graph = graph
            self._topology_revision += 1

    def _consume_concept_support(self, parent_ids: Collection[str]) -> None:
        self._lifecycle.consume_concept_support(parent_ids)

    @property
    def shadow_predictions(self) -> tuple[ShadowPrediction, ...]:
        return self._predictors.shadow_predictions

    def _prune_shadow_predictions(self) -> None:
        node_kinds, _ = self._topology_cache()
        self._predictors.prune_shadows(
            node_kinds=node_kinds,
            topology_revision=self._topology_revision,
            max_nodes=self._kernel_limits.max_nodes,
        )

    def promote_shadow_prediction(
        self,
        source_id: str,
        target_id: str,
        *,
        tick: int,
    ) -> bool:
        candidate_id = f"predictor:{source_id}:{target_id}"
        if candidate_id in self._contention.candidates:
            return True
        proposal = self._predictors.propose_promotion(
            source_id,
            target_id,
            graph=self._graph,
            develop_senses=self._develop_senses,
        )
        if proposal is None:
            return False
        candidate_id, mutations = proposal
        return self._contention.register(
            candidate_id=candidate_id,
            family="predictor",
            eligible_tick=tick,
            mutations=mutations,
        )

    def nominate_shadow_prediction(self, *, tick: int) -> bool:
        producer_id = StructuralContention.producer_id_for_family(
            "predictor"
        )
        if any(
            candidate.producer_id == producer_id
            for candidate in self._contention.candidates.values()
        ):
            return False
        nominee = self._predictors.nominate_shadow(
            tiebreak=self._contention.candidate_tiebreak,
        )
        if nominee is None:
            return False
        return self.promote_shadow_prediction(
            nominee[0],
            nominee[1],
            tick=tick,
        )

    @property
    def stranded_concepts(self) -> tuple[str, ...]:
        """Concepts receiving activation but lacking a path to a readout."""
        unrouted = set(self._lifecycle.unrouted_since_tick)
        return tuple(sorted(node_id for node_id in unrouted if node_id in self._lifecycle.concept_last_active_tick))

    def _salient_concept_ids(
        self,
        activations: Mapping[str, float],
        *,
        limit: int = 4,
    ) -> tuple[str, ...]:
        node_kinds, _ = self._topology_cache()
        return self._lifecycle.salient_concept_ids(
            activations,
            node_kinds=node_kinds,
            limit=limit,
        )

    def observe_retrospective_support(
        self,
        source_ids: Collection[str],
        *,
        support_epochs: int,
    ) -> int:
        if not isinstance(self._graph, CognitiveGraph):
            return 0
        node_kinds, _ = self._topology_cache()
        return self._lifecycle.observe_retrospective_support(
            source_ids,
            support_epochs=support_epochs,
            node_kinds=node_kinds,
            graph=self._graph,
            topology_revision=self._topology_revision,
            develop_senses=self._develop_senses,
        )

    def _record_concept_support(
        self,
        activations: Mapping[str, float],
    ) -> None:
        if not isinstance(self._graph, CognitiveGraph):
            return
        node_kinds, _ = self._topology_cache()
        self._lifecycle.record_concept_support(
            activations,
            node_kinds=node_kinds,
            graph=self._graph,
            topology_revision=self._topology_revision,
            tick=self._tick,
            growth_threshold=(
                self._expression_state.effective_growth_threshold
            ),
            develop_senses=self._develop_senses,
        )

    def _concept_signature_exists(
        self,
        source_ids: tuple[str, str],
        *,
        graph: CognitiveGraph | None = None,
    ) -> bool:
        active_graph = self._graph if graph is None else graph
        return self._lifecycle.concept_signature_exists(
            source_ids,
            graph=active_graph,
            live_graph=self._graph,
            topology_revision=self._topology_revision,
        )

    def _extract_max_concept_index(
        self,
        graph: CognitiveGraph | None = None,
    ) -> int:
        return self._lifecycle.extract_max_concept_index(
            self._graph if graph is None else graph
        )

    def _new_node_id(
        self,
        prefix: str,
        *,
        graph: CognitiveGraph | None = None,
    ) -> str:
        return self._lifecycle.new_node_id(
            prefix,
            graph=self._graph if graph is None else graph,
        )

    def _register_germinal_concept_candidate(
        self,
        *,
        tick: int,
        graph: CognitiveGraph | None = None,
    ) -> None:
        active_graph = self._graph if graph is None else graph
        pending_concepts = sum(
            1
            for candidate in self._contention.candidates.values()
            if candidate.family == "concept"
        )
        proposal = self._lifecycle.propose_germinal_concept_candidate(
            graph=active_graph,
            live_graph=self._graph,
            topology_revision=self._topology_revision,
            pending_concepts=pending_concepts,
            existing_candidate_ids=self._contention.candidates,
            max_concepts=self._kernel_limits.max_concepts,
            minimum_support=self._genome.structure.minimum_support,
            develop_senses=self._develop_senses,
        )
        if proposal is None:
            return
        candidate_id, mutations = proposal
        self._contention.register(
            candidate_id=candidate_id,
            family="concept",
            eligible_tick=tick,
            mutations=mutations,
        )

    def _nodes_with_path_to_targets(
        self,
        target_ids: Collection[str],
        graph: CognitiveGraph | None = None,
    ) -> set[str]:
        return self._lifecycle.nodes_with_path_to_targets(
            target_ids,
            graph=self._graph if graph is None else graph,
        )

    def _nodes_with_path_to_core_readout(
        self,
        graph: CognitiveGraph | None = None,
    ) -> set[str]:
        return self._lifecycle.nodes_with_path_to_core_readout(
            graph=self._graph if graph is None else graph,
        )

    def _nodes_with_path_to_motor_readout(
        self, actuator_id: str, graph: CognitiveGraph | None = None
    ) -> set[str]:
        return self._nodes_with_path_to_targets((self._motor_readout_id(actuator_id),), graph)

    def _nodes_with_path_to_primitive_readout(
        self, primitive_id: str, graph: CognitiveGraph | None = None
    ) -> set[str]:
        return self._nodes_with_path_to_targets(
            (self._primitive_readout_id(primitive_id),),
            graph,
        )

    def _nodes_with_path_to_readout(self, graph: CognitiveGraph | None = None) -> set[str]:
        """Legacy alias: historically "readout" meant readout_core."""
        return self._nodes_with_path_to_core_readout(graph)

    def _update_unrouted_tracking(
        self,
        tick: int,
        *,
        graph: CognitiveGraph | None = None,
    ) -> set[str]:
        active_graph = self._graph if graph is None else graph
        routed = self._nodes_with_path_to_core_readout(active_graph)
        return self._lifecycle.update_unrouted(
            graph=active_graph,
            routed_ids=routed,
            tick=tick,
        )

    def _propose_concept_recycling_mutations(
        self,
        *,
        tick: int,
        mutation_slots: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[tuple[Mutation, ...], dict[str, object] | None]:
        return self._lifecycle.propose_recycling(
            graph=self._graph if graph is None else graph,
            tick=tick,
            mutation_slots=mutation_slots,
            develop_senses=self._develop_senses,
            kernel_limits=self._kernel_limits,
        )

    def _orphan_latent_ids(
        self,
        graph: CognitiveGraph | None = None,
    ) -> set[str]:
        return self._lifecycle.orphan_latent_ids(
            graph=self._graph if graph is None else graph,
        )

    def _orphan_node_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        return self._lifecycle.orphan_node_mutations(
            graph=self._graph if graph is None else graph,
            tick=tick,
            max_mutations=max_mutations,
            protected_node_ids=protected_node_ids,
            grace_ticks=self._genome.structure.tentative_lifetime_ticks,
            develop_senses=self._develop_senses,
        )

    def _sense_eviction_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        return self._lifecycle.sense_eviction_mutations(
            graph=self._graph if graph is None else graph,
            tick=tick,
            max_mutations=max_mutations,
            sense_node_limit=self._sense_node_limit,
            retention_ticks=self._genome.development.sense_retention_ticks,
            develop_senses=self._develop_senses,
        )

    def _has_sense_to_readout_path(
        self,
        graph: CognitiveGraph | None = None,
        *,
        established_only: bool = False,
    ) -> bool:
        return self._lifecycle.has_sense_to_readout_path(
            graph=self._graph if graph is None else graph,
            minimum_support=self._genome.structure.minimum_support,
            established_only=established_only,
        )

    def _classify_topology_health(
        self,
        graph: CognitiveGraph | None = None,
        *,
        include_recovery: bool = True,
    ) -> TopologyHealth:
        active_graph = self._graph if graph is None else graph
        if include_recovery and self._recovery_pending:
            return TopologyHealth.RECOVERING
        if not active_graph.nodes:
            return TopologyHealth.GERMINAL
        if self._has_sense_to_readout_path(active_graph, established_only=True):
            return TopologyHealth.ADAPTIVE
        if self._has_sense_to_readout_path(active_graph):
            return TopologyHealth.CONNECTED

        latent_nodes = [node for node in active_graph.nodes if node.kind is not NodeKind.SENSE]
        sense_count = sum(1 for node in active_graph.nodes if node.kind is NodeKind.SENSE)
        if self._develop_senses and sense_count > self._sense_node_limit:
            return TopologyHealth.DEGENERATE
        if not latent_nodes:
            return TopologyHealth.GERMINAL if self._develop_senses else TopologyHealth.DEVELOPING
        if self._develop_senses:
            node_budget_full = len(active_graph.nodes) >= self._soft_node_limit
            no_edges_with_latent = not active_graph.edges
            if no_edges_with_latent or node_budget_full:
                return TopologyHealth.DEGENERATE
        return TopologyHealth.DEVELOPING

    def _hard_deadlock_signature(self) -> bool:
        if not self._develop_senses or self._graph.edges:
            return False
        latent = any(node.kind is not NodeKind.SENSE for node in self._graph.nodes)
        return latent and len(self._graph.nodes) >= self._soft_node_limit

    def _enter_recovery_if_needed(self, *, prime_legacy_deadlock: bool = False) -> None:
        if not self._develop_senses or self._recovery_pending:
            return
        if self._classify_topology_health(include_recovery=False) is not TopologyHealth.DEGENERATE:
            return
        self._recovery_pending = True
        if prime_legacy_deadlock and self._hard_deadlock_signature():
            for node_id in self._orphan_latent_ids():
                self._lifecycle.orphan_since_tick.setdefault(node_id, 0)

    def _refresh_recovery_state(self) -> None:
        if not self._recovery_pending:
            return
        if self._classify_topology_health(include_recovery=False) is not TopologyHealth.DEGENERATE:
            self._recovery_pending = False

    @staticmethod
    def _edge_delta(mutations: Collection[Mutation]) -> int:
        delta = 0
        for mutation in mutations:
            if mutation.kind == "add_edge":
                delta += 1
            elif mutation.kind == "remove_edge":
                delta -= 1
            elif mutation.kind == "add_node":
                raw_sources = mutation.payload.get("source_ids", ())
                if isinstance(raw_sources, (list, tuple, set)):
                    delta += len(raw_sources)
        return delta

    def _record_applied_metadata(self, mutations: Collection[Mutation], *, tick: int) -> None:
        for mutation in mutations:
            if mutation.kind == "add_node":
                try:
                    kind = NodeKind(mutation.payload["kind"])
                except (KeyError, TypeError, ValueError):
                    continue
                node_id = str(mutation.payload.get("node_id", ""))
                if node_id:
                    self._representations.note_birth(node_id, tick=tick)
                if kind is NodeKind.CONCEPT:
                    raw_sources = mutation.payload.get("source_ids", ())
                    if isinstance(raw_sources, (list, tuple, set)):
                        parent_ids = tuple(sorted(str(value) for value in raw_sources))
                        if parent_ids:
                            self._lifecycle.lineage[node_id] = ConceptLineage(node_id, parent_ids, tick)
                            self._consume_concept_support(parent_ids)
            elif mutation.kind == "add_edge":
                source_id = str(mutation.payload.get("source_id", ""))
                target_id = str(mutation.payload.get("target_id", ""))
                if source_id and target_id:
                    self._structural_plasticity.mark_relation_explained(
                        source_id,
                        target_id,
                    )
            elif mutation.kind == "remove_node":
                node_id = str(mutation.payload.get("node_id", ""))
                self._lifecycle.lineage.pop(node_id, None)
                self._lifecycle.sense_last_seen_tick.pop(node_id, None)
                self._lifecycle.orphan_since_tick.pop(node_id, None)
                self._lifecycle.unrouted_since_tick.pop(node_id, None)
                self._normalizers.pop(node_id, None)
                self._predictors.utility.pop(node_id, None)
                self._predictors.retirement.pop(node_id, None)
                self._representations.remove(node_id)
                dead_prediction_keys = [k for k in self._predictors.shadows if k[0] == node_id or k[1] == node_id]
                for k in dead_prediction_keys:
                    del self._predictors.shadows[k]
                if dead_prediction_keys:
                    self._invalidate_shadow_predictions_cache()

    def _reconcile_node_metadata(self) -> None:
        node_ids = {node.node_id for node in self._graph.nodes}
        sense_ids = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.SENSE}
        concept_ids = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.CONCEPT}
        latent_ids = {
            node.node_id
            for node in self._graph.nodes
            if node.kind in (
                NodeKind.CONCEPT,
                NodeKind.STATE,
                NodeKind.GATE,
                NodeKind.READOUT,
            )
        }
        self._lifecycle.sense_last_seen_tick = {key: value for key, value in self._lifecycle.sense_last_seen_tick.items() if key in sense_ids}
        self._lifecycle.lineage = {key: value for key, value in self._lifecycle.lineage.items() if key in concept_ids}
        self._lifecycle.orphan_since_tick = {key: value for key, value in self._lifecycle.orphan_since_tick.items() if key in latent_ids}
        self._lifecycle.unrouted_since_tick = {key: value for key, value in self._lifecycle.unrouted_since_tick.items() if key in concept_ids}
        self._normalizers = {key: value for key, value in self._normalizers.items() if key in sense_ids}
        self._representations.reconcile(self._graph)
        self._lifecycle.concept_support = {
            pair: count
            for pair, count in self._lifecycle.concept_support.items()
            if pair[0] in sense_ids and pair[1] in sense_ids
        }
        self._structural_plasticity.reconcile(node_ids)
        self._predictors.shadows = {
            key: value
            for key, value in self._predictors.shadows.items()
            if key[0] in node_ids and key[1] in node_ids
        }
        predictor_ids = {
            node.node_id for node in self._graph.nodes
            if node.kind is NodeKind.PREDICTOR
        }
        self._predictors.utility = {
            key: value
            for key, value in self._predictors.utility.items()
            if key in predictor_ids
        }
        self._predictors.retirement = {
            key: value
            for key, value in self._predictors.retirement.items()
            if key in predictor_ids
        }

    def export_checkpoint(self) -> dict[str, object]:
        self._reconcile_node_metadata()
        return export_bridge_state(
            graph=self._graph,
            safety_state=self._safety_state,
            normalizers=self._normalizers,
            plasticity=self._plasticity,
            predictors=self._predictors,
            lifecycle=self._lifecycle,
            contention=self._contention,
            topology_revision=self._topology_revision,
            tick=self._tick,
            develop_senses=self._develop_senses,
            node_born_tick=self._node_born_tick,
            node_observation_count=self._node_observation_count,
            node_active_count=self._node_active_count,
            recovery_pending=self._recovery_pending,
            adaptive_node_budget=self._adaptive_node_budget,
            adaptive_edge_budget=self._adaptive_edge_budget,
            adaptive_sense_budget=self._adaptive_sense_budget,
        )

    @classmethod
    def restore(
        cls,
        payload: dict[str, object] | None,
        *,
        genome: Genome,
        kernel_limits: KernelLimits,
    ) -> "CognitiveBridge | None":
        state = restore_bridge_state(
            payload,
            genome=genome,
            kernel_limits=kernel_limits,
        )
        if state is None:
            return None

        structural_plasticity = StructuralPlasticity(
            min_candidate_support=genome.structure.minimum_support,
            tentative_lifetime_ticks=(
                genome.structure.tentative_lifetime_ticks
            ),
            cooldown_ticks=genome.structure.tentative_lifetime_ticks,
        )
        bridge = cls(
            graph=state.graph,
            genome=genome,
            kernel_limits=kernel_limits,
            structural_plasticity=structural_plasticity,
            safety_state=state.safety_state,
            develop_senses=state.develop_senses,
        )
        if state.adaptive_resource_budgets is not None:
            (
                bridge._adaptive_node_budget,
                bridge._adaptive_edge_budget,
                bridge._adaptive_sense_budget,
            ) = state.adaptive_resource_budgets

        bridge._tick = state.tick
        bridge._normalizers = state.normalizers
        bridge._lifecycle = state.lifecycle
        bridge._predictors = state.predictors
        bridge._contention = state.contention
        bridge._node_born_tick = state.node_born_tick
        bridge._node_observation_count = state.node_observation_count
        bridge._node_active_count = state.node_active_count
        bridge._recovery_pending = state.recovery_pending

        # Preserve historical restore ordering: shadow pruning runs against the
        # bridge's initial topology revision, then the persisted revision is
        # installed.
        bridge._prune_shadow_predictions()
        bridge._topology_revision = state.topology_revision
        bridge._reacclimation_remaining = kernel_limits.reacclimation_ticks
        bridge._reconcile_node_metadata()
        bridge._enter_recovery_if_needed(prime_legacy_deadlock=True)
        return bridge

    def _learning_nodes(self, attended_sense_ids: Collection[str] | None) -> set[str]:
        node_ids = {node.node_id for node in self._graph.nodes}
        if attended_sense_ids is None:
            return node_ids
        reachable = set(attended_sense_ids) & node_ids
        changed = True
        while changed:
            changed = False
            for edge in self._graph.edges:
                if edge.source_id in reachable and edge.target_id not in reachable:
                    reachable.add(edge.target_id)
                    changed = True
        return reachable

    @staticmethod
    def _tick_modulation(
        attended_sense_ids: Collection[str] | None,
        sense_modulation: Mapping[str, float] | None,
    ) -> float:
        if attended_sense_ids is None or sense_modulation is None:
            return 1.0
        values = []
        for sense_id in attended_sense_ids:
            raw = sense_modulation.get(sense_id, 0.0)
            if math.isfinite(raw):
                values.append(max(0.0, min(1.0, float(raw))))
        return sum(values) / len(values) if values else 0.0

    def tick(
        self,
        sense_values: Mapping[str, float],
        *,
        tick: int,
        attended_sense_ids: Collection[str] | None = None,
        sense_modulation: Mapping[str, float] | None = None,
        plasticity_enabled: bool = True,
        active_motor_actuator_ids: Collection[str] = (),
        motor_effect_actuator_ids: Collection[str] = (),
        active_primitive_ids: Collection[str] = (),
    ) -> CognitiveBridgeResult:
        self._tick = max(0, int(tick))
        self._sync_motor_readouts(active_motor_actuator_ids)
        self._sync_primitive_readouts(active_primitive_ids)
        if self._reacclimation_remaining > 0:
            self._reacclimation_remaining -= 1

        self._admit_senses(sense_values, tick=tick)
        self._enter_recovery_if_needed()

        sense_inputs: dict[str, float] = {}
        for node_id in self._topology_node_ids(NodeKind.SENSE):
            raw = sense_values.get(node_id)
            if raw is None:
                continue
            normalizer = self._normalizers.setdefault(node_id, SensoryNormalizer())
            sense_inputs[node_id] = normalizer.normalize(raw)

        try:
            frame = self._graph.activate(sense_inputs, TickContext(tick=tick), previous=self._previous_frame)
        except GraphError:
            self._safety_state.record_failure()
            return CognitiveBridgeResult(
                tick=tick,
                activations=dict(self._previous_frame),
                readouts={},
                prediction_errors=(),
                structural_mutations_applied=0,
                frozen=self._safety_state.frozen,
                topology_revision=self._topology_revision,
                consecutive_failures=self._safety_state.consecutive_failures,
                mutations=(),
                topology_health=self.topology_health,
                recovering=self._recovery_pending,
            )

        self._safety_state.record_success()
        prediction_errors = compute_prediction_errors(
            self._graph,
            current=frame.activations,
            previous=self._previous_frame,
        )
        self._predictors.record_prediction_errors(
            prediction_errors,
            previous=self._previous_frame,
            current=frame.activations,
        )

        self._update_predictor_retirement_state(tick=tick)

        frozen = self._safety_state.frozen
        learning_nodes = self._learning_nodes(attended_sense_ids)
        tick_modulation = self._tick_modulation(attended_sense_ids, sense_modulation)
        if not frozen and plasticity_enabled:
            self._plasticity.apply_learning(
                self._graph,
                sense_inputs=sense_inputs,
                previous_frame=self._previous_frame,
                activations=frame.activations,
                learning_nodes=learning_nodes,
                retiring_predictors={
                    predictor_id: retirement.entered_tick
                    for predictor_id, retirement
                    in self._predictors.retirement.items()
                },
                tick=tick,
                eligibility_decay=self._genome.plasticity.eligibility_decay,
                learning_rate=self._expression_state.effective_learning_rate,
                tick_modulation=tick_modulation,
                structural_plasticity_factor=(
                    self._expression_state.effective_structural_plasticity
                ),
                tentative_lifetime_ticks=(
                    self._genome.structure.tentative_lifetime_ticks
                ),
                structural_wait=self._oldest_blocked_structural_wait(tick=tick),
                max_incoming_norm=(
                    self._kernel_limits.max_incoming_consolidated_weight_norm
                ),
            )

            node_kinds, existing_relation_pairs = self._topology_cache()
            self._representations.observe(frame.activations)
            action_context_concepts = set(
                self._salient_concept_ids(frame.activations)
            )
            active_nodes = [
                node_id
                for node_id, value in frame.activations.items()
                if abs(value) >= _ACTIVITY_THRESHOLD
            ]
            structural_active_nodes = [
                node_id
                for node_id in active_nodes
                if (
                    node_id not in self._predictors.retirement
                    and self._representation_mature_enough_as_target(node_id)
                )
            ]
            for index, source_id in enumerate(structural_active_nodes):
                for target_id in structural_active_nodes[index + 1 :]:
                    if (source_id, target_id) in existing_relation_pairs:
                        self._structural_plasticity.mark_relation_explained(
                            source_id,
                            target_id,
                        )
                        continue
                    self._structural_plasticity.observe_coactivation(
                        source_id=source_id,
                        target_id=target_id,
                        source_active=True,
                        target_active=True,
                        tick=tick,
                        source_kind=node_kinds.get(source_id),
                        target_kind=node_kinds.get(target_id),
                    )
            motor_effect_ids = tuple(sorted({str(value) for value in motor_effect_actuator_ids if str(value)}))
            if motor_effect_ids:
                for source_id in sorted(action_context_concepts):
                    # This is evidence *from* an actually active concept to an
                    # already materialized opaque action readout. Requiring the
                    # source concept to survive a full structural maturation
                    # window discards genuine early sensorimotor evidence and
                    # is inconsistent with primitive execution credit below.
                    # Maturity remains relevant when a representation is being
                    # admitted as new structure, not when an existing concept
                    # is merely the observed source of an association.
                    if node_kinds.get(source_id) is not NodeKind.CONCEPT:
                        continue
                    for actuator_id in motor_effect_ids:
                        motor_readout_id = self._motor_readout_id(actuator_id)
                        if node_kinds.get(motor_readout_id) is not NodeKind.READOUT:
                            continue
                        self._structural_plasticity.observe_motor_association_evidence(
                            source_id=source_id,
                            motor_readout_id=motor_readout_id,
                            source_active=True,
                            actuator_has_effect_evidence=True,
                            tick=tick,
                        )
            self._record_concept_support(frame.activations)
            self._predictors.observe_shadows(
                previous_frame=self._previous_frame,
                activations=frame.activations,
                node_kinds=node_kinds,
                topology_revision=self._topology_revision,
                max_nodes=self._kernel_limits.max_nodes,
            )

        structural_mutations_applied = 0
        applied_mutations: tuple[Mutation, ...] = ()
        recycling_events: tuple[dict[str, object], ...] = ()
        interval = max(
            1,
            self._genome.development.consolidation_interval_ticks,
        )
        if (
            not frozen
            and self._reacclimation_remaining <= 0
            and tick % interval == 0
        ):
            planning = self._planner.plan_consolidation(
                graph=self._graph,
                tick=tick,
                frozen=frozen,
                predictors=self._predictors,
                lifecycle=self._lifecycle,
                contention=self._contention,
                develop_senses=self._develop_senses,
                topology_revision=self._topology_revision,
                active_motor_ids=active_motor_actuator_ids,
                active_primitive_ids=active_primitive_ids,
                pruning_threshold=(
                    self._expression_state.effective_pruning_threshold
                ),
                minimum_support=self._genome.structure.minimum_support,
                lifetime_ticks=(
                    self._genome.structure.tentative_lifetime_ticks
                ),
                sense_retention_ticks=(
                    self._genome.development.sense_retention_ticks
                ),
                max_concepts=self._kernel_limits.max_concepts,
            )
            recycling_events = planning.recycling_events
            if planning.mutations:
                if planning.candidate_graph is not self._graph:
                    self._graph = planning.candidate_graph
                    self._record_applied_metadata(
                        planning.mutations,
                        tick=tick,
                    )
                    self._plasticity.seed_new_edges(self._graph)
                    self._reconcile_node_metadata()
                    structural_mutations_applied = len(
                        planning.mutations
                    )
                    applied_mutations = planning.mutations
                    self._topology_revision += 1
                    self._contention.commit(
                        winner_id=planning.winner_id,
                        loser_ids=planning.loser_ids,
                    )
            else:
                self._reconcile_node_metadata()
            self._refresh_recovery_state()
            self._enter_recovery_if_needed()

        live_nodes = self._graph.nodes
        live_node_ids = {node.node_id for node in live_nodes}
        concept_node_ids = set(self._topology_node_ids(NodeKind.CONCEPT))
        self._previous_frame = {node_id: value for node_id, value in frame.activations.items() if node_id in live_node_ids}

        # Passive/reporting projection only.  The previous implementation
        # traversed every live node once for *each* maturity enum member,
        # calling _representation_maturity() ~N_states * N_nodes per tick.
        # Derive the same histogram in one node pass instead.
        representation_maturity_counts = {
            maturity.value: 0 for maturity in RepresentationMaturity
        }
        for node in live_nodes:
            maturity = self._representation_maturity(node.node_id)
            representation_maturity_counts[maturity.value] += 1

        return CognitiveBridgeResult(
            tick=tick,
            activations={node_id: value for node_id, value in frame.activations.items() if node_id in live_node_ids},
            readouts={
                node_id: value
                for node_id, value in frame.readouts.items()
                if (
                    node_id in live_node_ids
                    and not node_id.startswith(_MOTOR_READOUT_PREFIX)
                    and not node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
                )
            },
            prediction_errors=prediction_errors,
            structural_mutations_applied=structural_mutations_applied,
            frozen=frozen,
            topology_revision=self._topology_revision,
            consecutive_failures=self._safety_state.consecutive_failures,
            mutations=applied_mutations,
            topology_health=self.topology_health,
            recovering=self._recovery_pending,
            recycling_events=recycling_events,
            stranded_concepts=self.stranded_concepts,
            predictive_gain=max((item.predictive_gain for item in self._predictors.shadows.values()), default=0.0),
            motor_readouts={
                actuator_id: value
                for node_id, value in frame.readouts.items()
                if node_id in live_node_ids
                for actuator_id in (self._actuator_id_from_motor_readout(node_id),)
                if actuator_id is not None
            },
            primitive_readouts={
                primitive_id: value
                for node_id, value in frame.readouts.items()
                if node_id in live_node_ids
                for primitive_id in (self._primitive_id_from_readout(node_id),)
                if primitive_id is not None
            },
            active_concept_ids=tuple(
                node_id
                for node_id in self._salient_concept_ids(frame.activations)
                if node_id in live_node_ids and node_id in concept_node_ids
            ),
            retiring_predictors=tuple(sorted(self._predictors.retirement)),
            retirement_edges=sum(
                1
                for edge in self._graph.edges
                if (
                    edge.source_id in self._predictors.retirement
                    or edge.target_id in self._predictors.retirement
                )
            ),
            structural_candidates=len(self._contention.candidates),
            structural_producers=len({
                candidate.producer_id
                for candidate in self._contention.candidates.values()
            }),
            oldest_structural_wait_ticks=max(
                (
                    max(0, tick - candidate.eligible_tick)
                    for candidate in self._contention.candidates.values()
                ),
                default=0,
            ),
            representation_maturity=representation_maturity_counts,
            # NOTE(legacy): Legacy metric retained for snapshot compatibility. Producer-level
            # arbitration no longer accumulates contention debt.
            max_contention_losses=0,
            node_budget=self._adaptive_node_budget,
            edge_budget=self._adaptive_edge_budget,
            sense_budget=self._adaptive_sense_budget,
        )
