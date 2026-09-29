import { isStructuralAtlasEdge } from './relation-semantics.js';

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
  { id: 'anatomy', label: 'Anatomy', description: 'Regions, boundaries, bridges, hubs and bottlenecks' },
  { id: 'dynamics', label: 'Dynamics', description: 'Recent flow, activity, learning and prediction pressure' },
]);

export const ATLAS_CONFIG = Object.freeze({
  recencyHalfLifeTicks: 512,
  normalization: Object.freeze({
    supportScale: 3.2,
    stabilityScale: 4.0,
    predictionErrorScale: 3.0,
  }),
  activity: Object.freeze({ activation: 0.78, recency: 0.22 }),
  learning: Object.freeze({ plasticity: 0.48, instability: 0.30, error: 0.22 }),
  prediction: Object.freeze({ kind: 0.62, error: 0.38 }),
  dynamics: Object.freeze({ activity: 0.42, learning: 0.28, prediction: 0.20, recency: 0.10 }),
  motor: Object.freeze({ disconnectedDomain: 0.08, localRelated: 0.18, distanceDecay: 0.18 }),
});

export const MOTOR_NODE_KINDS = new Set([
  'motor_primitive',
  'motor_competence',
  'effect',
  'controller',
  'embodiment_binding',
  'body_schema',
  'action_dimension',
  'intervention_signature',
  'action_intent',
]);

export const MOTOR_EDGE_KINDS = new Set([
  'invokes',
  'produces',
  'requires',
  'bound_to',
  'causal_estimate',
  'affords',
  'intends_with',
  'anticipates',
  'motor_component',
  'causal_effect',
]);

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function saturatingLog(value, scale) {
  return clamp01(1 - Math.exp(-Math.log1p(Math.max(0, finite(value, 0))) / Math.max(1e-6, scale)));
}

function normalizePredictionError(value) {
  const n = Number(value);
  if (Number.isFinite(n)) {
    return clamp01(1 - Math.exp(-Math.abs(n) / ATLAS_CONFIG.normalization.predictionErrorScale));
  }
  const cls = String(value ?? '').toLowerCase();
  if (cls === 'extreme') return 1;
  if (cls === 'high') return 0.78;
  if (cls === 'medium') return 0.5;
  if (cls === 'low') return 0.24;
  return 0;
}

function percentile(values, q = 0.75) {
  const xs = values.filter(Number.isFinite).sort((a,b) => a - b);
  if (!xs.length) return 0;
  if (xs.length === 1) return xs[0];
  const pos = clamp01(q) * (xs.length - 1);
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  if (lo === hi) return xs[lo];
  return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo);
}

function normalizeSupport(value) {
  return saturatingLog(value, ATLAS_CONFIG.normalization.supportScale);
}

function normalizeStability(value) {
  return saturatingLog(value, ATLAS_CONFIG.normalization.stabilityScale);
}

function edgeEvidence(edge) {
  const support = normalizeSupport(edge.support ?? edge.action_support);
  const stable = normalizeStability(edge.stableTicks);
  const weight = Math.min(1, Math.abs(finite(edge.weight, 0)));
  const confidence = clamp01(edge.confidence ?? edge.evidence?.confidence ?? 0);
  return clamp01(support * 0.38 + stable * 0.30 + weight * 0.17 + confidence * 0.15);
}

function structuralEdgeScore(edge) {
  if (edge.kind === 'causal_estimate') return 0.03;
  if (['affords', 'intends_with', 'anticipates'].includes(edge.kind)) return 0.16;
  return clamp01(
    Math.abs(finite(edge.weight, 0)) * 0.35 +
    normalizeSupport(edge.support) * 0.65
  );
}

function edgeRecency(edge, tick) {
  const lastUse = finite(edge.lastUseTick, 0);
  if (lastUse <= 0 || tick <= 0) return 0;
  return Math.exp(-Math.max(0, tick - lastUse) / ATLAS_CONFIG.recencyHalfLifeTicks);
}

export function isMotorNode(node) {
  if (!node) return false;
  if (MOTOR_NODE_KINDS.has(node.kind)) return true;
  if (node.kind !== 'readout') return false;
  return (
    String(node.id).startsWith('readout_motor:') ||
    String(node.id).startsWith('readout_primitive:') ||
    node.subtype === 'motor' ||
    node.learnedLayer === 'motor'
  );
}

