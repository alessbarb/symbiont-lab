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
    nodes: list[AtlasNode] = []
    for item in topology.get("nodes", ()) or ():
        if not isinstance(item, Mapping) or item.get("id") is None:
            continue
        metadata = {
            key: item[key]
            for key in ("predictsNodeId", "bias", "tau")
            if item.get(key) is not None
        }
        nodes.append(AtlasNode(id=str(item["id"]), kind=str(item.get("kind", "concept")), metadata=metadata))
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


def _motor_competence_nodes(snapshot: Mapping[str, Any]) -> list[AtlasNode]:
    items = snapshot.get("motor_competences")
    if not isinstance(items, (list, tuple)):
        return []
    nodes: list[AtlasNode] = []
    for item in items:
        if not isinstance(item, Mapping) or item.get("competence_id") is None:
            continue
        metadata = {
            key: item[key]
            for key in (
                "controller_id", "effect_id", "maturity", "support", "failures",
                "reproducibility", "controllability", "directional_consistency",
                "parent_competence_ids",
            )
            if item.get(key) is not None
        }
        nodes.append(AtlasNode(id=str(item["competence_id"]), kind="motor_competence", metadata=metadata))
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
        metrics={"motor_capability": _motor_capability_metrics(snapshot)},
    )
