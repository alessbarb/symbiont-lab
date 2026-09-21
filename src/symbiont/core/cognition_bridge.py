from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Collection, Mapping

from ..cognition.activation import SensoryNormalizer
from ..cognition.checkpoint import (
    WEIGHT_CLASSES,
    export_graph_checkpoint,
    export_safety_state,
    export_sensory_normalizers,
    quantize_weight,
    restore_graph_checkpoint,
    restore_safety_state,
    restore_sensory_normalizers,
)
from ..cognition.genome import Genome
from ..cognition.graph import CognitiveGraph, GraphError, PlasticNode, TickContext
from ..cognition.learning import (
    PredictionError,
    ShadowPrediction,
    apply_oja_update,
    compute_prediction_errors,
    huber_loss,
    update_eligibility,
)
from ..cognition.limits import KernelLimits
from ..cognition.metaplasticity import SafetyState
from ..cognition.structure import (
    EdgeLifecycleState,
    Mutation,
    StructuralPlasticity,
    advance_edge_age,
    apply_mutations,
    evaluate_edge_lifecycle,
)
from ..cognition.types import WEIGHT_RANGE, EdgeKind, NodeKind
from .weight_stability import EdgeKey, WeightStabilityTracker

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


@dataclass(slots=True, frozen=True)
class ConceptLineage:
    concept_id: str
    parent_ids: tuple[str, ...]
    born_tick: int


