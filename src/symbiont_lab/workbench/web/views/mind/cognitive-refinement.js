/**
 * Final Cognitive Observatory refinements.
 *
 * Presentation/observer-only helpers: label priority, diff/episode impact and
 * in-session usage telemetry. Nothing here is fed back into Symbiont.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

export function labelPriority(node, {
  selectedNodeId = null,
  hoveredNodeId = null,
  focusedSectorId = null,
  pathNodeIds = new Set(),
  hubIds = new Set(),
  atlasMode = 'structure',
} = {}) {
  if (!node) return 0;
  if (node.id === selectedNodeId) return 100;
  if (node.id === hoveredNodeId) return 95;
  if (pathNodeIds.has(node.id)) return 90;
  if (focusedSectorId && node.community === focusedSectorId) {
    if (node.kind === 'readout' || node.kind === 'motor_primitive') return 84;
    if (hubIds.has(node.id)) return 82;
    return 58;
  }
  if (node.kind === 'readout' || node.kind === 'motor_primitive') return 74;
  if (hubIds.has(node.id)) return 68;
  if (atlasMode === 'prediction' && node.kind === 'predictor') return 66;
  if (atlasMode === 'learning' && finite(node.atlasScore, 0) >= 0.65) return 64;
  return 20 + clamp01(node.structuralImportance ?? node.visualValue) * 30;
}

export function labelBudget(detailLevel, focused = false) {
  if (focused) return 12;
  if (detailLevel === 'regions') return 0;
  if (detailLevel === 'meso') return 7;
  return 11;
}

export function prioritizedLabelIds(nodes, context = {}) {
  const budget = labelBudget(context.detailLevel, Boolean(context.focusedSectorId));
  if (budget <= 0) return new Set();
  return new Set(
    [...nodes]
      .map(node => ({ id: node.id, score: labelPriority(node, context) }))
      .filter(item => item.score >= 52)
      .sort((a,b) => b.score - a.score || a.id.localeCompare(b.id))
      .slice(0, budget)
      .map(item => item.id)
  );
}

function edgeMagnitude(item) {
  return (
    Math.abs(finite(item?.deltaWeight)) * 0.45 +
    Math.min(1, Math.abs(finite(item?.deltaSupport)) / 8) * 0.35 +
    Math.abs(finite(item?.deltaPlasticity)) * 0.20
  );
}

export function summarizeDiff(diff, nodes = [], regions = []) {
  if (!diff) return null;
  const nodeImpact = new Map();
  const bump = (id, amount) => {
    if (!id) return;
    nodeImpact.set(id, (nodeImpact.get(id) ?? 0) + amount);
  };
  for (const id of diff.addedNodes ?? []) bump(id, 1);
  for (const id of diff.removedNodes ?? []) bump(id, 0.9);
  for (const key of diff.addedEdges ?? []) {
    const [a,b] = key.split('|'); bump(a, 0.6); bump(b, 0.6);
  }
  for (const key of diff.removedEdges ?? []) {
    const [a,b] = key.split('|'); bump(a, 0.55); bump(b, 0.55);
  }
  for (const item of diff.changedEdges ?? []) {
    const [a,b] = item.key.split('|');
    const m = 0.25 + edgeMagnitude(item);
    bump(a,m); bump(b,m);
  }
  for (const item of diff.predictionErrorChanges ?? []) bump(item.id, 0.75);

  const nodeById = new Map(nodes.map(node => [node.id,node]));
  const topNodeEntry = [...nodeImpact.entries()]
    .sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0] ?? null;
  const topNode = topNodeEntry ? nodeById.get(topNodeEntry[0]) ?? { id: topNodeEntry[0] } : null;

  const regionScores = new Map();
  for (const [id,score] of nodeImpact.entries()) {
    const community = nodeById.get(id)?.community;
    if (!community || community === 'isolated') continue;
    regionScores.set(community, (regionScores.get(community) ?? 0) + score);
  }
  const topRegionEntry = [...regionScores.entries()]
    .sort((a,b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))[0] ?? null;
  const topRegion = topRegionEntry
    ? regions.find(region => region.id === topRegionEntry[0]) ?? { id: topRegionEntry[0] }
    : null;

  const motorEdgeChanged = [
    ...(diff.addedEdges ?? []),
    ...(diff.removedEdges ?? []),
    ...(diff.changedEdges ?? []).map(item => item.key),
  ].some(key =>
    String(key).includes('readout_motor:') ||
    String(key).includes('readout_primitive:') ||
    String(key).includes('motor_primitive:')
  );

  const categories = [
    ['nodes', (diff.addedNodes?.length ?? 0) + (diff.removedNodes?.length ?? 0)],
    ['relations', (diff.addedEdges?.length ?? 0) + (diff.removedEdges?.length ?? 0) + (diff.changedEdges?.length ?? 0)],
    ['prediction', diff.predictionErrorChanges?.length ?? 0],
  ].sort((a,b) => b[1] - a[1]);

  return {
    topNode,
    topRegion,
    largestDeltaType: categories[0]?.[1] ? categories[0][0] : 'none',
    motorLinkageChanged: motorEdgeChanged,
    nodeImpact,
  };
}

export function episodeImpact(episode) {
  const t = episode?.totals ?? {};
  const structural =
    (t.addedNodes ?? 0) * 2 +
    (t.removedNodes ?? 0) * 2 +
    (t.addedEdges ?? 0) * 0.45 +
    (t.removedEdges ?? 0) * 0.45 +
    (t.changedEdges ?? 0) * 0.16;
  const predictive =
    (t.predictionErrorChanges ?? 0) * 0.4 +
    (t.predictionShifts ?? 0) * 2.5;
  const transitions =
    (t.motorTransitions ?? 0) * 4 +
    (t.physiologyTransitions ?? 0) * 3;
  const raw = structural + predictive + transitions;
  const score = clamp01(raw / 40);
  return {
    score,
    label: score >= 0.75 ? 'high' : score >= 0.38 ? 'medium' : 'low',
    dominant: [
      ['structural', structural],
      ['prediction', predictive],
      ['transitions', transitions],
    ].sort((a,b) => b[1] - a[1])[0][0],
  };
}

export function createObserverUsage() {
  return {
    startedAt: Date.now(),
    modeChanges: {},
    dimensionChanges: {},
    selections: 0,
    regionFocuses: 0,
    timelineScrubs: 0,
    diffUses: 0,
    flowTraces: 0,
    lastMode: null,
  };
}

export function recordObserverUsage(usage, event, value = null) {
  if (!usage) return;
  if (event === 'mode') {
    usage.modeChanges[value] = (usage.modeChanges[value] ?? 0) + 1;
    usage.lastMode = value;
  } else if (event === 'dimension') {
    usage.dimensionChanges[value] = (usage.dimensionChanges[value] ?? 0) + 1;
  } else if (event === 'selection') usage.selections += 1;
  else if (event === 'region-focus') usage.regionFocuses += 1;
  else if (event === 'timeline') usage.timelineScrubs += 1;
  else if (event === 'diff') usage.diffUses += 1;
  else if (event === 'flow-trace') usage.flowTraces += 1;
}
