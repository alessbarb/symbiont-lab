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

export function enrichGraphModel(rawNodes, edges) {
  const adjacency = new Map(rawNodes.map(node => [node.id, new Set()]));
  const degree = new Map(rawNodes.map(node => [node.id, 0]));
  const incident = new Map(rawNodes.map(node => [node.id, []]));

  for (const edge of edges) {
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
    degree.set(edge.sourceId, (degree.get(edge.sourceId) ?? 0) + 1);
    degree.set(edge.targetId, (degree.get(edge.targetId) ?? 0) + 1);
    incident.get(edge.sourceId)?.push(edge);
    incident.get(edge.targetId)?.push(edge);
  }

  const maxDegree = Math.max(1, ...degree.values());
  const maxSupport = Math.max(
    1,
    ...edges.map(edge => Math.max(0, finiteNumber(edge.support, 0))),
  );
  const maxStable = Math.max(
    1,
    ...edges.map(edge => Math.max(0, finiteNumber(edge.stableTicks, 0))),
  );
  const communities = deriveLocalCommunities(rawNodes, adjacency);

  // Connected components are objective graph structure, unlike the local
  // observer-side communities used only for layout.
  const components = [];
  const componentByNode = new Map();
  const unvisited = new Set(rawNodes.map(node => node.id));
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
    for (const id of members) componentByNode.set(id, { rank, size: members.length });
  });

  const nodes = rawNodes.map(node => {
    const degreeNorm = (degree.get(node.id) ?? 0) / maxDegree;
    const incidentEdges = incident.get(node.id) ?? [];
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

    const component = componentByNode.get(node.id) ?? { rank: components.length, size: 1 };
    return {
      ...node,
      radius,
      degree: degree.get(node.id) ?? 0,
      degreeNorm,
      structuralImportance,
      visualValue: structuralImportance,
      lastUseTick,
      componentRank: component.rank,
      componentSize: component.size,
      isolated: component.size === 1 && (degree.get(node.id) ?? 0) === 0,
      community: communities.get(node.id) ?? null,
    };
  });

  return { nodes, edges, adjacency, communities, components, componentByNode };
}
