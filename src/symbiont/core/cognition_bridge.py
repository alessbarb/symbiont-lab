from __future__ import annotations

import hashlib
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
class _PredictorUtility:
    """Bounded evidence that a materialized predictor beats persistence."""

    samples: int = 0
    model_loss: float = 0.0
    persistence_loss: float = 0.0
    recent_gain: float = 0.0
    negative_streak: int = 0
    positive_streak: int = 0

    def observe(self, *, model_loss: float, persistence_loss: float) -> None:
        if not math.isfinite(model_loss) or not math.isfinite(persistence_loss):
            return
        model = max(0.0, float(model_loss))
        persistence = max(0.0, float(persistence_loss))
        sample_gain = persistence - model
        self.samples += 1
        self.model_loss += model
        self.persistence_loss += persistence
        alpha = 0.125
        self.recent_gain = (
            sample_gain
            if self.samples == 1
            else (1.0 - alpha) * self.recent_gain + alpha * sample_gain
        )
        epsilon = 1e-4
        if self.recent_gain < -epsilon:
            self.negative_streak += 1
            self.positive_streak = 0
        elif self.recent_gain > epsilon:
            self.positive_streak += 1
            self.negative_streak = 0
        else:
            self.negative_streak = max(0, self.negative_streak - 1)
            self.positive_streak = max(0, self.positive_streak - 1)

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
            "recent_gain": self.recent_gain,
            "negative_streak": self.negative_streak,
            "positive_streak": self.positive_streak,
        }


@dataclass(slots=True)
class _PredictorRetirement:
    predictor_id: str
    entered_tick: int
    last_evaluated_tick: int

    def checkpoint(self) -> dict[str, object]:
        return {
            "predictor_id": self.predictor_id,
            "entered_tick": self.entered_tick,
            "last_evaluated_tick": self.last_evaluated_tick,
        }


