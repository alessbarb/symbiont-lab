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

  for (const edge of edges) {
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
    degree.set(edge.sourceId, (degree.get(edge.sourceId) ?? 0) + 1);
    degree.set(edge.targetId, (degree.get(edge.targetId) ?? 0) + 1);
  }

  const maxDegree = Math.max(1, ...degree.values());
  const communities = deriveLocalCommunities(rawNodes, adjacency);

  const nodes = rawNodes.map(node => {
    const degreeNorm = (degree.get(node.id) ?? 0) / maxDegree;
    const visualValue = Math.max(
      clamp01(node.activationLevel ?? 0),
      clamp01(node.readoutMagnitude ?? 0),
      Math.min(0.55, degreeNorm * 0.55),
    );
    const radius = node.baseRadius
      + Math.sqrt(visualValue) * 6.0
      + degreeNorm * 2.2;

    return {
      ...node,
      radius,
      degree: degree.get(node.id) ?? 0,
      degreeNorm,
      visualValue,
      community: communities.get(node.id) ?? null,
    };
  });

  return { nodes, edges, adjacency, communities };
}
