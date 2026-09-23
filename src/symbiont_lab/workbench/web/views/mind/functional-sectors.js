/**
 * Observer-side functional cartography for the Cognition Map.
 *
 * Sectors are derived from graph relationships and node composition. The
 * organism does not receive these groups or their observer interpretations.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function jaccard(a, b) {
  if (!a?.size || !b?.size) return 0;
  let shared = 0;
  const small = a.size <= b.size ? a : b;
  const large = small === a ? b : a;
  for (const value of small) if (large.has(value)) shared += 1;
  return shared / (a.size + b.size - shared);
}

function primitiveSet(node) {
  return new Set((node?.actuatorIds ?? []).map(String));
}

export function buildLayoutAffinities(nodes, edges) {
  const links = [];
  const seen = new Set();

  for (const edge of edges) {
    const key = [edge.sourceId, edge.targetId].sort().join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    links.push({
      sourceId: edge.sourceId,
      targetId: edge.targetId,
      strength:
        edge.kind === 'predictive' ? 1.35 :
        edge.kind === 'invokes' ? 1.45 :
        edge.kind === 'causal_effect' ? 1.2 :
        1,
      basis: 'structural',
    });
  }

  const primitives = nodes.filter(node => node.kind === 'motor_primitive');
  for (let i = 0; i < primitives.length; i++) {
    const a = primitives[i];
    const setA = primitiveSet(a);
    for (let j = i + 1; j < primitives.length; j++) {
      const b = primitives[j];
      const overlap = jaccard(setA, primitiveSet(b));
      if (overlap < 0.2) continue;
      const key = [a.id, b.id].sort().join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      links.push({
        sourceId: a.id,
        targetId: b.id,
        strength: 0.9 + overlap * 1.8,
        basis: 'motor-similarity',
      });
    }
  }

  return links;
}

export function deriveFunctionalSectors(nodes, affinityLinks, rounds = 6) {
  const adjacency = new Map(nodes.map(node => [node.id, []]));
  for (const link of affinityLinks) {
    adjacency.get(link.sourceId)?.push({ id: link.targetId, strength: finite(link.strength, 1) });
    adjacency.get(link.targetId)?.push({ id: link.sourceId, strength: finite(link.strength, 1) });
  }

  const labels = new Map(nodes.map(node => [node.id, node.id]));
  const ordered = [...nodes].sort((a,b) => a.id.localeCompare(b.id));

  for (let round = 0; round < rounds; round++) {
    const next = new Map(labels);
    for (const node of ordered) {
      const neighbors = adjacency.get(node.id) ?? [];
      if (!neighbors.length) {
        next.set(node.id, 'isolated');
        continue;
      }
      const scores = new Map();
      for (const neighbor of neighbors) {
        const label = labels.get(neighbor.id) ?? neighbor.id;
        scores.set(label, (scores.get(label) ?? 0) + neighbor.strength);
      }
      // Small self-retention keeps sectors stable instead of chasing one edge.
      const own = labels.get(node.id) ?? node.id;
      scores.set(own, (scores.get(own) ?? 0) + 0.35);
      let best = own;
      let bestScore = -Infinity;
      for (const [label, score] of [...scores.entries()].sort(([a],[b]) => a.localeCompare(b))) {
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

export function describeFunctionalSector(nodes) {
  const counts = new Map();
  for (const node of nodes) counts.set(node.kind, (counts.get(node.kind) ?? 0) + 1);
  const total = Math.max(1, nodes.length);
  const ratio = kind => (counts.get(kind) ?? 0) / total;

  let interpretation = 'Mixed integration';
  if (ratio('motor_primitive') >= 0.45) interpretation = 'Motor coordination';
  else if (ratio('predictor') + ratio('state') >= 0.45) interpretation = 'Prediction / state';
  else if (ratio('sense') >= 0.45) interpretation = 'Sensory integration';
  else if (ratio('readout') + ratio('gate') >= 0.35) interpretation = 'Readout / selection';
  else if (ratio('concept') >= 0.45) interpretation = 'Concept integration';

  return {
    interpretation,
    counts: Object.fromEntries([...counts.entries()].sort()),
    total: nodes.length,
    motorShare: ratio('motor_primitive'),
  };
}

export function sectorBridges(edges, sectorByNode) {
  const grouped = new Map();
  for (const edge of edges) {
    const a = sectorByNode.get(edge.sourceId);
    const b = sectorByNode.get(edge.targetId);
    if (!a || !b || a === b || a === 'isolated' || b === 'isolated') continue;
    const key = [a,b].sort().join('|');
    const item = grouped.get(key) ?? { a, b, count: 0, edges: [] };
    item.count += 1;
    item.edges.push(edge);
    grouped.set(key, item);
  }
  return [...grouped.values()].sort((x,y) => y.count - x.count);
}
