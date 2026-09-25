from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Collection, Mapping

from ...cognition.activation import SensoryNormalizer
from ...cognition.checkpoint import (
    WEIGHT_CLASSES,
    export_graph_checkpoint,
    export_safety_state,
    export_sensory_normalizers,
    restore_graph_checkpoint,
    restore_safety_state,
    restore_sensory_normalizers,
)
from ...genetics.genome import Genome
from ...cognition.graph import CognitiveGraph, GraphError, PlasticNode, TickContext
from ...cognition.learning import (
    PredictionError,
    ShadowPrediction,
    apply_oja_update,
    compute_prediction_errors,
    update_eligibility,
)
from ...cognition.limits import KernelLimits
from ...genetics.expression import GeneExpressionState
from ...cognition.metaplasticity import SafetyState
from ...cognition.structure import (
    EdgeLifecycleState,
    Mutation,
    StructuralPlasticity,
    advance_edge_age,
    apply_mutations,
    evaluate_edge_lifecycle,
)
from ...cognition.types import WEIGHT_RANGE, EdgeKind, NodeKind
from .plasticity_state import PlasticityEngine
from .predictors import PredictorLifecycle, PredictorRetirement, PredictorUtility
from .structural_candidates import StructuralCandidate, StructuralContention

_ACTIVITY_THRESHOLD = 0.1
_EDGE_USAGE_THRESHOLD = 1e-3
_ELIGIBILITY_THRESHOLD = 1e-6
_TENTATIVE_WEIGHT = 0.05
_CORE_READOUT_ID = "readout_core"
_MOTOR_READOUT_PREFIX = "readout_motor:"
_PRIMITIVE_READOUT_PREFIX = "readout_primitive:"
_MAX_SHADOW_PREDICTIONS = 16384
_MAX_LIVE_SHADOW_FACTOR = 8
_MAX_PRELIMINARY_SHADOW_FACTOR = 16


class TopologyHealth(StrEnum):
    GERMINAL = "germinal"
    DEVELOPING = "developing"
    CONNECTED = "connected"
    ADAPTIVE = "adaptive"
    DEGENERATE = "degenerate"
    RECOVERING = "recovering"


class RepresentationMaturity(StrEnum):
    NASCENT = "nascent"
    PROVISIONAL = "provisional"
    MATURE = "mature"
    STABLE = "stable"
    WEAKENING = "weakening"
    RETIRING = "retiring"


@dataclass(slots=True, frozen=True)
class ConceptLineage:
    concept_id: str
    parent_ids: tuple[str, ...]
    born_tick: int


@dataclass(slots=True)
class StructuralCandidate:
    candidate_id: str
    family: str
    producer_id: str
    eligible_tick: int
    mutations: tuple[Mutation, ...]
    # NOTE(legacy): Legacy checkpoint field retained for one-way compatibility only.
    # Producer-level fair scheduling no longer accumulates access debt.
    contention_losses: int = 0

    @property
    def required_nodes(self) -> int:
        return sum(1 for mutation in self.mutations if mutation.kind == "add_node")

    @property
    def required_edges(self) -> int:
        return sum(1 for mutation in self.mutations if mutation.kind == "add_edge")

    def checkpoint(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "producer_id": self.producer_id,
            "eligible_tick": self.eligible_tick,
            "contention_losses": 0,
            "mutations": [
                {"kind": mutation.kind, "payload": dict(mutation.payload)}
                for mutation in self.mutations
            ],
        }


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


