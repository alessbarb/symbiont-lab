import { isStructuralAtlasEdge } from "./relation-semantics.js";

/**
 * Observer-side Cognitive Atlas analytics.
 *
 * This module derives presentation-only regions, view scores and exact graph
 * paths from an externally owned cognitive graph. Nothing here mutates or feeds
 * back into the source graph.
 */

export const ATLAS_MODES = Object.freeze([
  {
    id: "structure",
    label: "Structure",
    description: "Stable organisation and structural importance",
  },
  {
    id: "activity",
    label: "Activity",
    description: "Current activation and recent use",
  },
  {
    id: "learning",
    label: "Learning",
    description: "Plasticity, instability and prediction error",
  },
  {
    id: "prediction",
    label: "Prediction",
    description: "Predictive/state processing and error",
  },
  {
    id: "motor",
    label: "Motor",
    description: "Graph routes reaching motor-domain nodes",
  },
  {
    id: "evidence",
    label: "Evidence",
    description: "Support, stability and learned relation strength",
  },
  {
    id: "diff",
    label: "Diff",
    description: "Changes against the selected temporal baseline",
  },
  {
    id: "anatomy",
    label: "Anatomy",
    description: "Regions, boundaries, graph bridges, hubs and bottlenecks",
  },
  {
    id: "dynamics",
    label: "Dynamics",
    description: "Recent flow, activity, learning and prediction pressure",
  },
]);

export const ATLAS_CONFIG = Object.freeze({
  recencyHalfLifeTicks: 512,
  aggregationPercentile: 0.75,
  motorMaxDepth: 16,
  pathMaxDepth: 10,

  normalization: Object.freeze({
    supportScale: 3.2,
    stabilityScale: 4.0,
    predictionErrorScale: 3.0,
    counterfactualScale: 3.2,
  }),

  errorClasses: Object.freeze({
    low: 1,
    medium: 2,
    high: 4.5,
    extreme: 24,
  }),

  activity: Object.freeze({
    activation: 0.78,
    recency: 0.22,
  }),

  learning: Object.freeze({
    plasticity: 0.48,
    instability: 0.3,
    error: 0.22,
    edgePlasticity: 0.65,
    edgeInstability: 0.25,
    edgeSupport: 0.1,
    frontierMinScore: 0.12,
  }),

  prediction: Object.freeze({
    kind: 0.62,
    error: 0.38,
    predictiveEdge: 1,
    gatingEdge: 0.45,
    otherEdge: 0.08,
  }),

  dynamics: Object.freeze({
    activity: 0.42,
    learning: 0.28,
    prediction: 0.2,
    recency: 0.1,
    edgeActivity: 0.55,
    edgeLearning: 0.25,
    edgePrediction: 0.2,
  }),

  structure: Object.freeze({
    causalEstimate: 0.03,
    overlayRelation: 0.16,
    weight: 0.35,
    support: 0.65,
  }),

  evidence: Object.freeze({
    support: 0.38,
    stability: 0.3,
    weight: 0.17,
    confidence: 0.15,
    regularSupport: 0.55,
    regularStability: 0.45,
    causalConfidence: 0.46,
    causalSupport: 0.29,
    causalCounterfactual: 0.25,
  }),

  motor: Object.freeze({
    disconnectedDomain: 0.08,
    localRelated: 0.18,
    collapsedOnly: 0.32,
    distanceDecay: 0.18,
    connectedPreferredKind: 1,
    connectedOtherKind: 0.72,
    nonProgressPreferredKind: 0.62,
    nonProgressOtherKind: 0.24,
    weakRelatedEdge: 0.18,
    backgroundEdge: 0.025,
  }),

  anatomy: Object.freeze({
    degree: 0.3,
    betweenness: 0.35,
    articulation: 0.2,
    boundary: 0.15,
    bridgeEdge: 1,
    boundaryEdge: 0.72,
    structuralEdge: 0.45,
    backgroundEdge: 0.08,
  }),

  diff: Object.freeze({
    structure: 1,
    activity: 1,
    learning: 1,
    prediction: 1,
    motor: 1,
    evidence: 1,
  }),
});

export const MOTOR_NODE_KINDS = new Set([
  "motor_primitive",
  "motor_competence",
  "effect",
  "controller",
  "embodiment_binding",
  "body_schema",
  "action_dimension",
  "intervention_signature",
  "action_intent",
]);

export const MOTOR_EDGE_KINDS = new Set([
  "invokes",
  "produces",
  "requires",
  "bound_to",
  "causal_estimate",
  "affords",
  "intends_with",
  "anticipates",
  "motor_component",
  "causal_effect",
]);

const STRUCTURAL_OVERLAY_EDGE_KINDS = new Set([
  "affords",
  "intends_with",
  "anticipates",
]);

const SEARCH_FIELDS = Object.freeze([
  ["id", 100],
  ["observerLabel", 90],
  ["selfLabel", 90],
  ["kind", 70],
  ["surfaceFingerprint", 55],
  ["effectorId", 55],
  ["joint", 55],
  ["subtype", 45],
  ["learnedLayer", 45],
]);

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function saturatingLog(value, scale) {
  const safeScale = Math.max(1e-6, finite(scale, 1));
  return clamp01(
    1 - Math.exp(-Math.log1p(Math.max(0, finite(value, 0))) / safeScale),
  );
}

function exponentialMagnitude(value, scale) {
  const safeScale = Math.max(1e-6, finite(scale, 1));
  return clamp01(1 - Math.exp(-Math.abs(finite(value, 0)) / safeScale));
}