@dataclass(slots=True)
class _PredictorUtility:
    """Bounded evidence that a materialized predictor beats persistence."""

    samples: int = 0
    model_loss: float = 0.0
    persistence_loss: float = 0.0

    def observe(self, *, model_loss: float, persistence_loss: float) -> None:
        if not math.isfinite(model_loss) or not math.isfinite(persistence_loss):
            return
        self.samples += 1
        self.model_loss += max(0.0, float(model_loss))
        self.persistence_loss += max(0.0, float(persistence_loss))

    @property
    def predictive_gain(self) -> float:
        if self.samples <= 0:
            return 0.0
        return (self.persistence_loss - self.model_loss) / self.samples

    def checkpoint(self, predictor_id: str) -> dict[str, object]:
        return {
            "predictor_id": predictor_id,
            "samples": self.samples,
            "model_loss": self.model_loss,
            "persistence_loss": self.persistence_loss,
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
    ) -> None:
        self._graph = graph
        self._genome = genome
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
        self._concept_lineage: dict[str, ConceptLineage] = {}
        self._sense_last_seen_tick: dict[str, int] = {}
        self._orphan_since_tick: dict[str, int] = {}
        self._unrouted_since_tick: dict[str, int] = {}
        self._concept_last_active_tick: dict[str, int] = {}
        self._tick = 0
        self._shadow_predictions: dict[tuple[str, str], ShadowPrediction] = {}
        self._shadow_preliminary_support: dict[tuple[str, str], int] = {}
        self._predictor_utility: dict[str, _PredictorUtility] = {}
        self._next_concept_index: int = 1
        self._topology_revision = 0
        self._develop_senses = (not graph.nodes) if develop_senses is None else bool(develop_senses)
        self._recovery_pending = False
        self._weight_tracker = WeightStabilityTracker(kernel_limits=kernel_limits)
        self._tracked_edge_keys: set[tuple[str, str, str]] = set()
        self._seed_new_edges()
        self._reacclimation_remaining = 0

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
        return self._classify_topology_health()

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

    def _predictor_reclamation_mutations(
        self,
        *,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
        protected_node_ids: Collection[str] = (),
    ) -> tuple[Mutation, ...]:
        """Reclaim one demonstrably non-useful predictor under node pressure.

        A predictor is eligible only after enough observations show that it
        does not beat persistence, and only when it has no established
        downstream dependency. This is a generic retention rule: the caller
        requesting capacity receives no special priority merely because it is
        motor-related.
        """
        if max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        protected = set(protected_node_ids)
        minimum_samples = max(8, self._genome.structure.minimum_support)
        minimum_support = self._genome.structure.minimum_support
        prune_threshold = self._genome.structure.prune_threshold

        candidates: list[tuple[float, int, int, str, tuple[Mutation, ...]]] = []
        for node in active_graph.nodes:
            if node.kind is not NodeKind.PREDICTOR:
                continue
            if node.node_id in protected:
                continue
            utility = self._predictor_utility.get(node.node_id)
            if utility is None or utility.samples < minimum_samples:
                continue
            if utility.predictive_gain > 0.0:
                continue

            outgoing = [
                edge for edge in active_graph.edges
                if edge.source_id == node.node_id
            ]
            if any(
                edge.support >= minimum_support
                and abs(edge.weight) > prune_threshold
                for edge in outgoing
            ):
                continue

            incident = [
                edge for edge in active_graph.edges
                if edge.source_id == node.node_id or edge.target_id == node.node_id
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
                Mutation(kind="remove_node", payload={"node_id": node.node_id}),
            )
            if len(mutations) > max_mutations:
                continue

            last_use = max((edge.last_use_tick for edge in incident), default=0)
            total_support = sum(edge.support for edge in incident)
            candidates.append(
                (
                    utility.predictive_gain,
                    total_support,
                    last_use,
                    node.node_id,
                    mutations,
                )
            )

        if not candidates:
            return ()
        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        return candidates[0][4]

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
        """Find one safely expendable representation under fixed capacity."""
        active_graph = self._graph if graph is None else graph
        predictor = self._predictor_reclamation_mutations(
            max_mutations=max_mutations,
            graph=active_graph,
            protected_node_ids=protected_node_ids,
        )
        if predictor:
            return predictor
        return self._stale_concept_reclamation_mutations(
            max_mutations=max_mutations,
            graph=active_graph,
            protected_node_ids=protected_node_ids,
        )

    def _sync_motor_readouts(self, actuator_ids: Collection[str]) -> None:
        requested = sorted({str(value) for value in actuator_ids if str(value)})
        existing = {node.node_id for node in self._graph.nodes}
        missing = [
            self._motor_readout_id(actuator_id)
            for actuator_id in requested
            if self._motor_readout_id(actuator_id) not in existing
        ]
        if not missing:
            return

        mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation
        mutations: list[Mutation] = []
        planning_graph = self._graph
        for node_id in missing:
            if len(mutations) >= mutation_cap:
                break
            if len(planning_graph.nodes) >= self._soft_node_limit:
                reclaim = self._capacity_reclamation_mutations(
                    max_mutations=mutation_cap - len(mutations) - 1,
                    graph=planning_graph,
                )
                if not reclaim:
                    break
                candidate = apply_mutations(
                    planning_graph,
                    reclaim,
                    self._kernel_limits,
                    frozen=self._safety_state.frozen,
                )
                if candidate is planning_graph:
                    break
                mutations.extend(reclaim)
                planning_graph = candidate

            add = (
                Mutation(
                    kind="add_node",
                    payload={"node_id": node_id, "kind": NodeKind.READOUT},
                ),
            )
            candidate = apply_mutations(
                planning_graph,
                add,
                self._kernel_limits,
                frozen=self._safety_state.frozen,
            )
            if candidate is planning_graph:
                break
            mutations.extend(add)
            planning_graph = candidate

        if not mutations:
            return
        mutation_tuple = tuple(mutations)
        candidate = apply_mutations(
            self._graph,
            mutation_tuple,
            self._kernel_limits,
            frozen=self._safety_state.frozen,
        )
        if candidate is self._graph:
            return
        self._graph = candidate
        self._record_applied_metadata(mutation_tuple, tick=self._tick)
        self._seed_new_edges()
        self._reconcile_node_metadata()
        self._topology_revision += 1

    def _sync_primitive_readouts(self, primitive_ids: Collection[str]) -> None:
        requested_ids = sorted({str(value) for value in primitive_ids if str(value)})
        requested_nodes = {
            self._primitive_readout_id(primitive_id)
            for primitive_id in requested_ids
        }
        existing_nodes = {node.node_id for node in self._graph.nodes}
        existing_primitive_nodes = {
            node_id
            for node_id in existing_nodes
            if node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        }

        mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation
        mutations: list[Mutation] = []
        planning_graph = self._graph

        # Retracted learned actions release their readout and any associations.
        stale = sorted(existing_primitive_nodes - requested_nodes)
        for node_id in stale:
            incident = [
                edge for edge in planning_graph.edges
                if edge.source_id == node_id or edge.target_id == node_id
            ]
            needed = len(incident) + 1
            if len(mutations) + needed > mutation_cap:
                break
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
            ) + (
                Mutation(kind="remove_node", payload={"node_id": node_id}),
            )
            candidate = apply_mutations(
                planning_graph,
                stale_mutations,
                self._kernel_limits,
                frozen=self._safety_state.frozen,
            )
            if candidate is planning_graph:
                continue
            mutations.extend(stale_mutations)
            planning_graph = candidate

        missing = sorted(
            requested_nodes - {node.node_id for node in planning_graph.nodes}
        )
        for node_id in missing:
            if len(mutations) >= mutation_cap:
                break
            if len(planning_graph.nodes) >= self._soft_node_limit:
                # Reserve one mutation for the readout itself. Capacity is
                # reclaimed only from representations that already satisfy
                # generic expendability gates.
                reclaim = self._capacity_reclamation_mutations(
                    max_mutations=mutation_cap - len(mutations) - 1,
                    graph=planning_graph,
                )
                if not reclaim:
                    break
                candidate = apply_mutations(
                    planning_graph,
                    reclaim,
                    self._kernel_limits,
                    frozen=self._safety_state.frozen,
                )
                if candidate is planning_graph:
                    break
                mutations.extend(reclaim)
                planning_graph = candidate

            if len(planning_graph.nodes) >= self._soft_node_limit:
                break
            add = (
                Mutation(
                    kind="add_node",
                    payload={"node_id": node_id, "kind": NodeKind.READOUT},
                ),
            )
            candidate = apply_mutations(
                planning_graph,
                add,
                self._kernel_limits,
                frozen=self._safety_state.frozen,
            )
            if candidate is planning_graph:
                break
            mutations.extend(add)
            planning_graph = candidate

        if not mutations:
            return
        mutation_tuple = tuple(mutations)
        candidate = apply_mutations(
            self._graph,
            mutation_tuple,
            self._kernel_limits,
            frozen=self._safety_state.frozen,
        )
        if candidate is self._graph:
            return
        self._graph = candidate
        self._record_applied_metadata(mutation_tuple, tick=self._tick)
        self._seed_new_edges()
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
        node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
        readout_id = self._primitive_readout_id(str(primitive_id))
        if node_kinds.get(readout_id) is not NodeKind.READOUT:
            return False
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
        return True

    @property
    def _soft_node_limit(self) -> int:
        return min(self._genome.development.soft_node_budget, self._kernel_limits.max_nodes)

    @property
    def _sense_node_limit(self) -> int:
        return min(self._genome.development.sense_node_budget, self._soft_node_limit)

    @property
    def _soft_edge_limit(self) -> int:
        return min(self._genome.development.soft_edge_budget, self._kernel_limits.max_edges)

    def _seed_new_edges(self) -> None:
        current_keys = {(edge.source_id, edge.target_id, edge.kind.value) for edge in self._graph.edges}
        self._weight_tracker.reconcile(current_keys)
        for edge in self._graph.edges:
            key = (edge.source_id, edge.target_id, edge.kind.value)
            if key in self._tracked_edge_keys:
                continue
            self._weight_tracker.seed(key, quantize_weight(edge.weight))
        self._tracked_edge_keys = current_keys

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
                self._concept_support.pop((source_id, target_id), None)

    @property
    def shadow_predictions(self) -> tuple[ShadowPrediction, ...]:
        return tuple(sorted(self._shadow_predictions.values(), key=lambda item: (item.source_id, item.target_id)))

    @property
    def _live_shadow_limit(self) -> int:
        return min(
            _MAX_SHADOW_PREDICTIONS,
            max(32, self._kernel_limits.max_nodes * _MAX_LIVE_SHADOW_FACTOR),
        )

    @property
    def _preliminary_shadow_limit(self) -> int:
        return min(
            _MAX_SHADOW_PREDICTIONS,
            max(64, self._kernel_limits.max_nodes * _MAX_PRELIMINARY_SHADOW_FACTOR),
        )

    def _prune_preliminary_shadow_support(self) -> None:
        node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
        live_ids = set(node_kinds)
        self._shadow_preliminary_support = {
            key: support
            for key, support in self._shadow_preliminary_support.items()
            if node_kinds.get(key[0]) is NodeKind.SENSE and key[1] in live_ids
        }
        if len(self._shadow_preliminary_support) <= self._preliminary_shadow_limit:
            return
        retained = sorted(
            self._shadow_preliminary_support.items(),
            key=lambda item: (-item[1], item[0]),
        )[: self._preliminary_shadow_limit]
        self._shadow_preliminary_support = dict(retained)

    def _prune_shadow_predictions(self) -> None:
        """Retain only live, materializable bounded predictive hypotheses."""
        node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
        live_ids = set(node_kinds)
        self._shadow_predictions = {
            key: candidate
            for key, candidate in self._shadow_predictions.items()
            if (
                candidate.status != "retired"
                and node_kinds.get(candidate.source_id) is NodeKind.SENSE
                and candidate.target_id in live_ids
            )
        }
        if len(self._shadow_predictions) <= self._live_shadow_limit:
            return
        ranked = sorted(
            self._shadow_predictions.items(),
            key=lambda item: (
                item[1].status != "supported",
                -item[1].predictive_gain,
                -item[1].samples,
                item[0],
            ),
        )
        self._shadow_predictions = dict(ranked[: self._live_shadow_limit])

    def promote_shadow_prediction(self, source_id: str, target_id: str, *, tick: int) -> bool:
        """Materialize one validated lag-1 shadow relation as learned structure.

        ShadowPrediction evaluates source(t-1) against target(t). For a SENSE
        source, a zero-delay source->PREDICTOR edge makes predictor(t-1)
        represent that same source(t-1), which is exactly what
        compute_prediction_errors() compares with target(t). Latent sources
        cannot be materialized with the same timing under the current graph
        contract without adding an extra tick of delay, so they remain shadow
        evidence rather than being wired incorrectly.
        """
        candidate = self._shadow_predictions.get((source_id, target_id))
        if candidate is None or not candidate.promotable or not self._develop_senses:
            return False
        node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
        if node_kinds.get(source_id) is not NodeKind.SENSE:
            return False
        if target_id not in node_kinds:
            return False
        if any(
            node.kind is NodeKind.PREDICTOR and node.predicts_node_id == target_id
            for node in self._graph.nodes
        ):
            return False
        mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation
        planning_graph = self._graph
        reclaim: tuple[Mutation, ...] = ()
        if len(planning_graph.nodes) >= self._soft_node_limit:
            reclaim = self._capacity_reclamation_mutations(
                max_mutations=max(0, mutation_cap - 2),
                graph=planning_graph,
                protected_node_ids=(source_id, target_id),
            )
            if not reclaim:
                return False
            candidate = apply_mutations(
                planning_graph,
                reclaim,
                self._kernel_limits,
                frozen=False,
            )
            if candidate is planning_graph:
                return False
            planning_graph = candidate

        if (
            len(planning_graph.nodes) >= self._soft_node_limit
            or len(planning_graph.nodes) >= self._kernel_limits.max_nodes
            or len(planning_graph.edges) >= self._kernel_limits.max_edges
            or len(reclaim) + 2 > mutation_cap
        ):
            return False

        predictor_id = self._new_node_id("predictor", graph=planning_graph)
        mutations = reclaim + (
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
        )
        updated = apply_mutations(
            self._graph,
            mutations,
            self._kernel_limits,
            frozen=False,
        )
        if updated is self._graph:
            return False
        self._graph = updated
        self._record_applied_metadata(mutations, tick=tick)
        self._seed_new_edges()
        self._reconcile_node_metadata()
        self._topology_revision += 1
        return True

    @property
    def stranded_concepts(self) -> tuple[str, ...]:
        """Concepts receiving activation but lacking a path to a readout."""
        unrouted = set(self._unrouted_since_tick)
        return tuple(sorted(node_id for node_id in unrouted if node_id in self._concept_last_active_tick))

    def _record_concept_support(self, activations: Mapping[str, float]) -> None:
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        kinds = {node.node_id: node.kind for node in self._graph.nodes}
        for node_id, value in activations.items():
            if kinds.get(node_id) is NodeKind.CONCEPT and abs(value) >= _ACTIVITY_THRESHOLD:
                self._concept_last_active_tick[node_id] = self._tick
        threshold = max(_ACTIVITY_THRESHOLD, self._genome.structure.grow_threshold)
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
                    continue
                self._concept_support[key] = self._concept_support.get(key, 0) + 1

    def _concept_signature_exists(
        self, source_ids: tuple[str, str], *, graph: CognitiveGraph | None = None
    ) -> bool:
        pair = set(source_ids)
        if any(pair.issubset(set(lineage.parent_ids)) for lineage in self._concept_lineage.values()):
            return True
        active_graph = self._graph if graph is None else graph
        concept_ids = {node.node_id for node in active_graph.nodes if node.kind is NodeKind.CONCEPT}
        incoming: dict[str, set[str]] = {concept_id: set() for concept_id in concept_ids}
        for edge in active_graph.edges:
            if edge.target_id in incoming:
                incoming[edge.target_id].add(edge.source_id)
        return any(pair.issubset(sources) for sources in incoming.values())

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

    def _propose_germinal_concept_mutations(
        self,
        *,
        mutation_slots: int,
        node_slots: int,
        edge_slots: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        active_graph = self._graph if graph is None else graph
        if not self._develop_senses or mutation_slots < 2 or node_slots < 1 or edge_slots < 3:
            return ()
        concept_count = sum(1 for node in active_graph.nodes if node.kind is NodeKind.CONCEPT)
        if concept_count >= self._kernel_limits.max_concepts:
            return ()

        eligible = sorted(
            (
                (support, pair)
                for pair, support in self._concept_support.items()
                if support >= self._genome.structure.minimum_support
                and not self._concept_signature_exists(pair, graph=active_graph)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not eligible:
            return ()

        _, source_ids = eligible[0]
        node_kinds = {node.node_id: node.kind for node in active_graph.nodes}
        if any(node_kinds.get(source_id) is not NodeKind.SENSE for source_id in source_ids):
            return ()

        core_readouts = sorted(
            node.node_id
            for node in active_graph.nodes
            if node.kind is NodeKind.READOUT and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
            and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        )
        if _CORE_READOUT_ID in core_readouts:
            core_readouts = [_CORE_READOUT_ID]
        needs_readout = not core_readouts
        required_mutations = 3 if needs_readout else 2
        required_nodes = 2 if needs_readout else 1
        if mutation_slots < required_mutations or node_slots < required_nodes:
            return ()

        concept_id = self._new_node_id("concept", graph=active_graph)
        mutations: list[Mutation] = [
            Mutation(
                kind="add_node",
                payload={"node_id": concept_id, "kind": NodeKind.CONCEPT, "source_ids": source_ids},
            )
        ]
        if needs_readout:
            existing_ids = {node.node_id for node in active_graph.nodes}
            readout_id = (
                _CORE_READOUT_ID
                if _CORE_READOUT_ID not in existing_ids
                else self._new_node_id("readout", graph=active_graph)
            )
            mutations.append(Mutation(kind="add_node", payload={"node_id": readout_id, "kind": NodeKind.READOUT}))
        else:
            readout_id = core_readouts[0]
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
        return tuple(mutations)

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
        active_graph = self._graph if graph is None else graph
        if not self._develop_senses or mutation_slots < 4:
            return (), None

        concept_count = sum(1 for node in active_graph.nodes if node.kind is NodeKind.CONCEPT)
        node_budget_full = len(active_graph.nodes) >= self._soft_node_limit
        concept_budget_full = concept_count >= self._kernel_limits.max_concepts
        if not (node_budget_full or concept_budget_full):
            return (), None

        eligible = sorted(
            (
                (support, pair)
                for pair, support in self._concept_support.items()
                if support >= self._genome.structure.minimum_support
                and not self._concept_signature_exists(pair, graph=active_graph)
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not eligible:
            return (), None

        _, source_ids = eligible[0]
        node_kinds = {node.node_id: node.kind for node in active_graph.nodes}
        if any(node_kinds.get(source_id) is not NodeKind.SENSE for source_id in source_ids):
            return (), None

        core_readouts = sorted(
            node.node_id
            for node in active_graph.nodes
            if node.kind is NodeKind.READOUT and not node.node_id.startswith(_MOTOR_READOUT_PREFIX)
            and not node.node_id.startswith(_PRIMITIVE_READOUT_PREFIX)
        )
        if _CORE_READOUT_ID in core_readouts:
            core_readouts = [_CORE_READOUT_ID]
        if not core_readouts:
            return (), None
        readout_id = core_readouts[0]

        unrouted_ids = self._update_unrouted_tracking(tick, graph=active_graph)
        if not unrouted_ids:
            return (), None

        # A well-fed but unrouted concept gets one repair opportunity before
        # any recycling decision. This is deliberately bounded to one edge.
        stranded = [node_id for node_id in sorted(unrouted_ids) if node_id in self._concept_last_active_tick]
        if stranded and core_readouts and mutation_slots >= 1:
            concept_id, readout_id = stranded[0], core_readouts[0]
            if not any(edge.source_id == concept_id and edge.target_id == readout_id for edge in active_graph.edges):
                mutation = Mutation(kind="add_edge", payload={"source_id": concept_id, "target_id": readout_id,
                    "kind": EdgeKind.EXCITATORY, "weight": _TENTATIVE_WEIGHT, "plasticity": 0.25, "delay_ticks": 1})
                candidate = apply_mutations(active_graph, (mutation,), self._kernel_limits, frozen=False)
                if candidate is not active_graph:
                    return (mutation,), {"tick": tick, "concept_id": concept_id, "reason": "stranded_route_repair"}

        grace = max(1, self._genome.structure.tentative_lifetime_ticks)
        expendable: list[tuple[int, int, str]] = []
        for node_id in sorted(unrouted_ids):
            lineage = self._concept_lineage.get(node_id)
            born_tick = lineage.born_tick if lineage is not None else 0
            if tick - born_tick < grace:
                continue
            unrouted_since = self._unrouted_since_tick.get(node_id, tick)
            unrouted_ticks = tick - unrouted_since
            if unrouted_ticks < grace:
                continue
            expendable.append((-unrouted_ticks, born_tick, node_id))

        if not expendable:
            return (), None

        expendable.sort()
        _, born_tick, retire_concept_id = expendable[0]
        unrouted_ticks = tick - self._unrouted_since_tick.get(retire_concept_id, tick)

        incident_edges = [
            edge
            for edge in active_graph.edges
            if edge.source_id == retire_concept_id or edge.target_id == retire_concept_id
        ]
        needed_mutations = len(incident_edges) + 3
        if (
            mutation_slots < needed_mutations
            or needed_mutations > self._kernel_limits.max_structural_mutations_per_consolidation
        ):
            return (), None

        mutations: list[Mutation] = [
            Mutation(
                kind="remove_edge",
                payload={
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "kind": edge.kind.value,
                },
            )
            for edge in incident_edges
        ]
        mutations.append(Mutation(kind="remove_node", payload={"node_id": retire_concept_id}))

        new_concept_id = self._new_node_id("concept", graph=active_graph)
        mutations.append(
            Mutation(
                kind="add_node",
                payload={"node_id": new_concept_id, "kind": NodeKind.CONCEPT, "source_ids": source_ids},
            )
        )
        mutations.append(
            Mutation(
                kind="add_edge",
                payload={
                    "source_id": new_concept_id,
                    "target_id": readout_id,
                    "kind": EdgeKind.EXCITATORY,
                    "weight": _TENTATIVE_WEIGHT,
                    "plasticity": 0.5,
                    "delay_ticks": 1,
                },
            )
        )

        candidate = apply_mutations(active_graph, tuple(mutations), self._kernel_limits, frozen=False)
        if candidate is active_graph:
            return (), None

        event = {
            "tick": tick,
            "retired_concept_id": retire_concept_id,
            "unrouted_ticks": unrouted_ticks,
            "born_tick": born_tick,
            "new_concept_id": new_concept_id,
            "candidate_sources": list(source_ids),
            "reason": "unrouted_under_budget_pressure",
        }
        return tuple(mutations), event

    def _orphan_latent_ids(self, graph: CognitiveGraph | None = None) -> set[str]:
        active_graph = self._graph if graph is None else graph
        incident = {node.node_id: 0 for node in active_graph.nodes}
        for edge in active_graph.edges:
            incident[edge.source_id] = incident.get(edge.source_id, 0) + 1
            incident[edge.target_id] = incident.get(edge.target_id, 0) + 1
        return {
            node.node_id
            for node in active_graph.nodes
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT) and incident.get(node.node_id, 0) == 0
        }

    def _orphan_node_mutations(
        self,
        *,
        tick: int,
        max_mutations: int,
        graph: CognitiveGraph | None = None,
    ) -> tuple[Mutation, ...]:
        if not self._develop_senses or max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        orphan_ids = self._orphan_latent_ids(active_graph)
        for node in active_graph.nodes:
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT) and node.node_id not in orphan_ids:
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
                if kind is NodeKind.CONCEPT:
                    raw_sources = mutation.payload.get("source_ids", ())
                    if isinstance(raw_sources, (list, tuple, set)):
                        parent_ids = tuple(sorted(str(value) for value in raw_sources))
                        if parent_ids:
                            self._concept_lineage[node_id] = ConceptLineage(node_id, parent_ids, tick)
                            self._consume_concept_support(parent_ids)
            elif mutation.kind == "remove_node":
                node_id = str(mutation.payload.get("node_id", ""))
                self._concept_lineage.pop(node_id, None)
                self._sense_last_seen_tick.pop(node_id, None)
                self._orphan_since_tick.pop(node_id, None)
                self._unrouted_since_tick.pop(node_id, None)
                self._normalizers.pop(node_id, None)
                self._predictor_utility.pop(node_id, None)
                dead_prediction_keys = [k for k in self._shadow_predictions if k[0] == node_id or k[1] == node_id]
                for k in dead_prediction_keys:
                    del self._shadow_predictions[k]

    def _reconcile_node_metadata(self) -> None:
        node_ids = {node.node_id for node in self._graph.nodes}
        sense_ids = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.SENSE}
        concept_ids = {node.node_id for node in self._graph.nodes if node.kind is NodeKind.CONCEPT}
        latent_ids = {
            node.node_id
            for node in self._graph.nodes
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT)
        }
        self._sense_last_seen_tick = {key: value for key, value in self._sense_last_seen_tick.items() if key in sense_ids}
        self._concept_lineage = {key: value for key, value in self._concept_lineage.items() if key in concept_ids}
        self._orphan_since_tick = {key: value for key, value in self._orphan_since_tick.items() if key in latent_ids}
        self._unrouted_since_tick = {key: value for key, value in self._unrouted_since_tick.items() if key in concept_ids}
        self._normalizers = {key: value for key, value in self._normalizers.items() if key in sense_ids}
        self._concept_support = {
            pair: count
            for pair, count in self._concept_support.items()
            if pair[0] in sense_ids and pair[1] in sense_ids
        }
        self._structural_plasticity.reconcile(node_ids)
        self._shadow_predictions = {
            key: value
            for key, value in self._shadow_predictions.items()
            if key[0] in node_ids and key[1] in node_ids
        }
        predictor_ids = {
            node.node_id for node in self._graph.nodes
            if node.kind is NodeKind.PREDICTOR
        }
        self._predictor_utility = {
            key: value
            for key, value in self._predictor_utility.items()
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
                in sorted(self._predictor_utility.items())
            ],
        }

    def _weight_class_overrides(self) -> dict[tuple[str, str, str], int]:
        return {
            (edge.source_id, edge.target_id, edge.kind.value): self._weight_tracker.durable_class(
                (edge.source_id, edge.target_id, edge.kind.value)
            )
            for edge in self._graph.edges
        }

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
    ) -> dict[str, _PredictorUtility]:
        if payload is None:
            return {}
        allowed = set(allowed_predictor_ids)
        if not isinstance(payload, list) or len(payload) > len(allowed):
            raise GraphError("predictor_utility must be a bounded list")
        restored: dict[str, _PredictorUtility] = {}
        for entry in payload:
            if not isinstance(entry, Mapping):
                raise GraphError("predictor_utility entries must be objects")
            predictor_id = entry.get("predictor_id")
            samples = entry.get("samples", 0)
            model_loss = entry.get("model_loss", 0.0)
            persistence_loss = entry.get("persistence_loss", 0.0)
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
            restored[predictor_id] = _PredictorUtility(
                samples=samples,
                model_loss=float(model_loss),
                persistence_loss=float(persistence_loss),
            )
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
            if node.kind in (NodeKind.CONCEPT, NodeKind.READOUT)
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
        predictor_ids = {
            node.node_id for node in graph.nodes
            if node.kind is NodeKind.PREDICTOR
        }
        bridge._predictor_utility = cls._restore_predictor_utility(
            payload.get("predictor_utility"),
            allowed_predictor_ids=predictor_ids,
        )
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
        for node in self._graph.nodes:
            if node.kind is not NodeKind.SENSE:
                continue
            raw = sense_values.get(node.node_id)
            if raw is None:
                continue
            normalizer = self._normalizers.setdefault(node.node_id, SensoryNormalizer())
            sense_inputs[node.node_id] = normalizer.normalize(raw)

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
        for error in prediction_errors:
            target_previous = self._previous_frame.get(error.target_id)
            target_current = frame.activations.get(error.target_id)
            if target_previous is None or target_current is None:
                continue
            utility = self._predictor_utility.setdefault(
                error.predictor_id,
                _PredictorUtility(),
            )
            utility.observe(
                model_loss=error.loss,
                persistence_loss=huber_loss(target_current - target_previous),
            )

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
                eligible = (
                    edge.source_id in learning_nodes
                    and edge.target_id in learning_nodes
                    and abs(edge.eligibility) >= _ELIGIBILITY_THRESHOLD
                )
                apply_oja_update(
                    edge,
                    source_activation=source_value,
                    target_activation=target_current,
                    learning_rate=self._genome.plasticity.learning_rate.initial,
                    modulation=tick_modulation * edge.plasticity,
                    eligible=eligible,
                    frozen=frozen,
                )
                transmitted = edge.weight * source_value
                advance_edge_age(edge, tick=tick, used=abs(transmitted) >= _EDGE_USAGE_THRESHOLD)

            edges_by_target: dict[str, list] = {}
            for edge in self._graph.edges:
                key = (edge.source_id, edge.target_id, edge.kind.value)
                self._weight_tracker.observe(key, quantize_weight(edge.weight), tick=tick)
                edges_by_target.setdefault(edge.target_id, []).append(edge)
            for target_edges in edges_by_target.values():
                keys: list[EdgeKey] = [(edge.source_id, edge.target_id, edge.kind.value) for edge in target_edges]
                live_weights: dict[EdgeKey, float] = {key: float(edge.weight) for key, edge in zip(keys, target_edges)}
                self._weight_tracker.consolidate_node(
                    keys, live_weights, max_incoming_norm=self._kernel_limits.max_incoming_consolidated_weight_norm
                )

            node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
            active_nodes = [node_id for node_id, value in frame.activations.items() if abs(value) >= _ACTIVITY_THRESHOLD]
            for index, source_id in enumerate(active_nodes):
                for target_id in active_nodes[index + 1 :]:
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
                for source_id in active_nodes:
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
                node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
                preliminary_min = max(2, self._genome.structure.minimum_support)
                for source_id, source_value in self._previous_frame.items():
                    if node_kinds.get(source_id) is not NodeKind.SENSE:
                        continue
                    for target_id, target_value in frame.activations.items():
                        if source_id == target_id or target_id not in self._previous_frame:
                            continue
                        target_previous = self._previous_frame[target_id]
                        key = (source_id, target_id)
                        predictor = self._shadow_predictions.get(key)
                        if predictor is not None:
                            # Once admitted, evaluate the hypothesis on every
                            # compatible tick. Preliminary selection must not
                            # censor boring/negative evidence.
                            predictor.observe(
                                source_value,
                                target_value,
                                target_previous,
                            )
                            continue

                        if abs(source_value) < _ACTIVITY_THRESHOLD:
                            continue
                        if abs(target_value - target_previous) < _EDGE_USAGE_THRESHOLD:
                            continue
                        support = self._shadow_preliminary_support.get(key, 0) + 1
                        self._shadow_preliminary_support[key] = support
                        if support < preliminary_min:
                            continue
                        if len(self._shadow_predictions) >= self._live_shadow_limit:
                            self._prune_shadow_predictions()
                        if len(self._shadow_predictions) >= self._live_shadow_limit:
                            continue
                        predictor = ShadowPrediction(source_id, target_id)
                        self._shadow_predictions[key] = predictor
                        self._shadow_preliminary_support.pop(key, None)
                        predictor.observe(source_value, target_value, target_previous)
                self._prune_preliminary_shadow_support()
                self._prune_shadow_predictions()

        structural_mutations_applied = 0
        applied_mutations: tuple[Mutation, ...] = ()
        recycling_events: tuple[dict[str, object], ...] = ()
        interval = max(1, self._genome.development.consolidation_interval_ticks)
        if not frozen and self._reacclimation_remaining <= 0 and tick % interval == 0:
            mutation_cap = self._kernel_limits.max_structural_mutations_per_consolidation

            # Maintenance is planned sequentially but committed only once:
            # prune edges -> GC newly/previously orphaned latent nodes -> evict
            # disconnected senses. Each stage sees the topology produced by
            # the previous stage, so pruning can begin an orphan grace period
            # immediately without exposing a partial graph.
            prune_candidates = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={"source_id": edge.source_id, "target_id": edge.target_id, "kind": edge.kind},
                )
                for edge in self._graph.edges
                if evaluate_edge_lifecycle(
                    edge,
                    current_tick=tick,
                    prune_threshold=self._genome.structure.prune_threshold,
                    minimum_support=self._genome.structure.minimum_support,
                    quarantine_window_ticks=self._genome.structure.tentative_lifetime_ticks,
                    tentative_lifetime_ticks=self._genome.structure.tentative_lifetime_ticks,
                )
                is EdgeLifecycleState.REMOVED
            )
            prune_mutations = prune_candidates[:mutation_cap]
            remaining = mutation_cap - len(prune_mutations)
            after_prune = apply_mutations(self._graph, prune_mutations, self._kernel_limits, frozen=frozen)
            if prune_mutations and after_prune is self._graph:
                prune_mutations = ()
                remaining = mutation_cap
                after_prune = self._graph

            orphan_mutations = self._orphan_node_mutations(
                tick=tick,
                max_mutations=remaining,
                graph=after_prune,
            )
            remaining -= len(orphan_mutations)
            after_orphans = apply_mutations(after_prune, orphan_mutations, self._kernel_limits, frozen=frozen)
            if orphan_mutations and after_orphans is after_prune:
                orphan_mutations = ()
                remaining = mutation_cap - len(prune_mutations)
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
                remaining = mutation_cap - len(prune_mutations) - len(orphan_mutations)
                planning_graph = after_orphans

            maintenance_mutations = prune_mutations + orphan_mutations + sense_evictions

            # Growth is planned against the reclaimed budget: concepts first,
            # then generic legal edges.
            edge_slots = max(0, self._soft_edge_limit - len(planning_graph.edges))
            node_slots = max(0, self._soft_node_limit - len(planning_graph.nodes))
            concept_mutations = self._propose_germinal_concept_mutations(
                mutation_slots=remaining,
                node_slots=node_slots,
                edge_slots=edge_slots,
                graph=planning_graph,
            )
            if not concept_mutations:
                self._update_unrouted_tracking(tick, graph=planning_graph)
                recycled_mutations, event = self._propose_concept_recycling_mutations(
                    tick=tick,
                    mutation_slots=remaining,
                    graph=planning_graph,
                )
                if recycled_mutations:
                    concept_mutations = recycled_mutations
                    if event is not None:
                        recycling_events = (event,)
            else:
                self._update_unrouted_tracking(tick, graph=planning_graph)

            remaining -= len(concept_mutations)
            planning_after_concepts = apply_mutations(
                planning_graph, concept_mutations, self._kernel_limits, frozen=frozen
            )
            edge_slots = max(0, self._soft_edge_limit - len(planning_after_concepts.edges))
            proposed = self._structural_plasticity.propose(
                planning_after_concepts,
                kernel_limits=self._kernel_limits,
                tick=tick,
                max_mutations=min(remaining, edge_slots),
            )

            # The complete maintenance+growth transaction is committed against
            # the original graph. Any invalid step rolls the whole batch back.
            all_mutations = maintenance_mutations + concept_mutations + proposed
            if all_mutations:
                candidate = apply_mutations(self._graph, all_mutations, self._kernel_limits, frozen=frozen)
                if candidate is not self._graph:
                    self._graph = candidate
                    self._record_applied_metadata(all_mutations, tick=tick)
                    self._seed_new_edges()
                    self._reconcile_node_metadata()
                    structural_mutations_applied = len(all_mutations)
                    applied_mutations = all_mutations
                    self._topology_revision += 1
            else:
                self._reconcile_node_metadata()
            self._refresh_recovery_state()
            self._enter_recovery_if_needed()

        live_node_ids = {node.node_id for node in self._graph.nodes}
        live_node_kinds = {
            node.node_id: node.kind for node in self._graph.nodes
        }
        self._previous_frame = {node_id: value for node_id, value in frame.activations.items() if node_id in live_node_ids}
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
            predictive_gain=max((item.predictive_gain for item in self._shadow_predictions.values()), default=0.0),
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
            active_concept_ids=tuple(sorted(
                node_id
                for node_id, value in frame.activations.items()
                if (
                    node_id in live_node_ids
                    and live_node_kinds.get(node_id) is NodeKind.CONCEPT
                    and abs(value) >= _ACTIVITY_THRESHOLD
                )
            )),
        )
