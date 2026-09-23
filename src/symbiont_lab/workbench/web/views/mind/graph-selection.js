/**
 * Pure graph selection helpers for the Mind cognition view.
 *
 * These functions operate only on observer-side graph data.
 */

export function graphSubgraphIds(topology, focusId, depth = 2) {
  if (!focusId) return null;
  const graph = topology ?? { nodes: [], edges: [] };
  const adjacency = new Map();
  for (const node of graph.nodes ?? []) adjacency.set(node.id, new Set());
  for (const edge of graph.edges ?? []) {
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
  }
  const visited = new Set([focusId]);
  let frontier = new Set([focusId]);
  for (let step = 0; step < depth; step++) {
    const next = new Set();
    for (const id of frontier) {
      for (const neighbor of adjacency.get(id) ?? []) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          next.add(neighbor);
        }
      }
    }
    frontier = next;
    if (!frontier.size) break;
  }
  return visited;
}

export function filterGraphForView(nodes, edges, viewMode) {
  const degree = new Map(nodes.map(node => [node.id, 0]));
  for (const edge of edges) {
    degree.set(edge.sourceId, (degree.get(edge.sourceId) ?? 0) + 1);
    degree.set(edge.targetId, (degree.get(edge.targetId) ?? 0) + 1);
  }

  let visible = nodes;
  if (viewMode === 'connected') {
    visible = nodes.filter(node => (degree.get(node.id) ?? 0) > 0);
  } else if (viewMode === 'core') {
    visible = nodes.filter(node => node.kind !== 'sense' && (degree.get(node.id) ?? 0) > 0);
  }

  const keep = new Set(visible.map(node => node.id));
  return {
    nodes: visible,
    edges: edges.filter(edge => keep.has(edge.sourceId) && keep.has(edge.targetId)),
  };
}