function normalizePredictionError(value) {
  const n = Number(value);

  if (Number.isFinite(n)) {
    return exponentialMagnitude(
      n,
      ATLAS_CONFIG.normalization.predictionErrorScale,
    );
  }

  const cls = String(value ?? "").toLowerCase();
  const equivalent = ATLAS_CONFIG.errorClasses[cls];

  if (equivalent == null) return 0;

  return exponentialMagnitude(
    equivalent,
    ATLAS_CONFIG.normalization.predictionErrorScale,
  );
}

function percentile(values, q = ATLAS_CONFIG.aggregationPercentile) {
  const xs = values
    .map((value) => Number(value))
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

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

function normalizeCounterfactual(value) {
  return saturatingLog(value, ATLAS_CONFIG.normalization.counterfactualScale);
}

function edgeEvidence(edge) {
  const cfg = ATLAS_CONFIG.evidence;

  const support = normalizeSupport(edge.support ?? edge.action_support);

  const stability = normalizeStability(edge.stableTicks);

  const weight = Math.min(1, Math.abs(finite(edge.weight, 0)));

  const confidence = clamp01(edge.confidence ?? edge.evidence?.confidence ?? 0);

  return clamp01(
    support * cfg.support +
      stability * cfg.stability +
      weight * cfg.weight +
      confidence * cfg.confidence,
  );
}

function structuralEdgeScore(edge) {
  const cfg = ATLAS_CONFIG.structure;

  if (edge.kind === "causal_estimate") {
    return cfg.causalEstimate;
  }

  if (STRUCTURAL_OVERLAY_EDGE_KINDS.has(edge.kind)) {
    return cfg.overlayRelation;
  }

  return clamp01(
    Math.abs(finite(edge.weight, 0)) * cfg.weight +
      normalizeSupport(edge.support) * cfg.support,
  );
}

function edgeRecency(edge, tick) {
  const lastUse = finite(edge.lastUseTick, 0);
  const currentTick = finite(tick, 0);

  if (lastUse <= 0 || currentTick <= 0) {
    return 0;
  }

  const delta = Math.max(0, currentTick - lastUse);

  const halfLife = Math.max(1e-6, ATLAS_CONFIG.recencyHalfLifeTicks);

  return Math.exp((-Math.LN2 * delta) / halfLife);
}

function dynamicsScore(signal) {
  const cfg = ATLAS_CONFIG.dynamics;

  return clamp01(
    finite(signal?.activity, 0) * cfg.activity +
      finite(signal?.learning, 0) * cfg.learning +
      finite(signal?.prediction, 0) * cfg.prediction +
      finite(signal?.recency, 0) * cfg.recency,
  );
}

function stableEdgeId(edge, index = 0) {
  if (edge?.id != null) {
    return String(edge.id);
  }

  return [
    String(edge?.sourceId ?? ""),
    "→",
    String(edge?.targetId ?? ""),
    ":",
    String(edge?.kind ?? ""),
    ":",
    index,
  ].join("");
}

function undirectedPairKey(a, b) {
  const x = String(a);
  const y = String(b);

  return x < y ? `${x}\u0000${y}` : `${y}\u0000${x}`;
}

export function isMotorNode(node) {
  if (!node) return false;

  if (MOTOR_NODE_KINDS.has(node.kind)) {
    return true;
  }

  if (node.kind !== "readout") {
    return false;
  }

  // Structured metadata is authoritative.
  // Prefix checks remain only for backwards compatibility.
  if (node.subtype === "motor" || node.learnedLayer === "motor") {
    return true;
  }

  return (
    String(node.id).startsWith("readout_motor:") ||
    String(node.id).startsWith("readout_primitive:")
  );
}

function isCognitiveMotorSource(node) {
  if (!node || isMotorNode(node)) {
    return false;
  }

  return ["sense", "concept", "predictor", "state", "readout"].includes(
    node.kind,
  );
}

/**
 * Build a reusable graph index.
 *
 * Invalid edges are excluded from adjacency structures but preserved in
 * diagnostics.
 *
 * Duplicate node ids are diagnosed. The first node wins, so accidental
 * duplicates never silently overwrite already indexed data.
 */
export function buildAtlasGraph(nodes = [], edges = [], options = {}) {
  const diagnostics = {
    duplicateNodeIds: [],
    danglingEdges: [],
    selfLoops: [],
  };

  const nodesById = new Map();

  for (const node of nodes) {
    if (!node || node.id == null) {
      continue;
    }

    if (nodesById.has(node.id)) {
      diagnostics.duplicateNodeIds.push(node.id);
      continue;
    }

    nodesById.set(node.id, node);
  }

  const canonicalNodes = [...nodesById.values()];

  const incoming = new Map(canonicalNodes.map((node) => [node.id, []]));

  const outgoing = new Map(canonicalNodes.map((node) => [node.id, []]));

  const incident = new Map(canonicalNodes.map((node) => [node.id, []]));

  const validEdges = [];

  edges.forEach((edge, edgeIndex) => {
    if (!edge) return;

    const hasSource = nodesById.has(edge.sourceId);
    const hasTarget = nodesById.has(edge.targetId);

    if (!hasSource || !hasTarget) {
      diagnostics.danglingEdges.push({
        edgeId: stableEdgeId(edge, edgeIndex),
        sourceId: edge.sourceId ?? null,
        targetId: edge.targetId ?? null,
        missingSource: !hasSource,
        missingTarget: !hasTarget,
      });

      return;
    }

    if (edge.sourceId === edge.targetId) {
      diagnostics.selfLoops.push(stableEdgeId(edge, edgeIndex));
      // Keep recurrent evidence in the index. Only the undirected structural
      // projection excludes loops when calculating bridges and centrality.
    }

    validEdges.push(edge);

    outgoing.get(edge.sourceId).push({
      id: edge.targetId,
      edge,
    });

    incoming.get(edge.targetId).push({
      id: edge.sourceId,
      edge,
    });

    incident.get(edge.sourceId).push(edge);

    if (edge.targetId !== edge.sourceId) {
      incident.get(edge.targetId).push(edge);
    }
  });

  const index = {
    nodes: canonicalNodes,
    edges: validEdges,
    allEdges: [...edges],

    nodesById,
    incoming,
    outgoing,
    incident,

    diagnostics,
  };

  if (
    options.throwOnInvalid &&
    (diagnostics.duplicateNodeIds.length || diagnostics.danglingEdges.length)
  ) {
    throw new Error(
      `Invalid atlas graph: ` +
        `${diagnostics.duplicateNodeIds.length} duplicate node ids, ` +
        `${diagnostics.danglingEdges.length} dangling edges`,
    );
  }

  return index;
}

function shortestDistances(
  seedIds,
  adjacency,
  maxDepth = ATLAS_CONFIG.motorMaxDepth,
) {
  const distance = new Map();
  const queue = [];

  for (const id of seedIds) {
    if (distance.has(id)) {
      continue;
    }

    distance.set(id, 0);
    queue.push(id);
  }

  let head = 0;

  while (head < queue.length) {
    const id = queue[head++];
    const depth = distance.get(id) ?? 0;

    if (depth >= maxDepth) {
      continue;
    }

    for (const next of adjacency.get(id) ?? []) {
      if (distance.has(next.id)) {
        continue;
      }

      distance.set(next.id, depth + 1);

      queue.push(next.id);
    }
  }

  return distance;
}

export function motorReachability(
  nodes,
  edges,
  maxDepth = ATLAS_CONFIG.motorMaxDepth,
  existingIndex = null,
) {
  const index = existingIndex ?? buildAtlasGraph(nodes, edges);

  const canonicalNodes = index.nodes;

  const motorIds = canonicalNodes.filter(isMotorNode).map((node) => node.id);

  const cognitiveIds = canonicalNodes
    .filter(isCognitiveMotorSource)
    .map((node) => node.id);

  // Reverse walk from motor-domain targets gives the distance from
  // arbitrary nodes to their nearest motor target.
  const distanceToMotor = shortestDistances(motorIds, index.incoming, maxDepth);

  // Forward walk from cognitive sources tells whether motor-domain
  // structure is actually reachable from cognition.
  const distanceFromCognition = shortestDistances(
    cognitiveIds,
    index.outgoing,
    maxDepth,
  );

  const result = new Map();

  for (const node of canonicalNodes) {
    const motorDomain = isMotorNode(node);

    const distanceTo = distanceToMotor.get(node.id);

    const distanceFrom = distanceFromCognition.get(node.id);

    const reachableFromCognition =
      Number.isFinite(distanceFrom) && distanceFrom > 0;

    const canReachMotor = Number.isFinite(distanceTo);

    const connected = motorDomain ? reachableFromCognition : canReachMotor;

    const hasMotorRelation = (index.incident.get(node.id) ?? []).some((edge) =>
      MOTOR_EDGE_KINDS.has(edge.kind),
    );

    result.set(node.id, {
      motorDomain,

      reachableFromCognition,
      canReachMotor,
      hasMotorRelation,

      motorRelated: connected || motorDomain || hasMotorRelation,

      motorConnected: connected,

      distanceToMotor: distanceTo ?? null,

      distanceFromCognition: distanceFrom ?? null,

      motorDistance: motorDomain
        ? (distanceFrom ?? null)
        : (distanceTo ?? null),
    });
  }

  return {
    index,
    nodes: result,
  };
}

function motorVisualScore(visibleState, fullState) {
  const cfg = ATLAS_CONFIG.motor;

  const collapsedOnly = Boolean(
    fullState.motorConnected && !visibleState.motorConnected,
  );

  if (visibleState.motorConnected) {
    return clamp01(
      1 /
        (1 +
          Math.max(0, finite(visibleState.motorDistance, 0)) *
            cfg.distanceDecay),
    );
  }

  if (collapsedOnly) {
    return cfg.collapsedOnly;
  }

  if (fullState.motorDomain) {
    return cfg.disconnectedDomain;
  }

  if (fullState.motorRelated) {
    return cfg.localRelated;
  }

  return 0;
}

function computeNodeEdgeSignals(related, tick, nodeError) {
  const perEdge = related.map((edge) => {
    const stability = normalizeStability(edge.stableTicks);

    const plasticity = clamp01(edge.plasticity);

    const recency = edgeRecency(edge, tick);

    const evidence = edgeEvidence(edge);

    const learning = clamp01(
      plasticity * ATLAS_CONFIG.learning.plasticity +
        (1 - stability) * ATLAS_CONFIG.learning.instability +
        nodeError * ATLAS_CONFIG.learning.error,
    );

    return {
      edge,
      evidence,
      recency,
      plasticity,
      stability,
      learning,
    };
  });

  return {
    perEdge,

    evidence: percentile(perEdge.map((item) => item.evidence)),

    recency: percentile(perEdge.map((item) => item.recency)),

    plasticity: percentile(perEdge.map((item) => item.plasticity)),

    stability: percentile(perEdge.map((item) => item.stability)),

    learning: percentile(perEdge.map((item) => item.learning)),
  };
}

/**
 * Create node signals.
 *
 * options.baselineSignals:
 *   Previous Map of node signals. If supplied, diff is computed.
 *
 * options.fullMotor:
 *   Full-graph motor reachability when the rendered graph is collapsed.
 */
export function atlasSignals(nodes, edges, tick = 0, options = {}) {
  const index = options.index ?? buildAtlasGraph(nodes, edges);

  const reachability =
    options.motorReachability ??
    motorReachability(
      index.nodes,
      index.edges,
      options.motorMaxDepth ?? ATLAS_CONFIG.motorMaxDepth,
      index,
    );

  const fullMotor = options.fullMotor ?? null;

  const baselineSignals = options.baselineSignals ?? null;

  const signals = new Map();

  for (const node of index.nodes) {
    const related = index.incident.get(node.id) ?? [];

    const error = normalizePredictionError(
      node.predictionError ?? node.errorCls,
    );

    const edgeSummary = computeNodeEdgeSignals(related, tick, error);

    const activity = clamp01(
      finite(node.activationLevel, 0) * ATLAS_CONFIG.activity.activation +
        edgeSummary.recency * ATLAS_CONFIG.activity.recency,
    );

    const learning = related.length ? edgeSummary.learning : 0;

    const prediction = clamp01(
      (node.kind === "predictor" || node.kind === "state"
        ? ATLAS_CONFIG.prediction.kind
        : 0) +
        error * ATLAS_CONFIG.prediction.error,
    );

    const visibleMotor = reachability.nodes.get(node.id) ?? {
      motorDomain: false,
      motorRelated: false,
      motorConnected: false,
      motorDistance: null,
    };

    const fullState = fullMotor?.nodes?.get?.(node.id) ?? visibleMotor;

    const collapsedOnly = Boolean(
      fullState.motorConnected && !visibleMotor.motorConnected,
    );

    const motor = motorVisualScore(visibleMotor, fullState);

    const signal = {
      structure: clamp01(
        finite(node.structuralImportance ?? node.visualValue, 0),
      ),

      activity,
      learning,
      prediction,
      motor,

      evidence: edgeSummary.evidence,

      error,

      recency: edgeSummary.recency,

      plasticity: edgeSummary.plasticity,

      stability: edgeSummary.stability,

      motorDomain: fullState.motorDomain,

      motorRelated: fullState.motorRelated,

      motorConnected: visibleMotor.motorConnected,

      motorConnectedFull: fullState.motorConnected,

      motorCollapsedOnly: collapsedOnly,

      motorDistance: visibleMotor.motorConnected
        ? visibleMotor.motorDistance
        : fullState.motorDistance,

      diff: 0,
      anatomy: 0,
      dynamics: 0,
    };

    signal.dynamics = dynamicsScore(signal);

    signals.set(node.id, signal);
  }

  if (baselineSignals) {
    applySignalDiff(signals, baselineSignals);
  }

  const anatomy = options.anatomy ?? atlasAnatomy(index);

  for (const [nodeId, nodeAnatomy] of anatomy.nodes) {
    const signal = signals.get(nodeId);

    if (!signal) {
      continue;
    }

    signal.anatomy = nodeAnatomy.score;

    signal.degreeCentrality = nodeAnatomy.degreeCentrality;

    signal.betweennessCentrality = nodeAnatomy.betweennessCentrality;

    signal.articulationPoint = nodeAnatomy.articulationPoint;

    signal.boundaryRatio = nodeAnatomy.boundaryRatio;
  }

  return signals;
}

export function applySignalDiff(currentSignals, baselineSignals) {
  const weights = ATLAS_CONFIG.diff;

  const keys = Object.keys(weights);

  const weightTotal =
    keys.reduce((sum, key) => sum + Math.max(0, finite(weights[key], 0)), 0) ||
    1;

  for (const [nodeId, current] of currentSignals) {
    const baseline = baselineSignals?.get?.(nodeId);

    if (!baseline) {
      current.diff = 1;
      continue;
    }

    let delta = 0;

    for (const key of keys) {
      delta +=
        Math.abs(finite(current[key], 0) - finite(baseline[key], 0)) *
        weights[key];
    }

    current.diff = clamp01(delta / weightTotal);
  }

  return currentSignals;
}

function buildUndirectedStructuralAdjacency(index) {
  const adjacency = new Map(index.nodes.map((node) => [node.id, new Set()]));

  const pairEdges = new Map();

  index.edges.forEach((edge, edgeIndex) => {
    if (!isStructuralAtlasEdge(edge)) {
      return;
    }

    if (edge.sourceId === edge.targetId) {
      return;
    }

    adjacency.get(edge.sourceId)?.add(edge.targetId);

    adjacency.get(edge.targetId)?.add(edge.sourceId);

    const pair = undirectedPairKey(edge.sourceId, edge.targetId);

    if (!pairEdges.has(pair)) {
      pairEdges.set(pair, []);
    }

    pairEdges.get(pair).push({
      edge,
      edgeIndex,
    });
  });

  return {
    adjacency,
    pairEdges,
  };
}

/**
 * Tarjan articulation points and graph bridges on the undirected
 * structural projection.
 *
 * Parallel structural edges prevent an endpoint pair from being treated as a
 * true graph bridge.
 *
 * Implemented iteratively to avoid call-stack overflow on large graphs.
 */
function articulationAndBridges(index, undirected) {
  const { adjacency, pairEdges } = undirected;

  const discovery = new Map();

  const low = new Map();

  const parent = new Map();

  // DFS-tree children count per node, used for the root articulation check.
  const childrenCount = new Map();

  const articulationPoints = new Set();

  const bridgePairs = new Set();

  let time = 0;

  for (const startNode of index.nodes) {
    if (discovery.has(startNode.id)) {
      continue;
    }

    const rootId = startNode.id;
    discovery.set(rootId, ++time);
    low.set(rootId, time);
    childrenCount.set(rootId, 0);

    // Each stack entry: [nodeId, neighborIterator].
    // We advance the iterator one step per outer-loop iteration, pushing a new
    // frame when we find an unvisited neighbor (tree edge) and finalizing the
    // node when the iterator is exhausted.
    const stack = [[rootId, (adjacency.get(rootId) ?? new Set()).values()]];

    while (stack.length) {
      const frame = stack[stack.length - 1];
      const u = frame[0];
      const next = frame[1].next();

      if (next.done) {
        // All neighbors of u have been processed; pop and run post-visit logic.
        stack.pop();

        const p = parent.get(u);

        if (p !== undefined) {
          low.set(p, Math.min(low.get(p), low.get(u)));

          const isRoot = !parent.has(p);

          if (isRoot) {
            // Root is an articulation point iff it has more than one DFS child.
            if (childrenCount.get(p) > 1) {
              articulationPoints.add(p);
            }
          } else if (low.get(u) >= discovery.get(p)) {
            articulationPoints.add(p);
          }

          const pair = undirectedPairKey(p, u);

          const parallelCount = pairEdges.get(pair)?.length ?? 0;

          if (low.get(u) > discovery.get(p) && parallelCount === 1) {
            bridgePairs.add(pair);
          }
        }
      } else {
        const v = next.value;

        if (!discovery.has(v)) {
          // Tree edge: push child frame.
          parent.set(v, u);
          childrenCount.set(u, (childrenCount.get(u) ?? 0) + 1);
          discovery.set(v, ++time);
          low.set(v, time);
          childrenCount.set(v, 0);
          stack.push([v, (adjacency.get(v) ?? new Set()).values()]);
        } else if (parent.get(u) !== v) {
          // Back edge (not the tree edge we arrived from).
          low.set(u, Math.min(low.get(u), discovery.get(v)));
        }
      }
    }
  }

  const bridgeEdgeIds = new Set();

  for (const pair of bridgePairs) {
    for (const item of pairEdges.get(pair) ?? []) {
      bridgeEdgeIds.add(stableEdgeId(item.edge, item.edgeIndex));
    }
  }

  return {
    articulationPoints,
    bridgePairs,
    bridgeEdgeIds,
  };
}

/**
 * Exact unweighted node betweenness centrality using Brandes' algorithm on the
 * undirected structural projection.
 *
 * Returned values are normalized to 0..1.
 */
function betweennessCentrality(index, adjacency) {
  const nodeIds = index.nodes.map((node) => node.id);

  const centrality = new Map(nodeIds.map((id) => [id, 0]));

  for (const source of nodeIds) {
    const stack = [];

    const predecessors = new Map(nodeIds.map((id) => [id, []]));

    const sigma = new Map(nodeIds.map((id) => [id, 0]));

    const distance = new Map(nodeIds.map((id) => [id, -1]));

    sigma.set(source, 1);

    distance.set(source, 0);

    const queue = [source];
    let head = 0;

    while (head < queue.length) {
      const v = queue[head++];

      stack.push(v);

      for (const w of adjacency.get(v) ?? []) {
        if (distance.get(w) < 0) {
          distance.set(w, distance.get(v) + 1);

          queue.push(w);
        }

        if (distance.get(w) === distance.get(v) + 1) {
          sigma.set(w, sigma.get(w) + sigma.get(v));

          predecessors.get(w).push(v);
        }
      }
    }

    const dependency = new Map(nodeIds.map((id) => [id, 0]));

    while (stack.length) {
      const w = stack.pop();

      const sigmaW = sigma.get(w);

      if (sigmaW > 0) {
        for (const v of predecessors.get(w)) {
          const contribution =
            (sigma.get(v) / sigmaW) * (1 + dependency.get(w));

          dependency.set(v, dependency.get(v) + contribution);
        }
      }

      if (w !== source) {
        centrality.set(w, centrality.get(w) + dependency.get(w));
      }
    }
  }

  // Every unordered pair is counted twice on an undirected graph.
  for (const id of nodeIds) {
    centrality.set(id, centrality.get(id) / 2);
  }

  const n = nodeIds.length;

  const normalizer = n > 2 ? ((n - 1) * (n - 2)) / 2 : 1;

  for (const id of nodeIds) {
    centrality.set(id, clamp01(centrality.get(id) / normalizer));
  }

  return centrality;
}

export function atlasAnatomy(nodesOrIndex, maybeEdges = null) {
  const index =
    nodesOrIndex?.nodesById instanceof Map
      ? nodesOrIndex
      : buildAtlasGraph(nodesOrIndex ?? [], maybeEdges ?? []);

  const undirected = buildUndirectedStructuralAdjacency(index);

  const topology = articulationAndBridges(index, undirected);

  const betweenness = betweennessCentrality(index, undirected.adjacency);

  const n = Math.max(1, index.nodes.length - 1);

  const nodeResults = new Map();

  for (const node of index.nodes) {
    const neighbors = undirected.adjacency.get(node.id) ?? new Set();

    const degreeCentrality = clamp01(neighbors.size / n);

    const betweennessCentrality = betweenness.get(node.id) ?? 0;

    const articulationPoint = topology.articulationPoints.has(node.id);

    let structuralIncident = 0;
    let boundaryIncident = 0;

    for (const edge of index.incident.get(node.id) ?? []) {
      if (!isStructuralAtlasEdge(edge)) {
        continue;
      }

      structuralIncident += 1;

      const source = index.nodesById.get(edge.sourceId);

      const target = index.nodesById.get(edge.targetId);

      if (
        source?.community &&
        target?.community &&
        source.community !== target.community
      ) {
        boundaryIncident += 1;
      }
    }

    const boundaryRatio =
      structuralIncident > 0
        ? clamp01(boundaryIncident / structuralIncident)
        : 0;

    const cfg = ATLAS_CONFIG.anatomy;

    const score = clamp01(
      degreeCentrality * cfg.degree +
        betweennessCentrality * cfg.betweenness +
        (articulationPoint ? 1 : 0) * cfg.articulation +
        boundaryRatio * cfg.boundary,
    );

    nodeResults.set(node.id, {
      score,

      degreeCentrality,
      betweennessCentrality,

      articulationPoint,
      boundaryRatio,

      degree: neighbors.size,
    });
  }

  return {
    index,

    nodes: nodeResults,

    articulationPoints: topology.articulationPoints,

    bridgePairs: topology.bridgePairs,

    bridgeEdgeIds: topology.bridgeEdgeIds,

    adjacency: undirected.adjacency,
  };
}

export function atlasModeScore(node, signals, mode = "structure") {
  const signal = signals.get(node.id) ?? {};

  if (mode === "dynamics") {
    return dynamicsScore(signal);
  }

  return clamp01(signal[mode] ?? 0);
}

function scoreLearningEdge(edge) {
  const cfg = ATLAS_CONFIG.learning;

  const stability = normalizeStability(edge.stableTicks);

  const support = normalizeSupport(edge.support ?? edge.action_support);

  return clamp01(
    clamp01(edge.plasticity) * cfg.edgePlasticity +
      (1 - stability) * cfg.edgeInstability +
      support * cfg.edgeSupport,
  );
}

function scorePredictionEdge(edge) {
  if (edge.kind === "predictive") {
    return ATLAS_CONFIG.prediction.predictiveEdge;
  }

  if (edge.kind === "gating") {
    return ATLAS_CONFIG.prediction.gatingEdge;
  }

  return ATLAS_CONFIG.prediction.otherEdge;
}

function scoreMotorEdge(edge, signals) {
  const cfg = ATLAS_CONFIG.motor;

  const source = signals?.get?.(edge.sourceId) ?? null;

  const target = signals?.get?.(edge.targetId) ?? null;

  if (source?.motorConnected && target?.motorConnected) {
    const sourceDistance = finite(
      source.motorDistance,
      Number.POSITIVE_INFINITY,
    );

    const targetDistance = finite(
      target.motorDistance,
      Number.POSITIVE_INFINITY,
    );

    const preferredKind = MOTOR_EDGE_KINDS.has(edge.kind);

    if (targetDistance < sourceDistance) {
      return preferredKind
        ? cfg.connectedPreferredKind
        : cfg.connectedOtherKind;
    }

    return preferredKind
      ? cfg.nonProgressPreferredKind
      : cfg.nonProgressOtherKind;
  }

  if (
    MOTOR_EDGE_KINDS.has(edge.kind) &&
    (source?.motorRelated || target?.motorRelated)
  ) {
    return cfg.weakRelatedEdge;
  }

  return cfg.backgroundEdge;
}

function scoreEvidenceEdge(edge) {
  const cfg = ATLAS_CONFIG.evidence;

  const support = normalizeSupport(edge.support ?? edge.action_support);

  const stability = normalizeStability(edge.stableTicks);

  const confidence = clamp01(edge.confidence ?? edge.evidence?.confidence ?? 0);

  const counterfactual = normalizeCounterfactual(
    edge.counterfactualSupport ?? edge.counterfactual_support,
  );

  if (edge.kind === "causal_estimate") {
    return clamp01(
      confidence * cfg.causalConfidence +
        support * cfg.causalSupport +
        counterfactual * cfg.causalCounterfactual,
    );
  }

  return clamp01(
    support * cfg.regularSupport + stability * cfg.regularStability,
  );
}

function scoreAnatomyEdge(edge, anatomy, edgeIndex = 0) {
  const cfg = ATLAS_CONFIG.anatomy;

  const edgeId = stableEdgeId(edge, edgeIndex);

  if (anatomy?.bridgeEdgeIds?.has?.(edgeId)) {
    return cfg.bridgeEdge;
  }

  const source = anatomy?.index?.nodesById?.get?.(edge.sourceId);

  const target = anatomy?.index?.nodesById?.get?.(edge.targetId);

  if (
    source?.community &&
    target?.community &&
    source.community !== target.community
  ) {
    return cfg.boundaryEdge;
  }

  if (isStructuralAtlasEdge(edge)) {
    return clamp01(cfg.structuralEdge * 0.5 + structuralEdgeScore(edge) * 0.5);
  }

  return cfg.backgroundEdge;
}

function edgeDiffScore(edge, baselineEdge) {
  if (!baselineEdge) {
    return 1;
  }

  const current = {
    structure: structuralEdgeScore(edge),

    activity: edgeRecency(edge, edge.__atlasTick ?? 0),

    learning: scoreLearningEdge(edge),

    prediction: scorePredictionEdge(edge),

    evidence: scoreEvidenceEdge(edge),
  };

  const baseline = {
    structure: structuralEdgeScore(baselineEdge),

    activity: edgeRecency(baselineEdge, baselineEdge.__atlasTick ?? 0),

    learning: scoreLearningEdge(baselineEdge),

    prediction: scorePredictionEdge(baselineEdge),

    evidence: scoreEvidenceEdge(baselineEdge),
  };

  const keys = Object.keys(current);

  return clamp01(
    keys.reduce((sum, key) => sum + Math.abs(current[key] - baseline[key]), 0) /
      keys.length,
  );
}

/**
 * Score one graph edge for one atlas mode.
 *
 * Existing callers can continue using the first four parameters.
 *
 * context:
 * {
 *   anatomy,
 *   edgeIndex,
 *   baselineEdge,
 *   baselineTick
 * }
 */
export function atlasEdgeScore(
  edge,
  mode,
  tick = 0,
  signals = null,
  context = {},
) {
  if (mode === "structure") {
    return structuralEdgeScore(edge);
  }

  if (mode === "activity") {
    return edgeRecency(edge, tick);
  }

  if (mode === "learning") {
    return scoreLearningEdge(edge);
  }

  if (mode === "prediction") {
    return scorePredictionEdge(edge);
  }

  if (mode === "motor") {
    return scoreMotorEdge(edge, signals);
  }

  if (mode === "evidence") {
    return scoreEvidenceEdge(edge);
  }

  if (mode === "anatomy") {
    return context.anatomy
      ? scoreAnatomyEdge(edge, context.anatomy, context.edgeIndex ?? 0)
      : structuralEdgeScore(edge);
  }

  if (mode === "dynamics") {
    const cfg = ATLAS_CONFIG.dynamics;

    return clamp01(
      edgeRecency(edge, tick) * cfg.edgeActivity +
        scoreLearningEdge(edge) * cfg.edgeLearning +
        scorePredictionEdge(edge) * cfg.edgePrediction,
    );
  }

  if (mode === "diff") {
    if (!context.baselineEdge) {
      return 0;
    }

    return edgeDiffScore(
      {
        ...edge,
        __atlasTick: tick,
      },
      {
        ...context.baselineEdge,

        __atlasTick: context.baselineTick ?? tick,
      },
    );
  }

  return structuralEdgeScore(edge);
}

// Region summaries need degree, articulation points and bridges, not the
// all-pairs betweenness calculation used by node anatomy scores.
function regionTopology(index) {
  const undirected = buildUndirectedStructuralAdjacency(index);
  const topology = articulationAndBridges(index, undirected);
  const denominator = Math.max(1, index.nodes.length - 1);
  return {
    ...topology,
    nodes: new Map(index.nodes.map(node => [node.id, {
      degreeCentrality: (undirected.adjacency.get(node.id)?.size ?? 0) / denominator,
      articulationPoint: topology.articulationPoints.has(node.id),
    }])),
  };
}

export function atlasRegions(
  nodes,
  edges,
  sectorLabels,
  sectorDescriptions,
  signals,
  existingIndex = null,
  options = {},
) {
  const index = existingIndex ?? buildAtlasGraph(nodes, edges);

  const anatomy = options.anatomy ?? regionTopology(index);

  const grouped = new Map();

  for (const node of index.nodes) {
    if (!node.community || node.community === "isolated") {
      continue;
    }

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

      boundaryEdges: 0,
      graphBridges: 0,
      articulationPoints: 0,
      hubs: 0,
    };

    item.nodeIds.push(node.id);

    item.kinds[node.kind] = (item.kinds[node.kind] ?? 0) + 1;

    const signal = signals.get(node.id) ?? {};

    for (const key of [
      "structure",
      "activity",
      "learning",
      "prediction",
      "motor",
      "evidence",
      "diff",
      "anatomy",
    ]) {
      item[key] += finite(signal[key], 0);
    }

    item.dynamics += dynamicsScore(signal);

    const nodeAnatomy = anatomy.nodes.get(node.id);

    if (nodeAnatomy?.articulationPoint) {
      item.articulationPoints += 1;
    }

    // Simple deterministic hub indicator.
    // This is a presentation heuristic, not a graph-theoretic definition.
    if (finite(nodeAnatomy?.degreeCentrality, 0) >= 0.75) {
      item.hubs += 1;
    }

    grouped.set(node.community, item);
  }

  index.edges.forEach((edge, edgeIndex) => {
    if (!isStructuralAtlasEdge(edge)) {
      return;
    }

    const source = index.nodesById.get(edge.sourceId);

    const target = index.nodesById.get(edge.targetId);

    if (!source?.community || !target?.community) {
      return;
    }

    if (source.community !== target.community) {
      if (grouped.has(source.community)) {
        grouped.get(source.community).boundaryEdges += 1;
      }

      if (grouped.has(target.community)) {
        grouped.get(target.community).boundaryEdges += 1;
      }
    }

    const edgeId = stableEdgeId(edge, edgeIndex);

    if (anatomy.bridgeEdgeIds.has(edgeId)) {
      if (grouped.has(source.community)) {
        grouped.get(source.community).graphBridges += 1;
      }

      if (
        target.community !== source.community &&
        grouped.has(target.community)
      ) {
        grouped.get(target.community).graphBridges += 1;
      }
    }
  });

  return [...grouped.values()]
    .map((region) => {
      const n = Math.max(1, region.nodeIds.length);

      for (const key of [
        "structure",
        "activity",
        "learning",
        "prediction",
        "motor",
        "evidence",
        "diff",
        "anatomy",
        "dynamics",
      ]) {
        region[key] /= n;
      }

      const description = sectorDescriptions?.get?.(region.id) ?? null;

      return {
        ...region,

        // Compatibility alias.
        // Prefer boundaryEdges in new code.
        bridges: region.boundaryEdges,

        label: sectorLabels?.get?.(region.id) ?? "S-???",

        interpretation: description?.interpretation ?? "Mixed integration",

        total: region.nodeIds.length,
      };
    })
    .sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
}

