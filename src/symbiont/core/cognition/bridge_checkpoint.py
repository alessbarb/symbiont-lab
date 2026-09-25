from __future__ import annotations

import math
from typing import Collection, Mapping

from ...cognition.graph import CognitiveGraph, GraphError
from ...cognition.learning import ShadowPrediction
from ...cognition.limits import KernelLimits
from ...cognition.structure import Mutation
from ...cognition.types import NodeKind
from .predictors import PredictorRetirement, PredictorUtility
from .sense_concept_lifecycle import ConceptLineage
from .structural_candidates import StructuralCandidate, StructuralContention

_MAX_SHADOW_PREDICTIONS = 16384


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
