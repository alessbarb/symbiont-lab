/**
 * Passive, evidence-bounded "what is happening now" projection for the
 * Cognitive Observatory. No inferred intent, semantics, goals or feedback.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function topBy(items, score, limit = 4) {
  return [...items]
    .sort((a,b) => score(b) - score(a) || String(a.id ?? '').localeCompare(String(b.id ?? '')))
    .slice(0, limit);
}

export function cognitiveSituation({
  nodes = [],
  edges = [],
  regions = [],
  signals = new Map(),
  flow = null,
  frontierClusters = [],
  structures = null,
  tick = 0,
  motorOrigin = 'none',
  motorCompetences = [],
} = {}) {
  const byKind = new Map();
  for (const node of nodes) {
    if (!byKind.has(node.kind)) byKind.set(node.kind, []);
    byKind.get(node.kind).push(node);
  }

  const allActiveNodes = nodes.filter(
    node => finite(signals.get(node.id)?.activity, 0) > 0.08
  );
  const activeNodes = topBy(
    allActiveNodes,
    node => finite(signals.get(node.id)?.activity, 0),
    8,
  ).map(node => ({
    id: node.id,
    kind: node.kind,
    score: clamp01(signals.get(node.id)?.activity),
  }));

  const allActiveRegions = regions.filter(region => finite(region.activity, 0) > 0.04);
  const activeRegions = topBy(
    allActiveRegions,
    region => finite(region.activity, 0),
    5,
  ).map(region => ({
    id: region.id,
    label: region.label,
    interpretation: region.interpretation,
    score: clamp01(region.activity),
  }));

  const predictionNodes = (byKind.get('predictor') ?? []).length;
  const predictionErrors = nodes
    .map(node => ({
      id: node.id,
      error: clamp01(signals.get(node.id)?.error),
    }))
    .filter(item => item.error > 0)
    .sort((a,b) => b.error - a.error || a.id.localeCompare(b.id));
  const predictionPressure = predictionErrors.length
    ? predictionErrors.reduce((sum,item) => sum + item.error, 0) / predictionErrors.length
    : 0;

  const recentPaths = flow?.paths ?? [];
  const observedMotorPaths = recentPaths.filter(path => {
    const last = path.nodeIds?.[path.nodeIds.length - 1] ?? '';
    return String(last).startsWith('motor_primitive:') ||
      String(last).startsWith('readout_motor:') ||
      String(last).startsWith('readout_primitive:');
  });

  const observedSensoryStarts = recentPaths.filter(path => {
    const first = path.nodeIds?.[0];
    const node = nodes.find(item => item.id === first);
    return node?.kind === 'sense';
  });

  const recentEdgeCoverage = edges.length
    ? Math.min(1, finite(flow?.recentEdgeCount, 0) / edges.length)
    : 0;

  const learningNodes = frontierClusters.reduce(
    (sum, cluster) => sum + (cluster.nodeIds?.length ?? 0),
    0,
  );
  const learningBoundaryContacts = frontierClusters.reduce(
    (sum, cluster) => sum + (cluster.boundaryIds?.length ?? 0),
    0,
  );

  const stages = [
    {
      id: 'perception',
      label: 'Perception',
      total: (byKind.get('sense') ?? []).length,
      active: allActiveNodes.filter(item => item.kind === 'sense').length,
    },
    {
      id: 'integration',
      label: 'Integration',
      total:
        (byKind.get('concept') ?? []).length +
        (byKind.get('state') ?? []).length +
        (byKind.get('gate') ?? []).length,
      active: allActiveNodes.filter(item =>
        ['concept','state','gate'].includes(item.kind)
      ).length,
    },
    {
      id: 'prediction',
      label: 'Prediction',
      total: predictionNodes,
      active: allActiveNodes.filter(item => item.kind === 'predictor').length,
    },
    {
      id: 'readout',
      label: 'Readout',
      total: (byKind.get('readout') ?? []).length,
      active: allActiveNodes.filter(item => item.kind === 'readout').length,
    },
    {
      // motor_primitive never exists as a CognitiveGraph node kind by design; count real competences instead.
      id: 'motor',
      label: 'Motor capability',
      total: motorCompetences.length,
      active: motorCompetences.filter(item => item?.executable === true).length,
    },
  ];

  return {
    tick,
    activeNodes,
    activeNodeCount: allActiveNodes.length,
    activeRegions,
    activeRegionCount: allActiveRegions.length,
    stages,
    prediction: {
      predictors: predictionNodes,
      pressure: clamp01(predictionPressure),
      highestErrors: predictionErrors.slice(0, 5),
    },
    learning: {
      zones: frontierClusters.length,
      nodes: learningNodes,
      boundaryContacts: learningBoundaryContacts,
      peak: frontierClusters.length
        ? Math.max(...frontierClusters.map(cluster => finite(cluster.maxScore, 0)))
        : 0,
    },
    flow: {
      recentRelations: finite(flow?.recentEdgeCount, 0),
      relationCoverage: recentEdgeCoverage,
      paths: recentPaths.length,
      sensoryStarts: observedSensoryStarts.length,
      motorPaths: observedMotorPaths.length,
      longestPath: recentPaths.reduce(
        (best,path) => Math.max(best, path.nodeIds?.length ?? 0),
        0,
      ),
    },
    structure: {
      hubs: structures?.hubs?.length ?? 0,
      bottlenecks: structures?.bottlenecks?.length ?? 0,
      loops: structures?.loops?.length ?? 0,
    },
    motorOrigin: motorOrigin ?? 'none',
    provenance: {
      owner: 'observer',
      projection: 'cognitive-observatory-v1',
      feedsBack: false,
      claimsIntent: false,
    },
  };
}