function bfsPath(
  startId,
  targetPredicate,
  index,
  reverse = false,
  maxDepth = ATLAS_CONFIG.pathMaxDepth,
) {
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
      const pathEdges = [];

      let cursor = id;

      while (cursor != null) {
        nodeIds.push(cursor);

        const edge = parentEdge.get(cursor);

        if (edge) {
          pathEdges.push(edge);
        }

        cursor = parent.get(cursor);
      }

      nodeIds.reverse();
      pathEdges.reverse();

      return {
        nodeIds,
        edges: pathEdges,
      };
    }

    if (currentDepth >= maxDepth) {
      continue;
    }

    for (const next of adjacency.get(id) ?? []) {
      if (depth.has(next.id)) {
        continue;
      }

      depth.set(next.id, currentDepth + 1);

      parent.set(next.id, id);

      parentEdge.set(next.id, next.edge);

      queue.push(next.id);
    }
  }

  return null;
}

export function cognitivePath(
  startId,
  nodes,
  edges,
  maxDepth = ATLAS_CONFIG.pathMaxDepth,
  existingIndex = null,
) {
  if (!startId) {
    return null;
  }

  const index = existingIndex ?? buildAtlasGraph(nodes, edges);

  const start = index.nodesById.get(startId);

  if (!start) {
    return null;
  }

  const sensoryTarget = (node) => node?.kind === "sense";

  if (isMotorNode(start)) {
    return bfsPath(startId, sensoryTarget, index, true, maxDepth);
  }

  const downstream = bfsPath(startId, isMotorNode, index, false, maxDepth);

  if (downstream) {
    return downstream;
  }

  return bfsPath(startId, sensoryTarget, index, true, maxDepth);
}

