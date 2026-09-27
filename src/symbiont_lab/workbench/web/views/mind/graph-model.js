import { isStructuralAtlasEdge } from './relation-semantics.js';

/**
 * Pure cognition-graph model helpers.
 *
 * Observer-side only: these functions derive visual topology metadata without
 * mutating or classifying the organism itself.
 */

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finiteNumber(value, 0)));
}

export function deriveLocalCommunities(nodes, adjacency) {
  // Three deterministic label-propagation rounds intentionally stop before
  // global convergence. Labels describe local relationship neighbourhoods,
  // not semantic categories owned by Symbiont.
  const labels = new Map(nodes.map(node => [node.id, node.id]));
  const ordered = [...nodes].sort((a, b) => a.id.localeCompare(b.id));

  for (let round = 0; round < 3; round++) {
    const next = new Map(labels);
    for (const node of ordered) {
      const neighbors = adjacency.get(node.id) ?? new Set();
      if (!neighbors.size) {
        next.set(node.id, 'isolated');
        continue;
      }
      const scores = new Map();
      for (const neighborId of neighbors) {
        const label = labels.get(neighborId) ?? neighborId;
        scores.set(label, (scores.get(label) ?? 0) + 1);
      }
      let best = labels.get(node.id) ?? node.id;
      let bestScore = -1;
      for (const [label, score] of [...scores.entries()].sort(([a], [b]) => a.localeCompare(b))) {
        if (score > bestScore) {
          best = label;
          bestScore = score;
        }
      }
      next.set(node.id, best);
    }
    for (const [id, label] of next) labels.set(id, label);
  }
  return labels;
}

function connectedComponents(nodes, adjacency) {
  const components = [];
  const componentByNode = new Map();
  const unvisited = new Set(nodes.map(node => node.id));

  while (unvisited.size) {
    const seed = [...unvisited].sort()[0];
    const stack = [seed];
    const members = [];
    unvisited.delete(seed);
    while (stack.length) {
      const current = stack.pop();
      members.push(current);
      for (const neighbor of adjacency.get(current) ?? []) {
        if (unvisited.delete(neighbor)) stack.push(neighbor);
      }
    }
    members.sort();
    components.push(members);
  }

  components.sort((a, b) => b.length - a.length || a[0].localeCompare(b[0]));
  components.forEach((members, rank) => {
    const key = members[0] ?? `component.${rank}`;
    for (const id of members) {
      componentByNode.set(id, { rank, size: members.length, key });
    }
  });
  return { components, componentByNode };
}

