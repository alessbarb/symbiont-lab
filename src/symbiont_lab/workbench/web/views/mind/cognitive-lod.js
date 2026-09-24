/**
 * Multiscale observer projection for the Cognitive Atlas.
 *
 * This module decides presentation detail only. It never changes graph data and
 * never feeds observer-derived regions or frontier clusters back to Symbiont.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

export function atlasDetailLevel({
  dimension = '2d',
  scale = 1,
  cameraDistance = 900,
  focusedRegion = false,
  previousLevel = 'meso',
} = {}) {
  if (focusedRegion) return 'nodes';

  if (dimension === '3d') {
    if (previousLevel === 'regions') {
      if (cameraDistance > 1120) return 'regions';
    } else if (cameraDistance > 1320) {
      return 'regions';
    }

    if (previousLevel === 'nodes') {
      if (cameraDistance < 760) return 'nodes';
    } else if (cameraDistance < 590) {
      return 'nodes';
    }
    return 'meso';
  }

  if (previousLevel === 'regions') {
    if (scale < 0.82) return 'regions';
  } else if (scale < 0.64) {
    return 'regions';
  }

  if (previousLevel === 'nodes') {
    if (scale > 1.38) return 'nodes';
  } else if (scale > 1.72) {
    return 'nodes';
  }
  return 'meso';
}

function regionMembers(nodes) {
  const groups = new Map();
  for (const node of nodes) {
    if (!node.community || node.community === 'isolated') continue;
    if (!groups.has(node.community)) groups.set(node.community, []);
    groups.get(node.community).push(node);
  }
  return groups;
}

export function atlasVisibleNodeIds(
  nodes,
  detailLevel,
  {
    selectedNodeId = null,
    pathNodeIds = [],
    hubIds = [],
    bottleneckIds = [],
  } = {},
) {
  if (detailLevel === 'nodes') return new Set(nodes.map(node => node.id));

  const forced = new Set([
    selectedNodeId,
    ...pathNodeIds,
    ...hubIds,
    ...bottleneckIds,
  ].filter(Boolean));

  if (detailLevel === 'regions') return forced;

  const visible = new Set(forced);
  const groups = regionMembers(nodes);
  for (const members of groups.values()) {
    const ranked = [...members].sort((a,b) =>
      finite(b.atlasScore, 0) - finite(a.atlasScore, 0) ||
      finite(b.structuralImportance, 0) - finite(a.structuralImportance, 0) ||
      String(a.id).localeCompare(String(b.id))
    );
    const keep = Math.max(3, Math.ceil(ranked.length * 0.34));
    for (const node of ranked.slice(0, keep)) visible.add(node.id);
  }

  for (const node of nodes) {
    if (node.kind === 'readout' || node.kind === 'motor_primitive') visible.add(node.id);
  }
  return visible;
}

export function atlasRegionLinks(nodes, edges) {
  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const grouped = new Map();
  for (const edge of edges) {
    const source = nodeById.get(edge.sourceId);
    const target = nodeById.get(edge.targetId);
    const a = source?.community;
    const b = target?.community;
    if (!a || !b || a === 'isolated' || b === 'isolated' || a === b) continue;
    const key = [a,b].sort().join('|');
    const item = grouped.get(key) ?? {
      key,
      a,
      b,
      count: 0,
      support: 0,
      stableTicks: 0,
      lastUseTick: 0,
      kinds: {},
    };
    item.count += 1;
    item.support += Math.max(0, finite(edge.support, 0));
    item.stableTicks += Math.max(0, finite(edge.stableTicks, 0));
    item.lastUseTick = Math.max(item.lastUseTick, finite(edge.lastUseTick, 0));
    item.kinds[edge.kind ?? 'edge'] = (item.kinds[edge.kind ?? 'edge'] ?? 0) + 1;
    grouped.set(key, item);
  }
  return [...grouped.values()].sort((x,y) => y.count - x.count || x.key.localeCompare(y.key));
}

export function learningFrontierClusters(
  nodes,
  edges,
  signals,
  threshold = 0.30,
) {
  const frontierIds = new Set(
    nodes
      .filter(node => finite(signals.get(node.id)?.learning, 0) >= threshold)
      .map(node => node.id)
  );
  if (!frontierIds.size) return [];

  const adjacency = new Map([...frontierIds].map(id => [id, new Set()]));
  const boundary = new Map([...frontierIds].map(id => [id, new Set()]));
  for (const edge of edges) {
    const sourceIn = frontierIds.has(edge.sourceId);
    const targetIn = frontierIds.has(edge.targetId);
    if (sourceIn && targetIn) {
      adjacency.get(edge.sourceId)?.add(edge.targetId);
      adjacency.get(edge.targetId)?.add(edge.sourceId);
    } else if (sourceIn) {
      boundary.get(edge.sourceId)?.add(edge.targetId);
    } else if (targetIn) {
      boundary.get(edge.targetId)?.add(edge.sourceId);
    }
  }

  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const unvisited = new Set(frontierIds);
  const clusters = [];
  while (unvisited.size) {
    const seed = [...unvisited].sort()[0];
    const stack = [seed];
    const ids = [];
    unvisited.delete(seed);
    while (stack.length) {
      const id = stack.pop();
      ids.push(id);
      for (const next of adjacency.get(id) ?? []) {
        if (unvisited.delete(next)) stack.push(next);
      }
    }
    ids.sort();
    const scores = ids.map(id => finite(signals.get(id)?.learning, 0));
    const boundaryIds = new Set();
    for (const id of ids) {
      for (const outside of boundary.get(id) ?? []) boundaryIds.add(outside);
    }
    const communities = [...new Set(
      ids.map(id => nodeById.get(id)?.community).filter(value => value && value !== 'isolated')
    )];
    clusters.push({
      id: `frontier:${ids[0]}`,
      nodeIds: ids,
      boundaryIds: [...boundaryIds].sort(),
      communities,
      meanScore: mean(scores),
      maxScore: Math.max(...scores),
    });
  }

  return clusters.sort((a,b) =>
    b.maxScore - a.maxScore ||
    b.nodeIds.length - a.nodeIds.length ||
    a.id.localeCompare(b.id)
  );
}

export function reconcileFrontierEvolution(currentClusters, previousClusters = []) {
  const previous = previousClusters ?? [];
  return (currentClusters ?? []).map(cluster => {
    let best = null;
    let bestScore = 0;
    const current = new Set(cluster.nodeIds ?? []);
    for (const prior of previous) {
      const old = new Set(prior.nodeIds ?? []);
      if (!current.size || !old.size) continue;
      let shared = 0;
      for (const id of current) if (old.has(id)) shared += 1;
      const union = current.size + old.size - shared;
      const score = union ? shared / union : 0;
      if (score > bestScore) {
        best = prior;
        bestScore = score;
      }
    }
    const priorIds = new Set(best?.nodeIds ?? []);
    const enteredIds = [...current].filter(id => !priorIds.has(id)).sort();
    const exitedIds = [...priorIds].filter(id => !current.has(id)).sort();
    return {
      ...cluster,
      lineageId: bestScore >= 0.28
        ? (best?.lineageId ?? best?.id ?? cluster.id)
        : cluster.id,
      observations: bestScore >= 0.28 ? (best?.observations ?? 0) + 1 : 1,
      enteredIds,
      exitedIds,
      previousOverlap: bestScore,
    };
  });
}