@dataclass(slots=True)
class _StructuralCandidate:
    candidate_id: str
    family: str
    producer_id: str
    eligible_tick: int
    mutations: tuple[Mutation, ...]
    # Legacy checkpoint field retained for one-way compatibility only.
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
        self._shadow_predictions: dict[tuple[str, str], ShadowPrediction] = {}
        self._shadow_preliminary_support: dict[tuple[str, str], int] = {}
        self._predictor_utility: dict[str, _PredictorUtility] = {}
        self._predictor_retirement: dict[str, _PredictorRetirement] = {}
        self._structural_candidates: dict[str, _StructuralCandidate] = {}
        self._consolidation_generation: int = 0
        self._contention_identity: str = genome.genome_id
        self._last_consolidated_producer_id: str | None = None
        self._next_concept_index: int = 1
        self._topology_revision = 0
        self._develop_senses = (not graph.nodes) if develop_senses is None else bool(develop_senses)
        self._recovery_pending = False
        self._weight_tracker = WeightStabilityTracker(kernel_limits=kernel_limits)
        self._tracked_edge_keys: set[tuple[str, str, str]] = set()
        self._seed_new_edges()
        self._reacclimation_remaining = 0
        self._cached_topology_revision = -1
        self._cached_graph: CognitiveGraph | None = None
        self._cached_node_kinds: dict[str, NodeKind] = {}
        self._cached_relation_pairs: set[tuple[str, str]] = set()
        self._cached_concept_sig_rev = -1
        self._cached_concept_sig_lineage_len = -1
        self._cached_concept_sig_graph: CognitiveGraph | None = None
        self._cached_concept_signatures: list[set[str]] = []
        self._cached_concept_signature_pairs: set[tuple[str, str]] = set()

    def _topology_cache(self) -> tuple[dict[str, NodeKind], set[tuple[str, str]]]:
        if (
            self._cached_topology_revision != self._topology_revision
            or self._cached_graph is not self._graph
        ):
            self._cached_node_kinds = {node.node_id: node.kind for node in self._graph.nodes}
            self._cached_relation_pairs = {
                (edge.source_id, edge.target_id) for edge in self._graph.edges
            }
            self._cached_topology_revision = self._topology_revision
            self._cached_graph = self._graph
        return self._cached_node_kinds, self._cached_relation_pairs

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
    def _producer_id_for_family(family: str) -> str:
        """Return the opaque structural producer identity for a local family."""
        normalized = str(family).strip().replace("_", "-")
        return f"producer.{normalized}" if normalized else "producer.unknown"

    def _producer_rank(self, producer_id: str) -> int:
        material = f"{self._contention_identity}|producer-order|{producer_id}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    def _register_structural_candidate(
        self,
        *,
        candidate_id: str,
        family: str,
        mutations: tuple[Mutation, ...],
        eligible_tick: int,
        producer_id: str | None = None,
    ) -> bool:
        """Expose at most one outstanding structural proposal per producer.

        Local hypothesis multiplicity is intentionally hidden from global
        arbitration. A producer with an unresolved proposal is backpressured
        until that proposal is committed, invalidated or withdrawn.
        """
        if not candidate_id or not mutations:
            return False
        resolved_producer = (
            str(producer_id).strip()
            if producer_id is not None and str(producer_id).strip()
            else self._producer_id_for_family(family)
        )
        existing = self._structural_candidates.get(candidate_id)
        if existing is not None:
            existing.mutations = mutations
            existing.eligible_tick = min(
                existing.eligible_tick,
                max(0, int(eligible_tick)),
            )
            return True

        if any(
            candidate.producer_id == resolved_producer
            for candidate in self._structural_candidates.values()
        ):
            return False

        if len(self._structural_candidates) >= self._kernel_limits.max_consolidation_candidates:
            return False
        self._structural_candidates[candidate_id] = _StructuralCandidate(
            candidate_id=candidate_id,
            family=family,
            producer_id=resolved_producer,
            eligible_tick=max(0, int(eligible_tick)),
            mutations=mutations,
        )
        return True

    def _drop_structural_candidate(self, candidate_id: str) -> None:
        self._structural_candidates.pop(candidate_id, None)

    def bind_contention_identity(self, identity: str) -> None:
        value = str(identity)
        if value:
            self._contention_identity = value

    def _candidate_tiebreak(self, candidate_id: str) -> int:
        material = (
            f"{self._contention_identity}|{self._consolidation_generation}|{candidate_id}"
        ).encode("utf-8")
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

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

        if node.kind is NodeKind.PREDICTOR and node_id in self._predictor_retirement:
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
            utility = self._predictor_utility.get(node_id)
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
        candidate: _StructuralCandidate,
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
            shadow = self._shadow_predictions.get((source_id, target_id))
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
        for candidate_id, candidate in list(self._structural_candidates.items()):
            if not self._valid_candidate(
                candidate,
                graph=graph,
                active_motor_ids=active_motor_ids,
                active_primitive_ids=active_primitive_ids,
            ):
                self._structural_candidates.pop(candidate_id, None)

    def _select_structural_candidate(
        self,
        *,
        graph: CognitiveGraph,
        mutation_slots: int,
        node_slots: int,
        edge_slots: int,
    ) -> tuple[str | None, tuple[Mutation, ...], tuple[str, ...]]:
        """Schedule already-valid producer proposals without semantic inspection."""
        if mutation_slots <= 0:
            return None, (), ()

        valid: list[_StructuralCandidate] = []
        for candidate in self._structural_candidates.values():
            if (
                candidate.required_nodes <= node_slots
                and candidate.required_edges <= edge_slots
                and len(candidate.mutations) <= mutation_slots
            ):
                valid.append(candidate)

        if not valid:
            return None, (), ()

        # Legacy checkpoints may contain several candidates for one producer.
        # Collapse them locally before global arbitration so multiplicity can
        # never become additional structural voting power.
        nominees: dict[str, _StructuralCandidate] = {}
        for candidate in valid:
            current = nominees.get(candidate.producer_id)
            if current is None or (
                candidate.eligible_tick,
                self._candidate_tiebreak(candidate.candidate_id),
                candidate.candidate_id,
            ) < (
                current.eligible_tick,
                self._candidate_tiebreak(current.candidate_id),
                current.candidate_id,
            ):
                nominees[candidate.producer_id] = candidate

        if not nominees:
            return None, (), ()

        # Old proposals cannot be leapfrogged forever by newly arriving
        # producers. Age is the primary neutral fairness key; the stable
        # organism-specific ring only breaks ties among equally old proposals.
        oldest_tick = min(candidate.eligible_tick for candidate in nominees.values())
        eligible_producers = [
            producer_id
            for producer_id, candidate in nominees.items()
            if candidate.eligible_tick == oldest_tick
        ]
        producer_order = sorted(
            eligible_producers,
            key=lambda producer_id: (self._producer_rank(producer_id), producer_id),
        )

        if self._last_consolidated_producer_id is not None:
            cursor_key = (
                self._producer_rank(self._last_consolidated_producer_id),
                self._last_consolidated_producer_id,
            )
            after_cursor = [
                producer_id
                for producer_id in producer_order
                if (self._producer_rank(producer_id), producer_id) > cursor_key
            ]
            before_or_at_cursor = [
                producer_id
                for producer_id in producer_order
                if (self._producer_rank(producer_id), producer_id) <= cursor_key
            ]
            producer_order = after_cursor + before_or_at_cursor

        winner = nominees[producer_order[0]]
        candidate_graph = apply_mutations(
            graph,
            winner.mutations,
            self._kernel_limits,
            frozen=self._safety_state.frozen,
        )
        if candidate_graph is graph:
            self._structural_candidates.pop(winner.candidate_id, None)
            return None, (), ()

        # The third return value is retained as an API compatibility shell.
        # Non-winning producers do not accumulate debt and remain pending.
        return winner.candidate_id, winner.mutations, ()

    def _commit_contention_result(
        self,
        *,
        winner_id: str | None,
        loser_ids: Collection[str],
    ) -> None:
        if winner_id is None:
            return
        winner = self._structural_candidates.get(winner_id)
        if winner is not None:
            self._last_consolidated_producer_id = winner.producer_id
        self._structural_candidates.pop(winner_id, None)
        # loser_ids is deliberately ignored. Producer-level round-robin gives
        # bounded access without permanently accumulating contention debt.
        _ = loser_ids

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

    def _update_predictor_retirement_state(self, *, tick: int) -> None:
        """Enter/leave predictor quarantine using hysteretic internal evidence."""
        predictor_ids = {
            node.node_id for node in self._graph.nodes
            if node.kind is NodeKind.PREDICTOR
        }
        capacity_pressure = len(self._graph.nodes) >= self._soft_node_limit
        minimum_samples = max(8, self._genome.structure.minimum_support)
        enter_streak = max(4, self._genome.structure.minimum_support // 2)
        leave_streak = max(4, self._genome.structure.minimum_support // 2)

        if not capacity_pressure:
            # Retirement is pressure-driven, not a global judgment that weak
            # predictors should disappear. Soft-pruned edges remain able to
            # recover through normal plasticity after quarantine is cancelled.
            self._predictor_retirement.clear()
            return

        for predictor_id in tuple(self._predictor_retirement):
            if predictor_id not in predictor_ids:
                self._predictor_retirement.pop(predictor_id, None)

        # Incremental GC principle: at most one predictor retires at a time.
        # First give the current candidate a chance to recover.
        if self._predictor_retirement:
            predictor_id = next(iter(sorted(self._predictor_retirement)))
            utility = self._predictor_utility.get(predictor_id)
            retirement = self._predictor_retirement[predictor_id]
            retirement.last_evaluated_tick = tick
            if (
                utility is not None
                and utility.recent_gain > 0.0
                and utility.positive_streak >= leave_streak
            ):
                self._predictor_retirement.pop(predictor_id, None)
            else:
                return

        candidates: list[tuple[float, float, int, str]] = []
        for predictor_id in sorted(predictor_ids):
            utility = self._predictor_utility.get(predictor_id)
            if utility is None or utility.samples < minimum_samples:
                continue
            if utility.predictive_gain > 0.0 or utility.negative_streak < enter_streak:
                continue
            candidates.append(
                (
                    utility.recent_gain,
                    utility.predictive_gain,
                    -utility.negative_streak,
                    predictor_id,
                )
            )
        if candidates:
            _, _, _, predictor_id = min(candidates)
            self._predictor_retirement[predictor_id] = _PredictorRetirement(
                predictor_id=predictor_id,
                entered_tick=tick,
                last_evaluated_tick=tick,
            )

    def _retirement_edge_decay(self, edge, *, tick: int) -> None:
        """Soft-prune quarantined predictor edges without immediate deletion.

        Decay is reversible: if the predictor regains positive recent utility,
        quarantine is cancelled and normal Oja plasticity resumes. The rate is
        bounded and independent of task/world semantics.
        """
        retiring_id = None
        if edge.source_id in self._predictor_retirement:
            retiring_id = edge.source_id
        elif edge.target_id in self._predictor_retirement:
            retiring_id = edge.target_id
        if retiring_id is None:
            return

        retirement = self._predictor_retirement[retiring_id]
        age = max(0, tick - retirement.entered_tick)
        grace = max(1, self._genome.structure.tentative_lifetime_ticks // 4)
        if age < grace:
            return

        # Small bounded multiplicative decay: enough to cross the existing
        # prune threshold over many ticks, never an abrupt structural delete.
        decay = 0.99
        edge.weight *= decay
        if abs(edge.weight) < 1e-12:
            edge.weight = 0.0

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
            for predictor_id in self._predictor_retirement
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
        for candidate_id, candidate in list(self._structural_candidates.items()):
            if (
                candidate.family == "motor_readout"
                and candidate_id.removeprefix("motor:") not in requested_set
            ):
                self._drop_structural_candidate(candidate_id)

        for actuator_id in requested:
            node_id = self._motor_readout_id(actuator_id)
            if node_id in existing:
                self._drop_structural_candidate(f"motor:{actuator_id}")
                continue
            self._register_structural_candidate(
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

        for candidate_id, candidate in list(self._structural_candidates.items()):
            if (
                candidate.family == "primitive_readout"
                and candidate_id.removeprefix("primitive:") not in requested_set
            ):
                self._drop_structural_candidate(candidate_id)

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
                self._seed_new_edges()
                self._reconcile_node_metadata()
                self._topology_revision += 1

        existing_nodes = {node.node_id for node in self._graph.nodes}
        for primitive_id in requested:
            node_id = self._primitive_readout_id(primitive_id)
            candidate_id = f"primitive:{primitive_id}"
            if node_id in existing_nodes:
                self._drop_structural_candidate(candidate_id)
                continue
            self._register_structural_candidate(
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
        node_kinds, _ = self._topology_cache()
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
        node_kinds, _ = self._topology_cache()
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
        """Register one validated lag-1 predictor for structural contention.

        Promotion no longer materializes graph structure immediately. A
        promotable shadow hypothesis earns the right to contend for bounded
        cognitive capacity; only the consolidation arbiter may execute its
        add-node/add-edge transaction.
        """
        shadow = self._shadow_predictions.get((source_id, target_id))
        if shadow is None or not shadow.promotable or not self._develop_senses:
            return False
        source_node = self._graph.node_by_id(source_id)
        if source_node is None or source_node.kind is not NodeKind.SENSE:
            return False
        if self._graph.node_by_id(target_id) is None or target_id in self._predictor_retirement:
            return False
        if any(
            node.kind is NodeKind.PREDICTOR and node.predicts_node_id == target_id
            for node in self._graph.nodes
        ):
            return False

        candidate_id = f"predictor:{source_id}:{target_id}"
        existing = self._structural_candidates.get(candidate_id)
        if existing is not None:
            return True

        digest = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:16]
        predictor_id = f"predictor_{digest}"
        existing_ids = {node.node_id for node in self._graph.nodes}
        if predictor_id in existing_ids:
            return False

        return self._register_structural_candidate(
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
        producer_id = self._producer_id_for_family("predictor")
        if any(
            candidate.producer_id == producer_id
            for candidate in self._structural_candidates.values()
        ):
            return False

        ranked = sorted(
            (
                candidate
                for candidate in self._shadow_predictions.values()
                if candidate.promotable
            ),
            key=lambda candidate: (
                -candidate.predictive_gain,
                -candidate.samples,
                self._candidate_tiebreak(
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

    def _record_concept_support(self, activations: Mapping[str, float]) -> None:
        if not self._develop_senses or not isinstance(self._graph, CognitiveGraph):
            return
        kinds, _ = self._topology_cache()
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
            for candidate in self._structural_candidates.values()
            if candidate.family == "concept"
        )
        if concept_count + pending_concepts >= self._kernel_limits.max_concepts:
            return

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
            return

        _, source_ids = eligible[0]
        if any(
            (node := active_graph.node_by_id(source_id)) is None or node.kind is not NodeKind.SENSE
            for source_id in source_ids
        ):
            return

        signature = "|".join(source_ids)
        candidate_id = f"concept:{signature}"
        if candidate_id in self._structural_candidates:
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
        self._register_structural_candidate(
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
    ) -> tuple[Mutation, ...]:
        if not self._develop_senses or max_mutations <= 0:
            return ()
        active_graph = self._graph if graph is None else graph
        orphan_ids = self._orphan_latent_ids(active_graph)
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
                self._predictor_utility.pop(node_id, None)
                self._predictor_retirement.pop(node_id, None)
                self._node_born_tick.pop(node_id, None)
                self._node_observation_count.pop(node_id, None)
                self._node_active_count.pop(node_id, None)
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
        self._predictor_retirement = {
            key: value
            for key, value in self._predictor_retirement.items()
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
                in sorted(self._predictor_utility.items())
            ],
            "predictor_retirement": [
                retirement.checkpoint()
                for _, retirement
                in sorted(self._predictor_retirement.items())
            ],
            "structural_candidates": [
                candidate.checkpoint()
                for _, candidate
                in sorted(self._structural_candidates.items())
            ],
            "consolidation_generation": self._consolidation_generation,
            "last_consolidated_producer_id": self._last_consolidated_producer_id,
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
            restored[predictor_id] = _PredictorUtility(
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
    ) -> dict[str, _PredictorRetirement]:
        if payload is None:
            return {}
        allowed = set(allowed_predictor_ids)
        if not isinstance(payload, list) or len(payload) > 1:
            raise GraphError("predictor_retirement must contain at most one candidate")
        restored: dict[str, _PredictorRetirement] = {}
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
            restored[predictor_id] = _PredictorRetirement(
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
    ) -> dict[str, _StructuralCandidate]:
        if payload is None:
            return {}
        if (
            not isinstance(payload, list)
            or len(payload) > kernel_limits.max_consolidation_candidates
        ):
            raise GraphError("structural_candidates must be a bounded list")
        restored: dict[str, _StructuralCandidate] = {}
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
                else CognitiveBridge._producer_id_for_family(str(family))
            )
            candidate = _StructuralCandidate(
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
                    edge.source_id in self._predictor_retirement
                    or edge.target_id in self._predictor_retirement
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
                    learning_rate=self._genome.plasticity.learning_rate.initial,
                    modulation=tick_modulation * edge.plasticity,
                    eligible=eligible,
                    frozen=frozen,
                )
                if retiring_edge:
                    self._retirement_edge_decay(edge, tick=tick)
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

            node_kinds, existing_relation_pairs = self._topology_cache()
            for node_id, value in frame.activations.items():
                self._node_observation_count[node_id] = (
                    self._node_observation_count.get(node_id, 0) + 1
                )
                if abs(value) >= _ACTIVITY_THRESHOLD:
                    self._node_active_count[node_id] = (
                        self._node_active_count.get(node_id, 0) + 1
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
                    node_id not in self._predictor_retirement
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
                for source_id in active_nodes:
                    if (
                        node_kinds.get(source_id) is not NodeKind.CONCEPT
                        or not self._representation_mature_enough_as_target(source_id)
                    ):
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
                if len(self._shadow_predictions) >= self._live_shadow_limit:
                    self._prune_shadow_predictions()
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
                        support = self._shadow_preliminary_support.get(key, 0) + 1
                        self._shadow_preliminary_support[key] = support
                        if support < preliminary_min:
                            continue
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

            # Maintenance is planned sequentially but committed only once.
            # Fully detached quarantined predictors are reclaimed first using
            # one bounded mutation; edge retirement itself remains delegated to
            # the ordinary edge lifecycle below.
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

            remaining_after_gc = mutation_cap - len(retirement_gc)

            # prune edges -> GC newly/previously orphaned latent nodes -> evict
            # disconnected senses. Each stage sees the topology produced by
            # the previous stage, so pruning can begin an orphan grace period
            # immediately without exposing a partial graph.
            prune_candidates = tuple(
                Mutation(
                    kind="remove_edge",
                    payload={"source_id": edge.source_id, "target_id": edge.target_id, "kind": edge.kind},
                )
                for edge in after_retirement_gc.edges
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
            prune_mutations = prune_candidates[:remaining_after_gc]
            remaining = remaining_after_gc - len(prune_mutations)
            after_prune = apply_mutations(
                after_retirement_gc,
                prune_mutations,
                self._kernel_limits,
                frozen=frozen,
            )
            if prune_mutations and after_prune is after_retirement_gc:
                prune_mutations = ()
                remaining = remaining_after_gc
                after_prune = after_retirement_gc

            orphan_mutations = self._orphan_node_mutations(
                tick=tick,
                max_mutations=remaining,
                graph=after_prune,
            )
            remaining -= len(orphan_mutations)
            after_orphans = apply_mutations(after_prune, orphan_mutations, self._kernel_limits, frozen=frozen)
            if orphan_mutations and after_orphans is after_prune:
                orphan_mutations = ()
                remaining = mutation_cap - len(retirement_gc) - len(prune_mutations)
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
                    - len(prune_mutations)
                    - len(orphan_mutations)
                )
                planning_graph = after_orphans

            maintenance_mutations = (
                retirement_gc
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

            frozen_candidate_ids = tuple(sorted(self._structural_candidates))
            self._consolidation_generation += 1

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

            edge_slots = max(0, self._soft_edge_limit - len(planning_graph.edges))
            node_slots = max(0, self._soft_node_limit - len(planning_graph.nodes))

            # Contention sees exactly the candidates frozen at round start.
            # Candidates registered later wait for the next consolidation.
            original_registry = self._structural_candidates
            self._structural_candidates = {
                candidate_id: original_registry[candidate_id]
                for candidate_id in frozen_candidate_ids
                if candidate_id in original_registry
            }
            (
                contention_winner_id,
                admission_mutations,
                contention_loser_ids,
            ) = self._select_structural_candidate(
                graph=planning_graph,
                mutation_slots=remaining,
                node_slots=node_slots,
                edge_slots=edge_slots,
            )
            frozen_registry_after = self._structural_candidates
            self._structural_candidates = {
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
                        in self._predictor_retirement
                        or str(mutation.payload.get("target_id", ""))
                        in self._predictor_retirement
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
                    self._seed_new_edges()
                    self._reconcile_node_metadata()
                    structural_mutations_applied = len(all_mutations)
                    applied_mutations = all_mutations
                    self._topology_revision += 1
                    self._commit_contention_result(
                        winner_id=contention_winner_id,
                        loser_ids=contention_loser_ids,
                    )
            else:
                self._reconcile_node_metadata()
            self._refresh_recovery_state()
            self._enter_recovery_if_needed()

        live_nodes = self._graph.nodes
        live_node_ids = {node.node_id for node in live_nodes}
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
                    and (node := self._graph.node_by_id(node_id)) is not None
                    and node.kind is NodeKind.CONCEPT
                    and abs(value) >= _ACTIVITY_THRESHOLD
                )
            )),
            retiring_predictors=tuple(sorted(self._predictor_retirement)),
            retirement_edges=sum(
                1
                for edge in self._graph.edges
                if (
                    edge.source_id in self._predictor_retirement
                    or edge.target_id in self._predictor_retirement
                )
            ),
            structural_candidates=len(self._structural_candidates),
            structural_producers=len({
                candidate.producer_id
                for candidate in self._structural_candidates.values()
            }),
            oldest_structural_wait_ticks=max(
                (
                    max(0, tick - candidate.eligible_tick)
                    for candidate in self._structural_candidates.values()
                ),
                default=0,
            ),
            representation_maturity=representation_maturity_counts,
            # Legacy metric retained for snapshot compatibility. Producer-level
            # arbitration no longer accumulates contention debt.
            max_contention_losses=0,
        )
