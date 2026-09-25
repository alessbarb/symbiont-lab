from __future__ import annotations

import math
from typing import Collection, Mapping

from ...cognition.activation import SensoryNormalizer
from ...cognition.checkpoint import (
    export_graph_checkpoint,
    export_safety_state,
    export_sensory_normalizers,
    restore_graph_checkpoint,
    restore_safety_state,
    restore_sensory_normalizers,
)
from ...cognition.graph import CognitiveGraph, GraphError
from ...cognition.learning import ShadowPrediction
from ...cognition.limits import KernelLimits
from ...cognition.structure import Mutation
from ...cognition.types import NodeKind
from ...cognition.metaplasticity import SafetyState
from ...genetics.genome import Genome
from .plasticity_state import PlasticityEngine
from .predictors import PredictorLifecycle, PredictorRetirement, PredictorUtility
from .sense_concept_lifecycle import ConceptLineage, SenseConceptLifecycle
from .structural_candidates import StructuralCandidate, StructuralContention

_MAX_SHADOW_PREDICTIONS = 16384



@dataclass(slots=True)
class RestoredBridgeState:
    graph: CognitiveGraph
    safety_state: SafetyState
    develop_senses: bool
    tick: int
    normalizers: dict[str, SensoryNormalizer]
    lifecycle: SenseConceptLifecycle
    predictors: PredictorLifecycle
    contention: StructuralContention
    node_born_tick: dict[str, int]
    node_observation_count: dict[str, int]
    node_active_count: dict[str, int]
    recovery_pending: bool
    topology_revision: int
    adaptive_resource_budgets: tuple[int, int, int] | None


def export_bridge_state(
    *,
    graph: CognitiveGraph,
    safety_state: SafetyState,
    normalizers: dict[str, SensoryNormalizer],
    plasticity: PlasticityEngine,
    predictors: PredictorLifecycle,
    lifecycle: SenseConceptLifecycle,
    contention: StructuralContention,
    topology_revision: int,
    tick: int,
    develop_senses: bool,
    node_born_tick: dict[str, int],
    node_observation_count: dict[str, int],
    node_active_count: dict[str, int],
    recovery_pending: bool,
    adaptive_node_budget: int,
    adaptive_edge_budget: int,
    adaptive_sense_budget: int,
) -> dict[str, object]:
    return {
        "graph": export_graph_checkpoint(
            graph,
            weight_class_overrides=plasticity.weight_class_overrides(graph),
        ),
        "safety_state": export_safety_state(safety_state),
        "sensory_normalizers": export_sensory_normalizers(normalizers),
        "topology_revision": topology_revision,
        "tick": tick,
        "develop_senses": develop_senses,
        "concept_lineage": [
            {
                "concept_id": item.concept_id,
                "parent_ids": list(item.parent_ids),
                "born_tick": item.born_tick,
            }
            for item in lifecycle.concept_lineage
        ],
        "sense_last_seen_tick": dict(
            sorted(lifecycle.sense_last_seen_tick.items())
        ),
        "orphan_since_tick": dict(sorted(lifecycle.orphan_since_tick.items())),
        "unrouted_since_tick": dict(
            sorted(lifecycle.unrouted_since_tick.items())
        ),
        "concept_last_active_tick": dict(
            sorted(lifecycle.concept_last_active_tick.items())
        ),
        "node_born_tick": dict(sorted(node_born_tick.items())),
        "node_observation_count": dict(sorted(node_observation_count.items())),
        "node_active_count": dict(sorted(node_active_count.items())),
        "next_concept_index": lifecycle.next_concept_index,
        "recovery_pending": recovery_pending,
        "shadow_predictions": [
            {
                "source_id": item.source_id,
                "target_id": item.target_id,
                "samples": item.samples,
                "model_loss": item.model_loss,
                "persistence_loss": item.persistence_loss,
                "status": item.status,
            }
            for item in predictors.shadow_predictions
        ],
        "predictor_utility": [
            utility.checkpoint(predictor_id)
            for predictor_id, utility in sorted(predictors.utility.items())
        ],
        "predictor_retirement": [
            retirement.checkpoint()
            for _, retirement in sorted(predictors.retirement.items())
        ],
        "structural_candidates": [
            candidate.checkpoint()
            for _, candidate in sorted(contention.candidates.items())
        ],
        "consolidation_generation": contention.consolidation_generation,
        "last_consolidated_producer_id": (
            contention.last_consolidated_producer_id
        ),
        "adaptive_resource_budgets": {
            "nodes": adaptive_node_budget,
            "edges": adaptive_edge_budget,
            "senses": adaptive_sense_budget,
        },
    }