function isCognitiveMotorSource(node) {
  if (!node || isMotorNode(node)) return false;
  return ['sense', 'concept', 'predictor', 'state', 'readout'].includes(node.kind);
}

export function buildAtlasGraph(nodes, edges) {
  const nodesById = new Map(nodes.map(node => [node.id, node]));
  const incoming = new Map(nodes.map(node => [node.id, []]));
  const outgoing = new Map(nodes.map(node => [node.id, []]));
  const incident = new Map(nodes.map(node => [node.id, []]));

  for (const edge of edges) {
    if (!nodesById.has(edge.sourceId) || !nodesById.has(edge.targetId)) continue;
    outgoing.get(edge.sourceId)?.push({ id: edge.targetId, edge });
    incoming.get(edge.targetId)?.push({ id: edge.sourceId, edge });
    incident.get(edge.sourceId)?.push(edge);
    incident.get(edge.targetId)?.push(edge);
  }

  return { nodes, edges, nodesById, incoming, outgoing, incident };
}

function shortestDistances(seedIds, adjacency, maxDepth = 16) {
  const distance = new Map();
  const queue = [];
  for (const id of seedIds) {
    if (distance.has(id)) continue;
    distance.set(id, 0);
    queue.push(id);
  }
  let head = 0;
  while (head < queue.length) {
    const id = queue[head++];
    const depth = distance.get(id) ?? 0;
    if (depth >= maxDepth) continue;
    for (const next of adjacency.get(id) ?? []) {
      if (distance.has(next.id)) continue;
      distance.set(next.id, depth + 1);
      queue.push(next.id);
    }
  }
  return distance;
}

export function motorReachability(nodes, edges, maxDepth = 16) {
  const index = buildAtlasGraph(nodes, edges);
  const motorIds = nodes.filter(isMotorNode).map(node => node.id);
  const cognitiveIds = nodes.filter(isCognitiveMotorSource).map(node => node.id);

  // Nodes that can reach a motor target follow outgoing graph direction.
  // Starting from motor targets and walking incoming edges gives that distance
  // in one pass for the whole graph.
  const distanceToMotor = shortestDistances(motorIds, index.incoming, maxDepth);
  // A motor-domain node is only "connected" when some non-motor cognitive
  // structure can actually reach it.
  const distanceFromCognition = shortestDistances(cognitiveIds, index.outgoing, maxDepth);

  const result = new Map();
  for (const node of nodes) {
    const domain = isMotorNode(node);
    const motorDistance = distanceToMotor.get(node.id);
    const fromCognition = distanceFromCognition.get(node.id);
    const connected = domain
      ? Number.isFinite(fromCognition) && fromCognition > 0
      : Number.isFinite(motorDistance);
    const localRelated = domain || (index.incident.get(node.id) ?? []).some(edge => MOTOR_EDGE_KINDS.has(edge.kind));
    result.set(node.id, {
      motorDomain: domain,
      motorRelated: connected || localRelated,
      motorConnected: connected,
      motorDistance: domain ? fromCognition ?? null : motorDistance ?? null,
    });
  }
  return { index, nodes: result };
}

