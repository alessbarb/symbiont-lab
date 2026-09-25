"""Cognitive Atlas v2 projection.

Deterministic, read-only classification of a mind snapshot (see
`projection.mind_snapshot_from_rich_state`) into Atlas nodes/edges.

Per the Cognitive Atlas v2 spec: `CognitiveGraph` topology is one source
among several, not the definition of the Atlas. This module never touches
`symbiont` objects directly and never fabricates a relation the snapshot
does not evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

ATLAS_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class AtlasNode:
    id: str
    kind: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AtlasEdge:
    id: str
    source_id: str
    target_id: str
    kind: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CognitiveAtlasSnapshot:
    schema_version: int
    tick: int | None
    nodes: tuple[AtlasNode, ...]
    edges: tuple[AtlasEdge, ...]
    metrics: Mapping[str, Any]


def _topology_nodes(snapshot: Mapping[str, Any]) -> list[AtlasNode]:
    topology = snapshot.get("topology")
    if not isinstance(topology, Mapping):
        return []
    observer_analysis = snapshot.get("observer_analysis")
    activation_values = (
        observer_analysis.get("activationValues")
        if isinstance(observer_analysis, Mapping)
        else None
    )
    prediction_error_values = (
        observer_analysis.get("predictionErrorValues")
        if isinstance(observer_analysis, Mapping)
        else None
    )
    nodes: list[AtlasNode] = []
    for item in topology.get("nodes", ()) or ():
        if not isinstance(item, Mapping) or item.get("id") is None:
            continue
        node_id = str(item["id"])
        metadata = {
            key: item[key]
            for key in ("predictsNodeId", "bias", "tau")
            if item.get(key) is not None
        }
        if isinstance(activation_values, Mapping) and node_id in activation_values:
            metadata["activation"] = activation_values[node_id]
        kind = str(item.get("kind", "concept"))
        if (
            kind == "predictor"
            and isinstance(prediction_error_values, Mapping)
            and node_id in prediction_error_values
        ):
            metadata["predictionError"] = prediction_error_values[node_id]
        nodes.append(AtlasNode(id=node_id, kind=kind, metadata=metadata))
    return nodes


def _topology_edges(snapshot: Mapping[str, Any]) -> list[AtlasEdge]:
    topology = snapshot.get("topology")
    if not isinstance(topology, Mapping):
        return []
    edges: list[AtlasEdge] = []
    for item in topology.get("edges", ()) or ():
        if not isinstance(item, Mapping):
            continue
        source_id = item.get("sourceId")
        target_id = item.get("targetId")
        if source_id is None or target_id is None:
            continue
        metadata = {
            key: item[key]
            for key in ("weight", "plasticity", "delayTicks", "support", "ageTicks", "stableTicks", "lastUseTick")
            if item.get(key) is not None
        }
        edges.append(AtlasEdge(
            id=f"edge.topology.{source_id}.{target_id}",
            source_id=str(source_id),
            target_id=str(target_id),
            kind=str(item.get("kind", "associated_with")),
            metadata=metadata,
        ))
    return edges


_MATURE_MATURITY = frozenset({"established", "robust"})


def _bindings_by_competence(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    embodiment = snapshot.get("embodiment")
    if not isinstance(embodiment, Mapping):
        return {}
    items = embodiment.get("bindings")
    if not isinstance(items, (list, tuple)):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if isinstance(item, Mapping) and item.get("competence_id") is not None:
            result[str(item["competence_id"])] = item
    return result


def _competence_state(item: Mapping[str, Any], binding: Mapping[str, Any] | None) -> str:
    """Spec Sec 35: functional state, derived only from real fields (no
    fabricated 'available'/'inactive' -- nothing in source distinguishes
    those from 'unbound' today)."""
    if binding is None:
        return "unbound"
    maturity = item.get("maturity")
    if maturity not in _MATURE_MATURITY:
        return "calibrating"
    reliability = binding.get("reliability")
    if isinstance(reliability, (int, float)) and reliability >= 0.5:
        return "usable"
    return "degraded"


def _motor_competence_nodes(snapshot: Mapping[str, Any]) -> list[AtlasNode]:
    items = snapshot.get("motor_competences")
    if not isinstance(items, (list, tuple)):
        return []
    bindings = _bindings_by_competence(snapshot)
    nodes: list[AtlasNode] = []
    for item in items:
        if not isinstance(item, Mapping) or item.get("competence_id") is None:
            continue
        competence_id = str(item["competence_id"])
        metadata = {
            key: item[key]
            for key in (
                "controller_id", "effect_id", "maturity", "support", "failures",
                "reproducibility", "controllability", "directional_consistency",
                "parent_competence_ids",
            )
            if item.get(key) is not None
        }
        metadata["state"] = _competence_state(item, bindings.get(competence_id))
        nodes.append(AtlasNode(id=competence_id, kind="motor_competence", metadata=metadata))
    return nodes


def _effect_nodes(snapshot: Mapping[str, Any]) -> list[AtlasNode]:
    items = snapshot.get("effects")
    if not isinstance(items, (list, tuple)):
        return []
    nodes: list[AtlasNode] = []
    for item in items:
        if not isinstance(item, Mapping) or item.get("effect_id") is None:
            continue
        metadata = {
            key: item[key]
            for key in ("feature_refs", "support", "confidence")
            if item.get(key) is not None
        }
        nodes.append(AtlasNode(id=str(item["effect_id"]), kind="effect", metadata=metadata))
    return nodes


def _action_dimension_nodes(snapshot: Mapping[str, Any]) -> list[AtlasNode]:
    items = snapshot.get("action_dimensions")
    if not isinstance(items, (list, tuple)):
        return []
    nodes: list[AtlasNode] = []
    for item in items:
        if not isinstance(item, Mapping) or item.get("dimension_id") is None:
            continue
        metadata = {
            key: item[key]
            for key in ("availability", "controllability", "confidence", "usage_count", "embodiment_bound")
            if item.get(key) is not None
        }
        nodes.append(AtlasNode(id=str(item["dimension_id"]), kind="action_dimension", metadata=metadata))
    return nodes


def _embodiment_binding_nodes_and_edges(
    snapshot: Mapping[str, Any],
    known_competence_ids: set[str],
) -> tuple[list[AtlasNode], list[AtlasEdge]]:
    embodiment = snapshot.get("embodiment")
    if not isinstance(embodiment, Mapping):
        return [], []
    items = embodiment.get("bindings")
    if not isinstance(items, (list, tuple)):
        return [], []
    nodes: list[AtlasNode] = []
    edges: list[AtlasEdge] = []
    for item in items:
        if not isinstance(item, Mapping) or item.get("competence_id") is None:
            continue
        competence_id = str(item["competence_id"])
        node_id = f"binding.{competence_id}"
        metadata = {
            key: item[key]
            for key in ("surface_fingerprint", "effect_id", "reliability", "controllability", "last_evidence_tick")
            if item.get(key) is not None
        }
        nodes.append(AtlasNode(id=node_id, kind="embodiment_binding", metadata=metadata))
        if competence_id in known_competence_ids:
            evidence: dict[str, Any] = {"source": "embodiment_execution_binding"}
            if item.get("reliability") is not None:
                evidence["confidence"] = item["reliability"]
            if item.get("last_evidence_tick") is not None:
                evidence["last_tick"] = item["last_evidence_tick"]
            edges.append(AtlasEdge(
                id=f"edge.bound_to.{node_id}",
                source_id=node_id,
                target_id=competence_id,
                kind="bound_to",
                metadata={"evidence": evidence},
            ))
    return nodes, edges


def _competence_effect_edges(
    snapshot: Mapping[str, Any],
    known_effect_ids: set[str],
) -> list[AtlasEdge]:
    items = snapshot.get("motor_competences")
    if not isinstance(items, (list, tuple)):
        return []
    edges: list[AtlasEdge] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        competence_id = item.get("competence_id")
        effect_id = item.get("effect_id")
        if competence_id is None or effect_id is None or str(effect_id) not in known_effect_ids:
            continue
        evidence: dict[str, Any] = {"source": "sensorimotor_model"}
        if item.get("support") is not None:
            evidence["observations"] = item["support"]
        if item.get("reproducibility") is not None:
            evidence["confidence"] = item["reproducibility"]
        edges.append(AtlasEdge(
            id=f"edge.produces.{competence_id}.{effect_id}",
            source_id=str(competence_id),
            target_id=str(effect_id),
            kind="produces",
            metadata={"evidence": evidence},
        ))
    return edges


def _controller_nodes_and_edges(snapshot: Mapping[str, Any]) -> tuple[list[AtlasNode], list[AtlasEdge]]:
    """Spec Sec 12: controller is distinct from competence.

    Source (symbiont.actuation.controller) has no live controller registry --
    only an opaque `controller_id`/`controller_strategy_ref` threaded through
    each competence. Materialize only what that honestly supports: identity
    and which competences require it. No strategy classification is
    fabricated beyond the ref the organism itself recorded.
    """
    items = snapshot.get("motor_competences")
    if not isinstance(items, (list, tuple)):
        return [], []
    strategy_refs: dict[str, str] = {}
    requiring_competences: dict[str, list[str]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        controller_id = item.get("controller_id")
        competence_id = item.get("competence_id")
        if controller_id is None or competence_id is None:
            continue
        controller_id = str(controller_id)
        requiring_competences.setdefault(controller_id, []).append(str(competence_id))
        strategy_ref = item.get("controller_strategy_ref")
        if strategy_ref is not None and controller_id not in strategy_refs:
            strategy_refs[controller_id] = strategy_ref

    nodes: list[AtlasNode] = []
    edges: list[AtlasEdge] = []
    for controller_id, competence_ids in sorted(requiring_competences.items()):
        metadata: dict[str, Any] = {"competence_count": len(competence_ids)}
        if controller_id in strategy_refs:
            metadata["strategy_ref"] = strategy_refs[controller_id]
        nodes.append(AtlasNode(id=controller_id, kind="controller", metadata=metadata))
        for competence_id in competence_ids:
            edges.append(AtlasEdge(
                id=f"edge.requires.{competence_id}.{controller_id}",
                source_id=competence_id,
                target_id=controller_id,
                kind="requires",
            ))
    return nodes, edges


def _body_schema_nodes_and_edges(snapshot: Mapping[str, Any]) -> tuple[list[AtlasNode], list[AtlasEdge]]:
    """Spec Sec 17: cognitive body-model parts/dependencies, not anatomy.

    Source is BodySchemaEngine.export_representation() -- already bounded,
    already confidence-classed, already free of anatomical names for the
    'sense' parts. Projected as-is; nothing inferred here.
    """
    body_schema = snapshot.get("body_schema")
    if not isinstance(body_schema, Mapping):
        return [], []
    nodes: list[AtlasNode] = []
    part_ids: set[str] = set()
    for part in body_schema.get("parts", ()) or ():
        if not isinstance(part, Mapping) or part.get("part_id") is None:
            continue
        part_id = str(part["part_id"])
        metadata = {
            key: part[key]
            for key in (
                "kind", "existence_confidence_class", "confidence_class",
                "health_class", "activity_class", "cost_class",
                "maturity_class", "recency_class",
            )
            if part.get(key) is not None
        }
        nodes.append(AtlasNode(id=part_id, kind="body_schema", metadata=metadata))
        part_ids.add(part_id)

    edges: list[AtlasEdge] = []
    for dependency in body_schema.get("dependencies", ()) or ():
        if not isinstance(dependency, Mapping):
            continue
        source_id = dependency.get("source_id")
        target_id = dependency.get("target_id")
        if source_id is None or target_id is None:
            continue
        source_id, target_id = str(source_id), str(target_id)
        if source_id not in part_ids or target_id not in part_ids:
            continue
        evidence: dict[str, Any] = {"source": "body_schema_dependency_evidence"}
        for key in ("confidence_class", "support_class"):
            if dependency.get(key) is not None:
                evidence[key] = dependency[key]
        metadata = {"evidence": evidence}
        edges.append(AtlasEdge(
            id=f"edge.body_schema.{dependency.get('relation', 'depends_on')}.{source_id}.{target_id}",
            source_id=source_id,
            target_id=target_id,
            kind=str(dependency.get("relation", "correlates")),
            metadata=metadata,
        ))
    return nodes, edges


def _motor_capability_metrics(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    items = snapshot.get("motor_competences")
    if not isinstance(items, (list, tuple)):
        return {"supported": False, "known": None, "bound": None}
    known_ids = {str(item["competence_id"]) for item in items if isinstance(item, Mapping) and item.get("competence_id") is not None}
    embodiment = snapshot.get("embodiment")
    bound_ids: set[str] = set()
    if isinstance(embodiment, Mapping) and isinstance(embodiment.get("bindings"), (list, tuple)):
        bound_ids = {
            str(item["competence_id"])
            for item in embodiment["bindings"]
            if isinstance(item, Mapping) and item.get("competence_id") is not None
        }
    return {
        "supported": True,
        "known": len(known_ids),
        "bound": len(known_ids & bound_ids),
    }


def _prediction_metrics(nodes: list[AtlasNode]) -> Mapping[str, Any]:
    predictor_errors = [
        node.metadata["predictionError"]
        for node in nodes
        if node.kind == "predictor" and "predictionError" in node.metadata
    ]
    predictor_count = sum(1 for node in nodes if node.kind == "predictor")
    return {
        "predictors": predictor_count,
        "pressure": (sum(predictor_errors) / len(predictor_errors)) if predictor_errors else 0.0,
    }


def _knowledge_coverage_metrics(nodes: list[AtlasNode]) -> Mapping[str, Any]:
    """Spec Sec 60/62: separate per-domain counts, never a single fake
    'knowledge %'. Only the Symbiont-owned side (this snapshot's domain) --
    Body/Embodiment effector counts belong to a different owner's data."""
    def count(kind: str) -> int:
        return sum(1 for node in nodes if node.kind == kind)

    return {
        "action_dimensions": count("action_dimension"),
        "motor_competences": count("motor_competence"),
        "controllers": count("controller"),
        "embodiment_bindings": count("embodiment_binding"),
        "body_schema_parts": count("body_schema"),
        "predictors": count("predictor"),
    }


def build_cognitive_atlas(snapshot: Mapping[str, Any]) -> CognitiveAtlasSnapshot:
    """Classify one mind snapshot into an Atlas model. Pure function, no side effects."""
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot must be a mapping")

    nodes: list[AtlasNode] = []
    edges: list[AtlasEdge] = []

    nodes.extend(_topology_nodes(snapshot))
    edges.extend(_topology_edges(snapshot))

    competence_nodes = _motor_competence_nodes(snapshot)
    effect_nodes = _effect_nodes(snapshot)
    nodes.extend(competence_nodes)
    nodes.extend(effect_nodes)

    known_competence_ids = {node.id for node in competence_nodes}
    known_effect_ids = {node.id for node in effect_nodes}

    binding_nodes, binding_edges = _embodiment_binding_nodes_and_edges(snapshot, known_competence_ids)
    nodes.extend(binding_nodes)
    edges.extend(binding_edges)
    edges.extend(_competence_effect_edges(snapshot, known_effect_ids))

    controller_nodes, controller_edges = _controller_nodes_and_edges(snapshot)
    nodes.extend(controller_nodes)
    edges.extend(controller_edges)

    body_schema_nodes, body_schema_edges = _body_schema_nodes_and_edges(snapshot)
    nodes.extend(body_schema_nodes)
    edges.extend(body_schema_edges)

    nodes.extend(_action_dimension_nodes(snapshot))

    tick = snapshot.get("tick")
    try:
        tick = int(tick) if tick is not None else None
    except (TypeError, ValueError):
        tick = None

    return CognitiveAtlasSnapshot(
        schema_version=ATLAS_SCHEMA_VERSION,
        tick=tick,
        nodes=tuple(nodes),
        edges=tuple(edges),
        metrics={
            "motor_capability": _motor_capability_metrics(snapshot),
            "prediction": _prediction_metrics(nodes),
            "knowledge_coverage": _knowledge_coverage_metrics(nodes),
        },
    )


@dataclass(frozen=True, slots=True)
class CognitiveAtlasDiff:
    nodes_added: tuple[str, ...]
    nodes_removed: tuple[str, ...]
    nodes_updated: tuple[str, ...]
    edges_added: tuple[str, ...]
    edges_removed: tuple[str, ...]
    edges_strengthened: tuple[str, ...]
    edges_weakened: tuple[str, ...]
    activity_updates: Mapping[str, float]
    metrics: Mapping[str, Any]

    def to_delta_payload(self) -> dict[str, Any]:
        """Spec Sec 82: AtlasDelta wire shape. Pure serialization -- this
        does not itself decide how or whether a transport sends it."""
        return {
            "nodes_added": list(self.nodes_added),
            "nodes_removed": list(self.nodes_removed),
            "nodes_updated": list(self.nodes_updated),
            "edges_added": list(self.edges_added),
            "edges_removed": list(self.edges_removed),
            "edges_updated": sorted(set(self.edges_strengthened) | set(self.edges_weakened)),
            "activity_updates": dict(self.activity_updates),
        }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _edge_strength(edge: AtlasEdge) -> float | None:
    """Best available real numeric proxy for edge strength, in priority order."""
    metadata = edge.metadata
    if "weight" in metadata:
        value = metadata["weight"]
    elif "evidence" in metadata and isinstance(metadata["evidence"], Mapping) and "confidence" in metadata["evidence"]:
        value = metadata["evidence"]["confidence"]
    elif "support" in metadata:
        value = metadata["support"]
    else:
        return None
    return value if isinstance(value, (int, float)) else None


def diff_cognitive_atlas(before: CognitiveAtlasSnapshot, after: CognitiveAtlasSnapshot) -> CognitiveAtlasDiff:
    """Compare two Atlas snapshots. Pure function; never touches Symbiont state.

    Spec Sec 49/50: this is the re-embodiment comparison -- how much learned
    motor knowledge survives a body change versus how much embodiment
    binding has to be rediscovered.
    """
    before_node_ids = {node.id for node in before.nodes}
    after_node_ids = {node.id for node in after.nodes}
    before_edge_ids = {edge.id for edge in before.edges}
    after_edge_ids = {edge.id for edge in after.edges}

    before_competence_ids = {node.id for node in before.nodes if node.kind == "motor_competence"}
    after_competence_ids = {node.id for node in after.nodes if node.kind == "motor_competence"}
    before_binding_ids = {node.id for node in before.nodes if node.kind == "embodiment_binding"}
    after_binding_ids = {node.id for node in after.nodes if node.kind == "embodiment_binding"}
    after_bound_competence_ids = {
        edge.target_id for edge in after.edges if edge.kind == "bound_to"
    }

    preserved_competences = before_competence_ids & after_competence_ids
    immediately_usable = preserved_competences & after_bound_competence_ids
    requiring_remapping = preserved_competences - after_bound_competence_ids

    metrics = {
        "knowledge_preserved": {
            "count": len(preserved_competences),
            "ratio": _ratio(len(preserved_competences), len(before_competence_ids)),
        },
        "embodiment_mappings_preserved": {
            "count": len(before_binding_ids & after_binding_ids),
            "ratio": _ratio(len(before_binding_ids & after_binding_ids), len(before_binding_ids)),
        },
        "competences_immediately_usable": {
            "count": len(immediately_usable),
            "ratio": _ratio(len(immediately_usable), len(before_competence_ids)),
        },
        "competences_requiring_remapping": {
            "count": len(requiring_remapping),
            "ratio": _ratio(len(requiring_remapping), len(before_competence_ids)),
        },
    }

    before_edges_by_id = {edge.id: edge for edge in before.edges}
    after_edges_by_id = {edge.id: edge for edge in after.edges}
    strengthened: list[str] = []
    weakened: list[str] = []
    for edge_id in before_edge_ids & after_edge_ids:
        before_strength = _edge_strength(before_edges_by_id[edge_id])
        after_strength = _edge_strength(after_edges_by_id[edge_id])
        if before_strength is None or after_strength is None:
            continue
        if after_strength > before_strength:
            strengthened.append(edge_id)
        elif after_strength < before_strength:
            weakened.append(edge_id)

    before_nodes_by_id = {node.id: node for node in before.nodes}
    after_nodes_by_id = {node.id: node for node in after.nodes}
    nodes_updated: list[str] = []
    activity_updates: dict[str, float] = {}
    for node_id in before_node_ids & after_node_ids:
        before_node = before_nodes_by_id[node_id]
        after_node = after_nodes_by_id[node_id]
        if before_node.metadata != after_node.metadata:
            nodes_updated.append(node_id)
        after_activation = after_node.metadata.get("activation")
        if isinstance(after_activation, (int, float)) and before_node.metadata.get("activation") != after_activation:
            activity_updates[node_id] = after_activation

    return CognitiveAtlasDiff(
        nodes_added=tuple(sorted(after_node_ids - before_node_ids)),
        nodes_removed=tuple(sorted(before_node_ids - after_node_ids)),
        nodes_updated=tuple(sorted(nodes_updated)),
        edges_added=tuple(sorted(after_edge_ids - before_edge_ids)),
        edges_removed=tuple(sorted(before_edge_ids - after_edge_ids)),
        edges_strengthened=tuple(sorted(strengthened)),
        edges_weakened=tuple(sorted(weakened)),
        activity_updates=activity_updates,
        metrics=metrics,
    )