export function enrichGraphModel(rawNodes, edges) {
  const adjacency = new Map(rawNodes.map(node => [node.id, new Set()]));
  const projectedAdjacency = new Map(rawNodes.map(node => [node.id, new Set()]));
  const degree = new Map(rawNodes.map(node => [node.id, 0]));
  const structuralDegree = new Map(rawNodes.map(node => [node.id, 0]));
  const incident = new Map(rawNodes.map(node => [node.id, []]));
  const structuralIncident = new Map(rawNodes.map(node => [node.id, []]));

  for (const edge of edges) {
    projectedAdjacency.get(edge.sourceId)?.add(edge.targetId);
    projectedAdjacency.get(edge.targetId)?.add(edge.sourceId);
    degree.set(edge.sourceId, (degree.get(edge.sourceId) ?? 0) + 1);
    degree.set(edge.targetId, (degree.get(edge.targetId) ?? 0) + 1);
    incident.get(edge.sourceId)?.push(edge);
    incident.get(edge.targetId)?.push(edge);
    if (!isStructuralAtlasEdge(edge)) continue;
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
    structuralDegree.set(edge.sourceId, (structuralDegree.get(edge.sourceId) ?? 0) + 1);
    structuralDegree.set(edge.targetId, (structuralDegree.get(edge.targetId) ?? 0) + 1);
    structuralIncident.get(edge.sourceId)?.push(edge);
    structuralIncident.get(edge.targetId)?.push(edge);
  }

  const maxDegree = Math.max(1, ...structuralDegree.values());
  const structuralEdges = edges.filter(isStructuralAtlasEdge);
  const maxSupport = Math.max(
    1,
    ...structuralEdges.map(edge => Math.max(0, finiteNumber(edge.support, 0))),
  );
  const maxStable = Math.max(
    1,
    ...structuralEdges.map(edge => Math.max(0, finiteNumber(edge.stableTicks, 0))),
  );
  const communities = deriveLocalCommunities(rawNodes, adjacency);

  // Keep projected connectivity separate from persistent structural
  // connectivity. Overlay-only causal/evidence relations may form a visible
  // component without making the participating nodes structural peers.
  const {
    components,
    componentByNode,
  } = connectedComponents(rawNodes, projectedAdjacency);
  const {
    components: structuralComponents,
    componentByNode: structuralComponentByNode,
  } = connectedComponents(rawNodes, adjacency);

  const rawNodeById = new Map(rawNodes.map(node => [node.id, node]));
  const projectedHostFor = new Map();
  for (const node of rawNodes) {
    const nodeStructuralDegree = structuralDegree.get(node.id) ?? 0;
    const nodeDegree = degree.get(node.id) ?? 0;
    if (nodeStructuralDegree > 0 || nodeDegree === 0) continue;

    const candidates = [...(projectedAdjacency.get(node.id) ?? [])]
      .map(id => ({
        id,
        node: rawNodeById.get(id),
        structuralDegree: structuralDegree.get(id) ?? 0,
        degree: degree.get(id) ?? 0,
      }))
      .filter(item => item.node)
      .sort((a, b) =>
        b.structuralDegree - a.structuralDegree ||
        b.degree - a.degree ||
        String(a.id).localeCompare(String(b.id))
      );
    if (candidates.length) projectedHostFor.set(node.id, candidates[0].id);
  }

  const nodes = rawNodes.map(node => {
    const degreeNorm = (structuralDegree.get(node.id) ?? 0) / maxDegree;
    const incidentEdges = structuralIncident.get(node.id) ?? [];
    const supportNorm = incidentEdges.length
      ? Math.max(...incidentEdges.map(edge => Math.log1p(Math.max(0, finiteNumber(edge.support, 0))) / Math.log1p(maxSupport)))
      : 0;
    const stabilityNorm = incidentEdges.length
      ? Math.max(...incidentEdges.map(edge => Math.max(0, finiteNumber(edge.stableTicks, 0)) / maxStable))
      : 0;
    const lastUseTick = incidentEdges.length
      ? Math.max(...incidentEdges.map(edge => finiteNumber(edge.lastUseTick, 0)))
      : 0;

    // Size is stable structural importance. Current activation is deliberately
    // excluded here and represented by glow in the renderer.
    const structuralImportance = clamp01(
      degreeNorm * 0.45 +
      supportNorm * 0.35 +
      stabilityNorm * 0.20
    );
    const radius = node.baseRadius
      + Math.sqrt(structuralImportance) * 7.0
      + degreeNorm * 1.8;

    const component = componentByNode.get(node.id) ?? {
      rank: components.length,
      size: 1,
      key: node.id,
    };
    const structuralComponent = structuralComponentByNode.get(node.id) ?? {
      rank: structuralComponents.length,
      size: 1,
      key: node.id,
    };
    const nodeDegree = degree.get(node.id) ?? 0;
    const nodeStructuralDegree = structuralDegree.get(node.id) ?? 0;
    const overlayOnly = nodeStructuralDegree === 0 && nodeDegree > 0;
    const fringeStructural = (
      nodeStructuralDegree > 0 &&
      (nodeStructuralDegree <= 1 || structuralComponent.size <= 3)
    );
    const satelliteHostId = overlayOnly ? (projectedHostFor.get(node.id) ?? null) : null;
    const satelliteHasStructuralHost = satelliteHostId
      ? (structuralDegree.get(satelliteHostId) ?? 0) > 0
      : false;
    return {
      ...node,
      radius,
      degree: nodeDegree,
      structuralDegree: nodeStructuralDegree,
      degreeNorm,
      structuralImportance,
      visualValue: structuralImportance,
      lastUseTick,
      componentRank: component.rank,
      componentSize: component.size,
      componentKey: component.key,
      structuralComponentRank: structuralComponent.rank,
      structuralComponentSize: structuralComponent.size,
      structuralComponentKey: structuralComponent.key,
      isolated: component.size === 1 && nodeDegree === 0,
      structurallyDisconnected: nodeStructuralDegree === 0,
      overlayOnly,
      fringeStructural,
      satelliteHostId,
      satelliteHasStructuralHost,
      community: communities.get(node.id) ?? null,
    };
  });

  return {
    nodes,
    edges,
    adjacency,
    projectedAdjacency,
    communities,
    components,
    componentByNode,
    structuralComponents,
    structuralComponentByNode,
  };
}
