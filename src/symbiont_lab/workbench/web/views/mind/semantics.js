/**
 * Dual-semantic presentation helpers.
 *
 * Organism-owned labels and observer ground truth remain separate by design.
 */

export function sensorySemantic(observerSemantics, selfLabel) {
  const sensory = observerSemantics?.sensory ?? {};
  return sensory?.[selfLabel] ?? null;
}

export function observerContextForNode(
  topology,
  observerSemantics,
  nodeId,
  depth = 2,
  limit = 4,
) {
  const direct = sensorySemantic(observerSemantics, nodeId);
  if (direct?.observerSummary) {
    return {
      kind: 'exact-source',
      summary: direct.observerSummary,
      labels: direct.observerLabels ?? [direct.observerSummary],
      distance: 0,
    };
  }

  const graph = topology ?? { nodes: [], edges: [] };
  const adjacency = new Map();
  for (const node of graph.nodes ?? []) adjacency.set(node.id, new Set());
  for (const edge of graph.edges ?? []) {
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
  }

  const visited = new Set([nodeId]);
  let frontier = new Set([nodeId]);
  const matches = [];

  for (let step = 1; step <= depth; step++) {
    const next = new Set();
    for (const id of frontier) {
      for (const neighbor of adjacency.get(id) ?? []) {
        if (visited.has(neighbor)) continue;
        visited.add(neighbor);
        next.add(neighbor);
        const semantic = sensorySemantic(observerSemantics, neighbor);
        if (semantic?.observerSummary) {
          matches.push({
            id: neighbor,
            label: semantic.observerSummary,
            distance: step,
          });
        }
      }
    }
    if (matches.length) break;
    frontier = next;
    if (!frontier.size) break;
  }

  if (!matches.length) {
    return {
      kind: 'unresolved',
      summary: null,
      labels: [],
      distance: null,
    };
  }

  const unique = [];
  const seen = new Set();
  for (const match of matches) {
    if (seen.has(match.label)) continue;
    seen.add(match.label);
    unique.push(match.label);
    if (unique.length >= limit) break;
  }

  return {
    kind: 'sensory-context',
    summary: unique.join(' + '),
    labels: unique,
    distance: matches[0].distance,
  };
}

export function compactSelfLabel(value, head = 8, tail = 5) {
  const text = String(value ?? '');
  if (text.length <= head + tail + 1) return text;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}
