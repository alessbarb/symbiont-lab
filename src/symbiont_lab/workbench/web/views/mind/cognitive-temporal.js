/**
 * Temporal observer analytics for the Cognitive Atlas.
 *
 * Everything in this module is derived from captured observer snapshots and
 * graph evidence. It never changes organism state and never invents semantic
 * labels for the Symbiont.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function edgeKey(edge) {
  return `${edge.sourceId ?? edge.source_id}|${edge.targetId ?? edge.target_id}|${edge.kind ?? 'edge'}`;
}

function nodeId(node) {
  return String(node?.id ?? node?.node_id ?? '');
}

function topologyOf(snapshot) {
  return snapshot?.topology ?? { nodes: [], edges: [] };
}

function setOf(values) {
  return new Set(values.filter(Boolean));
}

export function jaccardSet(a, b) {
  if (!a?.size && !b?.size) return 1;
  if (!a?.size || !b?.size) return 0;
  let shared = 0;
  const small = a.size <= b.size ? a : b;
  const large = small === a ? b : a;
  for (const value of small) if (large.has(value)) shared += 1;
  return shared / Math.max(1, a.size + b.size - shared);
}

export function reconcileRegionLineage(
  currentGroups,
  previousLineage,
  tick,
  nextOrdinal = 1,
  minimumOverlap = 0.32,
) {
  const previous = new Map(previousLineage ?? []);
  const current = [...currentGroups.entries()]
    .map(([id, members]) => [id, new Set(members)])
    .sort((a,b) => b[1].size - a[1].size || String(a[0]).localeCompare(String(b[0])));

  const candidates = [];
  for (const [currentId, members] of current) {
    for (const [label, record] of previous.entries()) {
      const overlap = jaccardSet(members, record.members ?? new Set());
      if (overlap < minimumOverlap) continue;
      const previousSize = Math.max(1, record.members?.size ?? 0);
      const containment = [...members].filter(id => record.members?.has(id)).length /
        Math.max(1, Math.min(members.size, previousSize));
      candidates.push({ currentId, label, overlap, containment, score: overlap * 0.72 + containment * 0.28 });
    }
  }
  candidates.sort((a,b) => b.score - a.score || b.overlap - a.overlap || a.label.localeCompare(b.label));

  const assignedCurrent = new Set();
  const assignedLabels = new Set();
  const labels = new Map();
  for (const candidate of candidates) {
    if (assignedCurrent.has(candidate.currentId) || assignedLabels.has(candidate.label)) continue;
    labels.set(candidate.currentId, candidate.label);
    assignedCurrent.add(candidate.currentId);
    assignedLabels.add(candidate.label);
  }

  let ordinal = nextOrdinal;
  for (const [currentId] of current) {
    if (labels.has(currentId)) continue;
    labels.set(currentId, `R-${String(ordinal++).padStart(3, '0')}`);
  }

  const nextLineage = new Map();
  const events = [];
  for (const [currentId, members] of current) {
    const label = labels.get(currentId);
    const prior = previous.get(label);
    const record = {
      members,
      firstTick: prior?.firstTick ?? tick,
      lastTick: tick,
      observations: (prior?.observations ?? 0) + 1,
      previousMembers: prior?.members ?? new Set(),
    };
    nextLineage.set(label, record);
    if (!prior) {
      events.push({ type: 'region-born', label, tick, size: members.size });
    }
  }

  for (const [label, record] of previous.entries()) {
    if (!nextLineage.has(label)) {
      events.push({ type: 'region-disappeared', label, tick, size: record.members?.size ?? 0 });
    }
  }

  for (const [label, record] of previous.entries()) {
    const descendants = current
      .map(([currentId, members]) => ({
        currentId,
        label: labels.get(currentId),
        overlap: jaccardSet(record.members ?? new Set(), members),
      }))
      .filter(item => item.overlap >= minimumOverlap);
    if (descendants.length > 1) {
      events.push({
        type: 'region-split',
        label,
        tick,
        into: descendants.map(item => item.label),
      });
    }
  }

  for (const [currentId, members] of current) {
    const ancestors = [...previous.entries()]
      .map(([label, record]) => ({
        label,
        overlap: jaccardSet(record.members ?? new Set(), members),
      }))
      .filter(item => item.overlap >= minimumOverlap);
    if (ancestors.length > 1) {
      events.push({
        type: 'region-merged',
        label: labels.get(currentId),
        tick,
        from: ancestors.map(item => item.label),
      });
    }
  }

  return { labels, lineage: nextLineage, events, nextOrdinal: ordinal };
}

export function atlasSnapshotDiff(before, after) {
  const a = topologyOf(before);
  const b = topologyOf(after);
  const aNodes = new Map((a.nodes ?? []).map(node => [nodeId(node), node]));
  const bNodes = new Map((b.nodes ?? []).map(node => [nodeId(node), node]));
  const aEdges = new Map((a.edges ?? []).map(edge => [edgeKey(edge), edge]));
  const bEdges = new Map((b.edges ?? []).map(edge => [edgeKey(edge), edge]));

  const addedNodes = [...bNodes.keys()].filter(id => !aNodes.has(id));
  const removedNodes = [...aNodes.keys()].filter(id => !bNodes.has(id));
  const addedEdges = [...bEdges.keys()].filter(key => !aEdges.has(key));
  const removedEdges = [...aEdges.keys()].filter(key => !bEdges.has(key));

  const changedEdges = [];
  for (const [key, next] of bEdges.entries()) {
    const prior = aEdges.get(key);
    if (!prior) continue;
    const deltaWeight = finite(next.weight, 0) - finite(prior.weight, 0);
    const deltaSupport = finite(next.support, 0) - finite(prior.support, 0);
    const deltaPlasticity = finite(next.plasticity, 0) - finite(prior.plasticity, 0);
    if (
      Math.abs(deltaWeight) > 1e-9 ||
      Math.abs(deltaSupport) > 1e-9 ||
      Math.abs(deltaPlasticity) > 1e-9
    ) {
      changedEdges.push({ key, deltaWeight, deltaSupport, deltaPlasticity });
    }
  }

  const beforeErrors = before?.observerAnalysis?.predictionErrors ?? {};
  const afterErrors = after?.observerAnalysis?.predictionErrors ?? {};
  const predictionErrorChanges = [];
  for (const id of new Set([...Object.keys(beforeErrors), ...Object.keys(afterErrors)])) {
    if (beforeErrors[id] === afterErrors[id]) continue;
    predictionErrorChanges.push({ id, before: beforeErrors[id] ?? null, after: afterErrors[id] ?? null });
  }

  return {
    beforeTick: finite(before?.tick, 0),
    afterTick: finite(after?.tick, 0),
    addedNodes,
    removedNodes,
    addedEdges,
    removedEdges,
    changedEdges,
    predictionErrorChanges,
    changed: Boolean(
      addedNodes.length || removedNodes.length || addedEdges.length ||
      removedEdges.length || changedEdges.length || predictionErrorChanges.length
    ),
  };
}

function adjacency(nodes, edges, directed = false) {
  const map = new Map(nodes.map(node => [nodeId(node), new Set()]));
  for (const edge of edges) {
    const source = String(edge.sourceId ?? edge.source_id ?? '');
    const target = String(edge.targetId ?? edge.target_id ?? '');
    if (!map.has(source) || !map.has(target)) continue;
    map.get(source).add(target);
    if (!directed) map.get(target).add(source);
  }
  return map;
}

function articulationPoints(nodes, edges) {
  const adj = adjacency(nodes, edges, false);
  const discovery = new Map();
  const low = new Map();
  const parent = new Map();
  const result = new Set();
  let time = 0;

  function visit(id) {
    discovery.set(id, ++time);
    low.set(id, discovery.get(id));
    let children = 0;
    for (const next of adj.get(id) ?? []) {
      if (!discovery.has(next)) {
        parent.set(next, id);
        children += 1;
        visit(next);
        low.set(id, Math.min(low.get(id), low.get(next)));
        if (!parent.has(id) && children > 1) result.add(id);
        if (parent.has(id) && low.get(next) >= discovery.get(id)) result.add(id);
      } else if (next !== parent.get(id)) {
        low.set(id, Math.min(low.get(id), discovery.get(next)));
      }
    }
  }

  for (const id of adj.keys()) if (!discovery.has(id)) visit(id);
  return result;
}

function stronglyConnectedComponents(nodes, edges) {
  const ids = nodes.map(nodeId);
  const adj = adjacency(nodes, edges, true);
  let index = 0;
  const stack = [];
  const onStack = new Set();
  const indices = new Map();
  const lowlink = new Map();
  const components = [];

  function visit(id) {
    indices.set(id, index);
    lowlink.set(id, index);
    index += 1;
    stack.push(id);
    onStack.add(id);

    for (const next of adj.get(id) ?? []) {
      if (!indices.has(next)) {
        visit(next);
        lowlink.set(id, Math.min(lowlink.get(id), lowlink.get(next)));
      } else if (onStack.has(next)) {
        lowlink.set(id, Math.min(lowlink.get(id), indices.get(next)));
      }
    }

    if (lowlink.get(id) === indices.get(id)) {
      const component = [];
      while (stack.length) {
        const member = stack.pop();
        onStack.delete(member);
        component.push(member);
        if (member === id) break;
      }
      components.push(component);
    }
  }

  for (const id of ids) if (!indices.has(id)) visit(id);
  return components;
}

export function cognitiveStructures(nodes, edges) {
  const undirected = adjacency(nodes, edges, false);
  const degrees = [...undirected.entries()].map(([id, neighbors]) => ({ id, degree: neighbors.size }));
  const sorted = [...degrees].sort((a,b) => b.degree - a.degree || a.id.localeCompare(b.id));
  const hubCount = Math.max(1, Math.ceil(sorted.length * 0.08));
  const hubs = sorted.filter(item => item.degree > 1).slice(0, hubCount);
  const bottlenecks = [...articulationPoints(nodes, edges)]
    .map(id => ({ id, degree: undirected.get(id)?.size ?? 0 }))
    .sort((a,b) => b.degree - a.degree || a.id.localeCompare(b.id));
  const loops = stronglyConnectedComponents(nodes, edges)
    .filter(component => component.length > 1)
    .sort((a,b) => b.length - a.length || a[0].localeCompare(b[0]));

  return { hubs, bottlenecks, loops };
}

export function observedCognitiveFlow(nodes, edges, tick, windowTicks = 48, maxStepGap = 12) {
  const recentEdges = edges.filter(edge => {
    const lastUse = finite(edge.lastUseTick, 0);
    return lastUse > 0 && tick >= lastUse && tick - lastUse <= windowTicks;
  });
  const bySource = new Map();
  const incoming = new Map();
  for (const edge of recentEdges) {
    if (!bySource.has(edge.sourceId)) bySource.set(edge.sourceId, []);
    bySource.get(edge.sourceId).push(edge);
    incoming.set(edge.targetId, (incoming.get(edge.targetId) ?? 0) + 1);
  }

  const starts = nodes
    .map(node => nodeId(node))
    .filter(id => bySource.has(id) && !incoming.has(id))
    .sort();
  const paths = [];
  const consumed = new Set();

  function walk(start) {
    const nodeIds = [start];
    const pathEdges = [];
    let current = start;
    let previousUseTick = null;
    const visited = new Set([start]);
    while (true) {
      const candidates = (bySource.get(current) ?? [])
        .filter(edge => {
          if (consumed.has(edgeKey(edge))) return false;
          const useTick = finite(edge.lastUseTick, 0);
          if (previousUseTick == null) return true;
          return useTick >= previousUseTick && useTick - previousUseTick <= maxStepGap;
        })
        .sort((a,b) =>
          finite(a.lastUseTick, 0) - finite(b.lastUseTick, 0) ||
          finite(b.support, 0) - finite(a.support, 0)
        );
      if (!candidates.length) break;
      const edge = candidates[0];
      const key = edgeKey(edge);
      consumed.add(key);
      pathEdges.push(edge);
      previousUseTick = finite(edge.lastUseTick, previousUseTick ?? tick);
      current = edge.targetId;
      nodeIds.push(current);
      if (visited.has(current)) break;
      visited.add(current);
    }
    if (pathEdges.length) {
      paths.push({
        nodeIds,
        edges: pathEdges,
        startTick: finite(pathEdges[0]?.lastUseTick, tick),
        endTick: finite(pathEdges[pathEdges.length - 1]?.lastUseTick, tick),
      });
    }
  }

  for (const start of starts) walk(start);
  for (const edge of recentEdges) {
    if (!consumed.has(edgeKey(edge))) walk(edge.sourceId);
  }

  return {
    tick,
    windowTicks,
    maxStepGap,
    recentEdgeCount: recentEdges.length,
    paths: paths.sort((a,b) => b.edges.length - a.edges.length),
  };
}

function snapshotCounts(snapshot) {
  const topology = topologyOf(snapshot);
  const nodes = topology.nodes ?? [];
  return {
    concepts: nodes.filter(node => node.kind === 'concept').length,
    predictors: nodes.filter(node => node.kind === 'predictor').length,
    readouts: nodes.filter(node => node.kind === 'readout').length,
    edges: (topology.edges ?? []).length,
  };
}

export function deriveCognitiveEpisodes(
  historySnapshots,
  mindHistory = [],
  maxGapTicks = 160,
) {
  if (typeof mindHistory === 'number' && Number.isFinite(mindHistory)) {
    maxGapTicks = mindHistory;
    mindHistory = [];
  }

  const snapshots = [...(historySnapshots ?? [])].sort((a,b) => a.tick - b.tick);
  const timeline = [...(mindHistory ?? [])].sort((a,b) => a.tick - b.tick);
  const events = [];

  for (let i = 1; i < snapshots.length; i++) {
    const before = snapshots[i - 1];
    const after = snapshots[i];
    const diff = atlasSnapshotDiff(before.snapshot, after.snapshot);
    const beforeCounts = snapshotCounts(before.snapshot);
    const afterCounts = snapshotCounts(after.snapshot);
    if (!diff.changed) continue;
    events.push({
      kind: 'structural',
      startTick: before.tick,
      endTick: after.tick,
      diff,
      contextChanges: [],
      deltas: {
        concepts: afterCounts.concepts - beforeCounts.concepts,
        predictors: afterCounts.predictors - beforeCounts.predictors,
        readouts: afterCounts.readouts - beforeCounts.readouts,
        edges: afterCounts.edges - beforeCounts.edges,
      },
    });
  }

  for (let i = 1; i < timeline.length; i++) {
    const before = timeline[i - 1];
    const after = timeline[i];
    const contextChanges = [];
    if (before.motorOrigin !== after.motorOrigin) {
      contextChanges.push({
        type: 'motor-origin',
        before: before.motorOrigin ?? 'none',
        after: after.motorOrigin ?? 'none',
      });
    }
    if (before.physiology !== after.physiology) {
      contextChanges.push({
        type: 'physiology',
        before: before.physiology ?? 'unknown',
        after: after.physiology ?? 'unknown',
      });
    }
    const beforeError = finite(before.predictionError, 0);
    const afterError = finite(after.predictionError, 0);
    if (Math.abs(afterError - beforeError) >= 0.08) {
      contextChanges.push({
        type: 'prediction-error',
        before: beforeError,
        after: afterError,
      });
    }
    if (!contextChanges.length) continue;
    events.push({
      kind: 'context',
      startTick: before.tick,
      endTick: after.tick,
      diff: null,
      contextChanges,
      deltas: {
        concepts: finite(after.concepts, 0) - finite(before.concepts, 0),
        predictors: finite(after.predictors, 0) - finite(before.predictors, 0),
        readouts: finite(after.readouts, 0) - finite(before.readouts, 0),
        edges: finite(after.edges, 0) - finite(before.edges, 0),
      },
    });
  }

  events.sort((a,b) => a.startTick - b.startTick || a.endTick - b.endTick);

  const episodes = [];
  for (const event of events) {
    const previous = episodes[episodes.length - 1];
    if (!previous || event.startTick - previous.endTick > maxGapTicks) {
      episodes.push({
        startTick: event.startTick,
        endTick: event.endTick,
        events: [event],
      });
    } else {
      previous.endTick = Math.max(previous.endTick, event.endTick);
      previous.events.push(event);
    }
  }

  return episodes.map((episode, index) => {
    const totals = episode.events.reduce((acc, event) => {
      const diff = event.diff;
      if (diff) {
        acc.addedNodes += diff.addedNodes.length;
        acc.removedNodes += diff.removedNodes.length;
        acc.addedEdges += diff.addedEdges.length;
        acc.removedEdges += diff.removedEdges.length;
        acc.changedEdges += diff.changedEdges.length;
        acc.predictionErrorChanges += diff.predictionErrorChanges.length;
      }
      for (const change of event.contextChanges ?? []) {
        if (change.type === 'motor-origin') acc.motorTransitions += 1;
        if (change.type === 'physiology') acc.physiologyTransitions += 1;
        if (change.type === 'prediction-error') acc.predictionShifts += 1;
      }
      return acc;
    }, {
      addedNodes: 0,
      removedNodes: 0,
      addedEdges: 0,
      removedEdges: 0,
      changedEdges: 0,
      predictionErrorChanges: 0,
      motorTransitions: 0,
      physiologyTransitions: 0,
      predictionShifts: 0,
    });

    const contextPoints = timeline.filter(point =>
      point.tick >= episode.startTick && point.tick <= episode.endTick
    );
    const motorOrigins = [...new Set(contextPoints.map(point => point.motorOrigin).filter(Boolean))];
    const physiologyStates = [...new Set(contextPoints.map(point => point.physiology).filter(Boolean))];
    const predictionErrors = contextPoints
      .map(point => Number(point.predictionError))
      .filter(Number.isFinite);
    const resourceValues = contextPoints
      .map(point => Number(point.resourceProgress))
      .filter(Number.isFinite);

    return {
      id: `episode-${index + 1}`,
      ...episode,
      totals,
      context: {
        motorOrigins,
        physiologyStates,
        maxPredictionError: predictionErrors.length ? Math.max(...predictionErrors) : null,
        resourceProgressDelta: resourceValues.length > 1
          ? resourceValues[resourceValues.length - 1] - resourceValues[0]
          : 0,
      },
    };
  });
}