class CognitiveBridge:
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
        self._concept_support: dict[tuple[str, str], int] = {}
        self._retrospective_concept_support: dict[tuple[str, str], int] = {}
        self._concept_lineage: dict[str, ConceptLineage] = {}
        self._sense_last_seen_tick: dict[str, int] = {}
        self._orphan_since_tick: dict[str, int] = {}
        self._unrouted_since_tick: dict[str, int] = {}
        self._concept_last_active_tick: dict[str, int] = {}
        # Structural birth time is generic provenance, not semantic knowledge.
        # It gives internal representations a developmental integration window.
        self._node_born_tick: dict[str, int] = {
            node.node_id: 0 for node in graph.nodes
        }
        self._node_observation_count: dict[str, int] = {
            node.node_id: 0 for node in graph.nodes
        }
        self._node_active_count: dict[str, int] = {
            node.node_id: 0 for node in graph.nodes
        }
        self._tick = 0
        self._predictors = PredictorLifecycle()
        self._contention = StructuralContention(
            kernel_limits=kernel_limits,
            identity=genome.genome_id,
        )
        self._next_concept_index: int = 1
        self._topology_revision = 0
        node_ceiling = min(
            self._kernel_limits.max_nodes,
            self._genome.development.soft_node_budget,
        )
        edge_ceiling = min(
            self._kernel_limits.max_edges,
            self._genome.development.soft_edge_budget,
        )
        sense_ceiling = min(
            node_ceiling,
            self._genome.development.sense_node_budget,
        )
        # Genetic capacity is a developmental ceiling, not capacity granted at
        # birth. Germinal cognition starts with a bounded fraction and earns
        # further capacity only under structural demand.
        self._adaptive_node_budget = max(
            len(graph.nodes),
            min(node_ceiling, max(4, math.ceil(node_ceiling * 0.25))),
        )
        self._adaptive_edge_budget = max(
            len(graph.edges),
            min(edge_ceiling, max(8, math.ceil(edge_ceiling * 0.25))),
        )
        sense_count = sum(1 for node in graph.nodes if node.kind is NodeKind.SENSE)
        self._adaptive_sense_budget = max(
            sense_count,
            min(
                self._adaptive_node_budget,
                sense_ceiling,
                max(2, math.ceil(sense_ceiling * 0.25)),
            ),
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
        self._cached_concept_sig_rev = -1
        self._cached_concept_sig_lineage_len = -1
        self._cached_concept_sig_graph: CognitiveGraph | None = None
        self._cached_concept_signatures: list[set[str]] = []
        self._cached_concept_signature_pairs: set[tuple[str, str]] = set()
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
        return tuple(self._concept_lineage[key] for key in sorted(self._concept_lineage))

    @property
    def unrouted_since_tick(self) -> dict[str, int]:
        return dict(self._unrouted_since_tick)

    @property
    def next_concept_index(self) -> int:
        return self._next_concept_index

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
        """Derive maturity from generic developmental evidence.

        SENSE inputs are environmentally established. Internal representations
        must survive time, be repeatedly observable, become active often enough,
        and acquire at least one supported incident relation. Predictors retain
        their stronger predictive-gain requirement.
        """
        active_graph = self._graph if graph is None else graph
        node = active_graph.node_by_id(node_id)
        if node is None:
            return RepresentationMaturity.NASCENT
        if node.kind is NodeKind.SENSE:
            return RepresentationMaturity.STABLE

        if node.kind is NodeKind.PREDICTOR and node_id in self._predictors.retirement:
            return RepresentationMaturity.RETIRING

        orphan_since = self._orphan_since_tick.get(node_id)
        if orphan_since is not None:
            orphan_age = max(0, self._tick - orphan_since)
            grace = max(1, self._genome.structure.tentative_lifetime_ticks)
            if orphan_age >= max(1, grace // 2):
                return RepresentationMaturity.RETIRING
            return RepresentationMaturity.WEAKENING

        born_tick = self._node_born_tick.get(node_id, 0)
        age = max(0, self._tick - born_tick)
        grace = max(1, self._genome.structure.tentative_lifetime_ticks)
        observations = self._node_observation_count.get(node_id, 0)
        active = self._node_active_count.get(node_id, 0)
        minimum_support = max(2, self._genome.structure.minimum_support)

        if age < grace or observations < minimum_support:
            return RepresentationMaturity.NASCENT

        incident = active_graph.incident_edges(node_id)
        integrated = any(edge.support >= minimum_support for edge in incident)
        if active < minimum_support or not integrated:
            return RepresentationMaturity.PROVISIONAL

        if node.kind is NodeKind.PREDICTOR:
            utility = self._predictors.utility.get(node_id)
            if not (
                utility is not None
                and utility.samples >= max(8, minimum_support)
                and utility.predictive_gain > 0.0
                and utility.recent_gain > 0.0
            ):
                return RepresentationMaturity.PROVISIONAL

        stable_age = 2 * grace
        stable_activity = 2 * minimum_support
        if age >= stable_age and active >= stable_activity:
            return RepresentationMaturity.STABLE
        return RepresentationMaturity.MATURE

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

    def _valid_candidate(
        self,
        candidate: StructuralCandidate,
        *,
        graph: CognitiveGraph,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
    ) -> bool:
        existing_ids = {node.node_id for node in graph.nodes}
        if any(
            mutation.kind == "add_node"
            and str(mutation.payload.get("node_id", "")) in existing_ids
            for mutation in candidate.mutations
        ):
            return False
        if candidate.family == "motor_readout":
            return candidate.candidate_id.removeprefix("motor:") in set(active_motor_ids)
        if candidate.family == "primitive_readout":
            return candidate.candidate_id.removeprefix("primitive:") in set(active_primitive_ids)
        if candidate.family == "predictor":
            add_edge = next(
                (
                    mutation
                    for mutation in candidate.mutations
                    if mutation.kind == "add_edge"
                ),
                None,
            )
            add_node = next(
                (
                    mutation
                    for mutation in candidate.mutations
                    if mutation.kind == "add_node"
                ),
                None,
            )
            if add_edge is None or add_node is None:
                return False
            source_id = str(add_edge.payload.get("source_id", ""))
            target_id = str(add_node.payload.get("predicts_node_id", ""))
            shadow = self._predictors.shadows.get((source_id, target_id))
            # Shadow promotion is itself the evidence gate for this producer.
            # Requiring the target to be mature here makes promotion of a
            # validated predictor impossible for normal, newly-created
            # representations: the target's maturity would depend on the
            # predictor that is still waiting to be admitted.
            return bool(shadow is not None and shadow.promotable)
        if candidate.family == "concept":
            add_nodes = [m for m in candidate.mutations if m.kind == "add_node"]
            if not add_nodes:
                return False
            raw_sources = add_nodes[0].payload.get("source_ids", ())
            if not isinstance(raw_sources, (list, tuple, set)):
                return False
            source_ids = tuple(sorted(str(value) for value in raw_sources))
            return (
                len(source_ids) >= 2
                and not self._concept_signature_exists(source_ids[:2], graph=graph)
            )
        return True

    def _prune_invalid_structural_proposals(
        self,
        *,
        graph: CognitiveGraph,
        active_motor_ids: Collection[str],
        active_primitive_ids: Collection[str],
    ) -> None:
        """Let producer-local evidence withdraw stale proposals before scheduling."""
        for candidate_id, candidate in list(self._contention.candidates.items()):
            if not self._valid_candidate(
                candidate,
                graph=graph,
                active_motor_ids=active_motor_ids,
                active_primitive_ids=active_primitive_ids,
            ):
                self._contention.candidates.pop(candidate_id, None)

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
        """Age of the oldest node-producing proposal blocked by node capacity.

        This is intentionally semantic-free: motor, primitive, predictor and
        concept producers all create the same generic structural demand.  It is
        used only to adapt the *rate* at which already-negative predictive
        structure yields scarce capacity; it never ranks candidate meanings.
        """
        if len(self._graph.nodes) < self._soft_node_limit:
            return 0
        blocked = [
            candidate
            for candidate in self._contention.candidates.values()
            if candidate.required_nodes > 0
        ]
        if not blocked:
            return 0
        oldest = min(candidate.eligible_tick for candidate in blocked)
        return max(0, int(tick) - int(oldest))

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

    def _retirement_edge_decay(self, edge, *, tick: int) -> None:
        self._predictors.decay_retiring_edge(
            edge,
            tick=tick,
            structural_wait=self._oldest_blocked_structural_wait(tick=tick),
            tentative_lifetime_ticks=(
                self._genome.structure.tentative_lifetime_ticks
            ),
        )

    def _retirement_edge_gc_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        """Bound retirement latency under sustained structural starvation.

        Normal retirement remains reversible soft decay.  Only after a
        predictor has spent a full structural lifetime quarantined *and* some
        node-producing proposal has waited for two lifetimes do we retire one
        incident edge per consolidation.  The rule is generic, deterministic
        and bounded; it never inspects the waiting producer's semantic family.
        """
        if max_mutations <= 0:
            return ()
        lifetime = max(1, self._genome.structure.tentative_lifetime_ticks)
        if self._oldest_blocked_structural_wait(tick=tick) < 2 * lifetime:
            return ()
        active_graph = self._graph if graph is None else graph
        for predictor_id in sorted(self._predictors.retirement):
            retirement = self._predictors.retirement[predictor_id]
            if tick - retirement.entered_tick < lifetime:
                continue
            incident = sorted(
                (
                    edge
                    for edge in active_graph.edges
                    if edge.source_id == predictor_id or edge.target_id == predictor_id
                ),
                key=lambda edge: (
                    edge.source_id,
                    edge.target_id,
                    edge.kind.value,
                ),
            )
            if not incident:
                continue
            edge = incident[0]
            return (
                Mutation(
                    kind="remove_edge",
                    payload={
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "kind": edge.kind.value,
                    },
                ),
            )
        return ()

    def _retirement_node_gc_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        """Remove fully detached quarantined predictors one node at a time."""
        if max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        incident_ids = {
            node_id
            for edge in active_graph.edges
            for node_id in (edge.source_id, edge.target_id)
        }
        candidates = sorted(
            predictor_id
            for predictor_id in self._predictors.retirement
            if predictor_id not in incident_ids
            and any(
                node.node_id == predictor_id and node.kind is NodeKind.PREDICTOR
                for node in active_graph.nodes
            )
        )
        if not candidates:
            return ()
        return (
            Mutation(kind="remove_node", payload={"node_id": candidates[0]}),
        )

    def _stale_concept_reclamation_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        """Reclaim one already-expendable concept without inventing new value."""
        if max_mutations <= 0 or not self._develop_senses:
            return ()
        active_graph = self._graph if graph is None else graph
        protected = set(protected_node_ids)
        unrouted = self._update_unrouted_tracking(self._tick, graph=active_graph)
        grace = max(1, self._genome.structure.tentative_lifetime_ticks)

        candidates: list[tuple[int, int, str, tuple[Mutation, ...]]] = []
        for node_id in sorted(unrouted):
            if node_id in protected:
                continue
            lineage = self._concept_lineage.get(node_id)
            born_tick = lineage.born_tick if lineage is not None else 0
            if self._tick - born_tick < grace:
                continue
            unrouted_since = self._unrouted_since_tick.get(node_id, self._tick)
            if self._tick - unrouted_since < grace:
                continue
            last_active = self._concept_last_active_tick.get(node_id, born_tick)
            if self._tick - last_active < grace:
                continue

            incident = [
                edge for edge in active_graph.edges
                if edge.source_id == node_id or edge.target_id == node_id
            ]
            mutations = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "kind": edge.kind.value,
                    },
                )
                for edge in incident
            ) + (
                Mutation(kind="remove_node", payload={"node_id": node_id}),
            )
            if len(mutations) > max_mutations:
                continue
            candidates.append(
                (
                    -(self._tick - unrouted_since),
                    last_active,
                    node_id,
                    mutations,
                )
            )

        if not candidates:
            return ()
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0][3]

    def _capacity_reclamation_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        """Immediate reclaim is limited to concepts already safe to retire.

        Predictors never undergo monolithic deletion here. They enter a
        reversible retirement lifecycle and free capacity only after their
        edges disappear through ordinary maintenance.
        """
        return self._stale_concept_reclamation_mutations(
            max_mutations=max_mutations,
            graph=graph,
            protected_node_ids=protected_node_ids,
        )

    def _sync_motor_readouts(self, actuator_ids: Collection[str]) -> None:
        requested = sorted({str(value) for value in actuator_ids if str(value)})
        existing = {node.node_id for node in self._graph.nodes}
        requested_set = set(requested)

        # Remove stale requests from the registry; materialized readouts remain
        # governed by ordinary orphan/maintenance rules.
        for candidate_id, candidate in list(self._contention.candidates.items()):
            if (
                candidate.family == "motor_readout"
                and candidate_id.removeprefix("motor:") not in requested_set
            ):
                self._contention.drop(candidate_id)

        for actuator_id in requested:
            node_id = self._motor_readout_id(actuator_id)
            if node_id in existing:
                self._contention.drop(f"motor:{actuator_id}")
                continue
            self._contention.register(
                candidate_id=f"motor:{actuator_id}",
                family="motor_readout",
                mutations=(
                    Mutation(
                        kind="add_node",
                        payload={"node_id": node_id, "kind": NodeKind.READOUT},
                    ),
                ),
                eligible_tick=self._tick,
            )

    def _sync_primitive_readouts(self, primitive_ids: Collection[str]) -> None:
        requested = sorted({str(value) for value in primitive_ids if str(value)})
        requested_set = set(requested)
        requested_nodes = {
            self._primitive_readout_id(primitive_id)
            for primitive_id in requested
        }
        existing_nodes = {node.node_id for node in self._graph.nodes}
        existing_primitive_nodes = {
            node_id
            for node_id in existing_nodes
            if node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        }

        for candidate_id, candidate in list(self._contention.candidates.items()):
            if (
                candidate.family == "primitive_readout"
                and candidate_id.removeprefix("primitive:") not in requested_set
            ):
                self._contention.drop(candidate_id)

        # Retraction remains maintenance, not admission: learned actions that
        # cease to exist release their readouts but never create replacement
        # structure directly.
        mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation
        mutations: list[Mutation] = []
        planning_graph = self._graph
        for node_id in sorted(existing_primitive_nodes - requested_nodes):
            incident = [
                edge for edge in planning_graph.edges
                if edge.source_id == node_id or edge.target_id == node_id
            ]
            stale_mutations = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "kind": edge.kind.value,
                    },
                )
                for edge in incident
            ) + (Mutation(kind="remove_node", payload={"node_id": node_id}),)
            if len(mutations) + len(stale_mutations) > mutation_cap:
                break
            candidate_graph = apply_mutations(
                planning_graph,
                stale_mutations,
                self._kernel_limits,
                frozen=self._safety_state.frozen,
            )
            if candidate_graph is planning_graph:
                continue
            mutations.extend(stale_mutations)
            planning_graph = candidate_graph

        if mutations:
            mutation_tuple = tuple(mutations)
            candidate_graph = apply_mutations(
                self._graph,
                mutation_tuple,
                self._kernel_limits,
                frozen=self._safety_state.frozen,
            )
            if candidate_graph is not self._graph:
                self._graph = candidate_graph
                self._record_applied_metadata(mutation_tuple, tick=self._tick)
                self._plasticity.seed_new_edges(self._graph)
                self._reconcile_node_metadata()
                self._topology_revision += 1

        existing_nodes = {node.node_id for node in self._graph.nodes}
        for primitive_id in requested:
            node_id = self._primitive_readout_id(primitive_id)
            candidate_id = f"primitive:{primitive_id}"
            if node_id in existing_nodes:
                self._contention.drop(candidate_id)
                continue
            self._contention.register(
                candidate_id=candidate_id,
                family="primitive_readout",
                mutations=(
                    Mutation(
                        kind="add_node",
                        payload={"node_id": node_id, "kind": NodeKind.READOUT},
                    ),
                ),
                eligible_tick=self._tick,
            )

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

        changed = False
        learning_rate = 0.20
        for edge in self._graph.edges:
            if (
                edge.source_id not in concept_set
                or edge.target_id != readout_id
                or edge.kind is not EdgeKind.EXCITATORY
            ):
                continue
            before = edge.weight
            edge.weight = max(
                WEIGHT_RANGE[0],
                min(
                    WEIGHT_RANGE[1],
                    float(edge.weight) + learning_rate * value,
                ),
            )
            edge.last_use_tick = max(edge.last_use_tick, int(tick))
            if value > 0.0:
                edge.support += 1
            changed = changed or abs(edge.weight - before) > 1e-12

        return changed
    @property
    def _soft_node_limit(self) -> int:
        return self._adaptive_node_budget

    @property
    def _sense_node_limit(self) -> int:
        return min(self._adaptive_sense_budget, self._adaptive_node_budget)

    @property
    def _soft_edge_limit(self) -> int:
        return self._adaptive_edge_budget

    def _expand_resource_budgets(
        self,
        *,
        need_nodes: bool = False,
        need_edges: bool = False,
        need_senses: bool = False,
    ) -> bool:
        """Develop capacity toward inherited ceilings under structural demand."""
        sensitivity = max(
            0.0,
            min(1.0, self._genome.development.capacity_growth_sensitivity),
        )
        if sensitivity <= 0.0:
            return False

        node_ceiling = min(
            self._kernel_limits.max_nodes,
            self._genome.development.soft_node_budget,
        )
        edge_ceiling = min(
            self._kernel_limits.max_edges,
            self._genome.development.soft_edge_budget,
        )
        sense_ceiling = min(
            node_ceiling,
            self._genome.development.sense_node_budget,
        )

        def grow(current: int, ceiling: int) -> int:
            if current >= ceiling:
                return current
            remaining = ceiling - current
            step = max(1, math.ceil(remaining * sensitivity * 0.25))
            return min(ceiling, current + step)

        changed = False
        if need_nodes:
            updated = grow(self._adaptive_node_budget, node_ceiling)
            changed = changed or updated != self._adaptive_node_budget
            self._adaptive_node_budget = updated
        if need_edges:
            updated = grow(self._adaptive_edge_budget, edge_ceiling)
            changed = changed or updated != self._adaptive_edge_budget
            self._adaptive_edge_budget = updated
        if need_senses:
            effective_ceiling = min(sense_ceiling, self._adaptive_node_budget)
            updated = grow(self._adaptive_sense_budget, effective_ceiling)
            changed = changed or updated != self._adaptive_sense_budget
            self._adaptive_sense_budget = updated
        return changed

    def _admit_senses(self, sense_values: Mapping[str, float], *, tick: int) -> None:
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        existing_ids = {node.node_id for node in self._graph.nodes}
        existing_senses = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.SENSE}
        for sense_id in set(sense_values) & existing_senses:
            self._sense_last_seen_tick[sense_id] = tick

        candidates = sorted(set(sense_values) - existing_ids)
        if not candidates:
            return

        graph = self._graph
        admitted = 0
        sense_count = len(existing_senses)
        if (
            len(graph.nodes) >= self._soft_node_limit
            or sense_count >= self._sense_node_limit
        ):
            self._expand_resource_budgets(
                need_nodes=len(graph.nodes) >= self._soft_node_limit,
                need_senses=sense_count >= self._sense_node_limit,
            )
        for sense_id in candidates:
            if len(graph.nodes) >= self._soft_node_limit or sense_count >= self._sense_node_limit:
                break
            try:
                graph = CognitiveGraph(
                    nodes=(*graph.nodes, PlasticNode(node_id=sense_id, kind=NodeKind.SENSE)),
                    edges=graph.edges,
                    kernel_limits=self._kernel_limits,
                )
            except GraphError:
                continue
            admitted += 1
            sense_count += 1
            self._sense_last_seen_tick[sense_id] = tick

        if admitted:
            self._graph = graph
            self._topology_revision += 1

    def _consume_concept_support(self, parent_ids: Collection[str]) -> None:
        """Forget candidate evidence represented by a committed concept.

        Candidate support is only a pre-birth hypothesis signal. Once a
        concept exists, retaining that evidence would let a later failed and
        garbage-collected concept respawn from historical support instead of
        earning a new birth from fresh observations.
        """
        parents = sorted(set(parent_ids))
        for index, source_id in enumerate(parents):
            for target_id in parents[index + 1 :]:
                key = (source_id, target_id)
                self._concept_support.pop(key, None)
                self._retrospective_concept_support.pop(key, None)

    def _invalidate_shadow_predictions_cache(self) -> None:
        self._predictors.invalidate_shadow_cache()

    @property
    def shadow_predictions(self) -> tuple[ShadowPrediction, ...]:
        return self._predictors.shadow_predictions

    @property
    def _live_shadow_limit(self) -> int:
        return self._predictors.live_shadow_limit(self._kernel_limits.max_nodes)

    @property
    def _preliminary_shadow_limit(self) -> int:
        return self._predictors.preliminary_shadow_limit(
            self._kernel_limits.max_nodes
        )

    def _prune_preliminary_shadow_support(self) -> None:
        node_kinds, _ = self._topology_cache()
        self._predictors.prune_preliminary(
            node_kinds=node_kinds,
            max_nodes=self._kernel_limits.max_nodes,
        )

    def _prune_shadow_predictions(self) -> None:
        node_kinds, _ = self._topology_cache()
        self._predictors.prune_shadows(
            node_kinds=node_kinds,
            topology_revision=self._topology_revision,
            max_nodes=self._kernel_limits.max_nodes,
        )

    def promote_shadow_prediction(self, source_id: str, target_id: str, *, tick: int) -> bool:
        """Register one validated lag-1 predictor for structural contention.

        Promotion no longer materializes graph structure immediately. A
        promotable shadow hypothesis earns the right to contend for bounded
        cognitive capacity; only the consolidation arbiter may execute its
        add-node/add-edge transaction.
        """
        shadow = self._predictors.shadows.get((source_id, target_id))
        if shadow is None or not shadow.promotable or not self._develop_senses:
            return False
        source_node = self._graph.node_by_id(source_id)
        if source_node is None or source_node.kind is not NodeKind.SENSE:
            return False
        if self._graph.node_by_id(target_id) is None or target_id in self._predictors.retirement:
            return False
        if any(
            node.kind is NodeKind.PREDICTOR and node.predicts_node_id == target_id
            for node in self._graph.nodes
        ):
            return False

        candidate_id = f"predictor:{source_id}:{target_id}"
        existing = self._contention.candidates.get(candidate_id)
        if existing is not None:
            return True

        digest = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16]
        predictor_id = f"predictor_{digest}"
        existing_ids = {node.node_id for node in self._graph.nodes}
        if predictor_id in existing_ids:
            return False

        return self._contention.register(
            candidate_id=candidate_id,
            family="predictor",
            eligible_tick=tick,
            mutations=(
                Mutation(
                    kind="add_node",
                    payload={
                        "node_id": predictor_id,
                        "kind": NodeKind.PREDICTOR,
                        "predicts_node_id": target_id,
                    },
                ),
                Mutation(
                    kind="add_edge",
                    payload={
                        "source_id": source_id,
                        "target_id": predictor_id,
                        "kind": EdgeKind.PREDICTIVE,
                        "weight": 1.0,
                        "plasticity": 0.25,
                        "delay_ticks": 0,
                    },
                ),
            ),
        )


    def nominate_shadow_prediction(self, *, tick: int) -> bool:
        """Let predictive learning expose exactly one locally selected nominee.

        The global arbiter never sees shadow multiplicity. Local ranking uses
        only evidence produced by this predictive mechanism and therefore does
        not compare semantic value across cognitive producers.
        """
        producer_id = StructuralContention.producer_id_for_family("predictor")
        if any(
            candidate.producer_id == producer_id
            for candidate in self._contention.candidates.values()
        ):
            return False

        ranked = sorted(
            (
                candidate
                for candidate in self._predictors.shadows.values()
                if candidate.promotable
            ),
            key=lambda candidate: (
                -candidate.predictive_gain,
                -candidate.samples,
                self._contention.candidate_tiebreak(
                    f"{candidate.source_id}:{candidate.target_id}"
                ),
                candidate.source_id,
                candidate.target_id,
            ),
        )
        for candidate in ranked:
            if self.promote_shadow_prediction(
                candidate.source_id,
                candidate.target_id,
                tick=tick,
            ):
                return True
        return False

    @property
    def stranded_concepts(self) -> tuple[str, ...]:
        """Concepts receiving activation but lacking a path to a readout."""
        unrouted = set(self._unrouted_since_tick)
        return tuple(sorted(node_id for node_id in unrouted if node_id in self._concept_last_active_tick))

    def _salient_concept_ids(
        self,
        activations: Mapping[str, float],
        *,
        limit: int = 8,
    ) -> tuple[str, ...]:
        """Scale-adaptive concept context for action learning.

        Absolute 0.1 activity remains the normal criterion. If no concept
        reaches it, retain only the strongest relative outliers so a globally
        low-amplitude but structured graph does not become behaviorally mute.
        This fallback depends only on the organism's own concurrent concept
        activations and carries no environmental semantics.
        """
        kinds, _ = self._topology_cache()
        values = [
            (str(node_id), abs(float(value)))
            for node_id, value in activations.items()
            if (
                kinds.get(node_id) is NodeKind.CONCEPT
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                and abs(float(value)) > 1e-9
            )
        ]
        if not values:
            return ()

        absolute = sorted(
            node_id for node_id, magnitude in values
            if magnitude >= _ACTIVITY_THRESHOLD
        )
        if absolute:
            return tuple(absolute)

        magnitudes = sorted(magnitude for _node_id, magnitude in values)
        midpoint = len(magnitudes) // 2
        if len(magnitudes) % 2:
            median = magnitudes[midpoint]
        else:
            median = 0.5 * (magnitudes[midpoint - 1] + magnitudes[midpoint])
        deviations = sorted(abs(value - median) for value in magnitudes)
        midpoint = len(deviations) // 2
        if len(deviations) % 2:
            mad = deviations[midpoint]
        else:
            mad = 0.5 * (deviations[midpoint - 1] + deviations[midpoint])

        peak = magnitudes[-1]
        relative_threshold = max(
            1e-4,
            median + 1.5 * mad,
            peak * 0.35,
        )
        ranked = sorted(
            (
                (magnitude, node_id)
                for node_id, magnitude in values
                if magnitude >= relative_threshold
            ),
            key=lambda item: (-item[0], item[1]),
        )
        return tuple(sorted(node_id for _magnitude, node_id in ranked[:max(1, int(limit))]))

    def observe_retrospective_support(
        self,
        source_ids: Collection[str],
        *,
        support_epochs: int,
    ) -> int:
        """Retain independent episodic co-occurrence without double counting live support.

        Retrospective evidence is kept separate from per-tick live coactivation.
        Concept birth uses the stronger of the two evidence channels, never
        their sum, so replay cannot manufacture support from the same event.
        """
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return 0
        if (
            isinstance(support_epochs, bool)
            or not isinstance(support_epochs, int)
            or support_epochs <= 0
        ):
            return 0
        kinds, _ = self._topology_cache()
        eligible = tuple(sorted({
            str(source_id)
            for source_id in source_ids
            if kinds.get(str(source_id)) is NodeKind.SENSE
        }))
        if len(eligible) < 2:
            return 0

        gained = 0
        for index, source_id in enumerate(eligible):
            for target_id in eligible[index + 1 :]:
                key = (source_id, target_id)
                if self._concept_signature_exists(key):
                    self._concept_support.pop(key, None)
                    self._retrospective_concept_support.pop(key, None)
                    continue
                previous = self._retrospective_concept_support.get(key, 0)
                updated = max(previous, support_epochs)
                self._retrospective_concept_support[key] = updated
                gained += max(0, updated - previous)
        return gained

    def _record_concept_support(self, activations: Mapping[str, float]) -> None:
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        kinds, _ = self._topology_cache()
        for node_id in self._salient_concept_ids(activations):
            self._concept_last_active_tick[node_id] = self._tick
        threshold = max(_ACTIVITY_THRESHOLD, self._expression_state.effective_growth_threshold)
        active_senses = sorted(
            node_id
            for node_id, value in activations.items()
            if kinds.get(node_id) is NodeKind.SENSE and abs(value) >= threshold
        )
        for index, source_id in enumerate(active_senses):
            for target_id in active_senses[index + 1 :]:
                key = (source_id, target_id)
                if self._concept_signature_exists(key):
                    self._concept_support.pop(key, None)
                    self._retrospective_concept_support.pop(key, None)
                    continue
                self._concept_support[key] = self._concept_support.get(key, 0) + 1

    def _concept_signature_exists(
        self, source_ids: tuple[str, str], *, graph: CognitiveGraph | None = None
    ) -> bool:
        active_graph = self._graph if graph is None else graph
        if active_graph is self._graph:
            if (
                self._cached_concept_sig_rev != self._topology_revision
                or self._cached_concept_sig_graph is not self._graph
                or self._cached_concept_sig_lineage_len != len(self._concept_lineage)
            ):
                sigs = [set(lineage.parent_ids) for lineage in self._concept_lineage.values()]
                concept_ids = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.CONCEPT}
                incoming: dict[str, set[str]] = {concept_id: set() for concept_id in concept_ids}
                for edge in active_graph.edges:
                    if edge.target_id in incoming:
                        incoming[edge.target_id].add(edge.source_id)
                sigs.extend(incoming.values())
                signature_pairs: set[tuple[str, str]] = set()
                for sources in sigs:
                    ordered = sorted(sources)
                    for index, source_id in enumerate(ordered):
                        for target_id in ordered[index + 1 :]:
                            signature_pairs.add((source_id, target_id))
                self._cached_concept_signatures = sigs
                self._cached_concept_signature_pairs = signature_pairs
                self._cached_concept_sig_graph = self._graph
                self._cached_concept_sig_rev = self._topology_revision
                self._cached_concept_sig_lineage_len = len(self._concept_lineage)
            signatures = self._cached_concept_signatures
        else:
            signatures = [set(lineage.parent_ids) for lineage in self._concept_lineage.values()]
            concept_ids = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.CONCEPT}
            incoming = {concept_id: set() for concept_id in concept_ids}
            for edge in active_graph.edges:
                if edge.target_id in incoming:
                    incoming[edge.target_id].add(edge.source_id)
            signatures.extend(incoming.values())

        if len(source_ids) == 2:
            s1, s2 = source_ids[0], source_ids[1]
            if active_graph is self._graph:
                key = (s1, s2) if s1 <= s2 else (s2, s1)
                return key in self._cached_concept_signature_pairs
            return any(s1 in sources and s2 in sources for sources in signatures)
        pair = set(source_ids)
        return any(pair.issubset(sources) for sources in signatures)

    def _extract_max_concept_index(self, graph: CognitiveGraph | None = None) -> int:
        active_graph = self._graph if graph is None else graph
        max_idx = 0
        all_ids = {node.node_id for node in active_graph.nodes} | set(self._concept_lineage.keys())
        for nid in all_ids:
            if nid.startswith("concept_"):
                try:
                    val = int(nid.split("_", 1)[1], 16)
                    if val > max_idx:
                        max_idx = val
                except ValueError:
                    pass
        return max_idx

    def _new_node_id(self, prefix: str, *, graph: CognitiveGraph | None = None) -> str:
        active_graph = self._graph if graph is None else graph
        existing = {node.node_id for node in active_graph.nodes} | set(self._concept_lineage.keys())
        if prefix == "concept":
            while True:
                candidate = f"concept_{self._next_concept_index:016x}"
                self._next_concept_index += 1
                if candidate not in existing:
                    return candidate
        index = 1
        while True:
            candidate = f"{prefix}_{index:016x}"
            if candidate not in existing:
                return candidate
            index += 1

    def _register_germinal_concept_candidate(
        self,
        *,
        tick: int,
        graph: CognitiveGraph | None = None,
    ) -> None:
        active_graph = self._graph if graph is None else graph
        if not self._develop_senses:
            return
        concept_count = sum(
            1 for node in active_graph.nodes if node.kind is NodeKind.CONCEPT
        )
        pending_concepts = sum(
            1
            for candidate in self._contention.candidates.values()
            if candidate.family == "concept"
        )
        if concept_count + pending_concepts >= self._kernel_limits.max_concepts:
            return

        support_pairs = set(self._concept_support) | set(
            self._retrospective_concept_support
        )
        eligible = sorted(
            (
                (
                    max(
                        self._concept_support.get(pair, 0),
                        self._retrospective_concept_support.get(pair, 0),
                    ),
                    pair,
                )
                for pair in support_pairs
                if max(
                    self._concept_support.get(pair, 0),
                    self._retrospective_concept_support.get(pair, 0),
                ) >= self._genome.structure.minimum_support
                and not self._concept_signature_exists(pair, graph=active_graph)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not eligible:
            return

        _, source_ids = eligible[0]
        if any(
            (node := active_graph.node_by_id(source_id)) is None or node.kind is not NodeKind.SENSE
            for source_id in source_ids
        ):
            return

        signature = "|".join(source_ids)
        candidate_id = f"concept:{signature}"
        if candidate_id in self._contention.candidates:
            return

        core_readouts = sorted(
            node.node_id
            for node in active_graph.nodes
            if node.kind is NodeKind.READOUT
            and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
            and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        )
        if _CORE_READOUT_ID in core_readouts:
            core_readouts = [_CORE_READOUT_ID]

        concept_id = self._new_node_id("concept", graph=active_graph)
        mutations: list[Mutation] = [
            Mutation(
                kind="add_node",
                payload={
                    "node_id": concept_id,
                    "kind": NodeKind.CONCEPT,
                    "source_ids": source_ids,
                },
            )
        ]

        if core_readouts:
            readout_id = core_readouts[0]
        else:
            # A germinal concept and its first usable output form one minimal
            # functional unit. Admit them atomically so neither half can be
            # orphaned while waiting for another producer turn.
            existing_ids = {node.node_id for node in active_graph.nodes}
            if _CORE_READOUT_ID in existing_ids:
                return
            readout_id = _CORE_READOUT_ID
            mutations.append(
                Mutation(
                    kind="add_node",
                    payload={
                        "node_id": readout_id,
                        "kind": NodeKind.READOUT,
                    },
                )
            )

        mutations.append(
            Mutation(
                kind="add_edge",
                payload={
                    "source_id": concept_id,
                    "target_id": readout_id,
                    "kind": EdgeKind.EXCITATORY,
                    "weight": _TENTATIVE_WEIGHT,
                    "plasticity": 0.5,
                    "delay_ticks": 1,
                },
            )
        )
        self._contention.register(
            candidate_id=candidate_id,
            family="concept",
            eligible_tick=tick,
            mutations=tuple(mutations),
        )

    def _nodes_with_path_to_targets(
        self, target_ids: Collection[str], graph: CognitiveGraph | None = None
    ) -> set[str]:
        active_graph = self._graph if graph is None else graph
        node_ids = {node.node_id for node in active_graph.nodes}
        targets = set(target_ids) & node_ids
        if not targets:
            return set()
        reverse_adj: dict[str, set[str]] = {}
        for edge in active_graph.edges:
            reverse_adj.setdefault(edge.target_id, set()).add(edge.source_id)
        reachable = set(targets)
        frontier = list(targets)
        while frontier:
            target = frontier.pop()
            for source in reverse_adj.get(target, ()):
                if source not in reachable:
                    reachable.add(source)
                    frontier.append(source)
        return reachable

    def _nodes_with_path_to_core_readout(self, graph: CognitiveGraph | None = None) -> set[str]:
        active_graph = self._graph if graph is None else graph
        core_readouts = [
            node.node_id
            for node in active_graph.nodes
            if node.kind is NodeKind.READOUT and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
            and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        ]
        if _CORE_READOUT_ID in core_readouts:
            targets = (_CORE_READOUT_ID,)
        else:
            targets = tuple(core_readouts)
        return self._nodes_with_path_to_targets(targets, active_graph)

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

    def _update_unrouted_tracking(self, tick: int, *, graph: CognitiveGraph | None = None) -> set[str]:
        active_graph = self._graph if graph is None else graph
        routed = self._nodes_with_path_to_core_readout(active_graph)
        concept_ids = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.CONCEPT}
        unrouted = concept_ids - routed
        for node_id in concept_ids:
            if node_id in unrouted:
                self._unrouted_since_tick.setdefault(node_id, tick)
            else:
                self._unrouted_since_tick.pop(node_id, None)
        return unrouted

    def _propose_concept_recycling_mutations(
        self,
        *,
        tick: int,
        mutation_slots: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[tuple[Mutation, ...], dict[str, object] | None]:
        """Repair a stranded concept without creating replacement nodes.

        New concepts are admitted exclusively through structural contention.
        """
        active_graph = self._graph if graph is None else graph
        if not self._develop_senses or mutation_slots < 1:
            return (), None

        core_readouts = sorted(
            node.node_id
            for node in active_graph.nodes
            if node.kind is NodeKind.READOUT
            and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
            and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        )
        if _CORE_READOUT_ID in core_readouts:
            core_readouts = [_CORE_READOUT_ID]
        if not core_readouts:
            return (), None

        unrouted_ids = self._update_unrouted_tracking(tick, graph=active_graph)
        stranded = [
            node_id
            for node_id in sorted(unrouted_ids)
            if node_id in self._concept_last_active_tick
        ]
        if not stranded:
            return (), None

        concept_id = stranded[0]
        readout_id = core_readouts[0]
        if any(
            edge.source_id == concept_id and edge.target_id == readout_id
            for edge in active_graph.edges
        ):
            return (), None

        mutation = Mutation(
            kind="add_edge",
            payload={
                "source_id": concept_id,
                "target_id": readout_id,
                "kind": EdgeKind.EXCITATORY,
                "weight": _TENTATIVE_WEIGHT,
                "plasticity": 0.25,
                "delay_ticks": 1,
            },
        )
        candidate_graph = apply_mutations(
            active_graph, (mutation,), self._kernel_limits, frozen=False
        )
        if candidate_graph is active_graph:
            return (), None
        return (
            (mutation,),
            {"tick": tick, "concept_id": concept_id, "reason": "stranded_route_repair"},
        )

    def _orphan_latent_ids(self, graph: CognitiveGraph | None = None) -> set[str]:
        active_graph = self._graph if graph is None else graph
        incident = {node.node_id: 0 for node in active_graph.nodes}
        for edge in active_graph.edges:
            incident[edge.source_id] = incident.get(edge.source_id, 0) + 1
            incident[edge.target_id] = incident.get(edge.target_id, 0) + 1
        return {
            node.node_id
            for node in active_graph.nodes
            if (
                node.kind in (
                    NodeKind.CONCEPT,
                    NodeKind.STATE,
                    NodeKind.GATE,
                    NodeKind.READOUT,
                )
                and incident.get(node.node_id, 0) == 0
            )
        }

    def _orphan_node_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        if not self._develop_senses or max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        protected = {str(node_id) for node_id in protected_node_ids if str(node_id)}
        orphan_ids = self._orphan_latent_ids(active_graph) - protected
        for node in active_graph.nodes:
            if (
                node.kind in (
                    NodeKind.CONCEPT,
                    NodeKind.STATE,
                    NodeKind.GATE,
                    NodeKind.READOUT,
                )
                and node.node_id not in orphan_ids
            ):
                self._orphan_since_tick.pop(node.node_id, None)

        grace = max(1, self._genome.structure.tentative_lifetime_ticks)
        mutations: list[Mutation] = []
        for node_id in sorted(orphan_ids):
            since = self._orphan_since_tick.setdefault(node_id, tick)
            if tick - since < grace:
                continue
            mutations.append(Mutation(kind="remove_node", payload={"node_id": node_id}))
            if len(mutations) >= max_mutations:
                break
        return tuple(mutations)

    def _sense_eviction_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        if not self._develop_senses or max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        senses = [node for node in active_graph.nodes if node.kind is NodeKind.SENSE]
        if not senses:
            return ()
        incident_ids = {node_id for edge in active_graph.edges for node_id in (edge.source_id, edge.target_id)}
        over_budget = max(0, len(senses) - self._sense_node_limit)
        retention = max(1, self._genome.development.sense_retention_ticks)
        candidates: list[tuple[bool, int, str]] = []
        for node in senses:
            if node.node_id in incident_ids:
                continue
            last_seen = self._sense_last_seen_tick.get(node.node_id, 0)
            stale = tick - last_seen >= retention
            candidates.append((stale, last_seen, node.node_id))

        candidates.sort(key=lambda item: (not item[0], item[1], item[2]))
        mutations: list[Mutation] = []
        needed_over_budget = over_budget
        for stale, _, node_id in candidates:
            if not stale and needed_over_budget <= 0:
                continue
            mutations.append(Mutation(kind="remove_node", payload={"node_id": node_id}))
            if needed_over_budget > 0:
                needed_over_budget -= 1
            if len(mutations) >= max_mutations:
                break
        return tuple(mutations)

    def _has_sense_to_readout_path(
        self, graph: CognitiveGraph | None = None, *, established_only: bool = False
    ) -> bool:
        active_graph = self._graph if graph is None else graph
        senses = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.SENSE}
        readouts = {
            node.node_id
            for node in active_graph.nodes
            if node.kind is NodeKind.READOUT and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
            and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        }
        if _CORE_READOUT_ID in readouts:
            readouts = {_CORE_READOUT_ID}
        if not senses or not readouts:
            return False
        adjacency: dict[str, set[str]] = {}
        for edge in active_graph.edges:
            if established_only and edge.support < self._genome.structure.minimum_support:
                continue
            adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        frontier = list(senses)
        visited = set(senses)
        while frontier:
            source_id = frontier.pop()
            for target_id in adjacency.get(source_id, ()):
                if target_id in readouts:
                    return True
                if target_id not in visited:
                    visited.add(target_id)
                    frontier.append(target_id)
        return False

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
                self._orphan_since_tick.setdefault(node_id, 0)

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
                    self._node_born_tick.setdefault(node_id, max(0, int(tick)))
                    self._node_observation_count.setdefault(node_id, 0)
                    self._node_active_count.setdefault(node_id, 0)
                if kind is NodeKind.CONCEPT:
                    raw_sources = mutation.payload.get("source_ids", ())
                    if isinstance(raw_sources, (list, tuple, set)):
                        parent_ids = tuple(sorted(str(value) for value in raw_sources))
                        if parent_ids:
                            self._concept_lineage[node_id] = ConceptLineage(node_id, parent_ids, tick)
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
                self._concept_lineage.pop(node_id, None)
                self._sense_last_seen_tick.pop(node_id, None)
                self._orphan_since_tick.pop(node_id, None)
                self._unrouted_since_tick.pop(node_id, None)
                self._normalizers.pop(node_id, None)
                self._predictors.utility.pop(node_id, None)
                self._predictors.retirement.pop(node_id, None)
                self._node_born_tick.pop(node_id, None)
                self._node_observation_count.pop(node_id, None)
                self._node_active_count.pop(node_id, None)
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
        self._sense_last_seen_tick = {key: value for key, value in self._sense_last_seen_tick.items() if key in sense_ids}
        self._concept_lineage = {key: value for key, value in self._concept_lineage.items() if key in concept_ids}
        self._orphan_since_tick = {key: value for key, value in self._orphan_since_tick.items() if key in latent_ids}
        self._unrouted_since_tick = {key: value for key, value in self._unrouted_since_tick.items() if key in concept_ids}
        self._normalizers = {key: value for key, value in self._normalizers.items() if key in sense_ids}
        self._node_born_tick = {
            key: value for key, value in self._node_born_tick.items() if key in node_ids
        }
        for node_id in node_ids:
            self._node_born_tick.setdefault(node_id, 0)
        self._node_observation_count = {
            key: value
            for key, value in self._node_observation_count.items()
            if key in node_ids
        }
        self._node_active_count = {
            key: value
            for key, value in self._node_active_count.items()
            if key in node_ids
        }
        for node_id in node_ids:
            self._node_observation_count.setdefault(node_id, 0)
            self._node_active_count.setdefault(node_id, 0)
        self._concept_support = {
            pair: count
            for pair, count in self._concept_support.items()
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
        return {
            "graph": export_graph_checkpoint(self._graph, weight_class_overrides=self._weight_class_overrides()),
            "safety_state": export_safety_state(self._safety_state),
            "sensory_normalizers": export_sensory_normalizers(self._normalizers),
            "topology_revision": self._topology_revision,
            "tick": self._tick,
            "develop_senses": self._develop_senses,
            "concept_lineage": [
                {"concept_id": x.concept_id, "parent_ids": list(x.parent_ids), "born_tick": x.born_tick}
                for x in self.concept_lineage
            ],
            "sense_last_seen_tick": dict(sorted(self._sense_last_seen_tick.items())),
            "orphan_since_tick": dict(sorted(self._orphan_since_tick.items())),
            "unrouted_since_tick": dict(sorted(self._unrouted_since_tick.items())),
            "concept_last_active_tick": dict(sorted(self._concept_last_active_tick.items())),
            "node_born_tick": dict(sorted(self._node_born_tick.items())),
            "node_observation_count": dict(sorted(self._node_observation_count.items())),
            "node_active_count": dict(sorted(self._node_active_count.items())),
            "next_concept_index": self._next_concept_index,
            "recovery_pending": self._recovery_pending,
            "shadow_predictions": [
                {"source_id": item.source_id, "target_id": item.target_id,
                 "samples": item.samples, "model_loss": item.model_loss,
                 "persistence_loss": item.persistence_loss, "status": item.status}
                for item in self.shadow_predictions
            ],
            "predictor_utility": [
                utility.checkpoint(predictor_id)
                for predictor_id, utility
                in sorted(self._predictors.utility.items())
            ],
            "predictor_retirement": [
                retirement.checkpoint()
                for _, retirement
                in sorted(self._predictors.retirement.items())
            ],
            "structural_candidates": [
                candidate.checkpoint()
                for _, candidate
                in sorted(self._contention.candidates.items())
            ],
            "consolidation_generation": self._contention.consolidation_generation,
            "last_consolidated_producer_id": self._contention.last_consolidated_producer_id,
            "adaptive_resource_budgets": {
                "nodes": self._adaptive_node_budget,
                "edges": self._adaptive_edge_budget,
                "senses": self._adaptive_sense_budget,
            },
        }

    def _weight_class_overrides(self) -> dict[tuple[str, str, str], int]:
        return self._plasticity.weight_class_overrides(self._graph)

    @staticmethod
    def _restore_nonnegative_tick_map(
        payload: object, *, allowed_ids: Collection[str], field: str
    ) -> dict[str, int]:
        if payload is None:
            return {}
        if not isinstance(payload, Mapping):
            raise GraphError(f"{field} must be an object")
        allowed = set(allowed_ids)
        restored: dict[str, int] = {}
        for raw_id, raw_tick in payload.items():
            node_id = str(raw_id)
            if node_id not in allowed:
                continue
            if isinstance(raw_tick, bool) or not isinstance(raw_tick, int) or raw_tick < 0:
                raise GraphError(f"{field} values must be non-negative integers")
            restored[node_id] = raw_tick
        return restored


    @staticmethod
    def _restore_shadow_predictions(
        payload: object, *, max_predictions: int = _MAX_SHADOW_PREDICTIONS
    ) -> dict[tuple[str, str], ShadowPrediction]:
        if payload is None:
            return {}
        if not isinstance(payload, list) or len(payload) > max_predictions:
            raise GraphError("shadow_predictions must be a bounded list")
        restored: dict[tuple[str, str], ShadowPrediction] = {}
        for entry in payload:
            if not isinstance(entry, Mapping):
                raise GraphError("shadow_predictions entries must be objects")
            source_id = str(entry.get("source_id", ""))[:128]
            target_id = str(entry.get("target_id", ""))[:128]
            if not source_id or not target_id or source_id == target_id or (source_id, target_id) in restored:
                continue
            samples = entry.get("samples", 0)
            model_loss = entry.get("model_loss", 0.0)
            persistence_loss = entry.get("persistence_loss", 0.0)
            status = str(entry.get("status", "candidate"))
            if isinstance(samples, bool) or not isinstance(samples, int) or not 0 <= samples <= 1_000_000:
                raise GraphError("shadow prediction samples out of bounds")
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) < 0.0
                   for value in (model_loss, persistence_loss)):
                raise GraphError("shadow prediction losses out of bounds")
            if status not in {"candidate", "supported", "contradicted", "retired"}:
                raise GraphError("invalid shadow prediction status")
            restored[(source_id, target_id)] = ShadowPrediction(
                source_id, target_id, samples, float(model_loss), float(persistence_loss), status
            )
        return restored

    @staticmethod
    def _restore_predictor_utility(
        payload: object,
        *,
        allowed_predictor_ids: Collection[str],
    ) -> dict[str, PredictorUtility]:
        if payload is None:
            return {}
        allowed = set(allowed_predictor_ids)
        if not isinstance(payload, list):
            raise GraphError("predictor_utility must be a bounded list")
        restored: dict[str, PredictorUtility] = {}
        for entry in payload:
            if not isinstance(entry, Mapping):
                raise GraphError("predictor_utility entries must be objects")
            predictor_id = entry.get("predictor_id")
            samples = entry.get("samples", 0)
            model_loss = entry.get("model_loss", 0.0)
            persistence_loss = entry.get("persistence_loss", 0.0)
            recent_gain = entry.get("recent_gain", 0.0)
            negative_streak = entry.get("negative_streak", 0)
            positive_streak = entry.get("positive_streak", 0)
            if not isinstance(predictor_id, str) or predictor_id not in allowed:
                continue
            if (
                isinstance(samples, bool)
                or not isinstance(samples, int)
                or not 0 <= samples <= 1_000_000_000
            ):
                raise GraphError("predictor utility samples out of bounds")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0.0
                for value in (model_loss, persistence_loss)
            ):
                raise GraphError("predictor utility losses out of bounds")
            if (
                isinstance(recent_gain, bool)
                or not isinstance(recent_gain, (int, float))
                or not math.isfinite(float(recent_gain))
            ):
                raise GraphError("predictor recent gain must be finite")
            if any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 1_000_000_000
                for value in (negative_streak, positive_streak)
            ):
                raise GraphError("predictor utility streak out of bounds")
            restored[predictor_id] = PredictorUtility(
                samples=samples,
                model_loss=float(model_loss),
                persistence_loss=float(persistence_loss),
                recent_gain=float(recent_gain),
                negative_streak=negative_streak,
                positive_streak=positive_streak,
            )
        return restored


    @staticmethod
    def _restore_predictor_retirement(
        payload: object,
        *,
        allowed_predictor_ids: Collection[str],
    ) -> dict[str, PredictorRetirement]:
        if payload is None:
            return {}
        allowed = set(allowed_predictor_ids)
        if not isinstance(payload, list) or len(payload) > 1:
            raise GraphError("predictor_retirement must contain at most one candidate")
        restored: dict[str, PredictorRetirement] = {}
        for entry in payload:
            if not isinstance(entry, Mapping):
                raise GraphError("predictor_retirement entries must be objects")
            predictor_id = entry.get("predictor_id")
            entered_tick = entry.get("entered_tick")
            last_evaluated_tick = entry.get("last_evaluated_tick")
            if not isinstance(predictor_id, str) or predictor_id not in allowed:
                continue
            if any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in (entered_tick, last_evaluated_tick)
            ):
                raise GraphError("predictor retirement ticks must be non-negative")
            restored[predictor_id] = PredictorRetirement(
                predictor_id=predictor_id,
                entered_tick=entered_tick,
                last_evaluated_tick=last_evaluated_tick,
            )
        return restored


    @staticmethod
    def _restore_structural_candidates(
        payload: object,
        *,
        kernel_limits: KernelLimits,
    ) -> dict[str, StructuralCandidate]:
        if payload is None:
            return {}
        if (
            not isinstance(payload, list)
            or len(payload) > kernel_limits.max_consolidation_candidates
        ):
            raise GraphError("structural_candidates must be a bounded list")
        restored: dict[str, StructuralCandidate] = {}
        for entry in payload:
            if not isinstance(entry, Mapping):
                raise GraphError("structural candidate entries must be objects")
            candidate_id = entry.get("candidate_id")
            family = entry.get("family")
            producer_id = entry.get("producer_id")
            eligible_tick = entry.get("eligible_tick")
            contention_losses = entry.get("contention_losses", 0)
            raw_mutations = entry.get("mutations")
            if (
                not isinstance(candidate_id, str)
                or not candidate_id
                or len(candidate_id) > 512
                or candidate_id in restored
                or not isinstance(family, str)
                or not family
                or len(family) > 128
                or (
                    producer_id is not None
                    and (
                        not isinstance(producer_id, str)
                        or not producer_id
                        or len(producer_id) > 256
                    )
                )
            ):
                continue
            if any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in (eligible_tick, contention_losses)
            ):
                raise GraphError("structural candidate counters must be non-negative")
            if (
                not isinstance(raw_mutations, list)
                or not 1 <= len(raw_mutations)
                <= kernel_limits.max_structural_mutations_per_consolidation
            ):
                raise GraphError("structural candidate mutations out of bounds")
            mutations: list[Mutation] = []
            for raw in raw_mutations:
                if not isinstance(raw, Mapping):
                    raise GraphError("structural candidate mutation must be an object")
                kind = raw.get("kind")
                payload_map = raw.get("payload")
                if kind not in {"add_node", "add_edge"} or not isinstance(payload_map, Mapping):
                    raise GraphError("invalid structural candidate mutation")
                mutations.append(Mutation(kind=str(kind), payload=dict(payload_map)))
            resolved_producer = (
                str(producer_id)
                if isinstance(producer_id, str) and producer_id
                else StructuralContention.producer_id_for_family(str(family))
            )
            candidate = StructuralCandidate(
                candidate_id=candidate_id,
                family=str(family),
                producer_id=resolved_producer,
                eligible_tick=eligible_tick,
                contention_losses=0,
                mutations=tuple(mutations),
            )
            incumbent = next(
                (
                    existing
                    for existing in restored.values()
                    if existing.producer_id == resolved_producer
                ),
                None,
            )
            if incumbent is None:
                restored[candidate_id] = candidate
            elif (candidate.eligible_tick, candidate.candidate_id) < (
                incumbent.eligible_tick,
                incumbent.candidate_id,
            ):
                restored.pop(incumbent.candidate_id, None)
                restored[candidate_id] = candidate
        return restored


    @classmethod
    def _restore_concept_lineage(
        cls, payload: object, *, graph: CognitiveGraph, kernel_limits: KernelLimits
    ) -> dict[str, ConceptLineage]:
        concept_ids = {node.node_id for node in graph.nodes if node.kind is NodeKind.CONCEPT}
        restored: dict[str, ConceptLineage] = {}
        if payload is not None:
            if not isinstance(payload, list):
                raise GraphError("concept_lineage must be a list")
            if len(payload) > kernel_limits.max_concepts:
                raise GraphError("concept_lineage exceeds kernel concept bound")
            for entry in payload:
                if not isinstance(entry, Mapping):
                    raise GraphError("concept_lineage entries must be objects")
                concept_id = str(entry.get("concept_id", ""))
                if concept_id not in concept_ids or concept_id in restored:
                    continue
                raw_parents = entry.get("parent_ids")
                if not isinstance(raw_parents, list) or not 2 <= len(raw_parents) <= 4:
                    raise GraphError("concept_lineage.parent_ids must contain 2 to 4 ids")
                parent_ids = tuple(str(value) for value in raw_parents)
                if len(set(parent_ids)) != len(parent_ids):
                    raise GraphError("concept_lineage.parent_ids must be unique")
                born_tick = entry.get("born_tick")
                if isinstance(born_tick, bool) or not isinstance(born_tick, int) or born_tick < 0:
                    raise GraphError("concept_lineage.born_tick must be a non-negative integer")
                restored[concept_id] = ConceptLineage(concept_id, parent_ids, born_tick)

        incoming: dict[str, set[str]] = {concept_id: set() for concept_id in concept_ids}
        for edge in graph.edges:
            if edge.target_id in incoming:
                incoming[edge.target_id].add(edge.source_id)
        for concept_id, parents in incoming.items():
            if concept_id not in restored and len(parents) >= 2:
                restored[concept_id] = ConceptLineage(concept_id, tuple(sorted(parents))[:4], 0)
        return restored

    @classmethod
    def restore(
        cls, payload: dict[str, object] | None, *, genome: Genome, kernel_limits: KernelLimits
    ) -> "CognitiveBridge | None":
        if payload is None:
            return None
        raw_graph = payload.get("graph")
        graph_payload = raw_graph if isinstance(raw_graph, dict) else None
        graph = restore_graph_checkpoint(graph_payload, kernel_limits=kernel_limits)
        if graph is None:
            return None
        raw_safety = payload.get("safety_state")
        safety_payload = raw_safety if isinstance(raw_safety, dict) else None
        safety_state = restore_safety_state(safety_payload)
        structural_plasticity = StructuralPlasticity(
            min_candidate_support=genome.structure.minimum_support,
            tentative_lifetime_ticks=genome.structure.tentative_lifetime_ticks,
            cooldown_ticks=genome.structure.tentative_lifetime_ticks,
        )
        raw_develop_senses = payload.get("develop_senses")
        if raw_develop_senses is None:
            develop_senses = not graph.nodes
        elif not isinstance(raw_develop_senses, bool):
            raise GraphError("develop_senses must be a boolean")
        else:
            develop_senses = raw_develop_senses
        bridge = cls(
            graph=graph,
            genome=genome,
            kernel_limits=kernel_limits,
            structural_plasticity=structural_plasticity,
            safety_state=safety_state,
            develop_senses=develop_senses,
        )
        raw_budgets = payload.get("adaptive_resource_budgets")
        if raw_budgets is not None:
            if not isinstance(raw_budgets, Mapping):
                raise GraphError("adaptive_resource_budgets must be an object")
            for field, ceiling in (
                ("nodes", kernel_limits.max_nodes),
                ("edges", kernel_limits.max_edges),
                ("senses", kernel_limits.max_nodes),
            ):
                value = raw_budgets.get(field)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0
                    or value > ceiling
                ):
                    raise GraphError(f"invalid adaptive {field} budget")
            bridge._adaptive_node_budget = max(
                len(graph.nodes),
                int(raw_budgets["nodes"]),
            )
            bridge._adaptive_edge_budget = max(
                len(graph.edges),
                int(raw_budgets["edges"]),
            )
            sense_count = sum(
                1 for node in graph.nodes if node.kind is NodeKind.SENSE
            )
            bridge._adaptive_sense_budget = min(
                bridge._adaptive_node_budget,
                max(sense_count, int(raw_budgets["senses"])),
            )
        raw_tick = payload.get("tick", 0)
        if isinstance(raw_tick, bool) or not isinstance(raw_tick, int) or raw_tick < 0:
            raise GraphError("tick must be a non-negative integer")
        bridge._tick = raw_tick
        raw_normalizers = payload.get("sensory_normalizers")
        normalizers_payload = raw_normalizers if isinstance(raw_normalizers, dict) else None
        bridge._normalizers = restore_sensory_normalizers(normalizers_payload)
        bridge._concept_lineage = cls._restore_concept_lineage(
            payload.get("concept_lineage"), graph=graph, kernel_limits=kernel_limits
        )
        sense_ids = {node.node_id for node in graph.nodes if node.kind is NodeKind.SENSE}
        latent_ids = {
            node.node_id
            for node in graph.nodes
            if node.kind in (
                NodeKind.CONCEPT,
                NodeKind.STATE,
                NodeKind.GATE,
                NodeKind.READOUT,
            )
        }
        bridge._sense_last_seen_tick = cls._restore_nonnegative_tick_map(
            payload.get("sense_last_seen_tick"), allowed_ids=sense_ids, field="sense_last_seen_tick"
        )
        bridge._orphan_since_tick = cls._restore_nonnegative_tick_map(
            payload.get("orphan_since_tick"), allowed_ids=latent_ids, field="orphan_since_tick"
        )
        concept_ids = {node.node_id for node in graph.nodes if node.kind is NodeKind.CONCEPT}
        bridge._unrouted_since_tick = cls._restore_nonnegative_tick_map(
            payload.get("unrouted_since_tick"), allowed_ids=concept_ids, field="unrouted_since_tick"
        )
        bridge._concept_last_active_tick = cls._restore_nonnegative_tick_map(
            payload.get("concept_last_active_tick"), allowed_ids=concept_ids, field="concept_last_active_tick"
        )
        bridge._node_born_tick = {
            node.node_id: 0 for node in graph.nodes
        }
        all_node_ids = {node.node_id for node in graph.nodes}
        bridge._node_born_tick.update(
            cls._restore_nonnegative_tick_map(
                payload.get("node_born_tick"),
                allowed_ids=all_node_ids,
                field="node_born_tick",
            )
        )
        bridge._node_observation_count = {
            node.node_id: 0 for node in graph.nodes
        }
        bridge._node_observation_count.update(
            cls._restore_nonnegative_tick_map(
                payload.get("node_observation_count"),
                allowed_ids=all_node_ids,
                field="node_observation_count",
            )
        )
        bridge._node_active_count = {
            node.node_id: 0 for node in graph.nodes
        }
        bridge._node_active_count.update(
            cls._restore_nonnegative_tick_map(
                payload.get("node_active_count"),
                allowed_ids=all_node_ids,
                field="node_active_count",
            )
        )
        raw_next_idx = payload.get("next_concept_index")
        if isinstance(raw_next_idx, int) and raw_next_idx > 0:
            bridge._next_concept_index = raw_next_idx
        else:
            bridge._next_concept_index = bridge._extract_max_concept_index(graph=graph) + 1
        raw_recovery = payload.get("recovery_pending", False)
        if not isinstance(raw_recovery, bool):
            raise GraphError("recovery_pending must be a boolean")
        bridge._recovery_pending = raw_recovery
        shadow_limit = min(_MAX_SHADOW_PREDICTIONS, kernel_limits.max_nodes * kernel_limits.max_nodes)
        bridge._shadow_predictions = cls._restore_shadow_predictions(
            payload.get("shadow_predictions"), max_predictions=shadow_limit
        )
        bridge._invalidate_shadow_predictions_cache()
        bridge._shadow_prune_dirty = True
        bridge._shadow_prune_topology_revision = -1
        predictor_ids = {
            node.node_id for node in graph.nodes
            if node.kind is NodeKind.PREDICTOR
        }
        bridge._predictor_utility = cls._restore_predictor_utility(
            payload.get("predictor_utility"),
            allowed_predictor_ids=predictor_ids,
        )
        bridge._predictor_retirement = cls._restore_predictor_retirement(
            payload.get("predictor_retirement"),
            allowed_predictor_ids=predictor_ids,
        )
        bridge._structural_candidates = cls._restore_structural_candidates(
            payload.get("structural_candidates"),
            kernel_limits=kernel_limits,
        )
        raw_generation = payload.get("consolidation_generation", 0)
        if (
            isinstance(raw_generation, bool)
            or not isinstance(raw_generation, int)
            or raw_generation < 0
        ):
            raise GraphError("consolidation_generation must be non-negative")
        bridge._consolidation_generation = raw_generation
        raw_last_producer = payload.get("last_consolidated_producer_id")
        if raw_last_producer is not None and (
            not isinstance(raw_last_producer, str)
            or not raw_last_producer
            or len(raw_last_producer) > 256
        ):
            raise GraphError("last_consolidated_producer_id must be a bounded string")
        bridge._last_consolidated_producer_id = raw_last_producer
        bridge._prune_shadow_predictions()
        raw_revision = payload.get("topology_revision", 0)
        if isinstance(raw_revision, bool) or not isinstance(raw_revision, int) or raw_revision < 0:
            raise GraphError("topology_revision must be a non-negative integer")
        bridge._topology_revision = raw_revision
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
            for edge in self._graph.edges:
                source_value = (
                    sense_inputs.get(edge.source_id, 0.0)
                    if edge.delay_ticks == 0
                    else self._previous_frame.get(edge.source_id, 0.0)
                )
                target_current = frame.activations.get(edge.target_id, 0.0)
                update_eligibility(
                    edge,
                    source_previous=source_value,
                    target_current=target_current,
                    decay=self._genome.plasticity.eligibility_decay,
                )
                retiring_edge = (
                    edge.source_id in self._predictors.retirement
                    or edge.target_id in self._predictors.retirement
                )
                eligible = (
                    not retiring_edge
                    and edge.source_id in learning_nodes
                    and edge.target_id in learning_nodes
                    and abs(edge.eligibility) >= _ELIGIBILITY_THRESHOLD
                )
                apply_oja_update(
                    edge,
                    source_activation=source_value,
                    target_activation=target_current,
                    learning_rate=self._expression_state.effective_learning_rate,
                    modulation=(tick_modulation * edge.plasticity * self._expression_state.effective_structural_plasticity),
                    eligible=eligible,
                    frozen=frozen,
                )
                if retiring_edge:
                    self._retirement_edge_decay(edge, tick=tick)
                transmitted = edge.weight * source_value
                advance_edge_age(edge, tick=tick, used=abs(transmitted) >= _EDGE_USAGE_THRESHOLD)

            self._plasticity.observe_and_consolidate(
                self._graph,
                tick=tick,
                max_incoming_norm=(
                    self._kernel_limits.max_incoming_consolidated_weight_norm
                ),
            )

            node_kinds, existing_relation_pairs = self._topology_cache()
            for node_id, value in frame.activations.items():
                self._node_observation_count[node_id] = (
                    self._node_observation_count.get(node_id, 0) + 1
                )
                if abs(value) >= _ACTIVITY_THRESHOLD:
                    self._node_active_count[node_id] = (
                        self._node_active_count.get(node_id, 0) + 1
                    )
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
            if self._previous_frame is not None:
                # Preliminary shadow hypotheses are cheap, bounded evidence
                # records. Structural promotion still requires the separate
                # eight-sample gain gate, so delaying admission by the genome
                # concept-growth support threshold loses the first part of a
                # valid time series and makes checkpoint replay path-dependent.
                preliminary_min = 1
                if len(self._predictors.shadows) >= self._live_shadow_limit:
                    self._prune_shadow_predictions()
                for source_id, source_value in self._previous_frame.items():
                    if node_kinds.get(source_id) is not NodeKind.SENSE:
                        continue
                    for target_id, target_value in frame.activations.items():
                        if source_id == target_id or target_id not in self._previous_frame:
                            continue
                        target_previous = self._previous_frame[target_id]
                        key = (source_id, target_id)
                        predictor = self._predictors.shadows.get(key)
                        if predictor is not None:
                            # Once admitted, evaluate the hypothesis on every
                            # compatible tick. Preliminary selection must not
                            # censor boring/negative evidence.
                            previous_status = predictor.status
                            predictor.observe(
                                source_value,
                                target_value,
                                target_previous,
                            )
                            if (
                                previous_status != "retired"
                                and predictor.status == "retired"
                            ):
                                self._predictors.mark_shadow_dirty()
                            continue

                        if abs(source_value) < _ACTIVITY_THRESHOLD:
                            continue
                        support = self._predictors.preliminary_support.get(key, 0) + 1
                        self._predictors.preliminary_support[key] = support
                        if support < preliminary_min:
                            continue
                        if len(self._predictors.shadows) >= self._live_shadow_limit:
                            continue
                        predictor = ShadowPrediction(source_id, target_id)
                        self._predictors.shadows[key] = predictor
                        self._invalidate_shadow_predictions_cache()
                        self._predictors.preliminary_support.pop(key, None)
                        predictor.observe(source_value, target_value, target_previous)
                self._prune_preliminary_shadow_support()
                self._prune_shadow_predictions()

        structural_mutations_applied = 0
        applied_mutations: tuple[Mutation, ...] = ()
        recycling_events: tuple[dict[str, object], ...] = ()
        interval = max(1, self._genome.development.consolidation_interval_ticks)
        if not frozen and self._reacclimation_remaining <= 0 and tick % interval == 0:
            mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation

            # Maintenance is planned sequentially but committed only once.
            # Fully detached quarantined predictors are reclaimed first using
            # one bounded mutation. Under sustained generic structural
            # starvation, one already-quarantined incident edge may then retire
            # within the same bounded maintenance budget.
            retirement_gc = self._retirement_node_gc_mutations(
                max_mutations=min(1, mutation_cap),
                graph=self._graph,
            )
            after_retirement_gc = apply_mutations(
                self._graph,
                retirement_gc,
                self._kernel_limits,
                frozen=frozen,
            )
            if retirement_gc and after_retirement_gc is self._graph:
                retirement_gc = ()
                after_retirement_gc = self._graph

            remaining_after_node_gc = mutation_cap - len(retirement_gc)
            retirement_edge_gc = self._retirement_edge_gc_mutations(
                tick=tick,
                max_mutations=min(1, remaining_after_node_gc),
                graph=after_retirement_gc,
            )
            after_retirement_edge_gc = apply_mutations(
                after_retirement_gc,
                retirement_edge_gc,
                self._kernel_limits,
                frozen=frozen,
            )
            if retirement_edge_gc and after_retirement_edge_gc is after_retirement_gc:
                retirement_edge_gc = ()
                after_retirement_edge_gc = after_retirement_gc

            remaining_after_gc = (
                mutation_cap - len(retirement_gc) - len(retirement_edge_gc)
            )

            # prune edges -> GC newly/previously orphaned latent nodes -> evict
            # disconnected senses. Each stage sees the topology produced by
            # the previous stage, so pruning can begin an orphan grace period
            # immediately without exposing a partial graph.
            prune_candidates = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={"source_id": edge.source_id, "target_id": edge.target_id, "kind": edge.kind},
                )
                for edge in after_retirement_edge_gc.edges
                if evaluate_edge_lifecycle(
                    edge,
                    current_tick=tick,
                    prune_threshold=self._expression_state.effective_pruning_threshold,
                    minimum_support=self._genome.structure.minimum_support,
                    quarantine_window_ticks=self._genome.structure.tentative_lifetime_ticks,
                    tentative_lifetime_ticks=self._genome.structure.tentative_lifetime_ticks,
                )
                is EdgeLifecycleState.REMOVED
            )
            prune_mutations = prune_candidates[:remaining_after_gc]
            remaining = remaining_after_gc - len(prune_mutations)
            after_prune = apply_mutations(
                after_retirement_edge_gc,
                prune_mutations,
                self._kernel_limits,
                frozen=frozen,
            )
            if prune_mutations and after_prune is after_retirement_edge_gc:
                prune_mutations = ()
                remaining = remaining_after_gc
                after_prune = after_retirement_edge_gc

            protected_action_readouts = {
                *(
                    self._motor_readout_id(str(actuator_id))
                    for actuator_id in active_motor_actuator_ids
                    if str(actuator_id)
                ),
                *(
                    self._primitive_readout_id(str(primitive_id))
                    for primitive_id in active_primitive_ids
                    if str(primitive_id)
                ),
            }
            orphan_mutations = self._orphan_node_mutations(
                tick=tick,
                max_mutations=remaining,
                graph=after_prune,
                protected_node_ids=protected_action_readouts,
            )
            remaining -= len(orphan_mutations)
            after_orphans = apply_mutations(after_prune, orphan_mutations, self._kernel_limits, frozen=frozen)
            if orphan_mutations and after_orphans is after_prune:
                orphan_mutations = ()
                remaining = (
                    mutation_cap
                    - len(retirement_gc)
                    - len(retirement_edge_gc)
                    - len(prune_mutations)
                )
                after_orphans = after_prune

            sense_evictions = self._sense_eviction_mutations(
                tick=tick,
                max_mutations=remaining,
                graph=after_orphans,
            )
            remaining -= len(sense_evictions)
            planning_graph = apply_mutations(after_orphans, sense_evictions, self._kernel_limits, frozen=frozen)
            if sense_evictions and planning_graph is after_orphans:
                sense_evictions = ()
                remaining = (
                    mutation_cap
                    - len(retirement_gc)
                    - len(retirement_edge_gc)
                    - len(prune_mutations)
                    - len(orphan_mutations)
                )
                planning_graph = after_orphans

            maintenance_mutations = (
                retirement_gc
                + retirement_edge_gc
                + prune_mutations
                + orphan_mutations
                + sense_evictions
            )

            # Register and locally validate producer proposals before freezing
            # the global scheduling round. The scheduler itself remains opaque
            # to producer semantics.
            self._register_germinal_concept_candidate(tick=tick, graph=self._graph)
            self._prune_invalid_structural_proposals(
                graph=planning_graph,
                active_motor_ids=active_motor_actuator_ids,
                active_primitive_ids=active_primitive_ids,
            )

            frozen_candidate_ids = tuple(sorted(self._contention.candidates))
            self._contention.consolidation_generation += 1

            self._update_unrouted_tracking(tick, graph=planning_graph)
            repair_mutations, event = self._propose_concept_recycling_mutations(
                tick=tick,
                mutation_slots=remaining,
                graph=planning_graph,
            )
            if repair_mutations:
                repaired_graph = apply_mutations(
                    planning_graph,
                    repair_mutations,
                    self._kernel_limits,
                    frozen=frozen,
                )
                if repaired_graph is planning_graph:
                    repair_mutations = ()
                else:
                    recycling_events = (event,) if event is not None else ()
                    remaining -= len(repair_mutations)
                    planning_graph = repaired_graph

            pending_node_demand = any(
                candidate.required_nodes > 0
                for candidate in self._contention.candidates.values()
            )
            pending_edge_demand = any(
                candidate.required_edges > 0
                for candidate in self._contention.candidates.values()
            ) or bool(self._predictors.shadows)
            self._expand_resource_budgets(
                need_nodes=(
                    pending_node_demand
                    and len(planning_graph.nodes) >= self._soft_node_limit
                ),
                need_edges=(
                    pending_edge_demand
                    and len(planning_graph.edges) >= self._soft_edge_limit
                ),
            )
            edge_slots = max(0, self._soft_edge_limit - len(planning_graph.edges))
            node_slots = max(0, self._soft_node_limit - len(planning_graph.nodes))

            # Contention sees exactly the candidates frozen at round start.
            # Candidates registered later wait for the next consolidation.
            original_registry = self._contention.candidates
            self._contention.candidates = {
                candidate_id: original_registry[candidate_id]
                for candidate_id in frozen_candidate_ids
                if candidate_id in original_registry
            }
            (
                contention_winner_id,
                admission_mutations,
                contention_loser_ids,
            ) = self._contention.select(
                graph=planning_graph,
                mutation_slots=remaining,
                node_slots=node_slots,
                edge_slots=edge_slots,
                frozen=frozen,
            )
            frozen_registry_after = self._contention.candidates
            self._contention.candidates = {
                **{
                    candidate_id: candidate
                    for candidate_id, candidate in original_registry.items()
                    if candidate_id not in frozen_candidate_ids
                },
                **frozen_registry_after,
            }

            remaining -= len(admission_mutations)
            planning_after_admission = apply_mutations(
                planning_graph,
                admission_mutations,
                self._kernel_limits,
                frozen=frozen,
            )
            edge_slots = max(
                0,
                self._soft_edge_limit - len(planning_after_admission.edges),
            )
            proposed = self._structural_plasticity.propose(
                planning_after_admission,
                kernel_limits=self._kernel_limits,
                tick=tick,
                max_mutations=min(remaining, edge_slots),
            )
            proposed = tuple(
                mutation
                for mutation in proposed
                if not (
                    mutation.kind == "add_edge"
                    and (
                        str(mutation.payload.get("source_id", ""))
                        in self._predictors.retirement
                        or str(mutation.payload.get("target_id", ""))
                        in self._predictors.retirement
                    )
                )
            )

            # The complete maintenance+growth transaction is committed against
            # the original graph. Any invalid step rolls the whole batch back.
            all_mutations = (
                maintenance_mutations
                + repair_mutations
                + admission_mutations
                + proposed
            )
            if all_mutations:
                candidate = apply_mutations(self._graph, all_mutations, self._kernel_limits, frozen=frozen)
                if candidate is not self._graph:
                    self._graph = candidate
                    self._record_applied_metadata(all_mutations, tick=tick)
                    self._plasticity.seed_new_edges(self._graph)
                    self._reconcile_node_metadata()
                    structural_mutations_applied = len(all_mutations)
                    applied_mutations = all_mutations
                    self._topology_revision += 1
                    self._contention.commit(
                        winner_id=contention_winner_id,
                        loser_ids=contention_loser_ids,
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
