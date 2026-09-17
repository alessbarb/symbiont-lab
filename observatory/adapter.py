"""Passive projection from a real Symbiont runtime into Observatory v1-v3."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from symbiont.cognition.checkpoint import (
    ELIGIBILITY_CLASSES,
    ELIGIBILITY_RANGE,
    WEIGHT_CLASSES,
    dequantize_weight,
    quantize_signed,
    quantize_weight,
)
from symbiont.cognition.genome import Genome
from symbiont.cognition.graph import CognitiveGraph
from symbiont.cognition.types import WEIGHT_RANGE

try:
    from .config import (
        INGESTION_MAX_TICKS as MAX_TICKS,
        INGESTION_MAX_SENSORY_PARTS as MAX_SENSORY_PARTS,
        INGESTION_MAX_COGNITIVE_REGIONS as MAX_COGNITIVE_REGIONS,
        INGESTION_MAX_BODY_PARTS as MAX_BODY_PARTS,
        INGESTION_MAX_BODY_DEPENDENCIES as MAX_BODY_DEPENDENCIES,
    )
except ImportError:
    from config import (
        INGESTION_MAX_TICKS as MAX_TICKS,
        INGESTION_MAX_SENSORY_PARTS as MAX_SENSORY_PARTS,
        INGESTION_MAX_COGNITIVE_REGIONS as MAX_COGNITIVE_REGIONS,
        INGESTION_MAX_BODY_PARTS as MAX_BODY_PARTS,
        INGESTION_MAX_BODY_DEPENDENCIES as MAX_BODY_DEPENDENCIES,
    )

SCHEMA_VERSION = 1
BODY_SCHEMA_SNAPSHOT_VERSION = 3
ENVELOPE_TYPE = "symbiont-observatory-snapshot"


def _text(value: Any, limit: int) -> str:
    return str(value).replace("\x00", "")[:limit]


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _quality(value: Any) -> tuple[float, bool]:
    name = _enum_value(value).lower()
    scores = {"nominal": 1.0, "degraded": 0.6, "stale": 0.25, "unavailable": 0.0}
    return scores.get(name, 0.5), name != "unavailable"


_LOSS_CLASS_BOUNDS: tuple[tuple[float, str], ...] = (
    (0.0, "zero"),
    (0.0001, "trace"),
    (0.01, "low"),
    (0.1, "medium"),
    (0.5, "high"),
    (2.0, "extreme"),
)


def loss_class(loss: float) -> str:
    """Independent quantization from weight/eligibility classes: a Huber
    loss has a different distribution/meaning than a weight or an
    eligibility trace, so only the discipline (bounded, discrete, never
    raw) is shared, not the thresholds."""
    if not math.isfinite(loss) or loss < 0:
        return "zero"
    result = "zero"
    for bound, name in _LOSS_CLASS_BOUNDS:
        if loss >= bound:
            result = name
    return result


def _certainty(uncertainty: Any) -> float:
    try:
        number = float(uncertainty)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number) or number < 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 / (1.0 + number)))


def _discrete_class(value: Any, maximum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value <= maximum else None


def _undeveloped_body_schema(version: int = 2) -> dict[str, Any]:
    return {
        "schema_version": version if version in (1, 2) else 2,
        "state": "undeveloped",
        "parts": [],
        "dependencies": [],
        "global_state": {},
    }


def _body_schema_state(body_schema: Any) -> dict[str, Any]:
    """Rebuild the public BodySchema representation from a closed allow-list.

    BodySchema v1 is the historical sensory-only contract. v2 additionally
    permits opaque cognitive regions and the weak learned relations
    ``co_acts_with`` / ``precedes``. Checkpoint-private salts, cognitive
    channel membership/evidence and any unknown fields fail closed rather
    than being forwarded.
    """
    if not isinstance(body_schema, dict):
        return _undeveloped_body_schema()
    version = body_schema.get("schema_version")
    fallback = _undeveloped_body_schema(version if version in (1, 2) else 2)
    if version not in (1, 2):
        return fallback
    if set(body_schema) != {"schema_version", "state", "parts", "dependencies", "global_state"}:
        return fallback
    if body_schema.get("global_state") != {}:
        return fallback

    state = body_schema.get("state")
    raw_parts = body_schema.get("parts")
    raw_dependencies = body_schema.get("dependencies")
    if state not in {"undeveloped", "partial"} or not isinstance(raw_parts, list) or not isinstance(raw_dependencies, list):
        return fallback
    max_parts = MAX_SENSORY_PARTS if version == 1 else MAX_BODY_PARTS
    max_dependencies = 0 if version == 1 else MAX_BODY_DEPENDENCIES
    if len(raw_parts) > max_parts or len(raw_dependencies) > max_dependencies:
        return fallback
    if state == "undeveloped":
        return fallback if raw_parts or raw_dependencies else fallback
    if not raw_parts:
        return fallback

    sense_keys = {
        "part_id", "kind", "existence_confidence_class", "health_class",
        "confidence_class", "cost_class", "maturity_class", "recency_class",
    }
    region_keys = {
        "part_id", "kind", "existence_confidence_class", "confidence_class",
        "activity_class", "maturity_class", "recency_class",
    }
    parts: list[dict[str, Any]] = []
    seen_parts: set[str] = set()
    region_ids: set[str] = set()
    sensory_count = 0
    region_count = 0

    for raw in raw_parts:
        if not isinstance(raw, dict):
            return fallback
        kind = raw.get("kind")
        part_id = raw.get("part_id")
        if not isinstance(part_id, str) or part_id in seen_parts:
            return fallback
        seen_parts.add(part_id)

        existence = _discrete_class(raw.get("existence_confidence_class"), 15)
        confidence = _discrete_class(raw.get("confidence_class"), 15)
        maturity = _discrete_class(raw.get("maturity_class"), 7)
        recency = _discrete_class(raw.get("recency_class"), 4)
        if None in (existence, confidence, maturity, recency):
            return fallback

        if kind == "sense":
            if set(raw) != sense_keys or not part_id.startswith("part.sense."):
                return fallback
            suffix = part_id.removeprefix("part.sense.")
            if len(suffix) != 32 or any(char not in "0123456789abcdef" for char in suffix):
                return fallback
            health = _discrete_class(raw.get("health_class"), 15)
            cost = _discrete_class(raw.get("cost_class"), 15)
            if health is None or cost is None:
                return fallback
            sensory_count += 1
            parts.append({
                "part_id": part_id,
                "kind": "sense",
                "existence_confidence_class": existence,
                "health_class": health,
                "confidence_class": confidence,
                "cost_class": cost,
                "maturity_class": maturity,
                "recency_class": recency,
            })
        elif version == 2 and kind == "cognitive_region":
            if set(raw) != region_keys or not part_id.startswith("part.region."):
                return fallback
            suffix = part_id.removeprefix("part.region.")
            if len(suffix) != 32 or any(char not in "0123456789abcdef" for char in suffix):
                return fallback
            activity = _discrete_class(raw.get("activity_class"), 15)
            if activity is None:
                return fallback
            region_count += 1
            region_ids.add(part_id)
            parts.append({
                "part_id": part_id,
                "kind": "cognitive_region",
                "existence_confidence_class": existence,
                "confidence_class": confidence,
                "activity_class": activity,
                "maturity_class": maturity,
                "recency_class": recency,
            })
        else:
            return fallback

    if sensory_count > MAX_SENSORY_PARTS or region_count > MAX_COGNITIVE_REGIONS:
        return fallback

    dependency_keys = {"source_id", "target_id", "relation", "confidence_class", "support_class"}
    dependencies: list[dict[str, Any]] = []
    seen_dependencies: set[tuple[str, str, str]] = set()
    for raw in raw_dependencies:
        if version != 2 or not isinstance(raw, dict) or set(raw) != dependency_keys:
            return fallback
        source = raw.get("source_id")
        target = raw.get("target_id")
        relation = raw.get("relation")
        if (
            not isinstance(source, str)
            or not isinstance(target, str)
            or source == target
            or source not in region_ids
            or target not in region_ids
            or relation not in {"co_acts_with", "precedes"}
            or (relation == "co_acts_with" and source >= target)
        ):
            return fallback
        confidence = _discrete_class(raw.get("confidence_class"), 15)
        support = _discrete_class(raw.get("support_class"), 15)
        if confidence is None or support is None:
            return fallback
        key = (relation, source, target)
        if key in seen_dependencies:
            return fallback
        seen_dependencies.add(key)
        dependencies.append({
            "source_id": source,
            "target_id": target,
            "relation": relation,
            "confidence_class": confidence,
            "support_class": support,
        })

    return {
        "schema_version": version,
        "state": "partial",
        "parts": parts,
        "dependencies": dependencies,
        "global_state": {},
    }


def _edge_deltas(
    graph: CognitiveGraph | None, previous_edge_classes: dict[str, tuple[int, int]] | None
) -> list[dict[str, Any]]:
    """Only edges whose quantized class changed since the last published
    tick -- the full edge table is topology, not per-tick state (spec:
    CognitionState carries deltas, CognitionTopology carries structure)."""
    if graph is None:
        return []
    deltas = []
    for edge in graph.edges[:1024]:
        weight_class = quantize_signed(edge.weight, WEIGHT_RANGE, WEIGHT_CLASSES)
        eligibility_class = quantize_signed(edge.eligibility, ELIGIBILITY_RANGE, ELIGIBILITY_CLASSES)
        current = (weight_class, eligibility_class)
        key = f"{edge.source_id}->{edge.target_id}"
        previous = previous_edge_classes.get(key) if previous_edge_classes is not None else None
        if previous != current:
            deltas.append(
                {
                    "source_id": _text(edge.source_id, 128),
                    "target_id": _text(edge.target_id, 128),
                    "weight_class": weight_class,
                    "eligibility_class": eligibility_class,
                }
            )
        if previous_edge_classes is not None:
            previous_edge_classes[key] = current
    return deltas


def _developmental_divergence(
    graph: CognitiveGraph,
    baseline: CognitiveGraph,
) -> float:
    """Compare opaque topology identity sets against an explicit baseline.

    This is a session-scoped structural observable, not a claim about fitness
    or semantics.  It deliberately ignores weights, activations and labels.
    The symmetric difference is normalized by the bounded union so a stable
    topology reports zero and a wholly different topology reports one.
    """
    current_nodes = {node.node_id for node in graph.nodes}
    baseline_nodes = {node.node_id for node in baseline.nodes}
    current_edges = {(edge.source_id, edge.target_id) for edge in graph.edges}
    baseline_edges = {(edge.source_id, edge.target_id) for edge in baseline.edges}
    changed = len(current_nodes ^ baseline_nodes) + len(current_edges ^ baseline_edges)
    total = len(current_nodes | baseline_nodes) + len(current_edges | baseline_edges)
    return 0.0 if total == 0 else max(0.0, min(1.0, changed / total))


def _cognition_state(
    cognition: Any,
    *,
    graph: CognitiveGraph | None = None,
    genome: Genome | None = None,
    previous_edge_classes: dict[str, tuple[int, int]] | None = None,
) -> dict[str, Any]:
    readouts = {key: round(float(value), 6) for key, value in dict(getattr(cognition, "readouts", {})).items()}
    prediction_errors = {
        error.predictor_id: loss_class(error.loss) for error in tuple(getattr(cognition, "prediction_errors", ()))
    }
    mutations = []
    for mutation in tuple(getattr(cognition, "mutations", ())):
        entry: dict[str, Any] = {"kind": _text(getattr(mutation, "kind", ""), 32)}
        payload = dict(getattr(mutation, "payload", {}))
        if "node_id" in payload:
            entry["node_id"] = _text(payload["node_id"], 128)
        elif "source_id" in payload and "target_id" in payload:
            entry["edge_id"] = _text(f"{payload['source_id']}->{payload['target_id']}", 260)
        mutations.append(entry)
    safety = {
        "consecutive_failures": max(0, int(getattr(cognition, "consecutive_failures", 0))),
        "frozen": bool(getattr(cognition, "frozen", False)),
    }
    topology_health = _enum_value(getattr(cognition, "topology_health", "germinal")).lower()
    allowed_health = {"germinal", "developing", "connected", "adaptive", "degenerate", "recovering"}
    if topology_health not in allowed_health:
        topology_health = "germinal"
    state = {
        "topology_revision": max(0, int(getattr(cognition, "topology_revision", 0))),
        "topology_health": topology_health,
        "recovering": bool(getattr(cognition, "recovering", False)),
        "readouts": readouts,
        "prediction_errors": prediction_errors,
        "edge_deltas": _edge_deltas(graph, previous_edge_classes),
        "mutations": mutations[:8],
        "safety_state": safety,
        "stranded_concepts": [_text(x, 128) for x in tuple(getattr(cognition, "stranded_concepts", ()))[:64]],
        "predictive_gain": round(float(getattr(cognition, "predictive_gain", 0.0)), 6),
    }
    if graph is not None and genome is not None:
        node_budget = max(1, int(genome.development.soft_node_budget))
        edge_budget = max(1, int(genome.development.soft_edge_budget))
        pressure = max(len(graph.nodes) / node_budget, len(graph.edges) / edge_budget)
        errors = [
            abs(edge.weight - dequantize_weight(quantize_weight(edge.weight)))
            for edge in graph.edges[:1024]
            if math.isfinite(edge.weight)
        ]
        state["structural_pressure"] = round(max(0.0, min(1.0, pressure)), 6)
        state["quantization_error"] = round(sum(errors) / len(errors), 6) if errors else 0.0
    return state


def _physiology_state(physiology: Any, *, resting_requested: bool | None = None) -> dict[str, Any] | None:
    """Project viability without exposing raw metabolic measurements."""
    if physiology is None:
        return None
    state = _enum_value(getattr(physiology, "state", "unknown")).lower()
    if state not in {"active", "stressed", "dormant", "agonizing", "dead"}:
        state = "unknown"
    transitions = max(0, int(getattr(physiology, "transitions", 0)))
    death_tick = getattr(physiology, "death_tick", None)
    requested = resting_requested
    if requested is None:
        requested = getattr(physiology, "resting_requested", False)
    return {"state": state, "transitions": transitions,
            "death_tick": max(0, int(death_tick)) if death_tick is not None else None,
            "resting_requested": bool(requested)}


def _metabolism_state(metabolism: Any) -> dict[str, Any] | None:
    """Project metabolic needs as classes, never raw reserves or costs."""
    if metabolism is None:
        return None
    pressure = _enum_value(getattr(metabolism, "pressure", "normal")).lower()
    if pressure not in {"normal", "elevated", "severe", "unrecoverable"}:
        pressure = "unknown"
    reserves = getattr(metabolism, "reserve", {})
    capacity = getattr(metabolism, "capacity", {})
    reserve_classes: dict[str, str] = {}
    if isinstance(reserves, dict) and isinstance(capacity, dict):
        for kind in sorted(set(reserves) & set(capacity))[:8]:
            try:
                ratio = float(reserves[kind]) / max(float(capacity[kind]), 1e-12)
            except (TypeError, ValueError, ZeroDivisionError):
                ratio = 0.0
            reserve_classes[_text(kind, 32)] = (
                "depleted" if ratio <= 0.0 else "low" if ratio < 0.25
                else "moderate" if ratio < 0.75 else "replete"
            )
    return {"pressure": pressure, "reserve_classes": reserve_classes}


def _development_state(development: Any) -> dict[str, Any] | None:
    """Project derived ontogeny without exposing evaluator labels or internals."""
    if development is None:
        return None

    def counter(name: str, maximum: int = 1_000_000) -> int:
        try:
            value = int(getattr(development, name, 0))
        except (TypeError, ValueError):
            value = 0
        return min(max(0, value), maximum)

    def ratio(name: str) -> float:
        try:
            value = float(getattr(development, name, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        return round(max(0.0, min(1.0, value)) if math.isfinite(value) else 0.0, 6)

    phase = _enum_value(getattr(development, "phase", "unknown")).lower()
    allowed_phases = {"germinal", "developing", "juvenile", "mature", "declining", "terminal", "dead"}
    if phase not in allowed_phases:
        phase = "unknown"
    topology_health = _text(getattr(development, "topology_health", "unknown"), 64)
    return {
        "phase": phase,
        "tick": counter("tick"),
        "stress_ticks": counter("stress_ticks"),
        "recovery_events": counter("recovery_events"),
        "repair_events": counter("repair_events"),
        "excretion_events": counter("excretion_events"),
        "maintenance_burden": ratio("maintenance_burden"),
        "senescence_index": ratio("senescence_index"),
        "action_attempts": counter("action_attempts"),
        "sensory_count": counter("sensory_count", MAX_SENSORY_PARTS),
        "topology_health": topology_health,
    }


def _degradation_state(result: Any) -> dict[str, int]:
    """Project bounded retention lifecycle counters without retained content."""
    try:
        excreted = max(0, int(getattr(result, "degradation_excreted", 0)))
        retained = max(0, int(getattr(result, "retained_items", 0)))
    except (TypeError, ValueError):
        excreted, retained = 0, 0
    return {"retained_items": min(retained, 256), "excreted_units": min(excreted, 256)}


def _attention_state(allocations: Iterable[Any]) -> dict[str, float]:
    """Expose bounded allocation concentration, never candidate semantics."""
    costs: list[float] = []
    for allocation in tuple(allocations)[:64]:
        try:
            cost = float(getattr(allocation, "cost", 0.0))
        except (TypeError, ValueError):
            cost = 0.0
        if math.isfinite(cost) and cost > 0.0:
            costs.append(cost)
    total = sum(costs)
    if not costs or total <= 0.0:
        return {"concentration": 0.0, "entropy": 0.0}
    shares = [cost / total for cost in costs]
    entropy = -sum(share * math.log(share) for share in shares)
    normalizer = math.log(len(shares)) if len(shares) > 1 else 1.0
    return {"concentration": round(max(shares), 6),
            "entropy": round(max(0.0, min(1.0, entropy / normalizer)), 6)}


def _social_state(relations: Iterable[Any], *, current_tick: int | None = None) -> list[dict[str, Any]]:
    """Bounded, aggregate relation projection; identities are caller-provided opaque ids."""
    projected: list[dict[str, Any]] = []
    for relation in tuple(relations)[:128]:
        source = _text(getattr(relation, "source_id", ""), 128)
        target = _text(getattr(relation, "target_id", ""), 128)
        if not source or not target or source == target:
            continue
        valence = _enum_value(getattr(relation, "valence", "unknown")).lower()
        if valence not in {"unknown", "positive", "negative"}:
            valence = "unknown"
        support = max(0.0, min(1_000_000.0, float(getattr(relation, "support", 0.0))))
        harm = max(0.0, min(1_000_000.0, float(getattr(relation, "harm", 0.0))))
        freshness = None
        if current_tick is not None and hasattr(relation, "freshness"):
            try:
                freshness = max(0.0, min(1.0, float(relation.freshness(current_tick))))
            except (TypeError, ValueError):
                freshness = None
        reliability = None
        if current_tick is not None and hasattr(relation, "reliability"):
            try:
                reliability = max(0.0, min(1.0, float(relation.reliability(current_tick))))
            except (TypeError, ValueError):
                reliability = None
        projected.append({"source_id": source, "target_id": target, "valence": valence,
                          "channel": _text(getattr(relation, "channel", "default"), 64) or "default",
                          "support": support, "harm": harm,
                          "observations": max(0, int(getattr(relation, "observations", 0))),
                          "reciprocal_observations": max(0, int(getattr(relation, "reciprocal_observations", 0))),
                          "conflicts": max(0, int(getattr(relation, "conflicts", 0))),
                          "rejections": max(0, int(getattr(relation, "rejections", 0))),
                          "freshness": freshness,
                          "reliability": reliability,
                          "last_tick": (max(0, int(getattr(relation, "last_tick")))
                                       if getattr(relation, "last_tick", None) is not None else None)})
    return projected


def _social_resource_state(evidence: Iterable[Any], *, current_tick: int | None = None) -> list[dict[str, Any]]:
    """Project local opaque-resource evidence without exposing host semantics."""
    projected: list[dict[str, Any]] = []
    for item in tuple(evidence)[:64]:
        token = _text(getattr(item, "token", ""), 64)
        if not token:
            continue
        requested = max(0.0, min(1_000_000.0, float(getattr(item, "requested", 0.0))))
        granted = max(0.0, min(requested, float(getattr(item, "granted", 0.0))))
        observations = max(0, int(getattr(item, "observations", 0)))
        denied = max(0, min(observations, int(getattr(item, "denied", 0))))
        last_tick = getattr(item, "last_tick", None)
        freshness = None
        if current_tick is not None and hasattr(item, "freshness"):
            try:
                freshness = max(0.0, min(1.0, float(item.freshness(current_tick))))
            except (TypeError, ValueError):
                freshness = None
        projected.append({
            "token": token,
            "requested": requested,
            "granted": granted,
            "availability": (granted / requested if requested > 0.0 else 0.0),
            "observations": observations,
            "denied": denied,
            "freshness": freshness,
            "last_tick": max(0, int(last_tick)) if last_tick is not None else None,
        })
    return projected


def _cultural_state(observations: Mapping[str, Any]) -> dict[str, Any]:
    """Project passive social lineage without exposing payloads or weights."""
    def count(name: str) -> int:
        try:
            return max(0, min(100_000, int(observations.get(name, 0))))
        except (TypeError, ValueError):
            return 0
    lineage = []
    for item in tuple(observations.get("claim_lineage", ()))[:128]:
        if not isinstance(item, Mapping):
            continue
        claim_id = _text(item.get("claim_id", ""), 128)
        if not claim_id:
            continue
        lineage.append({
            "claim_id": claim_id,
            "source": _text(item.get("source", ""), 128),
            "parents": [_text(value, 128) for value in tuple(item.get("parents", ()))[:8]],
            "roots": [_text(value, 128) for value in tuple(item.get("roots", ()))[:32]],
        })
    freshness = []
    for item in tuple(observations.get("freshness", ()))[:128]:
        if isinstance(item, Mapping) and item.get("claim_id"):
            try:
                value = max(0.0, min(1.0, float(item.get("value", 0.0))))
            except (TypeError, ValueError):
                value = 0.0
            freshness.append({"claim_id": _text(item["claim_id"], 128), "value": value})
    composites = []
    for item in tuple(observations.get("composite_lineage", ()))[:128]:
        if not isinstance(item, Mapping) or not item.get("composite_id"):
            continue
        composites.append({
            "composite_id": _text(item["composite_id"], 128),
            "components": [_text(value, 128) for value in tuple(item.get("components", ()))[:32]],
            "parents": [_text(value, 128) for value in tuple(item.get("parents", ()))[:8]],
            "contributors": [_text(value, 128) for value in tuple(item.get("contributors", ()))[:32]],
            "roots": [_text(value, 128) for value in tuple(item.get("roots", ()))[:32]],
            "generation": max(0, min(64, int(item.get("generation", 0))) if isinstance(item.get("generation", 0), int) and not isinstance(item.get("generation", 0), bool) else 0),
            "retired": item.get("retired") is True,
        })
    decisions = []
    for item in tuple(observations.get("cultural_decisions", ()))[:256]:
        if not isinstance(item, Mapping) or not item.get("decision_id"):
            continue
        decisions.append({
            "decision_id": _text(item.get("decision_id", ""), 128),
            "tick": max(0, int(item.get("tick", 0))) if isinstance(item.get("tick", 0), int) and not isinstance(item.get("tick", 0), bool) else 0,
            "action": _text(item.get("action", ""), 32),
            "items": [_text(value, 128) for value in tuple(item.get("items", ()))[:4]],
            "recipient": _text(item.get("recipient", ""), 128) if item.get("recipient") else None,
            "cost": max(0, int(item.get("cost", 0))) if isinstance(item.get("cost", 0), int) and not isinstance(item.get("cost", 0), bool) else 0,
        })
    return {
        "claim_count": count("claim_count"),
        "unique_roots": count("unique_roots"),
        "independent_roots": count("independent_roots"),
        "transmission_depth": count("transmission_depth"),
        "mutation_depth": count("mutation_depth"),
        "confirmed_locally": count("confirmed_locally"),
        "contradicted_locally": count("contradicted_locally"),
        "freshness": freshness,
        "lineage": lineage,
        "composite_count": count("composite_count"),
        "unique_contributors": count("unique_contributors"),
        "cultural_generation": count("cultural_generation"),
        "composite_lineage": composites,
        "cultural_decisions": decisions,
        "cultural_policy_cost": count("cultural_policy_cost"),
        "symbols_known": count("symbols_known"),
        "symbols_emitted": count("symbols_emitted"),
        "symbol_exposures": count("symbol_exposures"),
        "grounding_updates": count("grounding_updates"),
        "symbol_policy_cost": count("symbol_policy_cost"),
        "symbol_decisions": [{
            "decision_id": _text(item.get("decision_id", ""), 128),
            "tick": max(0, item.get("tick", 0)) if isinstance(item, Mapping) and isinstance(item.get("tick", 0), int) else 0,
            "action": _text(item.get("action", ""), 32),
            "symbol_id": _text(item.get("symbol_id", ""), 128) if isinstance(item, Mapping) and item.get("symbol_id") else None,
            "recipient_id": _text(item.get("recipient_id", ""), 128) if isinstance(item, Mapping) and item.get("recipient_id") else None,
            "cost": max(0, item.get("cost", 0)) if isinstance(item, Mapping) and isinstance(item.get("cost", 0), int) else 0,
        } for item in tuple(observations.get("symbol_decisions", ()))[:256] if isinstance(item, Mapping) and item.get("decision_id")],
        "symbol_grounding": [{
            "symbol_id": _text(item.get("symbol_id", ""), 128),
            "support": max(0, item.get("support", 0)) if isinstance(item.get("support", 0), int) and not isinstance(item.get("support", 0), bool) else 0,
            "contradiction": max(0, item.get("contradiction", 0)) if isinstance(item.get("contradiction", 0), int) and not isinstance(item.get("contradiction", 0), bool) else 0,
            "strength": max(0, item.get("strength", 0)) if isinstance(item.get("strength", 0), int) and not isinstance(item.get("strength", 0), bool) else 0,
        } for item in tuple(observations.get("symbol_grounding", ()))[:128] if isinstance(item, Mapping) and item.get("symbol_id")],
    }


def _state(result: Any) -> str:
    if getattr(result, "dissent", None) is not None:
        return "reflecting"
    if getattr(result, "investigated_capability", None):
        return "exploring"
    if getattr(result, "percepts", ()):
        return "observing"
    return "resting"


def project_tick(
    result: Any,
    *,
    acclimation: Any | None = None,
    display_id: str = "local-symbiont",
    ticks_remaining: int | None = None,
    revision_counts: dict[str, int] | None = None,
    genome: Genome | None = None,
    graph: CognitiveGraph | None = None,
    previous_edge_classes: dict[str, tuple[int, int]] | None = None,
    body_schema: dict[str, Any] | None = None,
    signal_knowledge: tuple[dict[str, Any], ...] | None = None,
    knowledge_events: tuple[dict[str, Any], ...] | None = None,
    signal_references: dict[str, str] | None = None,
    social_relations: Iterable[Any] | None = None,
    social_resource_evidence: Iterable[Any] | None = None,
    cultural_observations: Mapping[str, Any] | None = None,
    resting_requested: bool | None = None,
    relation_churn: float | None = None,
    developmental_baseline: CognitiveGraph | None = None,
) -> dict[str, Any]:
    """Project one RuntimeTickResult without coupling the core to this module.

    ``revision_counts`` is an optional accumulator (capability_id -> count)
    the caller keeps across ticks: each capability's dissent occurrence
    increments its own running total, so ``belief.revision_count`` is a
    real cumulative history rather than a per-tick 0/1 flag. Omitting it
    keeps the old per-tick-only behavior for a caller with no cross-tick
    state to offer.

    ``body_schema`` must be the observer-safe BodySchema representation. Its
    presence selects snapshot schema v3 independently of whether structural
    cognition is configured. This keeps self-perception and cognition as
    orthogonal capabilities rather than making either imply the other.
    """
    narratives = tuple(getattr(result, "narrative", ()))[:128]
    percepts = []
    for percept in tuple(getattr(result, "percepts", ()))[:32]:
        score, available = _quality(getattr(percept, "quality", "unknown"))
        name = _text(getattr(percept, "name", "percept"), 64)
        item = {"id": name, "label": name.replace("_", " "), "quality": score, "available": available}
        if signal_references and name in signal_references:
            item["knowledge_signal_id"] = _text(signal_references[name], 71)
        percepts.append(item)

    beliefs = []
    for entry in narratives:
        capability = _text(getattr(entry, "capability_id", "belief"), 64)
        contested_now = getattr(entry, "dissent", None) is not None
        if revision_counts is not None:
            if contested_now:
                revision_counts[capability] = revision_counts.get(capability, 0) + 1
            revision_count = revision_counts.get(capability, 0)
        else:
            revision_count = 1 if contested_now else 0
        beliefs.append({
            "id": capability,
            "label": _text(getattr(entry, "summary", capability), 120),
            "certainty": _certainty(getattr(entry, "uncertainty", None)),
            "evidence_count": max(0, int(getattr(entry, "evidence_gathered", 0))),
            "revision_count": revision_count,
            "contested": bool(getattr(entry, "contested", False)),
        })

    tick = max(0, int(getattr(result, "tick", 0)))
    events = []
    for percept in percepts[:32]:
        events.append({"id": _text(f"p-{tick}-{percept['id']}", 64), "type": "perception", "label": f"Observed {percept['label']}"})
    for allocation in tuple(getattr(result, "allocations", ()))[:16]:
        name = _text(getattr(allocation, "name", "attention"), 64)
        events.append({"id": _text(f"a-{tick}-{name}", 64), "type": "attention", "label": f"Attended to {name.replace('_', ' ')}"})
    dissent = getattr(result, "dissent", None)
    if dissent is not None:
        capability = _text(getattr(dissent, "capability_id", "belief"), 64)
        events.append({"id": _text(f"d-{tick}-{capability}", 64), "type": "contradiction", "label": f"Preserved contradictory evidence for {capability}", "belief_id": capability, "causal_chain": ["bounded second look", "evidence conflicted with baseline", "dissent preserved"]})
    action = getattr(result, "action_result", None)
    if action is not None:
        action_id = _text(getattr(action, "action_id", "action"), 64)
        executed = bool(getattr(action, "executed", False))
        raw_reason = getattr(action, "reason", None)
        reason = _text(raw_reason, 96) if raw_reason is not None else ""
        organism_action = {"action_id": action_id, "executed": executed, "reason": reason or None}
        events.append({
            "id": _text(f"x-{tick}-{action_id}", 64),
            "type": "action",
            "label": f"{'Executed' if executed else 'Rejected'} local action {action_id}",
            "action_id": action_id,
            "executed": executed,
        })
    else:
        organism_action = None

    # These entries are emitted by the organism runtime.  Observatory only
    # gives them a passive, bounded presentation; it does not infer lifecycle
    # facts from physiology snapshots or action fields.
    runtime_events = getattr(result, "runtime_events", None)
    if runtime_events is not None:
        for index, runtime_event in enumerate(tuple(runtime_events)[:32]):
            event_name = _text(runtime_event, 64)
            if not event_name:
                continue
            label = event_name.replace("_", " ")
            events.append({
                "id": _text(f"l-{tick}-{index}-{event_name}", 64),
                "type": "life_history",
                "label": _text(label[:1].upper() + label[1:], 160),
            })

    known = tuple(getattr(acclimation, "known_capabilities", ())) if acclimation is not None else ()
    acclimated = tuple(getattr(acclimation, "acclimated_capabilities", ())) if acclimation is not None else ()
    salient_notes: list[str] = []
    physiology_obj = getattr(result, "physiology", None)
    if physiology_obj is not None and getattr(physiology_obj, "state", None) and getattr(physiology_obj.state, "value", str(physiology_obj.state)) == "dormant":
        salient_notes.append("Resting in metabolic dormancy.")
    for name, observation in dict(getattr(result, "drift_observations", {})).items():
        if _enum_value(getattr(observation, "kind", "")).lower() == "regime_shift":
            salient_notes.append(f"Regime shift observed in {name}.")
    if dissent is not None:
        salient_notes.append(f"Contradictory evidence gathered for {capability}.")

    attended_summaries = [_text(getattr(entry, "summary", ""), 300) for entry in narratives if getattr(entry, "attended", False)]
    other_summaries = [_text(getattr(entry, "summary", ""), 300) for entry in narratives if not getattr(entry, "attended", False)]
    all_narratives = salient_notes + attended_summaries + other_summaries
    narrative_text = _text(" ".join(filter(None, all_narratives)), 600)

    organism: dict[str, Any] = {
        "display_id": _text(display_id, 48) or "local-symbiont",
        "state": _state(result),
        "narrative": narrative_text,
        "acclimation": len(acclimated) / len(known) if known else 0.0,
        "memory": [_text(s, 200) for s in all_narratives[:32]],
        "open_questions": [f"Learn more about {_text(getattr(entry, 'capability_id', 'this capability'), 64)}" for entry in narratives if _certainty(getattr(entry, "uncertainty", None)) < 0.5][:16],
        "investigations": ([f"Second look at {_text(result.investigated_capability, 64)}"] if getattr(result, "investigated_capability", None) else []),
        "regime_changes": [_text(name, 200) for name, observation in dict(getattr(result, "drift_observations", {})).items() if _enum_value(getattr(observation, "kind", "")).lower() == "regime_shift"][:16],
        "percepts": percepts,
        "beliefs": beliefs,
        "events": events[:64],
        "attention": _attention_state(getattr(result, "allocations", ())),
    }
    if organism_action is not None:
        organism["action"] = organism_action
    if signal_knowledge is not None:
        organism["signal_knowledge"] = list(signal_knowledge)[:64]
        organism["knowledge_events"] = list(knowledge_events or ())[:64]
    if ticks_remaining is not None:
        organism["resource_budget"] = {"ticks_remaining": max(0, int(ticks_remaining))}
    physiology = _physiology_state(getattr(result, "physiology", None), resting_requested=resting_requested)
    if physiology is not None:
        organism["physiology"] = physiology
    metabolism = _metabolism_state(getattr(result, "metabolism", None))
    if metabolism is not None:
        organism["metabolism"] = metabolism
    development = _development_state(getattr(result, "development", None))
    if development is not None:
        organism["development"] = development
    if social_relations is not None:
        organism["social_relations"] = _social_state(social_relations, current_tick=tick)
    if social_resource_evidence is not None:
        organism["social_resource_evidence"] = _social_resource_state(social_resource_evidence, current_tick=tick)
    if cultural_observations is not None:
        organism["cultural_claims"] = _cultural_state(cultural_observations)
    organism["degradation"] = _degradation_state(result)

    activity = min(1.0, (len(percepts) + len(getattr(result, "allocations", ())) * 2) / 12.0)
    member = {"display_id": organism["display_id"], "ecology": 0, "activity": activity, "knowledge_count": len(beliefs), "contested_count": sum(1 for belief in beliefs if belief["contested"])}

    cognition = getattr(result, "cognition", None)
    schema_version = SCHEMA_VERSION
    if cognition is not None and genome is not None:
        schema_version = 2
        organism["cognition"] = _cognition_state(cognition, graph=graph, genome=genome, previous_edge_classes=previous_edge_classes)
        if relation_churn is not None:
            try:
                churn = float(relation_churn)
            except (TypeError, ValueError):
                churn = 0.0
            organism["cognition"]["relation_churn"] = round(max(0.0, min(1.0, churn)), 6)
        if developmental_baseline is not None:
            organism["cognition"]["developmental_divergence"] = round(
                _developmental_divergence(graph, developmental_baseline), 6
            )
    # Signal knowledge is a v3 projection. v3 requires an explicit BodySchema,
    # so a caller that only has knowledge still publishes the honest
    # ``not_yet_developed`` representation rather than emitting an invalid
    # snapshot that the browser must reject.
    if signal_knowledge is not None and body_schema is None:
        body_schema = _undeveloped_body_schema()
    if body_schema is not None:
        schema_version = BODY_SCHEMA_SNAPSHOT_VERSION
        organism["body_schema"] = _body_schema_state(body_schema)
    if signal_knowledge is not None:
        schema_version = BODY_SCHEMA_SNAPSHOT_VERSION
    return {"schema_version": schema_version, "tick": tick, "organism": organism, "population": {"members": [member], "relationships": []}}


def project_topology(graph: CognitiveGraph, *, genome: Genome, kernel_version: str) -> dict[str, Any]:
    """Structural-only projection: never carries weight/eligibility -- those
    are per-tick CognitionState, quantized, in _cognition_state above."""
    return {
        "genome_id": _text(genome.genome_id, 72),
        "kernel_version": _text(kernel_version, 32),
        "topology_revision": 0,  # caller overwrites with the bridge's live counter
        "nodes": [
            {"node_id": _text(node.node_id, 128), "kind": node.kind.value, "bias": node.bias, "tau": node.tau}
            for node in graph.nodes[:128]
        ],
        "edges": [
            {"source_id": _text(edge.source_id, 128), "target_id": _text(edge.target_id, 128), "kind": edge.kind.value}
            for edge in graph.edges[:1024]
        ],
    }


def envelope(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"type": ENVELOPE_TYPE, "snapshot": snapshot}


def write_replay(path: str | Path, snapshots: Iterable[dict[str, Any]]) -> None:
    """Atomically write a bounded local replay; no data is transmitted."""
    target = Path(path)
    items = list(snapshots)
    if not 1 <= len(items) <= MAX_TICKS:
        raise ValueError(f"replay must contain between 1 and {MAX_TICKS} snapshots")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "snapshots": items}
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record bounded real Symbiont ticks for the passive Observatory")
    parser.add_argument("--ticks", type=int, default=20, help="finite tick budget (1-10000; default 20)")
    parser.add_argument("--output", type=Path, default=Path("symbiont-replay.json"))
    parser.add_argument("--display-id", default="local-symbiont", help="non-identifying display label")
    parser.add_argument("--checkpoint", type=Path, help="optional durable abstract runtime checkpoint")
    parser.add_argument("--stdout", action="store_true", help="also emit one postMessage-compatible JSON envelope per line")
    args = parser.parse_args(argv)
    if not 1 <= args.ticks <= MAX_TICKS:
        parser.error(f"--ticks must be between 1 and {MAX_TICKS}")

    from symbiont.core.governor import GovernedOrganism
    from symbiont.core.runtime import OrganismRuntime

    runtime = OrganismRuntime.load_or_create(args.checkpoint) if args.checkpoint else OrganismRuntime()
    organism = GovernedOrganism(runtime, max_ticks=args.ticks)
    revision_counts: dict[str, int] = {}
    snapshots = []
    for _ in range(args.ticks):
        result = organism.tick()
        snapshot = project_tick(
            result,
            acclimation=runtime.acclimation,
            display_id=args.display_id,
            ticks_remaining=organism.ticks_remaining,
            revision_counts=revision_counts,
            body_schema=runtime.body_schema.export_representation(current_tick=runtime.tick_count),
            signal_knowledge=result.signal_knowledge,
            knowledge_events=result.knowledge_events,
            signal_references=result.signal_references,
            social_relations=runtime.social_ledger.relations,
            social_resource_evidence=runtime.social_resource_ledger.evidence,
            cultural_observations=(runtime.cultural_observations() if hasattr(runtime, "cultural_observations") else None),
        )
        snapshots.append(snapshot)
        if args.stdout:
            print(json.dumps(envelope(snapshot), ensure_ascii=False, separators=(",", ":")), flush=True)
    write_replay(args.output, snapshots)
    if args.checkpoint:
        runtime.save(args.checkpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())