export function atlasSignals(nodes, edges, tick = 0) {
  const reachability = motorReachability(nodes, edges);
  const { incident } = reachability.index;
  const signals = new Map();

  for (const node of nodes) {
    const related = incident.get(node.id) ?? [];
    const edgeSignals = related.map(edge => {
      const stability = normalizeStability(edge.stableTicks);
      const plasticity = clamp01(edge.plasticity);
      return {
        evidence: edgeEvidence(edge),
        recency: edgeRecency(edge, tick),
        plasticity,
        stability,
      };
    });
    const evidence = percentile(edgeSignals.map(item => item.evidence));
    const recency = percentile(edgeSignals.map(item => item.recency));
    const plasticity = percentile(edgeSignals.map(item => item.plasticity));
    const stability = percentile(edgeSignals.map(item => item.stability));
    const error = normalizePredictionError(node.predictionError ?? node.errorCls);
    const activity = clamp01(
      finite(node.activationLevel, 0) * ATLAS_CONFIG.activity.activation +
      recency * ATLAS_CONFIG.activity.recency
    );
    const perEdgeLearning = edgeSignals.map(item => clamp01(
      item.plasticity * ATLAS_CONFIG.learning.plasticity +
      (1 - item.stability) * ATLAS_CONFIG.learning.instability +
      error * ATLAS_CONFIG.learning.error
    ));
    const learning = related.length ? percentile(perEdgeLearning) : 0;
    const prediction = clamp01(
      (node.kind === 'predictor' || node.kind === 'state' ? ATLAS_CONFIG.prediction.kind : 0) +
      error * ATLAS_CONFIG.prediction.error
    );

    const motorState = reachability.nodes.get(node.id) ?? {
      motorDomain: false,
      motorRelated: false,
      motorConnected: false,
      motorDistance: null,
    };
    let motor = 0;
    if (motorState.motorConnected) {
      motor = clamp01(1 / (1 + Math.max(0, finite(motorState.motorDistance, 0)) * ATLAS_CONFIG.motor.distanceDecay));
    } else if (motorState.motorDomain) {
      motor = ATLAS_CONFIG.motor.disconnectedDomain;
    } else if (motorState.motorRelated) {
      motor = ATLAS_CONFIG.motor.localRelated;
    }

    signals.set(node.id, {
      structure: clamp01(finite(node.structuralImportance ?? node.visualValue, 0)),
      activity,
      learning,
      prediction,
      motor,
      motorDomain: motorState.motorDomain,
      motorRelated: motorState.motorRelated,
      motorConnected: motorState.motorConnected,
      motorDistance: motorState.motorDistance,
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
  const signal = signals.get(node.id) ?? {};
  if (mode === 'anatomy') return clamp01(signal.structure ?? 0);
  if (mode === 'dynamics') return clamp01(
    (signal.activity ?? 0) * 0.42 +
    (signal.learning ?? 0) * 0.28 +
    (signal.prediction ?? 0) * 0.20 +
    (signal.recency ?? 0) * 0.10
  );
  return clamp01(signal[mode] ?? 0);
}

export function atlasEdgeScore(edge, mode, tick = 0, signals = null) {
  if (mode === 'structure') return structuralEdgeScore(edge);
  if (mode === 'activity') return edgeRecency(edge, tick);
  if (mode === 'learning') {
    const stability = normalizeStability(edge.stableTicks);
    const support = normalizeSupport(edge.support);
    const instability = 1 - stability;
    return clamp01(clamp01(edge.plasticity) * 0.65 + instability * 0.25 + support * 0.10);
  }
  if (mode === 'prediction') return edge.kind === 'predictive' ? 1 : edge.kind === 'gating' ? 0.45 : 0.08;
  if (mode === 'motor') {
    const source = signals?.get?.(edge.sourceId) ?? null;
    const target = signals?.get?.(edge.targetId) ?? null;
    if (source?.motorConnected && target?.motorConnected) {
      const sourceDistance = finite(source.motorDistance, 99);
      const targetDistance = finite(target.motorDistance, 99);
      if (targetDistance < sourceDistance) return MOTOR_EDGE_KINDS.has(edge.kind) ? 1 : 0.72;
      return MOTOR_EDGE_KINDS.has(edge.kind) ? 0.62 : 0.24;
    }
    if (MOTOR_EDGE_KINDS.has(edge.kind) && (source?.motorRelated || target?.motorRelated)) return 0.18;
    return 0.025;
  }
  if (mode === 'anatomy') return atlasEdgeScore(edge, 'structure', tick, signals);
  if (mode === 'dynamics') return clamp01(
    atlasEdgeScore(edge, 'activity', tick, signals) * 0.55 +
    atlasEdgeScore(edge, 'learning', tick, signals) * 0.25 +
    atlasEdgeScore(edge, 'prediction', tick, signals) * 0.20
  );
  if (mode === 'diff') return 0;
  if (mode === 'evidence') {
    const support = normalizeSupport(edge.support ?? edge.action_support);
    const stable = normalizeStability(edge.stableTicks);
    const confidence = clamp01(edge.confidence ?? edge.evidence?.confidence ?? 0);
    const counterfactual = Math.min(1, Math.log1p(Math.max(0, finite(edge.counterfactualSupport ?? edge.counterfactual_support, 0))) / 8);
    if (edge.kind === 'causal_estimate') {
      return clamp01(confidence * 0.46 + support * 0.29 + counterfactual * 0.25);
    }
    return clamp01(support * 0.55 + stable * 0.45);
  }
  return structuralEdgeScore(edge);
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
      diff: 0,
      anatomy: 0,
      dynamics: 0,
      bridges: 0,
    };
    item.nodeIds.push(node.id);
    item.kinds[node.kind] = (item.kinds[node.kind] ?? 0) + 1;
    const s = signals.get(node.id) ?? {};
    for (const key of ['structure','activity','learning','prediction','motor','evidence','diff']) {
      item[key] += finite(s[key], 0);
    }
    item.anatomy += finite(s.structure, 0);
    item.dynamics +=
      finite(s.activity, 0) * 0.42 +
      finite(s.learning, 0) * 0.28 +
      finite(s.prediction, 0) * 0.20 +
      finite(s.recency, 0) * 0.10;
    grouped.set(node.community, item);
  }

  const nodesById = new Map(nodes.map(node => [node.id, node]));
  for (const edge of edges) {
    if (!isStructuralAtlasEdge(edge)) continue;
    const source = nodesById.get(edge.sourceId);
    const target = nodesById.get(edge.targetId);
    if (!source?.community || !target?.community || source.community === target.community) continue;
    grouped.get(source.community) && (grouped.get(source.community).bridges += 1);
    grouped.get(target.community) && (grouped.get(target.community).bridges += 1);
  }

  return [...grouped.values()].map(region => {
    const n = Math.max(1, region.nodeIds.length);
    for (const key of ['structure','activity','learning','prediction','motor','evidence','diff','anatomy','dynamics']) {
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

function bfsPath(startId, targetPredicate, index, reverse = false, maxDepth = 10) {
  const adjacency = reverse ? index.incoming : index.outgoing;
  const queue = [startId];
  const depth = new Map([[startId, 0]]);
  const parent = new Map();
  const parentEdge = new Map();
  let head = 0;

  while (head < queue.length) {
    const id = queue[head++];
    const currentDepth = depth.get(id) ?? 0;
    if (id !== startId && targetPredicate(index.nodesById.get(id))) {
      const nodeIds = [];
      const edges = [];
      let cursor = id;
      while (cursor != null) {
        nodeIds.push(cursor);
        const edge = parentEdge.get(cursor);
        if (edge) edges.push(edge);
        cursor = parent.get(cursor);
      }
      nodeIds.reverse();
      edges.reverse();
      return { nodeIds, edges };
    }
    if (currentDepth >= maxDepth) continue;
    for (const next of adjacency.get(id) ?? []) {
      if (depth.has(next.id)) continue;
      depth.set(next.id, currentDepth + 1);
      parent.set(next.id, id);
      parentEdge.set(next.id, next.edge);
      queue.push(next.id);
    }
  }
  return null;
}

export function cognitivePath(startId, nodes, edges, maxDepth = 10) {
  if (!startId) return null;
  const index = buildAtlasGraph(nodes, edges);
  const start = index.nodesById.get(startId);
  if (!start) return null;
  const sensoryTarget = node => node?.kind === 'sense';

  if (isMotorNode(start)) {
    return bfsPath(startId, sensoryTarget, index, true, maxDepth);
  }

  const downstream = bfsPath(startId, isMotorNode, index, false, maxDepth);
  if (downstream) return downstream;
  return bfsPath(startId, sensoryTarget, index, true, maxDepth);
}

/**
 * Spec Sec 58: search by id, kind, semantic name or physical binding.
 * A physical-binding hit (e.g. "right_knee") locates the bound cognitive
 * node -- it never renames the underlying knowledge.
 */
export function searchAtlasNodes(nodes, query, limit = 20) {
  const needle = String(query ?? '').trim().toLowerCase();
  if (!needle) return [];
  const haystack = node => [
    node.id,
    node.kind,
    node.observerLabel,
    node.selfLabel,
    node.surfaceFingerprint,
    node.effectorId,
    node.joint,
  ].filter(Boolean).map(value => String(value).toLowerCase());

  return nodes
    .filter(node => haystack(node).some(field => field.includes(needle)))
    .sort((a, b) => String(a.id).localeCompare(String(b.id)))
    .slice(0, limit);
}

export function learningFrontier(nodes, signals, limit = 8) {
  return [...nodes]
    .map(node => ({ node, score: finite(signals.get(node.id)?.learning, 0) }))
    .filter(item => item.score > 0.12)
    .sort((a,b) => b.score - a.score || String(a.node.id).localeCompare(String(b.node.id)))
    .slice(0, limit);
}