function fieldMatchScore(field, needle, baseWeight) {
  if (!field) {
    return 0;
  }

  if (field === needle) {
    return baseWeight;
  }

  if (field.startsWith(needle)) {
    return baseWeight * 0.82;
  }

  const tokens = field.split(" ");

  if (tokens.includes(needle)) {
    return baseWeight * 0.7;
  }

  if (tokens.some((token) => token.startsWith(needle))) {
    return baseWeight * 0.58;
  }

  if (field.includes(needle)) {
    return baseWeight * 0.42;
  }

  const needleTokens = needle.split(" ").filter(Boolean);

  if (
    needleTokens.length > 1 &&
    needleTokens.every((token) => field.includes(token))
  ) {
    return baseWeight * 0.5;
  }

  return 0;
}

/**
 * Search by id, kind, semantic name or physical binding.
 *
 * Results remain plain node objects for backwards compatibility, but
 * are ranked by match quality.
 *
 * When the matched field or score are needed, use searchAtlasNodesRanked.
 */
export function searchAtlasNodes(nodes, query, limit = 20) {
  return searchAtlasNodesRanked(nodes, query, limit).map((item) => item.node);
}

export function searchAtlasNodesRanked(nodes, query, limit = 20) {
  const needle = normalizeText(query);

  if (!needle) {
    return [];
  }

  return nodes
    .map((node) => {
      let score = 0;
      let matchedField = null;

      for (const [fieldName, weight] of SEARCH_FIELDS) {
        const field = normalizeText(node?.[fieldName]);

        const fieldScore = fieldMatchScore(field, needle, weight);

        if (fieldScore > score) {
          score = fieldScore;

          matchedField = fieldName;
        }
      }

      return {
        node,
        score,
        matchedField,
      };
    })
    .filter((item) => item.score > 0)
    .sort(
      (a, b) =>
        b.score - a.score || String(a.node.id).localeCompare(String(b.node.id)),
    )
    .slice(0, Math.max(0, limit));
}

export function learningFrontier(nodes, signals, limitOrOptions = 8) {
  const options =
    typeof limitOrOptions === "object" && limitOrOptions !== null
      ? limitOrOptions
      : {
          limit: limitOrOptions,
        };

  const limit = Math.max(0, finite(options.limit, 8));

  const minScore = clamp01(
    options.minScore ?? ATLAS_CONFIG.learning.frontierMinScore,
  );

  return [...nodes]
    .map((node) => ({
      node,

      score: finite(signals.get(node.id)?.learning, 0),
    }))
    .filter((item) => item.score > minScore)
    .sort(
      (a, b) =>
        b.score - a.score || String(a.node.id).localeCompare(String(b.node.id)),
    )
    .slice(0, limit);
}
