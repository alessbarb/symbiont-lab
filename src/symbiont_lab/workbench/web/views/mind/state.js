/**
 * Mutable singleton state for the mounted Mind view.
 *
 * State lives here so renderers/controllers can share one explicit model
 * without circular dependencies through mind.js.
 */

export const identityHistory = [];
export const mindHistory = [];
export const milestones = [];
export const historySnapshots = [];
export const selfRegionHistory = new Map();
export const selfDependencyHistory = new Map();

export const tel = {
  tick: null,
  alive: null,
  schemaConf: null,
  schemaParts: null,
  schemaSensory: null,
  schemaCognitive: null,
  motorOrigin: null,
  predictorCount: null,
  sensorimotorPatterns: null,
  motorPrimitives: null,
  cognitiveMotorPrimitives: null,
  motorRepertoireSize: null,
  recurrentPrimitiveCandidates: null,
  maxPrimitiveSamples: null,
  fullCompetenceGateCandidates: null,
  motorReadoutNodes: null,
  primitiveReadoutNodes: null,
  cognitiveMotorOutputEdges: null,
  cognitiveConcepts: null,
  cognitiveReadouts: null,
  predictionError: null,
  prospective: null,
  prospectiveEV: null,
  slmActive: null,
  slmModels: null,
  jointMotion: null,
  resourceProgress: null,
  displacement: null,
  mechanicalWork: null,
  metabolicCost: null,
  metabolicReserve: null,
  resourceDistance: null,
  resourceRemaining: null,
  absorbedEnergy: null,
  activeEffectors: null,
};

export const snap = {
  senses: [],
  beliefs: [],
  sensoryDevelopment: [],
  sensoryRelations: [],
  cognition: null,
  topology: null,
  selfModel: null,
  bodySchema: null,
  sensoryPhenotype: null,
  metabolism: null,
  degradation: null,
  development: null,
  sampling: null,
  details: null,
  displayId: null,
  instanceId: null,
  organismState: null,
  observerAnalysis: null,
  observerSemantics: null,
  provenance: null,
  sensorimotor: null,
  outcome: null,
};

export const graph = {
  nodes: [],
  edges: [],
  cachedPositions: new Map(),
  alpha: 1.0,
  isRunning: false,
  scale: 1.0,
  panX: 0,
  panY: 0,
  hoveredNode: null,
  selectedNodeId: null,
  focusedSectorId: null,
  fmriEnabled: true,
  communities: new Map(),
  components: [],
  viewMode: 'full',
  atlasMode: 'structure',
  pathDepth: 2,
  replaySnapshot: null,
  replayTick: null,
  sectorMemory: new Map(),
  sectorLabels: new Map(),
  sectorDescriptions: new Map(),
  sectorAnchors: new Map(),
  layoutAffinities: [],
  bridgeEdges: new Set(),
  atlasSignals: new Map(),
  atlasRegions: [],
  atlasPath: null,
  learningFrontier: [],
  atlasRegionHitAreas2d: [],
  atlasRegionHitAreas3d: [],
  regionLineage: new Map(),
  regionEvents: [],
  atlasDiff: null,
  diffBaselineSnapshot: null,
  diffBaselineTick: null,
  cognitiveStructures: { hubs: [], bottlenecks: [], loops: [] },
  observedFlow: { tick: 0, windowTicks: 48, recentEdgeCount: 0, paths: [] },
  cognitiveEpisodes: [],
  timelineIndex: null,
  hiddenMotor: { actuators: 0, motorEdges: 0 },
  dimension: '2d',
  threeDMode: 'relational',
  camera3d: { yaw: -0.55, pitch: 0.34, distance: 900 },
  world3d: new Map(),
  velocity3d: new Map(),
  projected3d: new Map(),
  nextSectorId: 1,
};


export function resetMindDataState() {
  for (const key of Object.keys(tel)) tel[key] = null;
  for (const key of Object.keys(snap)) snap[key] = Array.isArray(snap[key]) ? [] : null;
  snap.senses = [];
  snap.beliefs = [];
  snap.sensoryDevelopment = [];
  snap.sensoryRelations = [];

  identityHistory.length = 0;
  mindHistory.length = 0;
  milestones.length = 0;
  historySnapshots.length = 0;
  selfRegionHistory.clear();
  selfDependencyHistory.clear();

  graph.cachedPositions.clear();
  graph.alpha = 1;
  graph.scale = 1;
  graph.panX = 0;
  graph.panY = 0;
  graph.hoveredNode = null;
  graph.selectedNodeId = null;
  graph.focusedSectorId = null;
  graph.atlasMode = 'structure';
  graph.viewMode = 'full';
  graph.replaySnapshot = null;
  graph.replayTick = null;
  graph.world3d.clear();
  graph.velocity3d.clear();
  graph.projected3d.clear();
  graph.atlasSignals.clear();
  graph.atlasRegions = [];
  graph.atlasPath = null;
  graph.learningFrontier = [];
  graph.atlasRegionHitAreas2d = [];
  graph.atlasRegionHitAreas3d = [];
  graph.regionLineage.clear();
  graph.regionEvents = [];
  graph.atlasDiff = null;
  graph.diffBaselineSnapshot = null;
  graph.diffBaselineTick = null;
  graph.cognitiveStructures = { hubs: [], bottlenecks: [], loops: [] };
  graph.observedFlow = { tick: 0, windowTicks: 48, recentEdgeCount: 0, paths: [] };
  graph.cognitiveEpisodes = [];
  graph.timelineIndex = null;
}
