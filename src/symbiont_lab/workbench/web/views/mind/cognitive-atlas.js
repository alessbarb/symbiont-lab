/**
 * Observer-side Cognitive Atlas analytics.
 *
 * This module derives presentation-only regions, scientific view scores and
 * exact graph paths from the organism-owned cognitive graph. Nothing here is
 * fed back into Symbiont.
 */

export const ATLAS_MODES = Object.freeze([
  { id: 'structure', label: 'Structure', description: 'Stable organisation and structural importance' },
  { id: 'activity', label: 'Activity', description: 'Current activation and recent use' },
  { id: 'learning', label: 'Learning', description: 'Plasticity, instability and prediction error' },
  { id: 'prediction', label: 'Prediction', description: 'Predictive/state processing and error' },
  { id: 'motor', label: 'Motor', description: 'Cognitive routes reaching learned motor primitives' },
  { id: 'evidence', label: 'Evidence', description: 'Support, stability and learned relation strength' },
  { id: 'diff', label: 'Diff', description: 'Changes against the selected temporal baseline' },
]);

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function errorScore(value) {
  if (Number.isFinite(Number(value))) return clamp01(Number(value) / 15);
  const cls = String(value ?? '').toLowerCase();
  if (cls === 'extreme') return 1;
  if (cls === 'high') return 0.78;
  if (cls === 'medium') return 0.5;
  if (cls === 'low') return 0.24;
  return 0;
}

function edgeEvidence(edge, maxima) {
  const support = Math.log1p(Math.max(0, finite(edge.support, 0))) / maxima.support;
  const stable = Math.log1p(Math.max(0, finite(edge.stableTicks, 0))) / maxima.stable;
  const weight = Math.min(1, Math.abs(finite(edge.weight, 0)));
  return clamp01(support * 0.45 + stable * 0.35 + weight * 0.20);
}

function edgeRecency(edge, tick) {
  const lastUse = finite(edge.lastUseTick, 0);
  if (lastUse <= 0 || tick <= 0) return 0;
  return Math.exp(-Math.max(0, tick - lastUse) / 512);
}

export function atlasSignals(nodes, edges, tick = 0) {
  const incident = new Map(nodes.map(node => [node.id, []]));
  for (const edge of edges) {
    incident.get(edge.sourceId)?.push(edge);
    incident.get(edge.targetId)?.push(edge);
  }

  const maxima = {
    support: Math.max(1, ...edges.map(edge => Math.log1p(Math.max(0, finite(edge.support, 0))))),
    stable: Math.max(1, ...edges.map(edge => Math.log1p(Math.max(0, finite(edge.stableTicks, 0))))),
  };

  const signals = new Map();
  for (const node of nodes) {
    const related = incident.get(node.id) ?? [];
    const evidence = related.length
      ? Math.max(...related.map(edge => edgeEvidence(edge, maxima)))
      : 0;
    const recency = related.length
      ? Math.max(...related.map(edge => edgeRecency(edge, tick)))
      : 0;
    const plasticity = related.length
      ? Math.max(...related.map(edge => clamp01(edge.plasticity)))
      : 0;
    const stability = related.length
      ? Math.max(...related.map(edge =>
          Math.log1p(Math.max(0, finite(edge.stableTicks, 0))) / maxima.stable
        ))
      : 0;
    const error = errorScore(node.errorCls);
    const activity = clamp01(finite(node.activationLevel, 0) * 0.78 + recency * 0.22);
    const learning = clamp01(
      plasticity * 0.48 +
      (1 - stability) * Math.min(1, related.length ? 0.30 : 0) +
      error * 0.22
    );
    const prediction = clamp01(
      (node.kind === 'predictor' || node.kind === 'state' ? 0.62 : 0) +
      error * 0.38
    );
    const motor = clamp01(
      (node.kind === 'motor_primitive' ? 0.82 : 0) +
      (node.kind === 'readout' && (
        String(node.id).startsWith('readout_motor:') ||
        String(node.id).startsWith('readout_primitive:')
      ) ? 0.72 : 0) +
      (node.cognitivePrimitive ? 0.18 : 0)
    );

    signals.set(node.id, {
      structure: clamp01(finite(node.structuralImportance ?? node.visualValue, 0)),
      activity,
      learning,
      prediction,
      motor,
      evidence,
      error,
      recency,
      plasticity,
      stability,
    });
  }
  return signals;
}

export function atlasModeScore(node, signals, mode = 'structure') {
  return clamp01(signals.get(node.id)?.[mode] ?? 0);
}