def restore_nonnegative_tick_map(
    payload: object,
    *,
    allowed_ids: Collection[str],
    field: str,
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


def restore_shadow_predictions(
    payload: object,
    *,
    max_predictions: int = _MAX_SHADOW_PREDICTIONS,
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
        if (
            not source_id
            or not target_id
            or source_id == target_id
            or (source_id, target_id) in restored
        ):
            continue
        samples = entry.get("samples", 0)
        model_loss = entry.get("model_loss", 0.0)
        persistence_loss = entry.get("persistence_loss", 0.0)
        status = str(entry.get("status", "candidate"))
        if (
            isinstance(samples, bool)
            or not isinstance(samples, int)
            or not 0 <= samples <= 1_000_000
        ):
            raise GraphError("shadow prediction samples out of bounds")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0.0
            for value in (model_loss, persistence_loss)
        ):
            raise GraphError("shadow prediction losses out of bounds")
        if status not in {"candidate", "supported", "contradicted", "retired"}:
            raise GraphError("invalid shadow prediction status")
        restored[(source_id, target_id)] = ShadowPrediction(
            source_id,
            target_id,
            samples,
            float(model_loss),
            float(persistence_loss),
            status,
        )
    return restored


def restore_predictor_utility(
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


def restore_predictor_retirement(
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


def restore_structural_candidates(
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
            if kind not in {"add_node", "add_edge"} or not isinstance(
                payload_map,
                Mapping,
            ):
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


def restore_concept_lineage(
    payload: object,
    *,
    graph: CognitiveGraph,
    kernel_limits: KernelLimits,
) -> dict[str, ConceptLineage]:
    concept_ids = {
        node.node_id
        for node in graph.nodes
        if node.kind is NodeKind.CONCEPT
    }
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
                raise GraphError(
                    "concept_lineage.parent_ids must contain 2 to 4 ids"
                )
            parent_ids = tuple(str(value) for value in raw_parents)
            if len(set(parent_ids)) != len(parent_ids):
                raise GraphError("concept_lineage.parent_ids must be unique")
            born_tick = entry.get("born_tick")
            if (
                isinstance(born_tick, bool)
                or not isinstance(born_tick, int)
                or born_tick < 0
            ):
                raise GraphError(
                    "concept_lineage.born_tick must be a non-negative integer"
                )
            restored[concept_id] = ConceptLineage(
                concept_id,
                parent_ids,
                born_tick,
            )

    incoming: dict[str, set[str]] = {
        concept_id: set()
        for concept_id in concept_ids
    }
    for edge in graph.edges:
        if edge.target_id in incoming:
            incoming[edge.target_id].add(edge.source_id)
    for concept_id, parents in incoming.items():
        if concept_id not in restored and len(parents) >= 2:
            restored[concept_id] = ConceptLineage(
                concept_id,
                tuple(sorted(parents))[:4],
                0,
            )
    return restored


def restore_bridge_state(
    payload: dict[str, object] | None,
    *,
    genome: Genome,
    kernel_limits: KernelLimits,
) -> RestoredBridgeState | None:
    if payload is None:
        return None
    raw_graph = payload.get("graph")
    graph_payload = raw_graph if isinstance(raw_graph, dict) else None
    graph = restore_graph_checkpoint(
        graph_payload,
        kernel_limits=kernel_limits,
    )
    if graph is None:
        return None

    raw_safety = payload.get("safety_state")
    safety_payload = raw_safety if isinstance(raw_safety, dict) else None
    safety_state = restore_safety_state(safety_payload)

    raw_develop_senses = payload.get("develop_senses")
    if raw_develop_senses is None:
        develop_senses = not graph.nodes
    elif not isinstance(raw_develop_senses, bool):
        raise GraphError("develop_senses must be a boolean")
    else:
        develop_senses = raw_develop_senses

    budgets: tuple[int, int, int] | None = None
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
        nodes = max(len(graph.nodes), int(raw_budgets["nodes"]))
        edges = max(len(graph.edges), int(raw_budgets["edges"]))
        sense_count = sum(
            1 for node in graph.nodes if node.kind is NodeKind.SENSE
        )
        senses = min(
            nodes,
            max(sense_count, int(raw_budgets["senses"])),
        )
        budgets = (nodes, edges, senses)

    raw_tick = payload.get("tick", 0)
    if (
        isinstance(raw_tick, bool)
        or not isinstance(raw_tick, int)
        or raw_tick < 0
    ):
        raise GraphError("tick must be a non-negative integer")

    raw_normalizers = payload.get("sensory_normalizers")
    normalizers_payload = (
        raw_normalizers
        if isinstance(raw_normalizers, dict)
        else None
    )
    normalizers = restore_sensory_normalizers(normalizers_payload)

    lifecycle = SenseConceptLifecycle()
    lifecycle.lineage = restore_concept_lineage(
        payload.get("concept_lineage"),
        graph=graph,
        kernel_limits=kernel_limits,
    )
    sense_ids = {
        node.node_id
        for node in graph.nodes
        if node.kind is NodeKind.SENSE
    }
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
    concept_ids = {
        node.node_id
        for node in graph.nodes
        if node.kind is NodeKind.CONCEPT
    }
    lifecycle.sense_last_seen_tick = restore_nonnegative_tick_map(
        payload.get("sense_last_seen_tick"),
        allowed_ids=sense_ids,
        field="sense_last_seen_tick",
    )
    lifecycle.orphan_since_tick = restore_nonnegative_tick_map(
        payload.get("orphan_since_tick"),
        allowed_ids=latent_ids,
        field="orphan_since_tick",
    )
    lifecycle.unrouted_since_tick = restore_nonnegative_tick_map(
        payload.get("unrouted_since_tick"),
        allowed_ids=concept_ids,
        field="unrouted_since_tick",
    )
    lifecycle.concept_last_active_tick = restore_nonnegative_tick_map(
        payload.get("concept_last_active_tick"),
        allowed_ids=concept_ids,
        field="concept_last_active_tick",
    )

    all_node_ids = {node.node_id for node in graph.nodes}
    node_born_tick = {node.node_id: 0 for node in graph.nodes}
    node_born_tick.update(
        restore_nonnegative_tick_map(
            payload.get("node_born_tick"),
            allowed_ids=all_node_ids,
            field="node_born_tick",
        )
    )
    node_observation_count = {
        node.node_id: 0 for node in graph.nodes
    }
    node_observation_count.update(
        restore_nonnegative_tick_map(
            payload.get("node_observation_count"),
            allowed_ids=all_node_ids,
            field="node_observation_count",
        )
    )
    node_active_count = {node.node_id: 0 for node in graph.nodes}
    node_active_count.update(
        restore_nonnegative_tick_map(
            payload.get("node_active_count"),
            allowed_ids=all_node_ids,
            field="node_active_count",
        )
    )

    raw_next_idx = payload.get("next_concept_index")
    if isinstance(raw_next_idx, int) and not isinstance(raw_next_idx, bool) and raw_next_idx > 0:
        lifecycle.next_concept_index = raw_next_idx
    else:
        lifecycle.next_concept_index = (
            lifecycle.extract_max_concept_index(graph) + 1
        )

    raw_recovery = payload.get("recovery_pending", False)
    if not isinstance(raw_recovery, bool):
        raise GraphError("recovery_pending must be a boolean")

    predictors = PredictorLifecycle()
    shadow_limit = min(
        _MAX_SHADOW_PREDICTIONS,
        kernel_limits.max_nodes * kernel_limits.max_nodes,
    )
    predictors.shadows = restore_shadow_predictions(
        payload.get("shadow_predictions"),
        max_predictions=shadow_limit,
    )
    predictors.invalidate_shadow_cache()
    predictors.mark_shadow_dirty()

    predictor_ids = {
        node.node_id
        for node in graph.nodes
        if node.kind is NodeKind.PREDICTOR
    }
    predictors.utility = restore_predictor_utility(
        payload.get("predictor_utility"),
        allowed_predictor_ids=predictor_ids,
    )
    predictors.retirement = restore_predictor_retirement(
        payload.get("predictor_retirement"),
        allowed_predictor_ids=predictor_ids,
    )

    contention = StructuralContention(
        kernel_limits=kernel_limits,
        identity=genome.genome_id,
    )
    contention.candidates = restore_structural_candidates(
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
    contention.consolidation_generation = raw_generation

    raw_last_producer = payload.get("last_consolidated_producer_id")
    if raw_last_producer is not None and (
        not isinstance(raw_last_producer, str)
        or not raw_last_producer
        or len(raw_last_producer) > 256
    ):
        raise GraphError(
            "last_consolidated_producer_id must be a bounded string"
        )
    contention.last_consolidated_producer_id = raw_last_producer

    raw_revision = payload.get("topology_revision", 0)
    if (
        isinstance(raw_revision, bool)
        or not isinstance(raw_revision, int)
        or raw_revision < 0
    ):
        raise GraphError("topology_revision must be a non-negative integer")

    return RestoredBridgeState(
        graph=graph,
        safety_state=safety_state,
        develop_senses=develop_senses,
        tick=raw_tick,
        normalizers=normalizers,
        lifecycle=lifecycle,
        predictors=predictors,
        contention=contention,
        node_born_tick=node_born_tick,
        node_observation_count=node_observation_count,
        node_active_count=node_active_count,
        recovery_pending=raw_recovery,
        topology_revision=raw_revision,
        adaptive_resource_budgets=budgets,
    )