export function atlasEdgeScore(edge, mode, tick = 0) {
  if (mode === 'activity') return edgeRecency(edge, tick);
  if (mode === 'learning') {
    const stability = Math.log1p(Math.max(0, finite(edge.stableTicks, 0)));
    const support = Math.log1p(Math.max(0, finite(edge.support, 0)));
    const instability = 1 / (1 + stability);
    return clamp01(clamp01(edge.plasticity) * 0.65 + instability * 0.25 + Math.min(1, support / 8) * 0.10);
  }
  if (mode === 'prediction') return edge.kind === 'predictive' ? 1 : edge.kind === 'gating' ? 0.45 : 0.08;
  if (mode === 'motor') return edge.kind === 'invokes' ? 1 : 0.06;
  if (mode === 'diff') return 0;
  if (mode === 'evidence') {
    const support = Math.min(1, Math.log1p(Math.max(0, finite(edge.support, 0))) / 8);
    const stable = Math.min(1, Math.log1p(Math.max(0, finite(edge.stableTicks, 0))) / 9);
    return clamp01(support * 0.55 + stable * 0.45);
  }
  return clamp01(Math.abs(finite(edge.weight, 0)) * 0.35 + Math.min(1, Math.log1p(Math.max(0, finite(edge.support, 0))) / 8) * 0.65);
}

export function atlasRegions(nodes, edges, sectorLabels, sectorDescriptions, signals) {
  const grouped = new Map();
  for (const node of nodes) {
    if (!node.community || node.community === 'isolated') continue;
    const item = grouped.get(node.community) ?? {
      id: node.community,
      nodeIds: [],
      kinds: {},
      structure: 0,
      activity: 0,
      learning: 0,
      prediction: 0,
      motor: 0,
      evidence: 0,
      bridges: 0,
    };
    item.nodeIds.push(node.id);
    item.kinds[node.kind] = (item.kinds[node.kind] ?? 0) + 1;
    const s = signals.get(node.id) ?? {};
    for (const key of ['structure','activity','learning','prediction','motor','evidence']) {
      item[key] += finite(s[key], 0);
    }
    grouped.set(node.community, item);
  }

  for (const edge of edges) {
    const source = nodes.find(node => node.id === edge.sourceId);
    const target = nodes.find(node => node.id === edge.targetId);
    if (!source?.community || !target?.community || source.community === target.community) continue;
    grouped.get(source.community) && (grouped.get(source.community).bridges += 1);
    grouped.get(target.community) && (grouped.get(target.community).bridges += 1);
  }

  return [...grouped.values()].map(region => {
    const n = Math.max(1, region.nodeIds.length);
    for (const key of ['structure','activity','learning','prediction','motor','evidence']) {
      region[key] /= n;
    }
    const description = sectorDescriptions.get(region.id) ?? null;
    return {
      ...region,
      label: sectorLabels.get(region.id) ?? 'S-???',
      interpretation: description?.interpretation ?? 'Mixed integration',
      total: region.nodeIds.length,
    };
  }).sort((a,b) => b.total - a.total || a.label.localeCompare(b.label));
}

function adjacencyFor(edges, reverse = false) {
  const adjacency = new Map();
  for (const edge of edges) {
    const from = reverse ? edge.targetId : edge.sourceId;
    const to = reverse ? edge.sourceId : edge.targetId;
    if (!adjacency.has(from)) adjacency.set(from, []);
    adjacency.get(from).push({ id: to, edge });
  }
  return adjacency;
}

function bfsPath(startId, targetPredicate, nodesById, edges, reverse = false, maxDepth = 10) {
  const adjacency = adjacencyFor(edges, reverse);
  const queue = [{ id: startId, path: [startId], edgePath: [] }];
  const visited = new Set([startId]);
  while (queue.length) {
    const current = queue.shift();
    if (current.id !== startId && targetPredicate(nodesById.get(current.id))) {
      return {
        nodeIds: reverse ? [...current.path].reverse() : current.path,
        edges: reverse ? [...current.edgePath].reverse() : current.edgePath,
      };
    }
    if (current.path.length > maxDepth) continue;
    for (const next of adjacency.get(current.id) ?? []) {
      if (visited.has(next.id)) continue;
      visited.add(next.id);
      queue.push({
        id: next.id,
        path: [...current.path, next.id],
        edgePath: [...current.edgePath, next.edge],
      });
    }
  }
  return null;
}

export function cognitivePath(startId, nodes, edges, maxDepth = 10) {
  if (!startId) return null;
  const nodesById = new Map(nodes.map(node => [node.id, node]));
  const start = nodesById.get(startId);
  if (!start) return null;

  const motorTarget = node => node?.kind === 'motor_primitive' || (
    node?.kind === 'readout' && (
      String(node.id).startsWith('readout_motor:') ||
      String(node.id).startsWith('readout_primitive:')
    )
  );
  const sensoryTarget = node => node?.kind === 'sense';

  if (motorTarget(start)) {
    return bfsPath(startId, sensoryTarget, nodesById, edges, true, maxDepth);
  }

  const downstream = bfsPath(startId, motorTarget, nodesById, edges, false, maxDepth);
  if (downstream) return downstream;

  const upstream = bfsPath(startId, sensoryTarget, nodesById, edges, true, maxDepth);
  return upstream;
}

export function learningFrontier(nodes, signals, limit = 8) {
  return [...nodes]
    .map(node => ({ node, score: finite(signals.get(node.id)?.learning, 0) }))
    .filter(item => item.score > 0.12)
    .sort((a,b) => b.score - a.score || String(a.node.id).localeCompare(String(b.node.id)))
    .slice(0, limit);
}
