/**
 * mind.js — Cognitive ("Mind") view for Symbiont Lab.
 *
 * ES module.  Public API:
 *   mount(root: HTMLElement)  → void
 *   unmount()                 → void
 *
 * Displays one live symbiont organism across six research tabs:
 *   Overview · Identity · Sensory · Cognition · Motor Learning · History
 *
 * SSE endpoints consumed:
 *   /api/organism   — type:'cognition' | type:'vitals' events (lightweight telemetry)
 *   /fleet          — instance list (picks first alive instance automatically)
 *   /instances/:id — full snapshot for the chosen instance
 *
 * No external dependencies (no Three.js). Uses CSS variables from app.css.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Constants & Palette
// ─────────────────────────────────────────────────────────────────────────────

import { enrichGraphModel } from './mind/graph-model.js';
import { filterGraphForView, graphSubgraphIds } from './mind/graph-selection.js';
import { computeObserverMapCoordinates, evaluateObserverRegime } from './mind/observer-map-model.js';
import { compactSelfLabel, observerContextForNode, sensorySemantic } from './mind/semantics.js';
import { augmentLearnedGraph } from './mind/learning-graph.js';
import { cartographicGraph } from './mind/cartographic-view.js';
import { buildLayoutAffinities, deriveFunctionalSectors, describeFunctionalSector, sectorBridges } from './mind/functional-sectors.js';

const NS = 'http://www.w3.org/2000/svg';

const PAL = {
  cyan:   '#50d9ff',
  violet: '#a777ff',
  amber:  '#ffbd54',
  coral:  '#ff7f83',
  mint:   '#71e9ba',
  muted:  '#627888',
  text:   '#c8d8e4',
  bg:     '#060e18',
  surface:'#0b1929',
  line:   '#1a2d40',
};

// Observer-defined reference zones. These are analytical overlays only:
 // they are not learned categories, attractors or concepts owned by Symbiont.
const REGIMES = [
  { id: 'low_activity',       name: 'Baja actividad',       x: -160, y:  130, color: PAL.cyan,  radius: 95,  description: 'Observer projection: low measured activity and low predictive tension.' },
  { id: 'sustained_activity', name: 'Actividad sostenida',  x:  170, y:  110, color: PAL.mint,  radius: 100, description: 'Observer projection: sustained activity with comparatively low predictive tension.' },
  { id: 'transient_activity', name: 'Actividad transitoria',x:  -40, y:  -50, color: PAL.amber, radius: 90,  description: 'Observer projection: intermediate activity with elevated short-term predictive tension.' },
  { id: 'high_tension',       name: 'Tensión elevada',      x:  180, y: -170, color: PAL.coral, radius: 95,  description: 'Observer projection: high activity and/or predictive tension.' },
];

// Physics constants for the Cognition force-directed graph
const REPULSION    = 7500;
const SPRING_K     = 0.045;
const SPRING_LEN   = 80;
const CENTER_G     = 0.015;
const DAMPING      = 0.86;
const ALPHA_DECAY  = 0.985;
const ALPHA_MIN    = 0.001;

// ─────────────────────────────────────────────────────────────────────────────
// Module-level state (single active view by public API contract)
// ─────────────────────────────────────────────────────────────────────────────

let _root           = null;
let _organismSse    = null;   // EventSource: /api/organism
let _fleetSse       = null;   // EventSource: /fleet
let _instanceSse    = null;   // EventSource: /instance/:id/stream
let _activeInstance = null;   // current instance id
let _activeRunId    = null;   // current observatory run id when known
let _localMindActive = false;  // Physics3D rich snapshot is authoritative when present
let _rafId          = null;   // cognition-graph animation frame
let _regimRafId     = null;   // regime-compass animation frame
let _resizeObs      = null;   // ResizeObserver on canvas wrappers
let _activeTab      = 'overview';
const _identityHistory = [];
const _mindHistory = [];
const _milestones = [];
const _historySnapshots = [];
const _selfRegionHistory = new Map();
const _selfDependencyHistory = new Map();
let _historySelectionTick = null;

// Lifecycle / UI state merged from the instance-oriented refactor.
let _uid                    = 'default';
let _rootStyleBeforeMount   = '';
let _lastUITime             = 0;
const UI_THROTTLE_MS        = 66; // ~15 FPS for text-only telemetry updates
let _graphWindowMouseMove   = null;
let _graphWindowMouseUp     = null;

// Telemetry state (updated by SSE events)
const _tel = {
  tick:             null,
  alive:            null,
  schemaConf:       null,
  schemaParts:      null,
  schemaSensory:    null,
  schemaCognitive:  null,
  motorOrigin:      null,
  predictorCount:   null,
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
  predictionError:  null,
  prospective:      null,
  prospectiveEV:    null,
  slmActive:        null,
  slmModels:        null,
  jointMotion:      null,
  resourceProgress: null,
  displacement:     null,
  mechanicalWork:   null,
  metabolicCost:    null,
  metabolicReserve: null,
  resourceDistance: null,
  resourceRemaining: null,
  absorbedEnergy: null,
  activeEffectors: null,
};

// Snapshot-derived state (updated by /instance/:id/stream)
const _snap = {
  senses:           [],
  beliefs:          [],
  sensoryDevelopment: [],
  sensoryRelations: [],
  cognition:        null,
  topology:         null,
  selfModel:        null,
  bodySchema:       null,
  sensoryPhenotype: null,
  metabolism:       null,
  degradation:      null,
  development:      null,
  sampling:         null,
  details:          null,
  displayId:        null,
  instanceId:       null,
  organismState:    null,
  observerAnalysis:  null,
  observerSemantics: null,
  provenance:        null,
  sensorimotor:      null,
  outcome:           null,
};

// Cognition-graph physics state
const _graph = {
  nodes:          [],
  edges:          [],
  cachedPositions: new Map(),
  alpha:          1.0,
  isRunning:      false,
  scale:          1.0,
  panX:           0,
  panY:           0,
  hoveredNode:    null,
  selectedNodeId: null,
  fmriEnabled:    true,
  communities:    new Map(),
  components:     [],
  viewMode:       'connected',
  pathDepth:      2,
  replaySnapshot: null,
  replayTick:     null,
  sectorMemory:   new Map(),
  sectorLabels:   new Map(),
  sectorDescriptions: new Map(),
  sectorAnchors:  new Map(),
  layoutAffinities: [],
  bridgeEdges:    new Set(),
  hiddenMotor:    { actuators: 0, motorEdges: 0 },
  nextSectorId:   1,
};

// Regime compass state
const _compass = {
  trail:        [],
  sonarPhase:   0,
  lastCoord:    null,
  velocity:     0,
  showContours: true,
  showTrail:    true,
  mousePos:     null,
};

// ─────────────────────────────────────────────────────────────────────────────
// SVG & DOM helpers
// ─────────────────────────────────────────────────────="
// ─────────────────────────────────────────────────────────────────────────────

/** Create an SVG element with a namespace and optional attributes. */
function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

/** Create an HTML element with optional className and inline styles. */
function el(tag, cls = '', styles = {}) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  Object.assign(e.style, styles);
  return e;
}

/** Format a ratio (0–1) as a percentage string. */
function pct(value) {
  return `${Math.round(Math.max(0, Math.min(1, value ?? 0)) * 100)}%`;
}

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finiteNumber(value, 0)));
}

function classRatio(value, maximum) {
  const number = finiteNumber(value, 0);
  return maximum > 0 ? clamp01(number / maximum) : 0;
}

function shortId(value, head = 10, tail = 6) {
  const text = String(value ?? '');
  if (text.length <= head + tail + 1) return text;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}

/** Hash a string to an integer (for deterministic seeding). */
function hashStr(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  return Math.abs(h);
}

// ─────────────────────────────────────────────────────────────────────────────
// Layout HTML
// ─────────────────────────────────────────────────────────────────────────────

/** Build the complete DOM structure for the Mind view and inject it into root. */
function buildLayout(root) {
  root.innerHTML = '';
  root.style.cssText = `
    height: 100%;
    display: grid;
    grid-template-rows: auto 1fr auto;
    overflow: hidden;
    background: var(--bg-deep, ${PAL.bg});
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  // ── Tab bar ─────────────────────────────────────────────────────────────────
  const tabBar = el('nav', 'mind-tab-bar');
  tabBar.setAttribute('aria-label', 'Mind view tabs');
  tabBar.style.cssText = `
    display: flex;
    gap: 4px;
    padding: 8px 12px 0;
    border-bottom: 1px solid var(--line, ${PAL.line});
    background: var(--surface, ${PAL.surface});
    flex-shrink: 0;
  `;

  const TABS = [
    { id: 'overview',   label: 'Overview' },
    { id: 'phenotype',  label: 'Identity' },
    { id: 'sensory',    label: 'Sensory' },
    { id: 'cognition',  label: 'Cognition' },
    { id: 'motor',      label: 'Motor Learning' },
    { id: 'history',    label: 'History' },
  ];

  for (const tab of TABS) {
    const btn = el('button', 'mind-tab');
    btn.dataset.tab = tab.id;
    btn.textContent = tab.label;
    btn.setAttribute('aria-pressed', tab.id === _activeTab ? 'true' : 'false');
    btn.style.cssText = `
      padding: 7px 16px;
      border: none;
      border-bottom: 2px solid transparent;
      background: none;
      color: var(--muted, ${PAL.muted});
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      border-radius: 6px 6px 0 0;
      transition: color 0.15s, border-color 0.15s;
    `;
    btn.addEventListener('click', () => switchTab(tab.id));
    tabBar.appendChild(btn);
  }
  root.appendChild(tabBar);

  // ── Workspace: senses panel + canvas ────────────────────────────────────────
  const workspace = el('div', 'mind-workspace');
  workspace.id = 'mind-workspace';
  workspace.style.cssText = `
    display: grid;
    grid-template-columns: 200px 1fr;
    overflow: hidden;
    min-height: 0;
  `;

  // Left senses panel
  const sensesPanel = el('aside', 'mind-senses-panel');
  sensesPanel.id = 'mind-senses-panel';
  sensesPanel.style.cssText = `
    border-right: 1px solid var(--line, ${PAL.line});
    background: var(--surface, ${PAL.surface});
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0;
  `;
  const sensesHeading = el('div', '');
  sensesHeading.style.cssText = `
    padding: 10px 12px 8px;
    font-size: 11px;
    font-weight: 600;
    color: var(--muted, ${PAL.muted});
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 1px solid var(--line, ${PAL.line});
    flex-shrink: 0;
  `;
  sensesHeading.textContent = 'Sensory State';
  const sensesList = el('div', '');
  sensesList.id = 'mind-senses-list';
  sensesList.style.cssText = 'flex: 1; overflow-y: auto;';
  sensesPanel.appendChild(sensesHeading);
  sensesPanel.appendChild(sensesList);

  // Contextual cognition inspector. Reuses the left rail only on Cognition so
  // sensory inventory does not consume space where it adds no analytical value.
  const cognitionInspector = el('aside', 'mind-cognition-inspector');
  cognitionInspector.id = 'mind-cognition-inspector';
  cognitionInspector.style.cssText = `
    border-right:1px solid var(--line, ${PAL.line});
    background:var(--surface, ${PAL.surface});
    overflow-y:auto;
    display:none;
    flex-direction:column;
    min-width:0;
  `;
  const cognitionInspectorHeading = el('div', '');
  cognitionInspectorHeading.style.cssText = `
    padding:10px 12px 8px;
    font-size:11px;font-weight:600;color:var(--muted, ${PAL.muted});
    text-transform:uppercase;letter-spacing:.08em;
    border-bottom:1px solid var(--line, ${PAL.line});
    flex-shrink:0;
  `;
  cognitionInspectorHeading.textContent = 'Cognitive Inspector';
  const cognitionInspectorBody = el('div', '');
  cognitionInspectorBody.id = 'mind-cognition-inspector-body';
  cognitionInspectorBody.style.cssText = 'padding:10px 11px 18px;overflow-y:auto;flex:1;';
  cognitionInspector.append(cognitionInspectorHeading, cognitionInspectorBody);

  // Main canvas area
  const canvasArea = el('div', 'mind-canvas-area');
  canvasArea.style.cssText = 'position: relative; overflow: hidden; min-height: 0;';

  // Phenotype / Self comparison — observed expression vs organism-owned self-model
  const identityWrap = el('div', 'mind-identity-wrap');
  identityWrap.id = 'mind-identity-wrap';
  identityWrap.style.cssText = `
    position: absolute; inset: 0;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 230px minmax(0, 1fr);
    gap: 1px;
    background: var(--line, ${PAL.line});
    min-width: 0;
    min-height: 0;
  `;

  const phenotypePane = el('section', 'mind-identity-pane');
  phenotypePane.style.cssText = `
    position: relative; min-width: 0; min-height: 0;
    overflow: hidden; background: var(--bg-deep, ${PAL.bg});
    display: grid; grid-template-rows: auto 1fr;
  `;
  const phenotypeHeading = el('header', '');
  phenotypeHeading.style.cssText = `
    padding: 10px 14px 9px;
    border-bottom: 1px solid var(--line, ${PAL.line});
    background: rgba(11,25,41,.82);
  `;
  const phenotypeTitle = el('strong', '');
  phenotypeTitle.style.cssText = 'display:block;font-size:12px;color:var(--text,#c8d8e4);';
  phenotypeTitle.textContent = 'Observed organism';
  const phenotypeSub = el('small', '');
  phenotypeSub.style.cssText = 'display:block;margin-top:2px;color:var(--muted);font-size:10px;';
  phenotypeSub.textContent = 'Externally measurable functional expression.';
  phenotypeHeading.append(phenotypeTitle, phenotypeSub);

  const phenotypeSvg = svgEl('svg', {
    id: 'mind-phenotype-svg',
    viewBox: '0 0 900 720',
    role: 'img',
    'aria-label': 'Observed functional phenotype of the Symbiont organism',
  });
  phenotypeSvg.style.cssText = 'width:100%;height:100%;display:block;min-width:0;min-height:0;';
  phenotypePane.append(phenotypeHeading, phenotypeSvg);

  const selfPane = el('section', 'mind-identity-pane');
  selfPane.style.cssText = `
    position: relative; min-width: 0; min-height: 0;
    overflow: hidden; background: var(--bg-deep, ${PAL.bg});
    display: grid; grid-template-rows: auto 1fr;
  `;
  const selfHeading = el('header', '');
  selfHeading.style.cssText = `
    padding: 10px 14px 9px;
    border-bottom: 1px solid var(--line, ${PAL.line});
    background: rgba(11,25,41,.82);
  `;
  const selfTitle = el('strong', '');
  selfTitle.style.cssText = 'display:block;font-size:12px;color:var(--text,#c8d8e4);';
  selfTitle.textContent = 'Self-model';
  const selfSub = el('small', '');
  selfSub.style.cssText = 'display:block;margin-top:2px;color:var(--muted);font-size:10px;';
  selfSub.textContent = 'Organism-owned representation of what belongs to self.';
  selfHeading.append(selfTitle, selfSub);

  const selfPanel = el('div', 'mind-self-panel');
  selfPanel.id = 'mind-self-panel';
  selfPanel.style.cssText = `
    min-width: 0; min-height: 0; overflow: auto;
    padding: 12px 14px 24px;
    background: var(--bg-deep, ${PAL.bg});
  `;
  selfPane.append(selfHeading, selfPanel);

  const gapPane = el('aside', 'mind-identity-gap');
  gapPane.id = 'mind-identity-gap';
  gapPane.style.cssText = `
    min-width:0;min-height:0;overflow:auto;
    background:rgba(7,18,30,.96);
    border-left:1px solid var(--line,${PAL.line});
    border-right:1px solid var(--line,${PAL.line});
    padding:12px 11px 18px;
  `;

  identityWrap.append(phenotypePane, gapPane, selfPane);

  // Sensory map placeholder panel
  const sensoryWrap = el('div', 'mind-sensory-wrap hidden');
  sensoryWrap.id = 'mind-sensory-wrap';
  sensoryWrap.style.cssText = `
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 14px;
    color: var(--muted, ${PAL.muted}); font-size: 13px;
    background: var(--bg-deep, ${PAL.bg});
    padding: 24px;
  `;
  // Sensory map SVG
  const sensoryMapSvg = svgEl('svg', {
    id: 'mind-sensory-map-svg',
    viewBox: '0 0 900 600',
    role: 'img',
    'aria-label': 'Sensory map — receptor groups and activity levels',
  });
  sensoryMapSvg.style.cssText = 'width: 100%; max-height: 100%; flex: 1;';
  const sensoryDetail = el('div', '');
  sensoryDetail.id = 'mind-sensory-detail';
  sensoryDetail.style.cssText = `
    font-size: 11px; color: var(--muted, ${PAL.muted}); padding: 8px 16px;
    text-align: center; max-width: 600px;
  `;
  sensoryDetail.textContent = 'Select a sense channel to inspect its receptor bindings and downstream path.';
  sensoryWrap.appendChild(sensoryMapSvg);
  sensoryWrap.appendChild(sensoryDetail);

  // Cognition canvas
  const cognitionWrap = el('div', 'mind-cognition-wrap hidden');
  cognitionWrap.id = 'mind-cognition-wrap';
  cognitionWrap.style.cssText = 'position: absolute; inset: 0; overflow: hidden;';
  const cognitionCanvas = document.createElement('canvas');
  cognitionCanvas.id = 'mind-cognition-canvas';
  cognitionCanvas.style.cssText = 'display: block; width: 100%; height: 100%;';
  const cognitionSummary = el('div', '');
  cognitionSummary.id = 'mind-cognition-summary';
  cognitionSummary.style.cssText = `
    position:absolute;top:12px;left:12px;z-index:2;
    padding:8px 10px;border:1px solid var(--line,${PAL.line});border-radius:8px;
    background:rgba(6,14,24,.82);font-size:9px;line-height:1.5;color:var(--muted);
    pointer-events:none;backdrop-filter:blur(4px);
  `;

  const cognitionModeControls = el('div', '');
  cognitionModeControls.style.cssText = `
    position:absolute;top:12px;right:12px;z-index:2;
    display:flex;gap:4px;
  `;
  for (const [mode, label] of [['full','Full'], ['connected','Connected'], ['core','Core']]) {
    const button = makeControlBtn(label, `Cognition view: ${label}`, mode === _graph.viewMode);
    button.dataset.graphMode = mode;
    button.addEventListener('click', () => {
      _graph.viewMode = mode;
      cognitionModeControls.querySelectorAll('button').forEach(item => {
        item.classList.toggle('active', item.dataset.graphMode === mode);
      });
      const canvas = document.getElementById('mind-cognition-canvas');
      if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
      renderCognitionInspector();
    });
    cognitionModeControls.appendChild(button);
  }

  const cognitionControls = el('div', '');
  cognitionControls.style.cssText = `
    position: absolute; bottom: 14px; right: 14px;
    display: flex; gap: 6px;
  `;
  const btnFmri  = makeControlBtn('⚡', 'Toggle fMRI', true);  btnFmri.id = 'mind-fmri-btn';
  const btnZoomIn= makeControlBtn('+', 'Zoom in', false);       btnZoomIn.id = 'mind-zoom-in';
  const btnZoomOut=makeControlBtn('−', 'Zoom out', false);      btnZoomOut.id = 'mind-zoom-out';
  const btnReset = makeControlBtn('⟲', 'Reset', false);         btnReset.id = 'mind-graph-reset';
  const btnLive = makeControlBtn('LIVE', 'Return to live cognition', false); btnLive.id = 'mind-graph-live';
  btnLive.addEventListener('click', () => {
    _graph.replaySnapshot = null;
    _graph.replayTick = null;
    updateCognitionSummary();
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
  });
  cognitionControls.append(btnLive, btnFmri, btnZoomIn, btnZoomOut, btnReset);
  cognitionWrap.append(cognitionCanvas, cognitionSummary, cognitionModeControls, cognitionControls);

  const overviewWrap = el('div', 'mind-overview-wrap hidden');
  overviewWrap.id = 'mind-overview-wrap';
  overviewWrap.style.cssText = 'position:absolute;inset:0;overflow:auto;background:var(--bg-deep);padding:18px 20px 28px;';

  const motorWrap = el('div', 'mind-motor-wrap hidden');
  motorWrap.id = 'mind-motor-wrap';
  motorWrap.style.cssText = 'position:absolute;inset:0;overflow:auto;background:var(--bg-deep);padding:18px 20px 28px;';

  const historyWrap = el('div', 'mind-history-wrap hidden');
  historyWrap.id = 'mind-history-wrap';
  historyWrap.style.cssText = 'position:absolute;inset:0;overflow:auto;background:var(--bg-deep);padding:18px 20px 28px;';

  // Observer map retained as a secondary analytical surface for History.
  // It is no longer a primary navigation tab.
    // Regime canvas
  const regimeWrap = el('div', 'mind-regime-wrap hidden');
  regimeWrap.id = 'mind-regime-wrap';
  regimeWrap.style.cssText = 'position: absolute; inset: 0; overflow: hidden;';
  const regimeCanvas = document.createElement('canvas');
  regimeCanvas.id = 'mind-regime-canvas';
  regimeCanvas.style.cssText = 'display: block; width: 100%; height: 100%;';
  const regimeHud = buildRegimeHud();
  const regimeControls = el('div', '');
  regimeControls.style.cssText = `
    position: absolute; bottom: 14px; right: 14px;
    display: flex; gap: 6px;
  `;
  const btnContour = makeControlBtn('🗺️', 'Toggle contours', true); btnContour.id = 'mind-contour-btn';
  const btnTrail   = makeControlBtn('〰️', 'Toggle trail', true);    btnTrail.id   = 'mind-trail-btn';
  const btnRegReset= makeControlBtn('⟲', 'Reset compass', false);   btnRegReset.id= 'mind-regime-reset';
  regimeControls.append(btnContour, btnTrail, btnRegReset);
  regimeWrap.appendChild(regimeCanvas);
  regimeWrap.appendChild(regimeHud);
  regimeWrap.appendChild(regimeControls);

  // Waiting overlay (when no organism is active yet)
  const waitingOverlay = el('div', 'mind-waiting');
  waitingOverlay.id = 'mind-waiting';
  waitingOverlay.style.cssText = `
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 16px;
    background: var(--bg-deep, ${PAL.bg});
    color: var(--muted, ${PAL.muted}); font-size: 14px;
    pointer-events: none;
  `;
  const waitSpinner = el('div', '');
  waitSpinner.style.cssText = `
    width: 36px; height: 36px; border-radius: 50%;
    border: 2px solid var(--line, ${PAL.line});
    border-top-color: var(--cyan, ${PAL.cyan});
    animation: mind-spin 1.2s linear infinite;
  `;
  const waitText = el('span', '');
  waitText.id = 'mind-wait-text';
  waitText.textContent = 'Waiting for live organism…';
  waitingOverlay.append(waitSpinner, waitText);

  // Assemble canvas area
  canvasArea.append(overviewWrap, identityWrap, sensoryWrap, cognitionWrap, motorWrap, historyWrap, regimeWrap, waitingOverlay);
  workspace.append(sensesPanel, cognitionInspector, canvasArea);
  root.appendChild(workspace);

  // ── Bottom telemetry strip ───────────────────────────────────────────────────
  const telemStrip = el('footer', 'mind-telemetry-strip');
  telemStrip.id = 'mind-telem-strip';
  telemStrip.style.cssText = `
    display: flex;
    gap: 0;
    padding: 0 14px;
    height: 32px;
    align-items: center;
    border-top: 1px solid var(--line, ${PAL.line});
    background: var(--surface, ${PAL.surface});
    font-size: 11px;
    color: var(--muted, ${PAL.muted});
    overflow: hidden;
    flex-shrink: 0;
  `;
  telemStrip.innerHTML = buildTelemHTML();
  root.appendChild(telemStrip);

  // ── Inject keyframe animation for the spinner ────────────────────────────────
  if (!document.querySelector('#mind-spin-style')) {
    const style = document.createElement('style');
    style.id = 'mind-spin-style';
    style.textContent = `
      @keyframes mind-spin { to { transform: rotate(360deg); } }
      .mind-tab[aria-pressed="true"] {
        color: var(--cyan, ${PAL.cyan}) !important;
        border-bottom-color: var(--cyan, ${PAL.cyan}) !important;
      }
      .mind-tab:hover { color: var(--text, ${PAL.text}) !important; }
      .mind-sense-row {
        display: flex; align-items: center; gap: 8px; padding: 8px 12px;
        cursor: pointer; border-bottom: 1px solid var(--line, ${PAL.line});
        font-size: 11px; color: var(--text, ${PAL.text});
        transition: background 0.1s;
      }
      .mind-sense-row:hover  { background: rgba(80,217,255,0.06); }
      .mind-sense-row.active { background: rgba(80,217,255,0.10); }
      .mind-sense-icon { font-size: 15px; flex-shrink: 0; }
      .mind-sense-copy { flex: 1; overflow: hidden; }
      .mind-sense-copy strong { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .mind-sense-copy small  { display: block; color: var(--muted, ${PAL.muted}); font-size: 10px; margin-top: 1px; }
      .mind-sense-bar  { height: 3px; margin-top: 4px; border-radius: 2px; background: rgba(80,217,255,0.18); }
      .mind-sense-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
      .hidden { display: none !important; }
      .mind-ctrl-btn {
        border: 1px solid var(--line, ${PAL.line});
        background: rgba(8,26,42,0.85);
        color: var(--text, ${PAL.text});
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
        cursor: pointer;
        transition: background 0.15s;
      }
      .mind-ctrl-btn:hover { background: rgba(80,217,255,0.12); }
      .mind-ctrl-btn.active { border-color: var(--cyan, ${PAL.cyan}); color: var(--cyan, ${PAL.cyan}); }
      .mind-telem-item { padding: 0 12px; border-right: 1px solid var(--line, ${PAL.line}); white-space: nowrap; }
      .mind-telem-item:last-child { border-right: none; }
      .mind-telem-item b { color: var(--text, ${PAL.text}); }
      .mind-self-heading { font-size: 15px; font-weight: 600; color: var(--text, ${PAL.text}); margin: 0 0 8px; }
      .mind-self-body { font-size: 12px; color: var(--muted, ${PAL.muted}); margin: 0 0 20px; line-height: 1.5; }
      .mind-self-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; max-width: 900px; }
      .mind-self-card {
        border: 1px solid var(--line, ${PAL.line});
        border-radius: 9px; padding: 12px;
        background: rgba(8,26,42,0.72);
      }
      .mind-self-card h4 { font-size: 12px; font-weight: 600; margin: 0 0 2px; color: var(--text, ${PAL.text}); }
      .mind-self-card code { font-size: 9px; color: var(--muted, ${PAL.muted}); word-break: break-all; }
      .mind-metric-row { display: grid; grid-template-columns: 70px 1fr 36px; align-items: center; gap: 6px; font-size: 10px; margin-top: 8px; }
      .mind-metric-row span { color: var(--muted, ${PAL.muted}); }
      .mind-metric-row progress { width: 100%; accent-color: var(--cyan, ${PAL.cyan}); }
      .mind-metric-row strong { text-align: right; color: var(--text, ${PAL.text}); }
      .mind-section-title {
        font-size: 11px; font-weight: 600; color: var(--muted, ${PAL.muted});
        text-transform: uppercase; letter-spacing: 0.07em;
        margin: 24px 0 10px;
        border-bottom: 1px solid var(--line, ${PAL.line}); padding-bottom: 4px;
      }
      .mind-dep-row {
        display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center;
        border: 1px solid var(--line, ${PAL.line}); border-radius: 8px;
        padding: 10px 12px; margin-bottom: 8px;
        background: rgba(8,26,42,0.54); font-size: 11px;
      }
      .mind-dep-row strong { color: var(--text, ${PAL.text}); display: block; margin-bottom: 3px; }
      .mind-dep-row small  { color: var(--muted, ${PAL.muted}); }
      .mind-compass-hud {
        position: absolute; top: 14px; left: 14px;
        background: rgba(8,26,42,0.88);
        border: 1px solid var(--line, ${PAL.line});
        border-radius: 10px; padding: 14px; width: 230px;
        font-size: 11px; color: var(--muted, ${PAL.muted});
      }
      .mind-compass-hud h3 { font-size: 13px; font-weight: 600; margin: 0 0 2px; color: var(--text, ${PAL.text}); }
      .mind-compass-hud p  { margin: 0 0 10px; font-size: 10px; }
      .mind-compass-badge  {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 9px; font-weight: 700; letter-spacing: 0.05em;
        margin-bottom: 10px;
      }
      .mind-compass-badge.familiar { background: rgba(113,233,186,0.18); color: var(--mint, ${PAL.mint}); }
      .mind-compass-badge.moderate { background: rgba(255,189,84,0.18);  color: var(--amber,${PAL.amber}); }
      .mind-compass-badge.alert    { background: rgba(255,127,131,0.18); color: var(--coral,${PAL.coral}); }
      .mind-compass-metric { margin-top: 6px; }
      .mind-compass-metric-head { display: flex; justify-content: space-between; }
      .mind-compass-meter { height: 3px; background: var(--line, ${PAL.line}); border-radius: 2px; margin-top: 4px; }
      .mind-compass-meter-fill { height: 100%; border-radius: 2px; transition: width 0.4s, background 0.4s; }
      .mind-compass-exp { font-size: 10px; margin-top: 10px; line-height: 1.4; }
    `;
    document.head.appendChild(style);
  }
}

function makeControlBtn(text, title, active) {
  const btn = el('button', `mind-ctrl-btn${active ? ' active' : ''}`);
  btn.textContent = text;
  btn.title = title;
  btn.setAttribute('aria-label', title);
  return btn;
}

function buildTelemHTML() {
  const items = [
    { id: 'mind-t-tick',     label: 'Tick',       init: '—' },
    { id: 'mind-t-phase',    label: 'Physiology', init: '—' },
    { id: 'mind-t-energy',   label: 'Energy',     init: '—' },
    { id: 'mind-t-resource', label: 'Resource Δ', init: '—' },
    { id: 'mind-t-cognition',label: 'Cognition',  init: '—' },
    { id: 'mind-t-motor',    label: 'Motor',      init: '—' },
    { id: 'mind-t-instance', label: 'Instance',   init: '—' },
  ];
  return items.map(i =>
    `<span class="mind-telem-item"><span>${i.label}: </span><b id="${i.id}">${i.init}</b></span>`
  ).join('');
}

function buildRegimeHud() {
  const hud = el('div', 'mind-compass-hud');
  hud.id = 'mind-compass-hud';
  hud.innerHTML = `
    <h3 id="mind-compass-title">—</h3>
    <p id="mind-compass-sub">Waiting for telemetry…</p>
    <span id="mind-compass-badge" class="mind-compass-badge familiar">—</span>
    <div class="mind-compass-metric">
      <div class="mind-compass-metric-head">
        <span>Reference distance</span><strong id="mind-compass-novelty">—</strong>
      </div>
      <div class="mind-compass-meter">
        <div class="mind-compass-meter-fill" id="mind-compass-novelty-bar" style="width:0%;background:${PAL.mint}"></div>
      </div>
    </div>
    <div class="mind-compass-metric" style="margin-top:8px">
      <div class="mind-compass-metric-head">
        <span>Observer drift</span><strong id="mind-compass-drift">0.000 units/tick</strong>
      </div>
    </div>
    <p class="mind-compass-exp" id="mind-compass-exp">Awaiting real-time data…</p>
  `;
  return hud;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab switching
// ─────────────────────────────────────────────────────────────────────────────

function panelSection(title, subtitle = '') {
  const section = el('section', '');
  section.style.cssText = 'border:1px solid var(--line);border-radius:10px;background:rgba(8,21,34,.72);padding:13px 14px;min-width:0;';
  const h = el('h3', '');
  h.style.cssText = 'font-size:12px;margin:0;color:var(--text);';
  h.textContent = title;
  section.appendChild(h);
  if (subtitle) {
    const p = el('p', '');
    p.style.cssText = 'margin:3px 0 10px;font-size:9px;line-height:1.4;color:var(--muted);';
    p.textContent = subtitle;
    section.appendChild(p);
  }
  return section;
}

function bigMetric(label, value, tone = null) {
  const wrap = el('div', '');
  wrap.style.cssText = 'padding:9px 10px;border:1px solid rgba(98,120,136,.16);border-radius:8px;background:rgba(255,255,255,.015);';
  const l = el('div', '');
  l.style.cssText='font-size:8px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);';
  l.textContent = label;
  const v = el('strong','');
  v.style.cssText='display:block;margin-top:3px;font-size:18px;line-height:1;color:var(--text);';
  if (tone) v.style.color = tone;
  v.textContent=String(value);
  wrap.append(l,v);
  return wrap;
}

function renderOverview() {
  const root = document.getElementById('mind-overview-wrap');
  if (!root) return;
  root.innerHTML = '';

  const topology = _snap.topology ?? {nodes:[], edges:[]};
  const nodes = topology.nodes ?? [];
  const sensorimotor = _snap.sensorimotor ?? {};
  const outcome = _snap.outcome ?? {};
  const physiology = currentPhysiologyState();
  const concepts = nodes.filter(n => n.kind === 'concept').length;
  const predictors = nodes.filter(n => n.kind === 'predictor').length;
  const motorEdges = currentMotorOutputEdges(topology);
  const energy = _tel.metabolicReserve;
  const repertoire = Array.isArray(sensorimotor.active_motor_repertoire) ? sensorimotor.active_motor_repertoire.length : 0;
  const readoutCount = nodes.filter(n => n.kind === 'readout' && (String(n.id).startsWith('readout_motor:') || String(n.id).startsWith('readout_primitive:'))).length;

  const heading = el('div','');
  heading.style.cssText='display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:14px;';
  const copy=el('div','');
  const h=el('h2',''); h.style.cssText='font-size:16px;margin:0;color:var(--text);'; h.textContent='Organism overview';
  const sub=el('p',''); sub.style.cssText='font-size:10px;color:var(--muted);margin:4px 0 0;'; sub.textContent='What exists, what has been learned, and what the organism can actually use.';
  copy.append(h,sub);
  const phase=el('strong',''); phase.style.cssText='font-size:12px;text-transform:uppercase;letter-spacing:.08em;'; phase.style.color =
    physiology==='dead'?PAL.coral:physiology==='dormant'?PAL.amber:physiology==='stressed'?PAL.coral:PAL.mint;
  phase.textContent=physiology;
  heading.append(copy,phase);
  root.appendChild(heading);

  const metrics=el('div','');
  metrics.style.cssText='display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:8px;margin-bottom:12px;';
  metrics.append(
    bigMetric('Tick', _tel.tick ?? '—'),
    bigMetric('Energy', energy != null ? pct(energy) : '—', energy != null && energy < .2 ? PAL.coral : PAL.mint),
    bigMetric('Resource progress', _tel.resourceProgress != null ? `${_tel.resourceProgress >=0?'+':''}${_tel.resourceProgress.toFixed(2)} m` : '—'),
    bigMetric('Cognition', `${concepts} C · ${predictors} P`, PAL.violet),
    bigMetric('Motor origin', _tel.motorOrigin ?? '—', _tel.motorOrigin === 'babbling' ? PAL.amber : PAL.mint),
  );
  root.appendChild(metrics);

  if (_mindHistory.length > 1) {
    const phaseStrip = panelSection('Observed physiology timeline','Session-local phase history; it never backdates states seen before attachment.');
    phaseStrip.style.marginBottom='12px';
    const track=el('div','');
    track.style.cssText='height:18px;display:flex;overflow:hidden;border-radius:5px;background:rgba(98,120,136,.12);';
    const points=_mindHistory;
    const t0=points[0].tick;
    const t1=points[points.length-1].tick;
    const runs=[];
    let runStart=points[0].tick;
    let runState=points[0].physiology;
    for(let i=1;i<points.length;i++){
      if(points[i].physiology!==runState){
        runs.push({state:runState,start:runStart,end:points[i].tick});
        runStart=points[i].tick; runState=points[i].physiology;
      }
    }
    runs.push({state:runState,start:runStart,end:t1+1});
    for(const run of runs){
      const seg=el('div','');
      const width=Math.max(1,((run.end-run.start)/Math.max(1,t1-t0+1))*100);
      const color=run.state==='dead'?PAL.coral:run.state==='dormant'?PAL.amber:run.state==='stressed'?'#d77676':PAL.mint;
      seg.style.cssText=`width:${width}%;background:${color};opacity:.62;position:relative;`;
      seg.title=`${run.state} · t${run.start}–t${run.end}`;
      track.appendChild(seg);
    }
    phaseStrip.appendChild(track);
    const labels=el('div','');
    labels.style.cssText='display:flex;justify-content:space-between;margin-top:4px;font-size:8px;color:var(--muted);';
    labels.innerHTML=`<span>t${t0}</span><span>t${t1}</span>`;
    phaseStrip.appendChild(labels);
    root.appendChild(phaseStrip);
  }

  const grid=el('div','');
  grid.style.cssText='display:grid;grid-template-columns:1.15fr 1fr;gap:12px;';

  const pipeline=panelSection('Learning pipeline','Three distinct levels: exists → learned → usable.');
  const stages=[
    ['Sensory system', `${_snap.sensoryPhenotype?.sensors?.length ?? nodes.filter(n=>n.kind==='sense').length} sensors`, true],
    ['Sensorimotor patterns', `${_tel.sensorimotorPatterns ?? sensorimotor.known_patterns ?? 0}`, (_tel.sensorimotorPatterns ?? sensorimotor.known_patterns ?? 0) > 0],
    ['Motor primitives', `${_tel.motorPrimitives ?? sensorimotor.primitives ?? 0}`, (_tel.motorPrimitives ?? sensorimotor.primitives ?? 0) > 0],
    ['Cognitive structure', `${concepts} concepts · ${predictors} predictors`, concepts > 0],
    ['Motor repertoire', `${repertoire}`, repertoire > 0],
    ['Motor readouts', `${readoutCount}`, readoutCount > 0],
    ['Cognition → motor edges', `${motorEdges}`, motorEdges > 0],
    ['Cognitive motor use', _tel.motorOrigin ?? 'none', ['cognition','mixed'].includes(_tel.motorOrigin) || String(_tel.motorOrigin).includes('primitive')],
  ];
  stages.forEach(([label,value,ok],idx)=>{
    const row=el('div','');
    row.style.cssText='display:grid;grid-template-columns:18px 1fr auto;gap:8px;align-items:center;padding:7px 0;border-top:1px solid rgba(98,120,136,.12);font-size:9px;';
    const dot=el('span',''); dot.textContent=ok?'●':'○'; dot.style.color=ok?PAL.mint:PAL.muted;
    const name=el('span',''); name.textContent=label; name.style.color='var(--text)';
    const val=el('strong',''); val.textContent=value; val.style.color=ok?'var(--text)':'var(--muted)';
    row.append(dot,name,val); pipeline.appendChild(row);
    if(idx<stages.length-1){
      const arrow=el('div',''); arrow.textContent='↓'; arrow.style.cssText='margin:-2px 0 -2px 4px;color:rgba(98,120,136,.45);font-size:9px;';
      pipeline.appendChild(arrow);
    }
  });

  const outcomePanel=panelSection('Outcome','External behavioral result; not a reward signal fed into cognition.');
  const startDist=finiteNumber(outcome.initial_resource_distance, NaN);
  const minDist=finiteNumber(outcome.minimum_resource_distance, NaN);
  const currentDist=finiteNumber(_tel.resourceDistance ?? outcome.current_resource_distance, NaN);
  const consumed=finiteNumber(_tel.absorbedEnergy ?? outcome.absorbed_energy, 0);
  [
    ['Start distance', Number.isFinite(startDist)?`${startDist.toFixed(2)} m`:'—'],
    ['Best distance', Number.isFinite(minDist)?`${minDist.toFixed(2)} m`:'—'],
    ['Current distance', Number.isFinite(currentDist)?`${currentDist.toFixed(2)} m`:'—'],
    ['Progress', _tel.resourceProgress!=null?`${_tel.resourceProgress>=0?'+':''}${_tel.resourceProgress.toFixed(2)} m`:'—'],
    ['Consumed energy', consumed.toFixed(2)],
    ['Resource remaining', _tel.resourceRemaining!=null?_tel.resourceRemaining.toFixed(2):outcome.resource_remaining ?? '—'],
  ].forEach(([k,v])=>inspectorMetric(outcomePanel,k,v));

  grid.append(pipeline,outcomePanel);
  root.appendChild(grid);

  const timeline=panelSection('Major milestones','First-occurrence lifecycle and learning events captured in the current browser session.');
  timeline.style.marginTop='12px';
  if(!_milestones.length){
    const empty=el('div',''); empty.style.cssText='font-size:9px;color:var(--muted);'; empty.textContent='No milestones recorded yet.'; timeline.appendChild(empty);
  } else {
    const strip=el('div',''); strip.style.cssText='display:flex;gap:6px;align-items:flex-start;overflow-x:auto;padding:4px 0 2px;';
    for(const m of _milestones){
      const b=el('button',''); b.type='button'; b.style.cssText='min-width:110px;text-align:left;padding:7px 8px;border:1px solid rgba(98,120,136,.2);border-radius:7px;background:rgba(255,255,255,.015);color:var(--text);cursor:pointer;';
      b.innerHTML=`<strong style="font-size:9px">t${m.tick}</strong><br><span style="font-size:8px;color:var(--muted)">${m.label}</span>`;
      b.addEventListener('click',()=>openHistoryTick(m.tick)); strip.appendChild(b);
    }
    timeline.appendChild(strip);
  }
  root.appendChild(timeline);
}

function renderMotorLearning() {
  const root=document.getElementById('mind-motor-wrap');
  if(!root) return;
  root.innerHTML='';
  const sm=_snap.sensorimotor ?? {};
  const topology=_snap.topology ?? {nodes:[],edges:[]};
  const nodes=topology.nodes ?? [];
  const motorEdges=finiteNumber(_tel.cognitiveMotorOutputEdges ?? currentMotorOutputEdges(topology),0);
  const repertoire=finiteNumber(
    _tel.motorRepertoireSize ?? (
      Array.isArray(sm.active_motor_repertoire)?sm.active_motor_repertoire.length:0
    ),
    0,
  );
  const motorReadouts=finiteNumber(
    _tel.motorReadoutNodes ?? nodes.filter(n=>n.kind==='readout'&&(String(n.id).startsWith('readout_motor:')||String(n.id).startsWith('readout_primitive:'))).length,
    0,
  );
  const values=[
    ['Sensorimotor patterns', finiteNumber(_tel.sensorimotorPatterns ?? sm.known_patterns,0), true, 'EXISTS'],
    ['Motor primitives', finiteNumber(_tel.motorPrimitives ?? sm.primitives,0), true, 'LEARNED'],
    ['Recurrent candidates', finiteNumber(_tel.recurrentPrimitiveCandidates ?? sm.recurrent_primitive_candidates,0), true, 'LEARNED'],
    ['Motor repertoire', repertoire, repertoire>0, 'USABLE'],
    ['Motor readouts', motorReadouts, motorReadouts>0, 'USABLE'],
    ['Cognitive motor edges', motorEdges, motorEdges>0, 'USABLE'],
    ['Actual cognitive control', _tel.motorOrigin ?? 'none', ['cognition','mixed'].includes(_tel.motorOrigin)||String(_tel.motorOrigin).includes('primitive'), 'USED'],
  ];

  const h=el('h2',''); h.style.cssText='font-size:16px;margin:0 0 4px;'; h.textContent='Motor learning';
  const p=el('p',''); p.style.cssText='font-size:10px;color:var(--muted);margin:0 0 16px;'; p.textContent='A funnel from discovered sensorimotor regularity to actual cognitive control.';
  root.append(h,p);
  const funnel=el('div',''); funnel.style.cssText='max-width:760px;margin:0 auto;';
  values.forEach(([label,value,ok,level],i)=>{
    const width=100-i*7;
    const row=el('div',''); row.style.cssText=`width:${width}%;margin:0 auto 4px;padding:10px 12px;display:grid;grid-template-columns:58px 1fr auto;gap:10px;border:1px solid ${ok?'rgba(113,233,186,.24)':'rgba(98,120,136,.18)'};border-radius:8px;background:${ok?'rgba(113,233,186,.035)':'rgba(255,255,255,.012)'};`;
    const badge=el('span',''); badge.style.cssText='font-size:7px;letter-spacing:.08em;color:var(--muted);'; badge.textContent=level;
    const name=el('span',''); name.style.cssText='font-size:10px;color:var(--muted);'; name.textContent=label;
    const val=el('strong',''); val.style.cssText='font-size:12px;'; val.style.color=ok?PAL.mint:PAL.muted; val.textContent=String(value);
    row.append(badge,name,val); funnel.appendChild(row);
    if(i<values.length-1){const a=el('div',''); a.textContent='↓'; a.style.cssText='text-align:center;color:rgba(98,120,136,.45);height:12px;'; funnel.appendChild(a);}
  });
  root.appendChild(funnel);

  const diag=panelSection('Why is control blocked?','Current readiness gates from the passive runtime snapshot.');
  diag.style.cssText += ';max-width:760px;margin:16px auto 0;';
  [
    ['Babbling coverage', sm.babbling_coverage!=null?pct(sm.babbling_coverage):'—'],
    ['Best controllability', sm.best_controllability!=null?sm.best_controllability.toFixed(3):'—'],
    ['Best directional consistency', sm.best_directional_consistency!=null?sm.best_directional_consistency.toFixed(3):'—'],
    ['Primitive replay', sm.replay_active?'active':'inactive'],
    ['Cognitive primitives', finiteNumber(_tel.cognitiveMotorPrimitives ?? sm.cognitive_primitives,0)],
    ['Max primitive samples', finiteNumber(_tel.maxPrimitiveSamples ?? sm.max_primitive_samples,0)],
    ['Full competence candidates', finiteNumber(_tel.fullCompetenceGateCandidates ?? sm.full_competence_gate_candidates,0)],
    ['Cognitive motor edges', motorEdges],
    ['Current motor origin', _tel.motorOrigin ?? '—'],
  ].forEach(([k,v])=>inspectorMetric(diag,k,v));
  root.appendChild(diag);
}

function sparklineSvg(points, key, color, width=900, height=90) {
  const svg=svgEl('svg',{viewBox:`0 0 ${width} ${height}`,role:'img'});
  svg.style.cssText='width:100%;height:90px;display:block;';
  if(points.length<2) return svg;
  const values=points.map(p=>finiteNumber(p[key],0));
  let lo=Math.min(...values), hi=Math.max(...values);
  if(Math.abs(hi-lo)<1e-9){hi=lo+1;}
  const t0=points[0].tick, t1=points[points.length-1].tick || t0+1;
  const coords=points.map((p,i)=>{
    const x=((p.tick-t0)/Math.max(1,t1-t0))*(width-20)+10;
    const y=height-10-((values[i]-lo)/(hi-lo))*(height-20);
    return [x,y];
  });
  const path=svgEl('path',{d:coords.map((p,i)=>`${i?'L':'M'} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' '),fill:'none',stroke:color,'stroke-width':'1.5'});
  svg.appendChild(path);
  return svg;
}

function renderHistory() {
  const root=document.getElementById('mind-history-wrap');
  if(!root) return;
  root.innerHTML='';
  const h=el('h2',''); h.style.cssText='font-size:16px;margin:0 0 4px;'; h.textContent='History';
  const p=el('p',''); p.style.cssText='font-size:10px;color:var(--muted);margin:0 0 14px;'; p.textContent='Bounded observer-side history for this browser session. Click a milestone to inspect the nearest captured graph.';
  root.append(h,p);

  const charts=el('div',''); charts.style.cssText='display:grid;grid-template-columns:1fr 1fr;gap:10px;';
  const energy=panelSection('Energy / physiology');
  energy.appendChild(sparklineSvg(_mindHistory.filter(x=>x.energy!=null),'energy',PAL.coral));
  const edges=panelSection('Cognitive edges');
  edges.appendChild(sparklineSvg(_mindHistory,'edges',PAL.violet));
  const concepts=panelSection('Concept growth');
  concepts.appendChild(sparklineSvg(_mindHistory,'concepts',PAL.cyan));
  const predictors=panelSection('Predictor growth');
  predictors.appendChild(sparklineSvg(_mindHistory,'predictors',PAL.amber));
  const resource=panelSection('Resource progress');
  resource.appendChild(sparklineSvg(_mindHistory,'resourceProgress',PAL.mint));
  const motor=panelSection('Motor-output edges');
  motor.appendChild(sparklineSvg(_mindHistory,'motorEdges','#e09f3e'));
  charts.append(energy,edges,concepts,predictors,resource,motor); root.appendChild(charts);

  const timeline=panelSection('Milestones');
  timeline.style.marginTop='10px';
  if(!_milestones.length){
    const e=el('div',''); e.style.cssText='font-size:9px;color:var(--muted);'; e.textContent='No milestones yet.'; timeline.appendChild(e);
  } else {
    for(const m of _milestones){
      const row=el('button',''); row.type='button'; row.style.cssText='width:100%;display:grid;grid-template-columns:60px 1fr;gap:10px;text-align:left;padding:8px 0;border:0;border-top:1px solid rgba(98,120,136,.14);background:none;color:var(--text);cursor:pointer;';
      const t=el('strong',''); t.textContent=`t${m.tick}`; t.style.color=PAL.cyan;
      const label=el('span',''); label.textContent=m.label; label.style.cssText='font-size:9px;';
      row.append(t,label); row.addEventListener('click',()=>openHistoryTick(m.tick)); timeline.appendChild(row);
    }
  }
  root.appendChild(timeline);

  const latest=_mindHistory[_mindHistory.length-1];
  if(latest){
    const observer=panelSection('Observer analysis','Secondary analytical projection; not part of the organism.');
    observer.style.marginTop='10px';
    const coord=computeObserverMapCoordinates({
      senses:_snap.senses,
      cognition:_snap.cognition,
      observerAnalysis:_snap.observerAnalysis,
    });
    const analysis=evaluateObserverRegime(coord,REGIMES);
    inspectorMetric(observer,'Measured activity',pct(coord.activityNorm));
    inspectorMetric(observer,'Predictive tension',pct(coord.predictiveTension));
    inspectorMetric(observer,'Nearest reference zone',analysis.nearest?.name ?? '—');
    root.appendChild(observer);
  }
}

function switchTab(tabId) {
  _activeTab = tabId;

  document.querySelectorAll('.mind-tab').forEach(btn => {
    const active = btn.dataset.tab === tabId;
    btn.setAttribute('aria-pressed', String(active));
    btn.style.color = active ? `var(--cyan, ${PAL.cyan})` : `var(--muted, ${PAL.muted})`;
    btn.style.borderBottomColor = active ? `var(--cyan, ${PAL.cyan})` : 'transparent';
  });

  const ids = ['overview','phenotype','sensory','cognition','motor','history'];
  const wraps = {
    overview: document.querySelector('#mind-overview-wrap'),
    phenotype: document.querySelector('#mind-identity-wrap'),
    sensory: document.querySelector('#mind-sensory-wrap'),
    cognition: document.querySelector('#mind-cognition-wrap'),
    motor: document.querySelector('#mind-motor-wrap'),
    history: document.querySelector('#mind-history-wrap'),
  };
  for (const id of ids) wraps[id]?.classList.toggle('hidden', id !== tabId);
  document.querySelector('#mind-regime-wrap')?.classList.add('hidden');

  const sensesPanel = document.querySelector('#mind-senses-panel');
  const cognitionInspector = document.querySelector('#mind-cognition-inspector');
  const workspace = document.querySelector('#mind-workspace');

  if (sensesPanel) sensesPanel.style.display = tabId === 'sensory' ? 'flex' : 'none';
  if (cognitionInspector) cognitionInspector.style.display = tabId === 'cognition' ? 'flex' : 'none';
  if (workspace) {
    workspace.style.gridTemplateColumns =
      tabId === 'cognition' ? '250px 1fr' :
      tabId === 'sensory' ? '220px 1fr' :
      '1fr';
  }

  if (tabId === 'overview') renderOverview();
  if (tabId === 'phenotype') {
    renderPhenotype();
    renderIdentityGap();
    renderSelf();
  }
  if (tabId === 'sensory') {
    renderSensesPanel();
    renderSensoryMap();
  }
  if (tabId === 'cognition') {
    startCognitionGraph();
    renderCognitionInspector();
  }
  if (tabId === 'motor') renderMotorLearning();
  if (tabId === 'history') renderHistory();
}

// ─────────────────────────────────────────────────────────────────────────────
// Telemetry strip update
// ─────────────────────────────────────────────────────────────────────────────

function updateTelemetryStrip(force = false) {
  const now = performance.now();
  if (!force && now - _lastUITime < UI_THROTTLE_MS) return;

  const topology = _snap.topology ?? { nodes: [] };
  const nodes = topology.nodes ?? [];
  const concepts = _tel.cognitiveConcepts ?? nodes.filter(node => node.kind === 'concept').length;
  const predictors = _tel.predictorCount ?? nodes.filter(node => node.kind === 'predictor').length;
  const physiology = currentPhysiologyState();

  setTelem('mind-t-tick', _tel.tick != null ? `t${_tel.tick}` : '—');
  setTelem(
    'mind-t-phase',
    physiology.toUpperCase(),
    physiology === 'dead' ? PAL.coral :
      physiology === 'dormant' ? PAL.amber :
      physiology === 'stressed' ? PAL.coral : PAL.mint,
  );
  setTelem(
    'mind-t-energy',
    _tel.metabolicReserve != null ? pct(_tel.metabolicReserve) : '—',
    _tel.metabolicReserve != null && _tel.metabolicReserve < 0.2 ? PAL.coral : null,
  );
  setTelem(
    'mind-t-resource',
    _tel.resourceProgress != null
      ? `${_tel.resourceProgress >= 0 ? '+' : ''}${_tel.resourceProgress.toFixed(2)} m`
      : '—',
  );
  setTelem('mind-t-cognition', `${concepts}C / ${predictors}P`, PAL.violet);
  setTelem(
    'mind-t-motor',
    _tel.motorOrigin ?? '—',
    ['cognition','mixed'].includes(_tel.motorOrigin) || String(_tel.motorOrigin).includes('primitive')
      ? PAL.mint
      : _tel.motorOrigin === 'babbling' ? PAL.amber : null,
  );
  setTelem('mind-t-instance', _snap.displayId ?? _snap.instanceId ?? '—');
  _lastUITime = now;
}

function setTelem(id, text, color = null) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  if (color) el.style.color = color;
}

// ─────────────────────────────────────────────────────────────────────────────
// Waiting overlay
// ─────────────────────────────────────────────────────────────────────────────

function setWaiting(visible, message) {
  const overlay = document.getElementById('mind-waiting');
  if (!overlay) return;
  overlay.style.display = visible ? 'flex' : 'none';
  const txt = document.getElementById('mind-wait-text');
  if (txt && message) txt.textContent = message;
}

// ─────────────────────────────────────────────────────────────────────────────
// Senses panel rendering
// ─────────────────────────────────────────────────────────────────────────────

function sensoryFacts() {
  const phenotype = _snap.sensoryPhenotype ?? {};
  const sensors = Array.isArray(phenotype.sensors) ? phenotype.sensors : [];
  const topology = _snap.topology ?? { nodes: [], edges: [] };
  const degree = new Map((topology.nodes ?? []).map(node => [node.id, 0]));
  for (const edge of topology.edges ?? []) {
    degree.set(edge.sourceId, (degree.get(edge.sourceId) ?? 0) + 1);
    degree.set(edge.targetId, (degree.get(edge.targetId) ?? 0) + 1);
  }
  const sampledIds = new Set((_snap.senses ?? []).filter(sense => sense.active).map(sense => sense.id));
  return sensors.map(sensor => {
    const cognitiveId = sensor.downstream_name ?? sensor.sensor_id;
    return {
      ...sensor,
      cognitiveId,
      sampled: sampledIds.has(cognitiveId) || sampledIds.has(sensor.sensor_id),
      degree: degree.get(cognitiveId) ?? 0,
      integrated: (degree.get(cognitiveId) ?? 0) > 0,
      utility: finiteNumber(sensor.utility, 0),
      confidence: clamp01(sensor.confidence),
      health: clamp01(sensor.health),
      maturity: String(sensor.maturity ?? 'unknown'),
    };
  });
}

function renderSensesPanel() {
  const list = document.getElementById('mind-senses-list');
  if (!list) return;
  list.innerHTML = '';

  const sensors = sensoryFacts();
  if (!sensors.length) {
    const empty = el('p', '');
    empty.style.cssText = 'padding:12px;font-size:10px;color:var(--muted);';
    empty.textContent = 'No sensory phenotype yet.';
    list.appendChild(empty);
    return;
  }

  const summary = el('div','');
  summary.style.cssText='padding:8px 10px;border-bottom:1px solid var(--line);font-size:8px;line-height:1.5;color:var(--muted);';
  const sampled = sensors.filter(sensor => sensor.sampled).length;
  const useful = sensors.filter(sensor => sensor.utility > 0).length;
  const integrated = sensors.filter(sensor => sensor.integrated).length;
  summary.innerHTML =
    `<strong style="color:var(--text)">${sensors.length} receptors</strong><br>` +
    `${sampled} sampled now · ${useful} utility &gt; 0 · ${integrated} cognition-integrated`;
  list.appendChild(summary);

  const header=el('div','');
  header.style.cssText='display:grid;grid-template-columns:minmax(0,1fr) 28px 34px 34px;gap:4px;padding:6px 8px;font-size:7px;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--line);';
  header.innerHTML='<span>receptor</span><span>now</span><span>util</span><span>deg</span>';
  list.appendChild(header);

  [...sensors]
    .sort((a,b) =>
      Number(b.integrated)-Number(a.integrated) ||
      b.utility-a.utility ||
      b.degree-a.degree ||
      String(a.cognitiveId).localeCompare(String(b.cognitiveId))
    )
    .forEach(sensor => {
      const row=el('button','');
      row.type='button';
      row.style.cssText='width:100%;display:grid;grid-template-columns:minmax(0,1fr) 28px 34px 34px;gap:4px;align-items:center;padding:6px 8px;border:0;border-bottom:1px solid rgba(98,120,136,.11);background:none;color:var(--text);font-size:8px;text-align:left;cursor:pointer;';
      const name=el('span','');
      name.style.cssText='overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      name.textContent=shortId(sensor.cognitiveId,9,5);
      name.title=`${sensor.cognitiveId}\nmaturity ${sensor.maturity} · health ${pct(sensor.health)} · confidence ${pct(sensor.confidence)}`;
      const sampledCell=el('span','');
      sampledCell.textContent=sensor.sampled?'●':'○';
      sampledCell.style.color=sensor.sampled?PAL.cyan:PAL.muted;
      const utility=el('span','');
      utility.textContent=sensor.utility.toFixed(2);
      utility.style.color=sensor.utility>0?PAL.mint:PAL.muted;
      const degree=el('span','');
      degree.textContent=String(sensor.degree);
      degree.style.color=sensor.integrated?PAL.violet:PAL.muted;
      row.append(name,sampledCell,utility,degree);
      row.addEventListener('click',()=>selectCognitiveNode(sensor.cognitiveId));
      list.appendChild(row);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Phenotype SVG rendering (adapted from observatory/render/organism.js)
// ─────────────────────────────────────────────────────────────────────────────

function renderPhenotype() {
  const canvas = document.getElementById('mind-phenotype-svg');
  if (!canvas) return;
  canvas.innerHTML = '';

  const senses   = _snap.senses ?? [];
  const beliefs  = _snap.beliefs ?? [];
  const cognition = _snap.cognition;
  const health   = cognition?.topologyHealth;
  const isFrozen = cognition?.safetyState?.frozen;
  const isStressed = Array.isArray(_snap.details?.regimeChanges) && _snap.details.regimeChanges.length > 0;
  const isAdaptive = health === 'adaptive' || health === 'connected';

  // Waiting state
  if (!senses.length && !beliefs.length) {
    const waiting = svgEl('text', { x: '450', y: '360', 'text-anchor': 'middle', 'dominant-baseline': 'middle', fill: PAL.muted, 'font-size': '14' });
    waiting.textContent = 'No snapshot data — connect a live organism';
    canvas.appendChild(waiting);
    return;
  }

  const defs = svgEl('defs');

  // Radial gradient
  let coreColor = '#17274e', midColor = '#0a2632', edgeColor = PAL.mint;
  if (isFrozen) { coreColor = '#1a212b'; midColor = '#141920'; edgeColor = '#627382'; }
  else if (isStressed) { coreColor = '#2d1628'; midColor = '#1f1422'; edgeColor = PAL.coral; }
  else if (isAdaptive) { coreColor = '#0d2b38'; midColor = '#0a262e'; edgeColor = PAL.mint; }

  const gradientId = `mind-cell-fill-${_uid}`;
  const grad = svgEl('radialGradient', { id: gradientId });
  grad.append(
    svgEl('stop', { offset: '0',   'stop-color': coreColor, 'stop-opacity': '.52' }),
    svgEl('stop', { offset: '.72', 'stop-color': midColor,  'stop-opacity': '.20' }),
    svgEl('stop', { offset: '1',   'stop-color': edgeColor, 'stop-opacity': '.10' }),
  );
  defs.appendChild(grad);

  // Arrow markers
  [{ id: `mind-arr-exc-${_uid}`, color: 'rgba(80,217,255,.8)' },
   { id: `mind-arr-inh-${_uid}`, color: 'rgba(255,127,131,.8)' },
   { id: `mind-arr-mod-${_uid}`, color: 'rgba(255,189,84,.8)'  }].forEach(m => {
    const marker = svgEl('marker', { id: m.id, viewBox: '0 0 6 6', refX: '5', refY: '3', markerWidth: '4', markerHeight: '4', orient: 'auto' });
    marker.appendChild(svgEl('path', { d: 'M 0 1 L 5 3 L 0 5 z', fill: m.color }));
    defs.appendChild(marker);
  });
  canvas.appendChild(defs);

  const group = svgEl('g', { class: 'mind-organism' });

  // Build a simplified boundary path (ellipse-like)
  const boundaryPath = buildBoundaryPath(450, 360, 280, 260, senses.length, isFrozen);

  // World signal nodes on left margin
  const sensePositions = new Map();
  const usable = senses.slice(0, 16);
  usable.forEach((sense, i) => {
    const y = 120 + (i * 490 / Math.max(1, usable.length - 1));
    const x = 80;
    sensePositions.set(sense.id, { x, y });

    // World signal dot
    const dot = svgEl('circle', { cx: x, cy: y, r: '4', class: `mind-world-signal ${sense.active ? 'active' : 'inactive'}`,
      fill: sense.active ? PAL.cyan : PAL.muted, opacity: sense.active ? '0.85' : '0.35' });
    group.appendChild(dot);

    // Dual semantic label: apparatus truth is observer-only; the opaque
    // organism label remains available in the tooltip.
    const semantic = sensorySemantic(_snap.observerSemantics, sense.id);
    const label = svgEl('text', { x: x + 12, y: y + 3, 'font-size': '10', fill: sense.active ? PAL.text : PAL.muted });
    label.textContent = (semantic?.observerSummary ?? sense.name ?? sense.id).slice(0, 28);
    const labelTitle = svgEl('title');
    labelTitle.textContent = semantic?.observerSummary
      ? `Observer: ${semantic.observerSummary}\nSelf: ${semantic.selfLabel ?? sense.id}`
      : `Self: ${sense.name ?? sense.id}\nObserver: unresolved`;
    label.appendChild(labelTitle);
    group.appendChild(label);

    // Connection to boundary
    const bx = 170, by = y;
    const path = svgEl('path', {
      d: `M ${x + 5} ${y} Q ${bx - 20} ${y} ${bx} ${by}`,
      fill: 'none', stroke: sense.active ? PAL.cyan : PAL.muted,
      'stroke-width': sense.active ? '1.2' : '0.5',
      opacity: sense.active ? '0.55' : '0.15',
    });
    group.appendChild(path);
  });

  // Membrane boundary
  const bndryClasses = ['mind-boundary'];
  if (isStressed)       bndryClasses.push('mind-boundary-stressed');
  else if (isAdaptive)  bndryClasses.push('mind-boundary-adaptive');
  else if (health === 'recovering') bndryClasses.push('mind-boundary-recovering');

  group.appendChild(svgEl('path', { d: boundaryPath, fill: `url(#${gradientId})`, class: bndryClasses.join(' '),
    stroke: edgeColor, 'stroke-width': '1.5', 'stroke-opacity': '0.55' }));

  // Internal nodes from topology
  const topology = _snap.topology;
  const internalAnchors = topology?.nodes ? layoutInternalAnchors(topology.nodes) : [];
  internalAnchors.forEach(anchor => {
    const errorCls = (_snap.observerAnalysis?.predictionErrors ?? cognition?.predictionErrors)?.[anchor.id];
    if (errorCls && ['medium', 'high', 'extreme'].includes(errorCls)) {
      group.appendChild(svgEl('circle', { cx: anchor.x, cy: anchor.y, r: (anchor.r + 6),
        fill: 'none', stroke: PAL.coral, 'stroke-width': '1.2', 'stroke-dasharray': '3 2', opacity: '0.7' }));
    }
    group.appendChild(makeInternalNode(anchor, cognition));
  });

  // Synaptic fibres
  if (topology?.edges && internalAnchors.length) {
    const anchorMap = new Map(internalAnchors.map(a => [a.id, a]));
    for (const edge of topology.edges) {
      const src = anchorMap.get(edge.sourceId);
      const tgt = anchorMap.get(edge.targetId);
      if (!src || !tgt) continue;
      const isExc = edge.kind === 'excitatory';
      const isMod = ['predictive', 'gating'].includes(edge.kind);
      const strokeColor = isExc ? 'rgba(80,217,255,.55)' : isMod ? 'rgba(255,189,84,.55)' : 'rgba(255,127,131,.55)';
      const marker = isExc
        ? `url(#mind-arr-exc-${_uid})`
        : isMod
          ? `url(#mind-arr-mod-${_uid})`
          : `url(#mind-arr-inh-${_uid})`;
      group.appendChild(svgEl('line', {
        x1: src.x, y1: src.y, x2: tgt.x, y2: tgt.y,
        stroke: strokeColor, 'stroke-width': '1', 'marker-end': marker,
      }));
    }
  }

  // Belief nodes
  beliefs.forEach((belief, i) => {
    const pos = resolveBeliefPos(belief, i, sensePositions);
    const evidence = Number(belief.evidence) || 0;
    const certainty = Number(belief.certainty) || 0;
    const r = Math.max(5, Math.min(13, 5 + Math.sqrt(evidence) * 1.3));
    if (belief.dissent || belief.contested) {
      group.appendChild(svgEl('circle', { cx: pos.x, cy: pos.y, r: r + 5,
        fill: 'none', stroke: PAL.coral, 'stroke-dasharray': '3 2', 'stroke-width': '1.2',
        class: 'mind-belief-contested-halo' }));
    }
    group.appendChild(svgEl('circle', { cx: pos.x, cy: pos.y, r, fill: PAL.violet,
      opacity: String(Math.max(0.3, certainty)) }));
  });

  // HUD bar
  const samplingActive  = _snap.sampling?.active ?? senses.filter(s => s.active).length;
  const samplingProbing = _snap.sampling?.probing ?? 0;
  const acclPct = Math.round((_snap.details?.acclimation ?? 0) * 100);
  const hud = svgEl('g', { transform: 'translate(280, 692)' });
  const hudBg = svgEl('rect', { x: '-12', y: '-14', width: '340', height: '22', rx: '4', fill: 'rgba(6,14,24,0.75)' });
  const hudText = svgEl('text', { 'font-size': '10', fill: PAL.muted, y: '0' });
  hudText.textContent = `Acclimation: ${acclPct}% · Signals: ${senses.length} · Active: ${samplingActive} · Probing: ${samplingProbing}`;
  hud.append(hudBg, hudText);
  group.appendChild(hud);

  canvas.appendChild(group);
}

/** Build an approximate organic boundary path for the cell membrane. */
function buildBoundaryPath(cx, cy, rx, ry, senseCount, frozen) {
  const pts = 32;
  const coords = [];
  for (let i = 0; i <= pts; i++) {
    const angle = (i / pts) * Math.PI * 2;
    const jitter = frozen ? 0 : (Math.sin(angle * 3) * 12 + Math.sin(angle * 7) * 5);
    const x = cx + (rx + jitter) * Math.cos(angle);
    const y = cy + (ry + jitter * 0.6) * Math.sin(angle);
    coords.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  return coords.join(' ') + ' Z';
}

/** Layout internal topology nodes inside the membrane area (450±180, 360±140). */
function layoutInternalAnchors(nodes) {
  const result = [];
  nodes.forEach((node, i) => {
    const seed = hashStr(node.id);
    const angle = (i * 2.399) + ((seed % 100) / 100) * 0.2;
    const spread = 55 + ((seed % 7) * 22);
    const x = 450 + Math.cos(angle) * Math.min(spread, 180);
    const y = 360 + Math.sin(angle) * Math.min(spread * 0.75, 130);
    const r = node.kind === 'readout' ? 11 : node.kind === 'sense' ? 7 : 8;
    result.push({ id: node.id, kind: node.kind ?? 'concept', x, y, r });
  });
  return result;
}

function makeInternalNode(anchor, cognition) {
  const { id, kind, x, y, r } = anchor;
  const actClass = (_snap.observerAnalysis?.activationClasses ?? cognition?.activationClasses)?.[id] ?? 0;
  const actLevel = actClass / 15;
  const color = { sense: PAL.cyan, readout: PAL.mint, state: '#4ecdc4', predictor: PAL.amber, gate: '#e09f3e', concept: PAL.violet }[kind] ?? PAL.violet;
  const opacity = String(0.55 + actLevel * 0.4);
  let node;
  if (kind === 'sense') {
    const pts = `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`;
    node = svgEl('polygon', { points: pts, fill: color, opacity });
  } else if (kind === 'state') {
    node = svgEl('rect', { x: x - r, y: y - r, width: r * 2, height: r * 2, rx: '3', fill: color, opacity });
  } else if (kind === 'predictor') {
    const pts = `${x},${y - r * 1.3} ${x + r},${y + r * 0.85} ${x - r},${y + r * 0.85}`;
    node = svgEl('polygon', { points: pts, fill: color, opacity });
  } else if (kind === 'gate') {
    const pts = Array.from({ length: 6 }, (_, i) => {
      const a = (Math.PI / 3) * i;
      return `${(x + r * 1.1 * Math.cos(a)).toFixed(1)},${(y + r * 1.1 * Math.sin(a)).toFixed(1)}`;
    }).join(' ');
    node = svgEl('polygon', { points: pts, fill: color, opacity });
  } else if (kind === 'readout') {
    const g = svgEl('g');
    g.appendChild(svgEl('circle', { cx: x, cy: y, r, fill: color, opacity }));
    g.appendChild(svgEl('circle', { cx: x, cy: y, r: r * 0.6, fill: 'none', stroke: color, 'stroke-width': '1.2', opacity: '0.8' }));
    return g;
  } else {
    node = svgEl('circle', { cx: x, cy: y, r, fill: color, opacity });
  }
  return node;
}

function resolveBeliefPos(belief, index, sensePositions) {
  for (const [senseId, pos] of sensePositions.entries()) {
    if (belief.id.includes(senseId) || (senseId.length > 5 && belief.id.includes(senseId.slice(0, 16)))) {
      const dx = pos.x - 450, dy = pos.y - 360;
      const dist = Math.hypot(dx, dy) || 1;
      const targetDist = 95 + (index % 4) * 28;
      return { x: Math.round(450 + (dx / dist) * targetDist), y: Math.round(360 + (dy / dist) * targetDist * 0.82) };
    }
  }
  if (belief.x != null && belief.y != null) return { x: belief.x, y: belief.y };
  const angle = index * 2.399;
  const radius = 52 + (index % 5) * 38;
  return { x: Math.round(450 + Math.cos(angle) * radius), y: Math.round(360 + Math.sin(angle) * radius * 0.82) };
}

// ─────────────────────────────────────────────────────────────────────────────
// Sensory Map (simplified receptor / sense map)
// ─────────────────────────────────────────────────────────────────────────────

function renderSensoryMap() {
  const mapSvg = document.getElementById('mind-sensory-map-svg');
  const detail = document.getElementById('mind-sensory-detail');
  if (!mapSvg) return;
  mapSvg.innerHTML = '';

  const senses = _snap.senses ?? [];
  const topology = _snap.topology ?? { nodes: [], edges: [] };
  const topoNodes = Array.isArray(topology.nodes) ? topology.nodes : [];
  const topoEdges = Array.isArray(topology.edges) ? topology.edges : [];

  if (!senses.length && !topoNodes.length) {
    const msg = svgEl('text', { x: '450', y: '300', 'text-anchor': 'middle', fill: PAL.muted, 'font-size': '14' });
    msg.textContent = 'No sensory topology yet — awaiting snapshot…';
    mapSvg.appendChild(msg);
    if (detail) detail.textContent = 'This view shows the real cognitive paths learned from body-derived sensory channels.';
    return;
  }

  const W = 900, H = 600;
  const sensorNodes = topoNodes.filter(n => n.kind === 'sense');
  const internalNodes = topoNodes.filter(n => n.kind !== 'sense');
  const nodeById = new Map(topoNodes.map(n => [n.id, n]));

  const outgoing = new Map();
  for (const edge of topoEdges) {
    if (!outgoing.has(edge.sourceId)) outgoing.set(edge.sourceId, []);
    outgoing.get(edge.sourceId).push(edge);
  }

  const connectedSensors = sensorNodes.filter(n => (outgoing.get(n.id) ?? []).length > 0);
  const sensory = sensoryFacts();
  const sampledSensors = sensory.filter(sensor => sensor.sampled);
  const usefulSensors = sensory.filter(sensor => sensor.utility > 0);
  const concepts = internalNodes.filter(n => n.kind === 'concept');
  const predictors = internalNodes.filter(n => n.kind === 'predictor');
  const readouts = internalNodes.filter(n => n.kind === 'readout');

  const title = svgEl('text', { x: 28, y: 28, fill: PAL.text, 'font-size': '13', 'font-weight': '600' });
  title.textContent = 'Body-derived sensory topology';
  mapSvg.appendChild(title);
  const summary = svgEl('text', { x: 28, y: 47, fill: PAL.muted, 'font-size': '10' });
  summary.textContent = `${sensory.length || sensorNodes.length} available · ${sampledSensors.length} sampled now · ${usefulSensors.length} utility > 0 · ${connectedSensors.length} cognition-integrated · ${concepts.length} concepts`;
  mapSvg.appendChild(summary);

  const sensorArea = { x: 45, y: 80, w: 300, h: 470 };
  const internalArea = { x: 500, y: 80, w: 340, h: 470 };

  const sensorCols = 16;
  const sensorRows = Math.max(1, Math.ceil(Math.max(1, sensorNodes.length) / sensorCols));
  const sx = sensorArea.w / Math.max(1, sensorCols - 1);
  const sy = Math.min(34, sensorArea.h / Math.max(1, sensorRows - 1));
  const sensorPos = new Map();

  sensorNodes.forEach((node, index) => {
    const col = index % sensorCols;
    const row = Math.floor(index / sensorCols);
    sensorPos.set(node.id, {
      x: sensorArea.x + col * sx,
      y: sensorArea.y + row * sy,
    });
  });

  const kinds = ['concept', 'predictor', 'state', 'gate', 'readout'];
  const internalPos = new Map();
  let cursorY = internalArea.y;
  for (const kind of kinds) {
    const group = internalNodes.filter(n => n.kind === kind);
    if (!group.length) continue;
    const heading = svgEl('text', {
      x: internalArea.x,
      y: cursorY,
      fill: PAL.muted,
      'font-size': '9',
      'font-weight': '600',
    });
    heading.textContent = `${kind.toUpperCase()} · ${group.length}`;
    mapSvg.appendChild(heading);
    cursorY += 16;
    const cols = Math.min(8, Math.max(1, group.length));
    const rows = Math.ceil(group.length / cols);
    const gx = internalArea.w / Math.max(1, cols - 1);
    const gy = Math.min(30, Math.max(18, 88 / Math.max(1, rows)));
    group.forEach((node, index) => {
      internalPos.set(node.id, {
        x: internalArea.x + (index % cols) * gx,
        y: cursorY + Math.floor(index / cols) * gy,
      });
    });
    cursorY += rows * gy + 28;
  }

  const allPos = new Map([...sensorPos, ...internalPos]);

  // Real learned topology edges first, behind nodes.
  for (const edge of topoEdges) {
    const source = allPos.get(edge.sourceId);
    const target = allPos.get(edge.targetId);
    if (!source || !target) continue;
    const color =
      edge.kind === 'inhibitory' ? PAL.coral :
      edge.kind === 'predictive' ? PAL.amber :
      edge.kind === 'gating' ? '#e09f3e' : PAL.cyan;
    mapSvg.appendChild(svgEl('line', {
      x1: source.x, y1: source.y, x2: target.x, y2: target.y,
      stroke: color,
      'stroke-width': edge.sourceId.startsWith('sensor.') ? '0.8' : '1.1',
      opacity: edge.sourceId.startsWith('sensor.') ? '0.22' : '0.38',
    }));
  }

  const kindColor = {
    sense: PAL.cyan,
    concept: PAL.violet,
    predictor: PAL.amber,
    readout: PAL.mint,
    state: '#4ecdc4',
    gate: '#e09f3e',
  };

  for (const node of topoNodes) {
    const pos = allPos.get(node.id);
    if (!pos) continue;
    const isSense = node.kind === 'sense';
    const degree = topoEdges.reduce((count, e) => count + (e.sourceId === node.id || e.targetId === node.id ? 1 : 0), 0);
    const circle = svgEl('circle', {
      cx: pos.x, cy: pos.y,
      r: isSense ? (degree ? 4.5 : 3.2) : Math.min(9, 5 + degree * 0.35),
      fill: kindColor[node.kind] ?? PAL.violet,
      opacity: isSense && !degree ? '0.32' : '0.9',
      stroke: degree ? 'rgba(255,255,255,.18)' : 'none',
      'stroke-width': '0.7',
    });
    const tooltip = svgEl('title');
    const semantic = sensorySemantic(_snap.observerSemantics, node.id);
    const observerContext = observerContextForNode(
      topology,
      _snap.observerSemantics,
      node.id,
      2,
    );
    const observerText = semantic?.observerSummary
      ? `Observer: ${semantic.observerSummary}`
      : observerContext.summary
        ? `Observer context: ${observerContext.summary}`
        : 'Observer: unresolved';
    tooltip.textContent = `${node.kind} · Self: ${node.id} · ${observerText} · degree ${degree}`;
    circle.appendChild(tooltip);
    circle.style.cursor = 'pointer';
    circle.addEventListener('click', () => selectCognitiveNode(node.id));
    mapSvg.appendChild(circle);
  }

  const sensorLabel = svgEl('text', { x: sensorArea.x, y: H - 24, fill: PAL.muted, 'font-size': '10' });
  sensorLabel.textContent = 'Sensors: brighter = participates in learned topology';
  mapSvg.appendChild(sensorLabel);

  if (detail) {
    const discovery = _snap.details?.sensoryDiscoveryCounts ?? {};
    const discoveryText = Object.entries(discovery)
      .sort((a,b) => b[1]-a[1])
      .map(([state,count]) => `${state} ${count}`)
      .join(' · ');
    detail.textContent =
      `Sensory funnel: available ${sensory.length || sensorNodes.length} → sampled ${sampledSensors.length} → useful-now ${usefulSensors.length} → cognition-integrated ${connectedSensors.length}. ` +
      (discoveryText ? `Discovery hypotheses: ${discoveryText}. ` : '') +
      'These sets overlap; the arrows are a reading aid, not a claim that every stage is a strict subset.';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Self-model projection — organism-owned BodySchema
// ─────────────────────────────────────────────────────────────────────────────

function identityMetrics() {
  const phenotype = _snap.sensoryPhenotype ?? {};
  const phenotypeSensors = Array.isArray(phenotype.sensors) ? phenotype.sensors : [];
  const schema = _snap.bodySchema ?? {};
  const parts = Array.isArray(schema.parts) ? schema.parts : [];
  const sensoryParts = parts.filter(part => part.kind === 'sense');
  const cognitiveRegions = parts.filter(part => part.kind === 'cognitive_region');
  const dependencies = Array.isArray(schema.dependencies) ? schema.dependencies : [];

  const topology = _snap.topology ?? {};
  const topoNodes = Array.isArray(topology.nodes) ? topology.nodes : [];
  const topoEdges = Array.isArray(topology.edges) ? topology.edges : [];
  const graphCounts = {
    sense: topoNodes.filter(node => node.kind === 'sense').length,
    concept: topoNodes.filter(node => node.kind === 'concept').length,
    predictor: topoNodes.filter(node => node.kind === 'predictor').length,
    readout: topoNodes.filter(node => node.kind === 'readout').length,
  };

  const mean = (values) => values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : 0;

  const existence = mean(sensoryParts.map(part => classRatio(part.existence_confidence_class, 15)));
  const confidence = mean(sensoryParts.map(part => classRatio(part.confidence_class, 15)));
  const maturity = mean(sensoryParts.map(part => classRatio(part.maturity_class, 7)));
  const health = mean(sensoryParts.map(part => classRatio(part.health_class, 15)));

  const observedSensorCount = phenotypeSensors.length || graphCounts.sense || (_snap.senses ?? []).length;
  const sensoryCoverage = observedSensorCount > 0
    ? Math.min(1, sensoryParts.length / observedSensorCount)
    : 0;

  return {
    tick: finiteNumber(_tel.tick, 0),
    observedSensorCount,
    sensoryPartCount: sensoryParts.length,
    sensoryCoverage,
    existence,
    confidence,
    maturity,
    health,
    cognitiveRegions: cognitiveRegions.length,
    dependencies: dependencies.length,
    schemaState: schema.state ?? 'unknown',
    graphCounts,
    graphEdges: topoEdges.length,
  };
}

function recordIdentityHistory(metrics) {
  const last = _identityHistory[_identityHistory.length - 1];
  if (last?.tick === metrics.tick) return;
  _identityHistory.push({ ...metrics });
  while (_identityHistory.length > 180) _identityHistory.shift();
}

function deltaText(value, previous, unit = '') {
  const delta = finiteNumber(value, 0) - finiteNumber(previous, 0);
  if (Math.abs(delta) < 1e-9) return 'stable';
  return `${delta > 0 ? '+' : ''}${Number.isInteger(delta) ? delta : delta.toFixed(2)}${unit}`;
}

function renderIdentityGap() {
  const panel = document.getElementById('mind-identity-gap');
  if (!panel) return;
  panel.innerHTML = '';

  const metrics = identityMetrics();
  recordIdentityHistory(metrics);
  const baseline = _identityHistory[0] ?? metrics;

  const title = el('h3', '');
  title.style.cssText = 'font-size:12px;margin:0 0 3px;color:var(--text);';
  title.textContent = 'Difference';
  const subtitle = el('p', '');
  subtitle.style.cssText = 'font-size:9px;line-height:1.35;color:var(--muted);margin:0 0 12px;';
  subtitle.textContent = 'What can be compared without breaking the organism’s opaque self-identities.';
  panel.append(title, subtitle);

  const metric = (label, left, right, note = '') => {
    const card = el('div', '');
    card.style.cssText = 'padding:8px 0;border-top:1px solid rgba(98,120,136,.18);';
    const head = el('div', '');
    head.style.cssText = 'font-size:9px;color:var(--muted);margin-bottom:5px;';
    head.textContent = label;
    const values = el('div', '');
    values.style.cssText = 'display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:5px;';
    const l = el('strong', '');
    l.style.cssText = 'font-size:13px;text-align:right;color:var(--cyan);';
    l.textContent = String(left);
    const arrow = el('span', '');
    arrow.style.cssText = 'font-size:10px;color:var(--muted);';
    arrow.textContent = '⇄';
    const r = el('strong', '');
    r.style.cssText = 'font-size:13px;color:var(--mint);';
    r.textContent = String(right);
    values.append(l, arrow, r);
    card.append(head, values);
    if (note) {
      const small = el('div', '');
      small.style.cssText = 'font-size:8px;line-height:1.3;color:var(--muted);margin-top:4px;';
      small.textContent = note;
      card.appendChild(small);
    }
    panel.appendChild(card);
  };

  metric(
    'Sensory presence',
    metrics.observedSensorCount,
    metrics.sensoryPartCount,
    `Self representation coverage: ${pct(metrics.sensoryCoverage)}`,
  );

  metric(
    'Internal structure',
    `${metrics.graphCounts.concept}C · ${metrics.graphCounts.predictor}P · ${metrics.graphEdges}E`,
    `${metrics.cognitiveRegions} regions · ${metrics.dependencies} deps`,
    'These are different representational spaces; counts are shown side by side, not treated as one-to-one matches.',
  );

  const certainty = el('div', '');
  certainty.style.cssText = 'padding:9px 0;border-top:1px solid rgba(98,120,136,.18);';
  const certaintyTitle = el('div', '');
  certaintyTitle.style.cssText = 'font-size:9px;color:var(--muted);margin-bottom:6px;';
  certaintyTitle.textContent = 'How certain is the self-model?';
  certainty.appendChild(certaintyTitle);
  for (const [label, value] of [
    ['existence', metrics.existence],
    ['confidence', metrics.confidence],
    ['maturity', metrics.maturity],
    ['health', metrics.health],
  ]) {
    const row = el('div', '');
    row.style.cssText = 'display:grid;grid-template-columns:62px 1fr 30px;gap:5px;align-items:center;margin:4px 0;font-size:8px;';
    const name = el('span', ''); name.style.color = 'var(--muted)'; name.textContent = label;
    const bar = el('div', ''); bar.style.cssText='height:3px;background:rgba(98,120,136,.25);border-radius:2px;overflow:hidden;';
    const fill = el('div',''); fill.style.cssText=`height:100%;width:${pct(value)};background:var(--mint);`;
    bar.appendChild(fill);
    const val = el('strong',''); val.style.cssText='font-size:8px;text-align:right;'; val.textContent=pct(value);
    row.append(name,bar,val); certainty.appendChild(row);
  }
  panel.appendChild(certainty);

  const change = el('div', '');
  change.style.cssText = 'padding:9px 0;border-top:1px solid rgba(98,120,136,.18);font-size:8px;line-height:1.55;color:var(--muted);';
  const spanTicks = Math.max(0, metrics.tick - baseline.tick);
  change.innerHTML =
    `<strong style="color:var(--text)">Recent self-model change</strong><br>` +
    `over ${spanTicks} ticks · sensory parts ${deltaText(metrics.sensoryPartCount, baseline.sensoryPartCount)} · ` +
    `regions ${deltaText(metrics.cognitiveRegions, baseline.cognitiveRegions)} · dependencies ${deltaText(metrics.dependencies, baseline.dependencies)} · ` +
    `existence ${deltaText(Math.round(metrics.existence*100), Math.round(baseline.existence*100), '%')}`;
  panel.appendChild(change);

  const opaque = el('div', '');
  opaque.style.cssText = 'margin-top:7px;padding:8px;border:1px solid rgba(255,189,84,.2);border-radius:7px;background:rgba(255,189,84,.035);font-size:8px;line-height:1.4;color:var(--muted);';
  opaque.textContent =
    'Per-sensor identity correspondence is intentionally unknown here: BodySchema exposes opaque part IDs, so the observer cannot claim which external sensor equals which self-part.';
  panel.appendChild(opaque);
}

function renderSelf() {
  const panel = document.getElementById('mind-self-panel');
  if (!panel) return;
  panel.innerHTML = '';

  const schema = _snap.bodySchema;
  if (!schema || !schema.parts?.length) {
    const h = el('h2', 'mind-self-heading');
    h.textContent = 'Self-model not yet developed';
    const p = el('p', 'mind-self-body');
    p.textContent = 'No organism-owned body representation is available yet.';
    panel.append(h, p);
    return;
  }

  const parts = schema.parts ?? [];
  const sensoryParts = parts.filter(part => part.kind === 'sense');
  const cognitiveRegions = parts.filter(part => part.kind === 'cognitive_region');
  const dependencies = schema.dependencies ?? [];

  const perceptualSelf = _snap.selfModel ?? {};
  const selfEntries = Object.entries(perceptualSelf);

  const h = el('h2', 'mind-self-heading');
  h.textContent = 'How it represents itself';
  h.style.cssText = 'font-size:14px;margin:0 0 5px;';
  const body = el('p', 'mind-self-body');
  body.style.cssText = 'font-size:10px;line-height:1.45;margin:0 0 8px;color:var(--muted);';
  body.textContent =
    'Organism-owned BodySchema only: sensory parts, cognitive regions and functional dependencies treated as self.';
  panel.append(h, body);

  const perceptual = el('section', '');
  perceptual.style.cssText = 'margin:8px 0 12px;padding:9px 10px;border:1px solid rgba(80,217,255,.15);border-radius:8px;background:rgba(80,217,255,.025);';
  const ptitle = el('strong','');
  ptitle.style.cssText='display:block;font-size:10px;color:var(--cyan);margin-bottom:3px;';
  ptitle.textContent='Perceptual self-model';
  const pcopy = el('div','');
  pcopy.style.cssText='font-size:8px;line-height:1.4;color:var(--muted);';
  pcopy.textContent=`${selfEntries.length} established self-modeled receptors · organism-owned cost/health/confidence/maturity/recency classes`;
  perceptual.append(ptitle,pcopy);

  if (selfEntries.length) {
    const dots=el('div','');
    dots.style.cssText='display:flex;flex-wrap:wrap;gap:3px;margin-top:7px;';
    selfEntries.slice(0,64).forEach(([id,entry])=>{
      const dot=el('span','');
      const confidence=classRatio(entry?.confidence_class,15);
      const health=classRatio(entry?.health_class,15);
      const maturity=classRatio(entry?.maturity_class,7);
      dot.style.cssText=`width:${4+Math.round(maturity*5)}px;height:${4+Math.round(maturity*5)}px;border-radius:50%;display:block;background:${health>.7?PAL.cyan:health>.4?PAL.amber:PAL.coral};opacity:${0.25+confidence*0.7};`;
      dot.title=`${id}\nhealth ${pct(health)} · confidence ${pct(confidence)} · maturity ${pct(maturity)} · recency class ${entry?.recency_class ?? '—'}`;
      dots.appendChild(dot);
    });
    perceptual.appendChild(dots);
  }
  panel.appendChild(perceptual);

  const schemaLabel=el('strong','');
  schemaLabel.style.cssText='display:block;font-size:10px;color:var(--mint);margin:3px 0 5px;';
  schemaLabel.textContent='Functional BodySchema';
  panel.appendChild(schemaLabel);

  const summary = el('div', '');
  summary.style.cssText = 'display:flex;gap:16px;flex-wrap:wrap;margin:0 0 14px;font-size:11px;color:var(--muted);';
  summary.textContent =
    `${sensoryParts.length} sensory parts · ${cognitiveRegions.length} cognitive regions · ${dependencies.length} learned dependencies · state ${schema.state ?? 'unknown'}`;
  panel.appendChild(summary);

  const portrait = svgEl('svg', {
    viewBox: '0 0 1000 650',
    role: 'img',
    'aria-label': 'Symbiont organism-owned self-model',
  });
  portrait.style.cssText = 'width:100%;height:auto;aspect-ratio:1000/650;max-height:calc(100% - 62px);display:block;border:1px solid var(--line);border-radius:10px;background:rgba(4,14,24,.55);';
  panel.appendChild(portrait);

  const cx = 500, cy = 325;
  const regionRadius = 135;
  const senseRadius = 270;

  // Self boundary is only an epistemic envelope, not anatomy. Individual
  // parts move inward/outward according to organism-owned certainty.
  const boundary = svgEl('ellipse', {
    cx, cy, rx: '330', ry: '265',
    fill: 'rgba(113,233,186,.025)',
    stroke: 'rgba(113,233,186,.34)',
    'stroke-width': '1.5',
    'stroke-dasharray': '6 7',
  });
  portrait.appendChild(boundary);

  const selfTitle = svgEl('text', {
    x: cx, y: cy + 4,
    'text-anchor': 'middle',
    fill: PAL.mint,
    'font-size': '15',
    'font-weight': '700',
  });
  selfTitle.textContent = 'SELF';
  portrait.appendChild(selfTitle);
  const selfSub = svgEl('text', {
    x: cx, y: cy + 23,
    'text-anchor': 'middle',
    fill: PAL.muted,
    'font-size': '9',
  });
  selfSub.textContent = 'organism-owned body schema';
  portrait.appendChild(selfSub);

  const regionPos = new Map();
  cognitiveRegions.forEach((region, index) => {
    const confidence = classRatio(region.confidence_class, 15);
    const maturity = classRatio(region.maturity_class, 7);
    const seed = hashStr(region.part_id);
    const angle = ((seed % 3600) / 3600) * Math.PI * 2;
    const inward = 1 - (0.55 * confidence + 0.45 * maturity);
    const radius = 50 + regionRadius * (0.35 + inward * 0.65);
    regionPos.set(region.part_id, {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius * 0.78,
    });
  });

  // Functional dependencies are temporally smoothed on the observer side:
  // current evidence is solid, recurrent-but-intermittent evidence remains faint.
  const nowTick = finiteNumber(_tel.tick, 0);
  const dependencyViews = [..._selfDependencyHistory.values()]
    .filter(state => state.current || (state.observations > 1 && nowTick - state.lastTick <= 256));
  for (const state of dependencyViews) {
    const dep = state.dep;
    const source = regionPos.get(dep.source_id);
    const target = regionPos.get(dep.target_id);
    if (!source || !target) continue;
    const confidence = classRatio(dep.confidence_class, 15);
    const support = classRatio(dep.support_class, 15);
    const persistent = state.observations >= 8;
    const recentBirth = nowTick - state.firstTick <= 32;
    const opacity = state.current
      ? Math.min(0.95, 0.28 + support * 0.55 + (persistent ? 0.12 : 0))
      : 0.12;
    const line = svgEl('line', {
      x1: source.x, y1: source.y,
      x2: target.x, y2: target.y,
      stroke: dep.relation === 'precedes' ? PAL.amber : PAL.violet,
      'stroke-width': String(state.current ? 1 + confidence * 3 : 0.8),
      opacity: String(opacity),
      'stroke-dasharray': !state.current ? '2 5' : dep.relation === 'precedes' ? '4 4' : 'none',
    });
    if (recentBirth && state.current) line.setAttribute('stroke-width', String(2 + confidence * 3));
    const title = svgEl('title');
    title.textContent =
      `${dep.relation} · confidence ${pct(confidence)} · support ${pct(support)} · ` +
      `${state.current ? 'current' : 'recurrent/intermittent'} · observed ${state.observations} snapshots`;
    line.appendChild(title);
    portrait.appendChild(line);
  }

  // Cognitive regions are the inner learned functional self.
  cognitiveRegions.forEach((region, index) => {
    const pos = regionPos.get(region.part_id);
    if (!pos) return;
    const existence = classRatio(region.existence_confidence_class, 15);
    const confidence = classRatio(region.confidence_class, 15);
    const activity = classRatio(region.activity_class, 15);
    const maturity = classRatio(region.maturity_class, 7);
    const persistence = _selfRegionHistory.get(region.part_id);
    const persistenceScore = persistence
      ? clamp01(persistence.observations / Math.max(8, _identityHistory.length || 8))
      : 0;
    const radius = 7 + 8 * Math.sqrt(Math.max(activity, maturity * 0.6)) + persistenceScore * 4;
    const node = svgEl('circle', {
      cx: pos.x, cy: pos.y, r: radius.toFixed(1),
      fill: PAL.violet,
      opacity: String(0.35 + existence * 0.6),
      stroke: confidence > 0.7 ? PAL.mint : 'rgba(167,119,255,.45)',
      'stroke-width': String(1 + confidence * 1.6 + persistenceScore * 1.5),
    });
    const title = svgEl('title');
    title.textContent =
      `Cognitive region ${index + 1}\nexistence ${pct(existence)} · confidence ${pct(confidence)} · activity ${pct(activity)} · maturity ${pct(maturity)} · persistence ${pct(persistenceScore)}\n${region.part_id}`;
    node.appendChild(title);
    portrait.appendChild(node);
  });

  // Sensory parts form the outer perceived boundary of self. Their positions
  // are deliberately non-anatomical because BodySchema contains no spatial
  // anatomy and inventing one would contaminate interpretation.
  sensoryParts.forEach((part, index) => {
    const existence = classRatio(part.existence_confidence_class, 15);
    const health = classRatio(part.health_class, 15);
    const confidence = classRatio(part.confidence_class, 15);
    const maturity = classRatio(part.maturity_class, 7);
    const seed = hashStr(part.part_id ?? String(index));
    const angle = ((seed % 10000) / 10000) * Math.PI * 2;
    const uncertainty = 1 - (existence * 0.55 + confidence * 0.25 + maturity * 0.20);
    const radialNoise = (((seed >>> 4) % 101) / 100 - 0.5) * 38;
    const r = 190 + senseRadius * 0.18 + uncertainty * 72 + radialNoise;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r * 0.78;
    const radius = 2.5 + 5.5 * Math.sqrt(Math.max(confidence, maturity * 0.5));
    const healthColor =
      health > 0.75 ? PAL.cyan :
      health > 0.45 ? PAL.amber : PAL.coral;

    const spoke = svgEl('line', {
      x1: cx, y1: cy, x2: x, y2: y,
      stroke: healthColor,
      'stroke-width': '0.55',
      opacity: String(0.035 + confidence * 0.11),
    });
    portrait.appendChild(spoke);

    const node = svgEl('circle', {
      cx: x, cy: y, r: radius.toFixed(1),
      fill: healthColor,
      opacity: String(0.22 + existence * 0.75),
      stroke: confidence > 0.75 ? 'rgba(255,255,255,.38)' : 'none',
      'stroke-width': '0.8',
    });
    const title = svgEl('title');
    title.textContent =
      `Sensory part ${index + 1}\nexistence ${pct(existence)} · health ${pct(health)} · confidence ${pct(confidence)} · maturity ${pct(maturity)}\n${part.part_id}`;
    node.appendChild(title);
    portrait.appendChild(node);
  });

  const legend = svgEl('text', {
    x: '26', y: '625',
    fill: PAL.muted,
    'font-size': '10',
  });
  legend.textContent =
    'Outer ring = self-known sensory parts · inner nodes = learned cognitive regions · lines = organism-inferred functional dependencies · size/opacity = organism-owned confidence/activity/maturity';
  portrait.appendChild(legend);
}

// ─────────────────────────────────────────────────────────────────────────────
// Cognition Graph (force-directed canvas; adapted from observatory/render/cognition-graph.js)
// ─────────────────────────────────────────────────────────────────────────────

function selectCognitiveNode(nodeId) {
  _graph.selectedNodeId = nodeId || null;
  switchTab('cognition');
  renderCognitionInspector();
  const canvas = document.getElementById('mind-cognition-canvas');
  if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
}

function buildGraphModel() {
  const source = _graph.replaySnapshot ?? _snap;
  const topology = source.topology;
  const cognition = source.cognition;

  if (!topology?.nodes?.length) {
    const beliefs = (_snap.beliefs ?? []).slice(0, 8);
    const senses  = (_snap.senses ?? []).slice(0, 4);
    const nodes = [
      ...senses.map(s => ({
        id: s.id,
        label: s.name ?? s.id,
        kind: 'sense',
        color: PAL.cyan,
        baseRadius: 6,
        activationLevel: s.active ? 0.8 : 0.1,
      })),
      ...beliefs.map(b => ({
        id: b.id,
        label: b.title ?? b.id,
        kind: 'concept',
        color: PAL.violet,
        baseRadius: 7,
        activationLevel: clamp01(b.certainty ?? 0.3),
      })),
    ];
    const edges = [];
    senses.forEach((s, si) => {
      beliefs.slice(si * 2, si * 2 + 2).forEach(b => {
        edges.push({ sourceId: s.id, targetId: b.id, kind: 'excitatory' });
      });
    });
    return enrichGraphModel(nodes, edges);
  }

  const errors   = (source.observerAnalysis?.predictionErrors ?? cognition?.predictionErrors) ?? {};
  const readouts = cognition?.readouts ?? {};
  const actClass = (source.observerAnalysis?.activationClasses ?? cognition?.activationClasses) ?? {};
  const stranded = cognition?.strandedConcepts ?? [];

  const learned = augmentLearnedGraph(
    topology,
    source.sensorimotor ?? _snap.sensorimotor,
    source.observerSemantics ?? _snap.observerSemantics,
    source.prospectiveAgency ?? null,
  );
  const cartography = cartographicGraph(
    learned.nodes,
    learned.edges,
    _graph.selectedNodeId,
  );
  _graph.hiddenMotor = cartography.hidden;
  const completeTopology = { nodes: cartography.nodes, edges: cartography.edges };

  const colorMap = {
    sense: PAL.cyan,
    readout: PAL.mint,
    state: '#4ecdc4',
    predictor: PAL.amber,
    gate: '#e09f3e',
    concept: PAL.violet,
    motor_primitive: '#ff8fd8',
    actuator: '#8fe3ff',
  };
  const baseRadiusMap = {
    sense: 5.2,
    readout: 8.5,
    state: 6.5,
    predictor: 7.2,
    gate: 6.8,
    concept: 6.4,
    motor_primitive: 8.4,
    actuator: 6.8,
  };

  const rawNodes = completeTopology.nodes.map(n => {
    const kind = n.kind ?? 'concept';
    const activationLevel = classRatio(actClass[n.id] ?? 0, 15);
    const readoutRaw = readouts[n.id];
    const readoutMagnitude = readoutRaw != null
      ? Math.min(1, Math.abs(finiteNumber(readoutRaw, 0)))
      : 0;

    const semantic = sensorySemantic(source.observerSemantics ?? _snap.observerSemantics, n.id);
    return {
      id: n.id,
      label: n.id,
      observerLabel: n.observerLabel ?? semantic?.observerSummary ?? null,
      kind,
      color: colorMap[kind] ?? PAL.violet,
      baseRadius: baseRadiusMap[kind] ?? 6.4,
      activationLevel: n.replayActive || n.prospectiveSelected
        ? 1
        : activationLevel,
      readoutMagnitude,
      errorCls: errors[n.id] ?? null,
      readoutVal: readoutRaw != null ? finiteNumber(readoutRaw, 0).toFixed(3) : null,
      isStranded: stranded.includes(n.id),
      learnedLayer: n.learnedLayer ?? null,
      cognitivePrimitive: Boolean(n.cognitive),
      replayActive: Boolean(n.replayActive),
      prospectiveSelected: Boolean(n.prospectiveSelected),
      controllability: finiteNumber(n.controllability, 0),
      directionalConsistency: finiteNumber(n.directionalConsistency, 0),
      samples: finiteNumber(n.samples, 0),
      effectVariance: finiteNumber(n.effectVariance, 0),
      effectStrength: finiteNumber(n.effectStrength, 0),
      activations: finiteNumber(n.activations, 0),
      causalRelationCount: finiteNumber(n.causalRelationCount, 0),
      actuatorIds: n.actuatorIds ?? [],
      primitiveId: n.primitiveId ?? null,
      activeRepertoire: Boolean(n.activeRepertoire),
      effectorId: n.effectorId ?? null,
    };
  });

  const nodeSet = new Set(rawNodes.map(n => n.id));
  const edges = (completeTopology.edges ?? [])
    .filter(e => nodeSet.has(e.sourceId) && nodeSet.has(e.targetId))
    .map(e => ({
      sourceId: e.sourceId,
      targetId: e.targetId,
      kind: e.kind ?? 'excitatory',
      weight: finiteNumber(e.weight, 0),
      plasticity: clamp01(e.plasticity),
      delayTicks: finiteNumber(e.delayTicks, 0),
      support: finiteNumber(e.support, 0),
      ageTicks: finiteNumber(e.ageTicks, 0),
      stableTicks: finiteNumber(e.stableTicks, 0),
      lastUseTick: finiteNumber(e.lastUseTick, 0),
      learnedLayer: e.learnedLayer ?? null,
      correlation: finiteNumber(e.correlation, 0),
      samples: finiteNumber(e.samples, 0),
    }));

  const filtered = filterGraphForView(rawNodes, edges, _graph.viewMode);
  const enriched = enrichGraphModel(filtered.nodes, filtered.edges);

  const affinities = buildLayoutAffinities(enriched.nodes, enriched.edges);
  const sectors = deriveFunctionalSectors(enriched.nodes, affinities);
  const sectorNodes = new Map();
  for (const node of enriched.nodes) {
    node.community = sectors.get(node.id) ?? 'isolated';
    if (node.community === 'isolated') continue;
    if (!sectorNodes.has(node.community)) sectorNodes.set(node.community, []);
    sectorNodes.get(node.community).push(node);
  }
  enriched.communities = sectors;
  enriched.layoutAffinities = affinities;
  enriched.sectorDescriptions = new Map(
    [...sectorNodes.entries()].map(([sectorId, members]) => [
      sectorId,
      describeFunctionalSector(members),
    ])
  );
  enriched.sectorBridges = sectorBridges(enriched.edges, sectors);
  return enriched;
}

function jaccardOverlap(a, b) {
  if (!a?.size || !b?.size) return 0;
  let intersection = 0;
  const smaller = a.size <= b.size ? a : b;
  const larger = smaller === a ? b : a;
  for (const item of smaller) if (larger.has(item)) intersection += 1;
  return intersection / (a.size + b.size - intersection);
}

function reconcileSectorLabels(communities, nodes) {
  const current = new Map();
  for (const node of nodes) {
    if (!node.community || node.community === 'isolated') continue;
    if (!current.has(node.community)) current.set(node.community, new Set());
    current.get(node.community).add(node.id);
  }

  const assigned = new Map();
  const usedPrevious = new Set();
  const ordered = [...current.entries()].sort((a,b) => b[1].size-a[1].size);

  for (const [communityId, members] of ordered) {
    let bestLabel = null;
    let bestOverlap = 0;
    for (const [label, previousMembers] of _graph.sectorMemory.entries()) {
      if (usedPrevious.has(label)) continue;
      const overlap = jaccardOverlap(members, previousMembers);
      if (overlap > bestOverlap) {
        bestOverlap = overlap;
        bestLabel = label;
      }
    }
    if (!bestLabel || bestOverlap < 0.45) {
      bestLabel = `S-${String(_graph.nextSectorId++).padStart(3,'0')}`;
    }
    usedPrevious.add(bestLabel);
    assigned.set(communityId, bestLabel);
  }

  _graph.sectorLabels = assigned;
  _graph.sectorMemory = new Map(
    [...assigned.entries()].map(([communityId,label]) => [label, new Set(current.get(communityId) ?? [])])
  );
}

function initGraphPhysics(width, height) {
  const {
    nodes: rawNodes,
    edges: rawEdges,
    adjacency,
    communities,
    components = [],
    layoutAffinities = [],
    sectorDescriptions = new Map(),
    sectorBridges: bridges = [],
  } = buildGraphModel();
  const cx = width / 2, cy = height / 2;
  const nodeMap = new Map();

  _graph.communities = new Map();
  _graph.components = components;
  _graph.layoutAffinities = layoutAffinities;
  _graph.sectorDescriptions = sectorDescriptions;
  _graph.bridgeEdges = new Set();
  for (const bridge of bridges) {
    const ranked = [...bridge.edges].sort((a,b) =>
      finiteNumber(b.support,0) - finiteNumber(a.support,0) ||
      Math.abs(finiteNumber(b.correlation,0)) - Math.abs(finiteNumber(a.correlation,0))
    ).slice(0, 2);
    for (const edge of ranked) {
      _graph.bridgeEdges.add(`${edge.sourceId}|${edge.targetId}|${edge.kind}`);
    }
  }
  for (const raw of rawNodes) {
    if (!raw.community || raw.community === 'isolated') continue;
    if (!_graph.communities.has(raw.community)) {
      _graph.communities.set(raw.community, []);
    }
    _graph.communities.get(raw.community).push(raw.id);
  }
  if (_graph.replaySnapshot) {
    _graph.sectorLabels = new Map(
      [..._graph.communities.keys()].map(communityId => [
        communityId,
        `R-${String(hashStr(String(communityId)) % 997).padStart(3,'0')}`,
      ])
    );
  } else {
    reconcileSectorLabels(_graph.communities, rawNodes);
  }

  const activeSectorLabels = new Set();
  for (const communityId of _graph.communities.keys()) {
    const label = _graph.sectorLabels.get(communityId);
    if (!label) continue;
    activeSectorLabels.add(label);
    if (!_graph.sectorAnchors.has(label)) {
      const ordinal = Math.max(1, parseInt(label.replace(/\D/g, ''), 10) || (hashStr(label) % 97) + 1);
      const angle = ordinal * 2.399963229728653;
      const ring = ordinal % 3;
      const rx = Math.min(width * (0.20 + ring * 0.035), 320);
      const ry = Math.min(height * (0.18 + ring * 0.03), 230);
      _graph.sectorAnchors.set(label, {
        x: cx + Math.cos(angle) * rx,
        y: cy + Math.sin(angle) * ry,
      });
    }
  }

  _graph.nodes = rawNodes.map((raw, i) => {
    let node = _graph.cachedPositions.get(raw.id);
    if (!node) {
      const seed = hashStr(raw.id);
      let x;
      let y;

      if (raw.isolated) {
        // Objective unintegrated pool: disconnected nodes occupy a peripheral
        // band instead of participating in the same force field as cognition.
        const cols = Math.max(8, Math.floor(width / 34));
        const isolatedIndex = rawNodes.slice(0, i + 1).filter(item => item.isolated).length - 1;
        const col = isolatedIndex % cols;
        const row = Math.floor(isolatedIndex / cols);
        x = 22 + col * ((width - 44) / Math.max(1, cols - 1));
        y = height - 28 - row * 20;
      } else {
        const sectorLabel = _graph.sectorLabels.get(raw.community);
        const anchor = sectorLabel ? _graph.sectorAnchors.get(sectorLabel) : null;
        const localAngle = ((seed % 360) / 180) * Math.PI;
        const localRadius = 18 + (seed % 7) * 9;
        x = (anchor?.x ?? cx) + Math.cos(localAngle) * localRadius;
        y = (anchor?.y ?? cy) + Math.sin(localAngle) * localRadius;
      }

      node = {
        ...raw,
        x, y,
        vx: 0,
        vy: 0,
        pinned: false,
      };
      _graph.cachedPositions.set(raw.id, node);
    } else {
      Object.assign(node, raw);
    }
    node.neighbors = adjacency.get(raw.id) ?? new Set();
    const sectorLabel = _graph.sectorLabels.get(raw.community);
    node.sectorLabel = sectorLabel ?? null;
    node.sectorAnchor = sectorLabel ? (_graph.sectorAnchors.get(sectorLabel) ?? null) : null;
    nodeMap.set(node.id, node);
    return node;
  });

  _graph.edges = rawEdges
    .map(e => ({
      ...e,
      source: nodeMap.get(e.sourceId),
      target: nodeMap.get(e.targetId),
    }))
    .filter(e => e.source && e.target);

  _graph.layoutAffinities = layoutAffinities
    .map(link => ({
      ...link,
      source: nodeMap.get(link.sourceId),
      target: nodeMap.get(link.targetId),
    }))
    .filter(link => link.source && link.target);

  _graph.alpha = 1.0;
  renderCognitionInspector();
}

function stepGraphPhysics(width, height) {
  const { nodes, edges } = _graph;
  const n = nodes.length;
  if (!n) return;
  const cx = width / 2, cy = height / 2;
  const alpha = _graph.alpha;

  const communityCenters = new Map();
  for (const node of nodes) {
    if (!node.community || node.community === 'isolated') continue;
    const state = communityCenters.get(node.community) ?? { x: 0, y: 0, n: 0 };
    state.x += node.x;
    state.y += node.y;
    state.n += 1;
    communityCenters.set(node.community, state);
  }
  for (const state of communityCenters.values()) {
    state.x /= Math.max(1, state.n);
    state.y /= Math.max(1, state.n);
  }

  // Relationship-aware repulsion/attraction.
  for (let i = 0; i < n; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < n; j++) {
      const b = nodes[j];
      const dx = b.x - a.x, dy = b.y - a.y;
      const distSq = dx * dx + dy * dy + 144;
      if (distSq > 490000) continue;
      const dist = Math.sqrt(distSq);

      const directlyRelated = a.neighbors?.has(b.id) || b.neighbors?.has(a.id);
      let shared = 0;
      if (!directlyRelated && a.neighbors?.size && b.neighbors?.size) {
        const smaller = a.neighbors.size < b.neighbors.size ? a.neighbors : b.neighbors;
        const larger  = smaller === a.neighbors ? b.neighbors : a.neighbors;
        for (const id of smaller) {
          if (larger.has(id)) shared += 1;
          if (shared >= 3) break;
        }
      }

      const sameCommunity =
        a.community &&
        b.community &&
        a.community !== 'isolated' &&
        a.community === b.community;

      // Unrelated nodes repel more strongly, making visual sectors emerge.
      const repulsionScale = directlyRelated ? 0.25 : sameCommunity ? 0.62 : 1.28;
      const force = ((REPULSION * repulsionScale) / distSq) * alpha;
      const fx = (dx / dist) * force, fy = (dy / dist) * force;
      if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
      if (!b.pinned) { b.vx += fx; b.vy += fy; }

      // Two nodes sharing downstream/upstream partners get a weak secondary
      // attraction. It uses graph structure only; no semantic clustering.
      if (!directlyRelated && shared > 0) {
        const desired = 95 + 18 / shared;
        const pull = (dist - desired) * 0.0065 * Math.min(3, shared) * alpha;
        const pfx = (dx / dist) * pull, pfy = (dy / dist) * pull;
        if (!a.pinned) { a.vx += pfx; a.vy += pfy; }
        if (!b.pinned) { b.vx -= pfx; b.vy -= pfy; }
      }
    }
  }

  // Direct graph edges are the strongest attractive force.
  for (const edge of edges) {
    const dx = edge.target.x - edge.source.x;
    const dy = edge.target.y - edge.source.y;
    const dist = Math.hypot(dx, dy) || 1;
    const touchesReadout = edge.source.kind === 'readout' || edge.target.kind === 'readout';
    const relationStrength = (
      edge.kind === 'gating' ? 1.25 :
      edge.kind === 'predictive' ? 1.18 :
      edge.kind === 'inhibitory' ? 1.05 : 1.0
    ) * (touchesReadout ? 0.58 : 1.0);
    const desired = touchesReadout ? 112 :
      edge.kind === 'predictive' ? 76 :
      edge.kind === 'gating' ? 72 : 88;
    const disp = dist - desired;
    const force = disp * SPRING_K * relationStrength * alpha;
    const fx = (dx / dist) * force, fy = (dy / dist) * force;
    if (!edge.source.pinned) { edge.source.vx += fx; edge.source.vy += fy; }
    if (!edge.target.pinned) { edge.target.vx -= fx; edge.target.vy -= fy; }
  }

  // Local-sector cohesion. This is only a layout force over communities derived
  // from topology; it does not alter or classify the organism.
  for (const node of nodes) {
    if (node.pinned || node.isolated) continue;
    const center = node.community ? communityCenters.get(node.community) : null;
    if (center) {
      const cohesion = 0.018 * alpha;
      node.vx += (center.x - node.x) * cohesion;
      node.vy += (center.y - node.y) * cohesion;
    }

    // Very weak global gravity prevents disconnected material escaping forever.
    node.vx += (cx - node.x) * (CENTER_G * 0.72) * alpha;
    node.vy += (cy - node.y) * (CENTER_G * 0.72) * alpha;

    const radial = Math.hypot(node.x - cx, node.y - cy);
    const maxRadius = Math.min(width, height) * 0.43;
    if (radial > maxRadius) {
      const excess = radial - maxRadius;
      node.vx += ((cx - node.x) / radial) * excess * 0.018 * alpha;
      node.vy += ((cy - node.y) / radial) * excess * 0.018 * alpha;
    }

    node.vx *= DAMPING;
    node.vy *= DAMPING;
    node.x += node.vx;
    node.y += node.vy;
  }

  _graph.alpha = Math.max(ALPHA_MIN, _graph.alpha * ALPHA_DECAY);
}

function drawGraphFrame(canvas) {
  updateCognitionSummary();
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  const { nodes, edges, scale, panX, panY, hoveredNode, fmriEnabled } = _graph;
  ctx.clearRect(0, 0, width, height);
  if (!nodes.length) return;

  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(scale, scale);

  const now = performance.now();

  const isolatedCount = nodes.filter(node => node.isolated).length;
  if (isolatedCount && _graph.viewMode === 'full') {
    ctx.font = '9px -apple-system, sans-serif';
    ctx.fillStyle = 'rgba(98,120,136,.72)';
    ctx.textAlign = 'left';
    ctx.fillText(`UNINTEGRATED · ${isolatedCount}`, 18, height / scale - 14);
  }

  // Draw relationship sectors behind the graph. Sectors are computed from the
  // current layout of topology-derived local communities; they are not organism
  // concepts and therefore carry no semantic labels.
  const communityStats = new Map();
  for (const node of nodes) {
    if (!node.community || node.community === 'isolated') continue;
    const s = communityStats.get(node.community) ?? { x: 0, y: 0, n: 0, nodes: [] };
    s.x += node.x; s.y += node.y; s.n += 1; s.nodes.push(node);
    communityStats.set(node.community, s);
  }
  for (const [communityId, s] of communityStats.entries()) {
    if (s.n < 3) continue;
    s.x /= s.n; s.y /= s.n;
    let radius = 0;
    for (const node of s.nodes) {
      radius = Math.max(radius, Math.hypot(node.x - s.x, node.y - s.y) + node.radius);
    }
    radius = Math.max(38, Math.min(180, radius + 18));
    const palette = [PAL.violet, PAL.cyan, PAL.amber, PAL.mint, '#4ecdc4', '#e09f3e'];
    const color = palette[hashStr(String(communityId)) % palette.length];
    ctx.beginPath();
    ctx.arc(s.x, s.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = `${color}0b`;
    ctx.strokeStyle = `${color}20`;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 7]);
    ctx.fill();
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.setLineDash([]);

    // Neutral observer label. It identifies a structural sector without
    // pretending that the organism has assigned it a semantic category.
    const sectorLabel = _graph.sectorLabels.get(communityId) ?? 'S-???';
    ctx.font = '9px -apple-system, sans-serif';
    ctx.fillStyle = `${color}99`;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${sectorLabel} · ${s.n}`, s.x + radius * 0.58, s.y - radius * 0.58);
  }

  const focusId = hoveredNode?.id ?? _graph.selectedNodeId;
  const activeTopology = currentRenderedTopology();
  const connectedIds = focusId ? graphSubgraphIds(activeTopology, focusId, _graph.pathDepth) : null;

  // Edges
  for (const edge of edges) {
    const isConn = Boolean(focusId && connectedIds?.has(edge.source.id) && connectedIds?.has(edge.target.id));
    const dimmed = Boolean(focusId && !isConn);
    let color;
    if (edge.kind === 'inhibitory')  color = `rgba(255,127,131,${isConn ? .95 : dimmed ? .04 : .35})`;
    else if (edge.kind === 'predictive') color = `rgba(255,189,84,${isConn ? .95 : dimmed ? .04 : .40})`;
    else if (edge.kind === 'gating') color = `rgba(224,159,62,${isConn ? .95 : dimmed ? .04 : .38})`;
    else if (edge.kind === 'invokes') color = `rgba(255,143,216,${isConn ? .98 : dimmed ? .05 : .68})`;
    else if (edge.kind === 'motor_component') color = `rgba(143,227,255,${isConn ? .98 : dimmed ? .05 : .58})`;
    else if (edge.kind === 'causal_effect') color = `rgba(113,233,186,${isConn ? .98 : dimmed ? .05 : .62})`;
    else                             color = `rgba(80,217,255,${isConn ? .95 : dimmed ? .04 : .28})`;
    ctx.beginPath();
    ctx.moveTo(edge.source.x, edge.source.y);
    ctx.lineTo(edge.target.x, edge.target.y);
    const supportScale = Math.min(1, Math.log1p(Math.max(0, edge.support ?? 0)) / 7);
    const liveTick = finiteNumber(_graph.replayTick ?? _tel.tick, 0);
    const idleTicks = Math.max(0, liveTick - finiteNumber(edge.lastUseTick, liveTick));
    const recency = Math.exp(-idleTicks / 512);
    ctx.strokeStyle = color;
    ctx.globalAlpha = dimmed ? 0.18 : Math.max(0.18, 0.35 + recency * 0.65);
    ctx.lineWidth   = isConn ? 2.8 : 0.8 + supportScale * 2.4;
    ctx.setLineDash(edge.kind === 'inhibitory' ? [4, 4] : edge.kind === 'gating' ? [2, 3] : edge.kind === 'causal_effect' ? [6, 3] : []);
    ctx.stroke();
    ctx.setLineDash([]);
    // Arrowhead
    if (!dimmed) {
      const dx = edge.target.x - edge.source.x, dy = edge.target.y - edge.source.y;
      const dist = Math.hypot(dx, dy);
      if (dist > 14) {
        const angle = Math.atan2(dy, dx);
        const tr = (edge.target.radius ?? 6) + 3;
        const tx = edge.target.x - Math.cos(angle) * tr;
        const ty = edge.target.y - Math.sin(angle) * tr;
        const al = isConn ? 6 : 4;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(tx - al * Math.cos(angle - Math.PI / 6), ty - al * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(tx - al * Math.cos(angle + Math.PI / 6), ty - al * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fill();
      }
    }
  }

  // Nodes
  for (const node of nodes) {
    const isHovered = hoveredNode && hoveredNode.id === node.id;
    const isSelected = _graph.selectedNodeId === node.id;
    const isConn = connectedIds && connectedIds.has(node.id);
    const dimmed = focusId && !isConn;
    const breath = (fmriEnabled && node.activationLevel > 0)
      ? Math.sin(now * 0.003 + hashStr(node.id)) * (node.activationLevel * 2.0)
      : 0;
    const r = ((isHovered || isSelected) ? node.radius * 1.35 : node.radius) + breath;

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fillStyle = isHovered ? '#fff' : node.color;
    ctx.shadowColor = node.color;
    ctx.shadowBlur  = isSelected ? 20 : isConn ? 14 : (fmriEnabled && node.activationLevel > 0 ? 4 + node.activationLevel * 12 : 3);
    const graphTick = finiteNumber(_graph.replayTick ?? _tel.tick, 0);
    const nodeIdleTicks = node.lastUseTick > 0 ? Math.max(0, graphTick - node.lastUseTick) : 2048;
    const nodeRecency = Math.exp(-nodeIdleTicks / 768);
    // Size is structural importance, glow is current activity, opacity is
    // recency of structural use. These dimensions deliberately stay separate.
    ctx.globalAlpha = dimmed
      ? 0.12
      : Math.min(1, 0.28 + nodeRecency * 0.52 + (isSelected || isHovered ? 0.2 : 0));
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.shadowBlur  = 0;

    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 5, 0, Math.PI * 2);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Error ring
    if (node.errorCls && ['medium', 'high', 'extreme'].includes(node.errorCls)) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 3.5, 0, Math.PI * 2);
      ctx.strokeStyle = PAL.coral;
      ctx.lineWidth = 1.4;
      ctx.setLineDash([2, 2]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Readout label
    if (node.kind === 'readout' && node.readoutVal) {
      ctx.font = '10px monospace';
      ctx.fillStyle = PAL.mint;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.readoutVal, node.x, node.y);
    }

    // Label below (visible at close zoom or for readout/sense)
    if (!dimmed && (isConn || scale >= 1.35 || node.kind === 'readout' || node.visualValue > 0.72)) {
      ctx.font = '10px -apple-system, sans-serif';
      ctx.fillStyle = isConn ? '#fff' : 'rgba(175,199,220,.7)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      const observerLabel = node.observerLabel;
      const primary = observerLabel ?? node.label;
      const lbl = primary.length > 22 ? primary.slice(0, 18) + '…' : primary;
      ctx.fillText(lbl, node.x, node.y + r + 10);
      if ((isHovered || isSelected) && observerLabel) {
        ctx.font = '8px -apple-system, sans-serif';
        ctx.fillStyle = 'rgba(175,199,220,.55)';
        ctx.fillText(compactSelfLabel(node.label), node.x, node.y + r + 20);
      }
    }
  }

  ctx.restore();
}

function cognitionAnimLoop() {
  if (_activeTab !== 'cognition') {
    _graph.isRunning = false;
    _rafId = null;
    return;
  }
  const canvas = document.getElementById('mind-cognition-canvas');
  if (!canvas) { _graph.isRunning = false; _rafId = null; return; }

  // Resize canvas to wrapper
  const wrap = canvas.parentElement;
  if (wrap) {
    const rect = wrap.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      if (canvas.width !== Math.floor(rect.width) || canvas.height !== Math.floor(rect.height)) {
        canvas.width  = Math.floor(rect.width);
        canvas.height = Math.floor(rect.height);
        _graph.alpha  = Math.max(_graph.alpha, 0.5);
      }
    }
  }

  stepGraphPhysics(canvas.width, canvas.height);
  drawGraphFrame(canvas);

  const keepRunning = _graph.alpha > ALPHA_MIN || _graph.isRunning;
  if (keepRunning) {
    _rafId = requestAnimationFrame(cognitionAnimLoop);
  } else {
    _rafId = null;
  }
}

function startCognitionGraph() {
  const canvas = document.getElementById('mind-cognition-canvas');
  if (!canvas) return;
  const wrap = canvas.parentElement;
  if (wrap) {
    const rect = wrap.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      canvas.width = Math.floor(rect.width);
      canvas.height = Math.floor(rect.height);
    }
  }
  if (!canvas.dataset.listenersInstalled) {
    installGraphListeners(canvas);
    canvas.dataset.listenersInstalled = 'true';
  }
  initGraphPhysics(canvas.width || 900, canvas.height || 600);
  _graph.isRunning = true;
  if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);

  // Button bindings
  const fmriBtn  = document.getElementById('mind-fmri-btn');
  const zoomIn   = document.getElementById('mind-zoom-in');
  const zoomOut  = document.getElementById('mind-zoom-out');
  const resetBtn = document.getElementById('mind-graph-reset');

  if (fmriBtn && !fmriBtn.dataset.bound) {
    fmriBtn.dataset.bound = 'true';
    fmriBtn.addEventListener('click', () => {
      _graph.fmriEnabled = !_graph.fmriEnabled;
      fmriBtn.classList.toggle('active', _graph.fmriEnabled);
    });
  }
  if (zoomIn && !zoomIn.dataset.bound) {
    zoomIn.dataset.bound = 'true';
    zoomIn.addEventListener('click', () => {
      const cx = canvas.width / 2, cy = canvas.height / 2;
      const ns = Math.min(5, _graph.scale * 1.25);
      _graph.panX = cx - (cx - _graph.panX) * (ns / _graph.scale);
      _graph.panY = cy - (cy - _graph.panY) * (ns / _graph.scale);
      _graph.scale = ns;
    });
  }
  if (zoomOut && !zoomOut.dataset.bound) {
    zoomOut.dataset.bound = 'true';
    zoomOut.addEventListener('click', () => {
      const cx = canvas.width / 2, cy = canvas.height / 2;
      const ns = Math.max(0.2, _graph.scale * 0.8);
      _graph.panX = cx - (cx - _graph.panX) * (ns / _graph.scale);
      _graph.panY = cy - (cy - _graph.panY) * (ns / _graph.scale);
      _graph.scale = ns;
    });
  }
  if (resetBtn && !resetBtn.dataset.bound) {
    resetBtn.dataset.bound = 'true';
    resetBtn.addEventListener('click', () => {
      _graph.scale = 1; _graph.panX = 0; _graph.panY = 0;
      _graph.cachedPositions.clear();
      _graph.alpha = 1.0;
    });
  }
}

function installGraphListeners(canvas) {
  let isPanning = false, isDragging = false, draggedNode = null;
  let pressedNode = null;
  let panStartX = 0, panStartY = 0, dragDist = 0;

  function canvasCoords(event) {
    const rect = canvas.getBoundingClientRect();
    const sx = rect.width > 0 ? canvas.width / rect.width : 1;
    const sy = rect.height > 0 ? canvas.height / rect.height : 1;
    return { x: (event.clientX - rect.left) * sx, y: (event.clientY - rect.top) * sy };
  }
  function findNode(mx, my) {
    const wx = (mx - _graph.panX) / _graph.scale;
    const wy = (my - _graph.panY) / _graph.scale;
    for (let i = _graph.nodes.length - 1; i >= 0; i--) {
      const n = _graph.nodes[i];
      if (Math.hypot(n.x - wx, n.y - wy) <= n.radius + 6) return n;
    }
    return null;
  }

  canvas.addEventListener('wheel', ev => {
    ev.preventDefault();
    const factor = ev.deltaY < 0 ? 1.12 : 0.89;
    const ns = Math.min(5, Math.max(0.2, _graph.scale * factor));
    const { x, y } = canvasCoords(ev);
    _graph.panX = x - (x - _graph.panX) * (ns / _graph.scale);
    _graph.panY = y - (y - _graph.panY) * (ns / _graph.scale);
    _graph.scale = ns;
    _graph.alpha = Math.max(_graph.alpha, 0.1);
    if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);
  }, { passive: false });

  canvas.addEventListener('mousedown', ev => {
    if (ev.button !== 0) return;
    const { x, y } = canvasCoords(ev);
    const node = findNode(x, y);
    dragDist = 0;
    pressedNode = node;
    if (node) { isDragging = true; draggedNode = node; node.pinned = true; node.vx = node.vy = 0; }
    else { isPanning = true; panStartX = x - _graph.panX; panStartY = y - _graph.panY; canvas.style.cursor = 'grabbing'; }
  });

  // Window listeners outlive the canvas, so keep explicit references and
  // remove them during unmount/remount. This prevents listener accumulation.
  if (_graphWindowMouseMove) window.removeEventListener('mousemove', _graphWindowMouseMove);
  if (_graphWindowMouseUp) window.removeEventListener('mouseup', _graphWindowMouseUp);

  _graphWindowMouseMove = ev => {
    const { x, y } = canvasCoords(ev);
    if (isDragging && draggedNode) {
      dragDist += Math.abs(ev.movementX) + Math.abs(ev.movementY);
      draggedNode.x = (x - _graph.panX) / _graph.scale;
      draggedNode.y = (y - _graph.panY) / _graph.scale;
      draggedNode.vx = draggedNode.vy = 0;
      _graph.alpha = Math.max(_graph.alpha, 0.4);
      if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);
    } else if (isPanning) {
      _graph.panX = x - panStartX;
      _graph.panY = y - panStartY;
      if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);
    } else {
      _graph.hoveredNode = findNode(x, y);
      canvas.style.cursor = _graph.hoveredNode ? 'pointer' : 'grab';
      if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);
    }
  };

  _graphWindowMouseUp = () => {
    const clicked = pressedNode && dragDist < 5 ? pressedNode : null;
    if (draggedNode) { draggedNode.pinned = false; draggedNode = null; }
    if (clicked) {
      _graph.selectedNodeId = _graph.selectedNodeId === clicked.id ? null : clicked.id;
      renderCognitionInspector();
      _graph.alpha = Math.max(_graph.alpha, 0.08);
      if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);
    } else if (!pressedNode && dragDist < 5) {
      _graph.selectedNodeId = null;
  _graph.sectorMemory.clear();
  _graph.sectorLabels.clear();
  _graph.nextSectorId = 1;
      renderCognitionInspector();
    }
    pressedNode = null;
    isDragging = false; isPanning = false;
    canvas.style.cursor = 'grab';
  };

  window.addEventListener('mousemove', _graphWindowMouseMove);
  window.addEventListener('mouseup', _graphWindowMouseUp);
}

// ─────────────────────────────────────────────────────────────────────────────
// Regime Compass (adapted from observatory/render/regime-compass.js)
// ─────────────────────────────────────────────────────────────────────────────

function updateRegimeHud(analysis) {
  const { nearest, distancePct, insideReference } = analysis;
  const titleEl = document.getElementById('mind-compass-title');
  const subEl = document.getElementById('mind-compass-sub');
  const badgeEl = document.getElementById('mind-compass-badge');
  const novEl = document.getElementById('mind-compass-novelty');
  const novBar = document.getElementById('mind-compass-novelty-bar');
  const driftEl = document.getElementById('mind-compass-drift');
  const expEl = document.getElementById('mind-compass-exp');
  if (!titleEl) return;

  titleEl.textContent = nearest.name;
  subEl.textContent = `Observer reference zone · distance ${distancePct}%`;
  if (badgeEl) {
    badgeEl.textContent = 'OBSERVER MODEL';
    badgeEl.className = `mind-compass-badge ${insideReference ? 'familiar' : 'moderate'}`;
  }
  if (novEl) novEl.textContent = `${distancePct}%`;
  if (novBar) {
    novBar.style.width = `${Math.max(3, distancePct)}%`;
    novBar.style.background = insideReference ? PAL.mint : PAL.amber;
  }

  const velocity = Number.isFinite(_compass.velocity) ? _compass.velocity : 0;
  if (driftEl) driftEl.textContent = `${velocity.toFixed(3)} units/tick`;
  if (expEl) {
    expEl.textContent = `${nearest.description} This panel is an observer-side projection and is not part of the organism's learned self-model.`;
  }
}

function drawRegimeFrame(canvas) {
  const ctx = canvas.getContext('2d');
  const { width: W, height: H } = canvas;
  ctx.clearRect(0, 0, W, H);
  const cx = W / 2, cy = H / 2;
  ctx.save();
  ctx.translate(cx, cy);

  // Radar grid
  [70, 140, 220, 300].forEach((r, i) => {
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.strokeStyle = i === 3 ? 'rgba(80,217,255,0.15)' : 'rgba(80,217,255,0.06)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 6]);
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // Axes
  ctx.strokeStyle = 'rgba(100,160,210,0.18)';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-340, 0); ctx.lineTo(340, 0);
  ctx.moveTo(0, -260); ctx.lineTo(0, 260);
  ctx.stroke();

  // Axis labels
  ctx.font = '10px -apple-system, sans-serif';
  ctx.fillStyle = 'rgba(148,184,215,0.6)';
  ctx.textAlign = 'center';
  ctx.fillText('▲ PREDICTIVE TENSION (observer)', 0, -272);
  ctx.fillText('LOW TENSION ▼', 0, 277);
  ctx.textAlign = 'left';
  ctx.fillText('MEASURED ACTIVITY ►', 200, -8);
  ctx.textAlign = 'right';
  ctx.fillText('◄ LOW ACTIVITY', -200, -8);

  // Basins
  if (_compass.showContours) {
    for (const r of REGIMES) {
      const grad = ctx.createRadialGradient(r.x, r.y, 10, r.x, r.y, r.radius * 1.3);
      grad.addColorStop(0, `${r.color}22`);
      grad.addColorStop(0.5, `${r.color}0d`);
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(r.x, r.y, r.radius * 1.3, 0, Math.PI * 2); ctx.fill();
      [0.4, 0.75, 1.15].forEach((sc, i) => {
        ctx.beginPath(); ctx.arc(r.x, r.y, r.radius * sc, 0, Math.PI * 2);
        ctx.strokeStyle = `${r.color}${i === 1 ? '44' : '22'}`; ctx.lineWidth = 1;
        ctx.setLineDash(i === 2 ? [3, 4] : []); ctx.stroke(); ctx.setLineDash([]);
      });
      ctx.beginPath(); ctx.arc(r.x, r.y, 8, 0, Math.PI * 2);
      ctx.fillStyle = r.color; ctx.fill();
      ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
      ctx.font = 'bold 10px -apple-system, sans-serif';
      ctx.fillStyle = '#fff'; ctx.fillText(r.name, r.x, r.y + 18);
    }
  }

  // Trail
  const coord = computeObserverMapCoordinates({
    senses: _snap.senses,
    cognition: _snap.cognition,
    observerAnalysis: _snap.observerAnalysis,
  });
  const tick = finiteNumber(_tel.tick, 0);
  if (_compass.lastCoord) {
    const dt = Math.max(1, tick - finiteNumber(_compass.lastCoord.tick, tick - 1));
    _compass.velocity = Math.hypot(
      coord.x - finiteNumber(_compass.lastCoord.x, coord.x),
      coord.y - finiteNumber(_compass.lastCoord.y, coord.y),
    ) / dt;
  } else {
    _compass.velocity = 0;
  }
  if (!_compass.trail.length || _compass.trail[_compass.trail.length - 1].tick !== tick) {
    _compass.trail.push({ x: coord.x, y: coord.y, tick });
    if (_compass.trail.length > 30) _compass.trail.shift();
  }
  _compass.lastCoord = { ...coord, tick };

  const analysis = evaluateObserverRegime(coord, REGIMES);
  updateRegimeHud(analysis);

  if (_compass.showTrail && _compass.trail.length > 1) {
    for (let i = 1; i < _compass.trail.length; i++) {
      const p0 = _compass.trail[i - 1], p1 = _compass.trail[i];
      const alpha = (i / _compass.trail.length) * 0.85;
      ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y);
      ctx.strokeStyle = !analysis.insideReference ? `rgba(255,127,131,${alpha})` : `rgba(80,217,255,${alpha})`;
      ctx.lineWidth = 2; ctx.stroke();
    }
  }

  // Current state particle
  _compass.sonarPhase = (_compass.sonarPhase + 0.04) % 1;
  const { x: px, y: py } = coord;
  const pointColor = !analysis.insideReference ? PAL.coral : (analysis.distancePct > 35 ? PAL.amber : PAL.mint);
  if (!analysis.insideReference) {
    const wr = 16 + _compass.sonarPhase * 70;
    ctx.beginPath(); ctx.arc(px, py, wr, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(255,127,131,${(1 - _compass.sonarPhase) * 0.6})`; ctx.lineWidth = 1.8; ctx.stroke();
  }
  const haloR = 12 + Math.sin(_compass.sonarPhase * Math.PI * 2) * 3;
  ctx.beginPath(); ctx.arc(px, py, haloR, 0, Math.PI * 2);
  ctx.fillStyle = `${pointColor}33`; ctx.fill();
  ctx.beginPath(); ctx.arc(px, py, 6.5, 0, Math.PI * 2);
  ctx.fillStyle = pointColor; ctx.shadowColor = pointColor; ctx.shadowBlur = 10; ctx.fill();
  ctx.shadowBlur = 0; ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.8; ctx.stroke();
  ctx.font = 'bold 10px -apple-system, sans-serif'; ctx.fillStyle = '#fff'; ctx.textAlign = 'left';
  ctx.fillText('OBSERVER PROJECTION', px + 14, py - 6);

  ctx.restore();
}

function regimeAnimLoop() {
  if (_activeTab !== 'regime') { _regimRafId = null; return; }
  const canvas = document.getElementById('mind-regime-canvas');
  if (!canvas) { _regimRafId = null; return; }
  const wrap = canvas.parentElement;
  if (wrap) {
    const rect = wrap.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      if (canvas.width !== Math.floor(rect.width) || canvas.height !== Math.floor(rect.height)) {
        canvas.width = Math.floor(rect.width);
        canvas.height = Math.floor(rect.height);
      }
    }
  }
  drawRegimeFrame(canvas);
  _regimRafId = requestAnimationFrame(regimeAnimLoop);
}

function startRegimeCompass() {
  const canvas = document.getElementById('mind-regime-canvas');
  if (!canvas) return;
  const wrap = canvas.parentElement;
  if (wrap) {
    const rect = wrap.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      canvas.width = Math.floor(rect.width);
      canvas.height = Math.floor(rect.height);
    }
  }
  if (!_regimRafId) _regimRafId = requestAnimationFrame(regimeAnimLoop);

  // Compass control buttons
  const btnContour = document.getElementById('mind-contour-btn');
  const btnTrail   = document.getElementById('mind-trail-btn');
  const btnReset   = document.getElementById('mind-regime-reset');

  if (btnContour && !btnContour.dataset.bound) {
    btnContour.dataset.bound = 'true';
    btnContour.addEventListener('click', () => {
      _compass.showContours = !_compass.showContours;
      btnContour.classList.toggle('active', _compass.showContours);
    });
  }
  if (btnTrail && !btnTrail.dataset.bound) {
    btnTrail.dataset.bound = 'true';
    btnTrail.addEventListener('click', () => {
      _compass.showTrail = !_compass.showTrail;
      btnTrail.classList.toggle('active', _compass.showTrail);
      if (!_compass.showTrail) _compass.trail = [];
    });
  }
  if (btnReset && !btnReset.dataset.bound) {
    btnReset.dataset.bound = 'true';
    btnReset.addEventListener('click', () => {
      _compass.trail = [];
      _compass.showContours = true;
      _compass.showTrail = true;
      btnContour?.classList.add('active');
      btnTrail?.classList.add('active');
    });
  }

  // Mouse crosshair on canvas
  if (!canvas.dataset.mouseInstalled) {
    canvas.dataset.mouseInstalled = 'true';
    canvas.addEventListener('mousemove', ev => {
      const rect = canvas.getBoundingClientRect();
      _compass.mousePos = {
        x: (ev.clientX - rect.left) * (canvas.width / rect.width) - canvas.width / 2,
        y: (ev.clientY - rect.top)  * (canvas.height / rect.height) - canvas.height / 2,
      };
    });
    canvas.addEventListener('mouseleave', () => { _compass.mousePos = null; });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Snapshot ingestion (simplified projection from instance stream)
// ─────────────────────────────────────────────────────────────────────────────

function ingestSnapshot(raw) {
  // Accept a variety of snapshot shapes the observatory supports
  const snap = raw?.snapshot ?? raw;
  if (!snap) return false;

  _snap.senses           = snap.senses ?? snap.percepts ?? [];
  _snap.beliefs          = snap.beliefs ?? [];
  _snap.cognition        = snap.cognition ?? null;
  _snap.topology         = snap.topology ?? null;
  _snap.selfModel        = snap.self_model ?? snap.selfModel ?? null;
  _snap.bodySchema       = snap.body_schema ?? snap.bodySchema ?? null;
  _snap.sensoryPhenotype = snap.sensory_phenotype ?? snap.sensoryPhenotype ?? null;
  _snap.sensoryDevelopment = snap.sensory_development ?? snap.sensoryDevelopment ?? [];
  _snap.sensoryRelations   = snap.sensory_relations ?? snap.sensoryRelations ?? [];
  _snap.metabolism         = snap.metabolism ?? null;
  _snap.degradation        = snap.degradation ?? null;
  _snap.development        = snap.development ?? null;
  _snap.sampling           = snap.sampling ?? null;
  _snap.details            = snap.details ?? null;
  _snap.displayId          = snap.display_id ?? snap.displayId ?? null;
  _snap.instanceId         = snap.instance_id ?? snap.instanceId ?? null;
  _snap.organismState      = snap.organism_state ?? snap.organismState ?? null;
  _snap.observerAnalysis    = snap.observer_analysis ?? snap.observerAnalysis ?? null;
  _snap.observerSemantics   = snap.observer_semantics ?? snap.observerSemantics ?? null;
  _snap.provenance          = snap.provenance ?? null;
  _snap.sensorimotor         = snap.sensorimotor ?? null;
  _snap.outcome              = snap.outcome ?? null;
  return true;
}

function currentMotorOutputEdges(topology = _snap.topology) {
  return (topology?.edges ?? []).filter(edge =>
    String(edge.targetId ?? '').startsWith('readout_motor:') ||
    String(edge.targetId ?? '').startsWith('readout_primitive:')
  ).length;
}

function currentPhysiologyState() {
  return String(
    _snap.organismState?.state ??
    (_tel.alive === false ? 'dead' : 'active')
  ).toLowerCase();
}

function snapshotForHistory() {
  return {
    topology: _snap.topology ? JSON.parse(JSON.stringify(_snap.topology)) : null,
    cognition: _snap.cognition ? JSON.parse(JSON.stringify(_snap.cognition)) : null,
    observerAnalysis: _snap.observerAnalysis ? JSON.parse(JSON.stringify(_snap.observerAnalysis)) : null,
    observerSemantics: _snap.observerSemantics ? JSON.parse(JSON.stringify(_snap.observerSemantics)) : null,
  };
}

function registerMilestone(kind, label, tick, tone = 'info') {
  if (!Number.isFinite(tick) || tick <= 0) return;
  if (_milestones.some(item => item.kind === kind)) return;
  _milestones.push({ kind, label, tick, tone });
  _milestones.sort((a, b) => a.tick - b.tick);
}

function recordSelfPersistence(tick) {
  const schema = _snap.bodySchema ?? {};
  const parts = Array.isArray(schema.parts) ? schema.parts : [];
  const dependencies = Array.isArray(schema.dependencies) ? schema.dependencies : [];

  for (const region of parts.filter(part => part.kind === 'cognitive_region')) {
    const key = String(region.part_id ?? '');
    if (!key) continue;
    const state = _selfRegionHistory.get(key) ?? { firstTick: tick, lastTick: tick, observations: 0 };
    state.lastTick = tick;
    state.observations += 1;
    _selfRegionHistory.set(key, state);
  }

  const currentKeys = new Set();
  for (const dep of dependencies) {
    const key = `${dep.source_id}→${dep.target_id}:${dep.relation ?? 'related'}`;
    currentKeys.add(key);
    const state = _selfDependencyHistory.get(key) ?? {
      firstTick: tick,
      lastTick: tick,
      observations: 0,
      dep: { ...dep },
    };
    state.lastTick = tick;
    state.observations += 1;
    state.dep = { ...dep };
    _selfDependencyHistory.set(key, state);
  }

  for (const [key, state] of _selfDependencyHistory.entries()) {
    state.current = currentKeys.has(key);
    if (tick - state.lastTick > 512) _selfDependencyHistory.delete(key);
  }
}

function recordMindHistory() {
  const tick = finiteNumber(_tel.tick ?? _snap.tick, 0);
  if (tick <= 0) return;

  recordSelfPersistence(tick);
  const topology = _snap.topology ?? { nodes: [], edges: [] };
  const nodes = topology.nodes ?? [];
  const sensorimotor = _snap.sensorimotor ?? {};
  const outcome = _snap.outcome ?? {};
  const selfSchema = _snap.bodySchema ?? {};
  const point = {
    tick,
    concepts: nodes.filter(node => node.kind === 'concept').length,
    predictors: nodes.filter(node => node.kind === 'predictor').length,
    readouts: nodes.filter(node => node.kind === 'readout').length,
    motorEdges: finiteNumber(_tel.cognitiveMotorOutputEdges ?? currentMotorOutputEdges(topology), 0),
    edges: (topology.edges ?? []).length,
    schemaConfidence: finiteNumber(_tel.schemaConf, 0),
    predictionError: finiteNumber(_tel.predictionError, 0),
    motorOrigin: _tel.motorOrigin ?? 'none',
    energy: _tel.metabolicReserve,
    physiology: currentPhysiologyState(),
    resourceProgress: finiteNumber(_tel.resourceProgress ?? outcome.resource_progress, 0),
    sensorimotorPatterns: finiteNumber(_tel.sensorimotorPatterns ?? sensorimotor.known_patterns, 0),
    motorPrimitives: finiteNumber(_tel.motorPrimitives ?? sensorimotor.primitives, 0),
    cognitivePrimitives: finiteNumber(_tel.cognitiveMotorPrimitives ?? sensorimotor.cognitive_primitives, 0),
    repertoire: finiteNumber(
      _tel.motorRepertoireSize ?? (
        Array.isArray(sensorimotor.active_motor_repertoire)
          ? sensorimotor.active_motor_repertoire.length
          : 0
      ),
      0,
    ),
    selfRegions: (_snap.bodySchema?.parts ?? []).filter(part => part.kind === 'cognitive_region').length,
    selfDependencies: (_snap.bodySchema?.dependencies ?? []).length,
  };

  const last = _mindHistory[_mindHistory.length - 1];
  if (last?.tick === point.tick) return;
  _mindHistory.push(point);
  while (_mindHistory.length > 2048) _mindHistory.shift();

  if (!_historySnapshots.length || tick - _historySnapshots[_historySnapshots.length - 1].tick >= 64) {
    _historySnapshots.push({ tick, snapshot: snapshotForHistory() });
    while (_historySnapshots.length > 96) _historySnapshots.shift();
  }

  // Never backdate a "first" event from an already-developed organism.
  // We only name a first occurrence when this observer actually saw the
  // transition from absent to present.
  if (!last) {
    registerMilestone('observer-attached', 'Observer attached', tick, 'info');
  } else {
    if (last.concepts === 0 && point.concepts > 0) registerMilestone('first-concept', 'First observed concept birth', tick, 'violet');
    if (last.predictors === 0 && point.predictors > 0) registerMilestone('first-predictor', 'First observed predictor birth', tick, 'amber');
    if (last.motorPrimitives === 0 && point.motorPrimitives > 0) registerMilestone('first-primitive', 'Motor primitives became available', tick, 'cyan');
    if (last.repertoire === 0 && point.repertoire > 0) registerMilestone('first-repertoire', 'Motor repertoire became available', tick, 'mint');
    if (last.motorEdges === 0 && point.motorEdges > 0) registerMilestone('first-motor-edge', 'First observed cognition → motor edge', tick, 'mint');

    const lastCognitiveUse = ['cognition','mixed'].includes(last.motorOrigin) || String(last.motorOrigin).includes('primitive');
    const cognitiveUse = ['cognition','mixed'].includes(point.motorOrigin) || String(point.motorOrigin).includes('primitive');
    if (!lastCognitiveUse && cognitiveUse) {
      registerMilestone('first-cognitive-motor-use', 'First observed cognitive motor use', tick, 'mint');
    }

    if (last.physiology !== point.physiology) {
      if (point.physiology === 'stressed') registerMilestone('stressed', 'Physiology → stressed', tick, 'coral');
      if (point.physiology === 'dormant') registerMilestone('dormant', 'Physiology → dormant', tick, 'amber');
      if (point.physiology === 'dead') registerMilestone('death', 'Death', tick, 'coral');
    }
  }
}

function nearestHistorySnapshot(tick) {
  let best = null;
  let distance = Infinity;
  for (const item of _historySnapshots) {
    const d = Math.abs(item.tick - tick);
    if (d < distance) {
      best = item;
      distance = d;
    }
  }
  return best;
}

function openHistoryTick(tick) {
  _historySelectionTick = tick;
  const historical = nearestHistorySnapshot(tick);
  if (historical?.snapshot?.topology) {
    _graph.replaySnapshot = historical.snapshot;
    _graph.replayTick = historical.tick;
    _graph.cachedPositions.clear();
    switchTab('cognition');
  } else {
    renderHistory();
  }
}

function topologyComponentStats(topology = _snap.topology) {
  const nodes = topology?.nodes ?? [];
  const adjacency = new Map(nodes.map(node => [node.id, new Set()]));
  for (const edge of topology?.edges ?? []) {
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
  }
  const unseen = new Set(nodes.map(node => node.id));
  const sizes = [];
  while (unseen.size) {
    const seed = unseen.values().next().value;
    unseen.delete(seed);
    const stack = [seed];
    let size = 0;
    while (stack.length) {
      const id = stack.pop();
      size += 1;
      for (const neighbor of adjacency.get(id) ?? []) {
        if (unseen.delete(neighbor)) stack.push(neighbor);
      }
    }
    sizes.push(size);
  }
  sizes.sort((a,b)=>b-a);
  return {
    count: sizes.length,
    main: sizes[0] ?? 0,
    isolates: sizes.filter(size=>size===1).length,
    secondary: sizes.filter(size=>size>1).slice(1).length,
    sizes,
  };
}

function currentRenderedTopology() {
  return {
    nodes: _graph.nodes.map(node => ({ id: node.id, kind: node.kind })),
    edges: _graph.edges.map(edge => ({
      sourceId: edge.source.id,
      targetId: edge.target.id,
      kind: edge.kind,
      support: edge.support,
      weight: edge.weight,
      plasticity: edge.plasticity,
      ageTicks: edge.ageTicks,
      stableTicks: edge.stableTicks,
      lastUseTick: edge.lastUseTick,
      correlation: edge.correlation,
      samples: edge.samples,
      learnedLayer: edge.learnedLayer,
    })),
  };
}

function cognitionNodeFacts(nodeId) {
  const topology = currentRenderedTopology();
  const edges = topology.edges ?? [];
  const inbound = edges.filter(edge => edge.targetId === nodeId);
  const outbound = edges.filter(edge => edge.sourceId === nodeId);
  const localIds = graphSubgraphIds(topology, nodeId, _graph.pathDepth) ?? new Set([nodeId]);
  const reachesMotor = [...localIds].some(id =>
    String(id).startsWith('readout_motor:') ||
    String(id).startsWith('readout_primitive:') ||
    String(id).startsWith('motor_primitive:') ||
    String(id).startsWith('actuator.')
  );
  return { inbound, outbound, localIds, reachesMotor };
}

function inspectorMetric(parent, label, value, color = null) {
  const row = el('div', '');
  row.style.cssText = 'display:grid;grid-template-columns:1fr auto;gap:8px;padding:5px 0;border-bottom:1px solid rgba(98,120,136,.12);font-size:9px;';
  const key = el('span', '');
  key.style.color = 'var(--muted)';
  key.textContent = label;
  const val = el('strong', '');
  val.style.cssText = 'font-size:9px;text-align:right;overflow-wrap:anywhere;';
  if (color) val.style.color = color;
  val.textContent = String(value);
  row.append(key, val);
  parent.appendChild(row);
}

function renderCognitionInspector() {
  const panel = document.getElementById('mind-cognition-inspector-body');
  if (!panel) return;
  panel.innerHTML = '';

  const selected = _graph.nodes.find(node => node.id === _graph.selectedNodeId) ?? null;
  if (selected) {
    const title = el('div', '');
    title.style.cssText = 'font-size:12px;font-weight:650;color:var(--text);overflow-wrap:anywhere;margin-bottom:3px;';
    title.textContent = selected.label ?? selected.id;
    const subtitle = el('div', '');
    subtitle.style.cssText = 'font-size:9px;color:var(--muted);margin-bottom:10px;';
    subtitle.textContent = `${selected.kind} · selected node`;
    panel.append(title, subtitle);

    const facts = cognitionNodeFacts(selected.id);
    const observerContext = observerContextForNode(
      _graph.replaySnapshot?.topology ?? _snap.topology,
      _graph.replaySnapshot?.observerSemantics ?? _snap.observerSemantics,
      selected.id,
      2,
    );
    const motorSemantic = selected.learnedLayer === 'motor' && selected.observerLabel
      ? {
          summary: selected.observerLabel,
          kind: selected.kind === 'actuator' ? 'exact-source' : 'composition',
          distance: 0,
        }
      : null;
    const displayedSemantic = motorSemantic ?? observerContext;
    inspectorMetric(panel, 'Self label', selected.id, PAL.violet);
    inspectorMetric(
      panel,
      displayedSemantic.kind === 'exact-source'
        ? 'Observer truth'
        : displayedSemantic.kind === 'composition'
          ? 'Observer composition'
          : 'Observer context',
      displayedSemantic.summary ?? 'unresolved',
      displayedSemantic.summary ? PAL.cyan : PAL.muted,
    );
    inspectorMetric(
      panel,
      'Semantic relation',
      displayedSemantic.kind === 'exact-source'
        ? 'exact source mapping'
        : displayedSemantic.kind === 'composition'
          ? 'physical composition only'
          : displayedSemantic.kind === 'sensory-context'
            ? `linked within ${displayedSemantic.distance} hops`
            : 'unresolved',
    );
    inspectorMetric(panel, 'Kind', selected.kind);
    if (selected.kind === 'motor_primitive') {
      inspectorMetric(panel, 'Cognitive reuse', selected.cognitivePrimitive ? 'eligible' : 'not yet');
      inspectorMetric(panel, 'Samples', selected.samples);
      inspectorMetric(panel, 'Controllability', selected.controllability.toFixed(4), PAL.mint);
      inspectorMetric(panel, 'Directional consistency', pct(selected.directionalConsistency));
      inspectorMetric(panel, 'Effect variance', selected.effectVariance.toFixed(4));
      inspectorMetric(panel, 'Actuators', selected.actuatorIds.length);
      inspectorMetric(panel, 'Replay', selected.replayActive ? 'active now' : 'inactive', selected.replayActive ? PAL.mint : PAL.muted);
    }
    if (selected.kind === 'actuator') {
      inspectorMetric(panel, 'Observer effector', selected.observerLabel ?? 'unresolved', PAL.cyan);
      inspectorMetric(panel, 'Motor repertoire', selected.activeRepertoire ? 'active' : 'not promoted');
      inspectorMetric(panel, 'Effect strength', selected.effectStrength.toFixed(3), PAL.mint);
      inspectorMetric(panel, 'Effect relations', selected.causalRelationCount);
      inspectorMetric(panel, 'Activations observed', selected.activations);
    }
    inspectorMetric(panel, 'Degree', selected.neighbors?.size ?? 0);
    inspectorMetric(panel, 'Activity', pct(selected.activationLevel ?? 0), PAL.cyan);
    inspectorMetric(panel, 'Structural importance', pct(selected.structuralImportance ?? selected.visualValue ?? 0));
    inspectorMetric(panel, 'Component', selected.isolated ? 'unintegrated' : `#${(selected.componentRank ?? 0) + 1} · ${selected.componentSize ?? 1} nodes`);
    inspectorMetric(panel, 'Sector', selected.community && selected.community !== 'isolated'
      ? (_graph.sectorLabels.get(selected.community) ?? 'unresolved')
      : 'none');
    inspectorMetric(panel, 'Inbound / outbound', `${facts.inbound.length} / ${facts.outbound.length}`);
    inspectorMetric(panel, `Within ${_graph.pathDepth} hops`, facts.localIds.size);
    inspectorMetric(
      panel,
      'Motor path nearby',
      facts.reachesMotor ? 'yes' : 'no',
      facts.reachesMotor ? PAL.mint : PAL.muted,
    );
    if (selected.errorCls) inspectorMetric(panel, 'Prediction error', selected.errorCls, PAL.coral);
    if (selected.readoutVal != null) inspectorMetric(panel, 'Readout', selected.readoutVal, PAL.mint);

    const relTitle = el('div', '');
    relTitle.style.cssText = 'margin:13px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
    relTitle.textContent = 'Direct relations';
    panel.appendChild(relTitle);

    const direct = [
      ...facts.inbound.map(edge => ({ dir: '←', other: edge.sourceId, edge })),
      ...facts.outbound.map(edge => ({ dir: '→', other: edge.targetId, edge })),
    ]
      .sort((a,b) => finiteNumber(b.edge.support,0) - finiteNumber(a.edge.support,0))
      .slice(0, 12);

    if (!direct.length) {
      const empty = el('div', '');
      empty.style.cssText = 'font-size:9px;color:var(--muted);';
      empty.textContent = 'No direct graph relations.';
      panel.appendChild(empty);
    } else {
      for (const relation of direct) {
        const row = el('button', '');
        row.type = 'button';
        row.style.cssText = `
          width:100%;display:block;text-align:left;padding:5px 6px;margin:3px 0;
          border:1px solid rgba(98,120,136,.16);border-radius:5px;
          background:rgba(80,217,255,.025);color:var(--muted);
          font-size:8px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
        `;
        row.textContent = `${relation.dir} ${shortId(relation.other, 9, 5)} · ${relation.edge.kind ?? 'edge'} · sup ${finiteNumber(relation.edge.support,0)}`;
        row.title =
          `${relation.other}\nkind ${relation.edge.kind ?? 'edge'} · weight ${finiteNumber(relation.edge.weight,0).toFixed(3)} · plasticity ${finiteNumber(relation.edge.plasticity,0).toFixed(3)}\nsupport ${finiteNumber(relation.edge.support,0)} · age ${finiteNumber(relation.edge.ageTicks,0)} · stable ${finiteNumber(relation.edge.stableTicks,0)} · last use t${finiteNumber(relation.edge.lastUseTick,0)}`;
        row.addEventListener('click', () => selectCognitiveNode(relation.other));
        panel.appendChild(row);
      }
    }

    const clear = el('button', 'mind-ctrl-btn');
    clear.type = 'button';
    clear.style.cssText = 'margin-top:12px;width:100%;';
    clear.textContent = 'Clear selection';
    clear.addEventListener('click', () => {
      _graph.selectedNodeId = null;
      renderCognitionInspector();
      _graph.alpha = Math.max(_graph.alpha, 0.08);
      if (!_rafId) _rafId = requestAnimationFrame(cognitionAnimLoop);
    });
    panel.appendChild(clear);
    return;
  }

  const title = el('div', '');
  title.style.cssText = 'font-size:12px;font-weight:650;color:var(--text);margin-bottom:3px;';
  title.textContent = 'Structural sectors';
  const subtitle = el('div', '');
  subtitle.style.cssText = 'font-size:9px;line-height:1.45;color:var(--muted);margin-bottom:10px;';
  subtitle.textContent =
    'Observer layout derived only from graph relations. Sectors are not concepts invented for the Symbiont.';
  panel.append(title, subtitle);

  const componentSizes = (_graph.components ?? []).map(component => component.length);
  if (componentSizes.length) {
    const objective = el('div','');
    objective.style.cssText='padding:8px 0 10px;border-top:1px solid rgba(98,120,136,.16);font-size:8px;line-height:1.45;color:var(--muted);';
    const isolates = componentSizes.filter(size => size === 1).length;
    objective.innerHTML =
      `<strong style="color:var(--text)">Connected components</strong><br>` +
      `${componentSizes.length} total · main ${componentSizes[0] ?? 0} nodes · ${isolates} isolates`;
    panel.appendChild(objective);
  }

  const sectors = [..._graph.communities.entries()]
    .map(([id, ids]) => {
      const sectorNodes = ids.map(nodeId => _graph.nodes.find(node => node.id === nodeId)).filter(Boolean);
      const kinds = {};
      for (const node of sectorNodes) kinds[node.kind] = (kinds[node.kind] ?? 0) + 1;
      const activity = sectorNodes.length
        ? sectorNodes.reduce((sum, node) => sum + finiteNumber(node.activationLevel, 0), 0) / sectorNodes.length
        : 0;
      return { id, ids, sectorNodes, kinds, activity };
    })
    .sort((a, b) => b.ids.length - a.ids.length);

  if (!sectors.length) {
    const empty = el('div', '');
    empty.style.cssText = 'font-size:9px;color:var(--muted);';
    empty.textContent = 'No multi-node sectors in the current view.';
    panel.appendChild(empty);
  }

  sectors.slice(0, 10).forEach((sector) => {
    const card = el('div', '');
    card.style.cssText = 'padding:8px 0;border-top:1px solid rgba(98,120,136,.16);';
    const head = el('div', '');
    head.style.cssText = 'display:flex;justify-content:space-between;gap:8px;font-size:9px;';
    const name = el('strong', '');
    name.textContent = _graph.sectorLabels.get(sector.id) ?? 'S-???';
    const count = el('span', '');
    count.style.color = 'var(--muted)';
    count.textContent = `${sector.ids.length} nodes`;
    head.append(name, count);
    const composition = el('div', '');
    composition.style.cssText = 'font-size:8px;color:var(--muted);margin-top:3px;line-height:1.35;';
    composition.textContent = Object.entries(sector.kinds)
      .sort((a,b) => b[1] - a[1])
      .map(([kind, n]) => `${n} ${kind}`)
      .join(' · ');
    const activity = el('div', '');
    activity.style.cssText = 'font-size:8px;color:var(--muted);margin-top:3px;';
    activity.textContent = `mean activity ${pct(sector.activity)}`;
    card.append(head, composition, activity);
    panel.appendChild(card);
  });

  const hint = el('div', '');
  hint.style.cssText = 'margin-top:12px;padding:8px;border:1px solid rgba(80,217,255,.14);border-radius:6px;font-size:8px;line-height:1.45;color:var(--muted);';
  hint.textContent = 'Click a node to inspect its real graph neighborhood and follow direct relations.';
  panel.appendChild(hint);
}

function updateCognitionSummary() {
  const panel = document.getElementById('mind-cognition-summary');
  if (!panel) return;
  const source = _graph.replaySnapshot ?? _snap;
  const topology = source.topology ?? { nodes: [], edges: [] };
  const learned = augmentLearnedGraph(
    topology,
    source.sensorimotor ?? _snap.sensorimotor,
    source.observerSemantics ?? _snap.observerSemantics,
    source.prospectiveAgency ?? null,
  );
  const nodes = learned.nodes;
  const topologyEdges = learned.edges;
  const current = {
    concepts: nodes.filter(node => node.kind === 'concept').length,
    predictors: nodes.filter(node => node.kind === 'predictor').length,
    edges: topologyEdges.length,
    motorEdges: topologyEdges.filter(edge =>
      String(edge.targetId ?? '').startsWith('readout_motor:') ||
      String(edge.targetId ?? '').startsWith('readout_primitive:')
    ).length,
    primitives: learned.counts.primitives,
    cognitivePrimitives: learned.counts.cognitivePrimitives,
    actuators: learned.counts.actuators,
    causalEffects: learned.counts.causalEffects,
    cognitiveMotorLinks: learned.counts.cognitiveMotorLinks,
  };
  const nowTick = finiteNumber(_tel.tick, 0);
  const baseline = [..._mindHistory].reverse().find(point => nowTick - point.tick >= 256)
    ?? _mindHistory[0]
    ?? { tick: nowTick, concepts: current.concepts, predictors: current.predictors, edges: current.edges };
  const sign = value => value > 0 ? `+${value}` : String(value);
  const components = topologyComponentStats({ nodes, edges: topologyEdges });
  const replayLabel = _graph.replayTick != null ? ` · replay t${_graph.replayTick}` : ' · LIVE';
  panel.innerHTML =
    `<strong style="color:var(--text)">Complete learned structure${replayLabel}</strong><br>` +
    `${current.concepts} concepts · ${current.predictors} predictors · ${current.primitives} motor primitives (${current.cognitivePrimitives} reusable) · ${current.actuators} learned actuators<br>` +
    `<span style="color:var(--muted)">${current.edges} visible learned relations · ${current.causalEffects} actuator→percept causal effects · ${current.cognitiveMotorLinks} readout→motor links</span><br>` +
    `<span style="color:var(--muted)">components ${components.count} · main ${components.main} · secondary ${components.secondary} · unintegrated ${components.isolates}</span><br>` +
    `<span style="color:var(--muted)">Δ since t${baseline.tick}: ${sign(current.concepts-baseline.concepts)} C · ${sign(current.predictors-baseline.predictors)} P · view ${_graph.viewMode}</span><br>` +
    `<span style="color:${current.cognitiveMotorLinks > 0 ? 'var(--mint)' : 'var(--muted)'}">${current.cognitiveMotorLinks > 0 ? 'cognition→motor linkage present' : 'motor learning exists outside cognitive control'} · motor origin ${_tel.motorOrigin ?? '—'}</span>`;
}

function refreshSnapshotViews() {
  setWaiting(false, null);
  recordMindHistory();
  updateTelemetryStrip();
  if (_activeTab === 'overview') renderOverview();
  if (_activeTab === 'phenotype') {
    renderPhenotype();
    renderIdentityGap();
    renderSelf();
  }
  if (_activeTab === 'sensory') {
    renderSensesPanel();
    renderSensoryMap();
  }
  if (_activeTab === 'cognition') {
    updateCognitionSummary();
    initGraphPhysics(
      document.getElementById('mind-cognition-canvas')?.width ?? 900,
      document.getElementById('mind-cognition-canvas')?.height ?? 600,
    );
    renderCognitionInspector();
  }
  if (_activeTab === 'motor') renderMotorLearning();
  if (_activeTab === 'history') renderHistory();
}

// ─────────────────────────────────────────────────────────────────────────────
// SSE connections
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Connect to /api/organism for lightweight cognition + vitals telemetry.
 * This stream runs at all times while the view is mounted.
 */
function connectOrganismStream() {
  if (_organismSse) _organismSse.close();
  _organismSse = new EventSource('/api/organism');

  _organismSse.addEventListener('message', ev => {
    let data;
    try { data = JSON.parse(ev.data); } catch { return; }
    if (!data?.type) return;

    if (data.type === 'mind_snapshot' && data.source === 'physics3d' && data.snapshot) {
      _localMindActive = true;
      if (_instanceSse) {
        _instanceSse.close();
        _instanceSse = null;
      }
      _activeInstance = null;
      _activeRunId = null;
      if (ingestSnapshot(data.snapshot)) refreshSnapshotViews();
      return;
    }

    // A selected Observatory instance is authoritative only when no local
    // Physics3D rich snapshot is active.
    if (!_localMindActive && _activeInstance && data.instance_id !== _activeInstance) return;
    if (_activeRunId && data.run_id && data.run_id !== _activeRunId) return;
    if (!_activeInstance) setWaiting(false, null);

    if (data.type === 'body') {
      _tel.tick = data.tick ?? _tel.tick;
      _tel.metabolicReserve = data.metabolic_reserve ?? _tel.metabolicReserve;
      updateTelemetryStrip();
    }

        if (data.type === 'cognition') {
      _tel.tick             = data.tick ?? _tel.tick;
      _tel.schemaConf       = data.schema_confidence ?? _tel.schemaConf;
      _tel.schemaParts      = data.schema_parts ?? _tel.schemaParts;
      _tel.schemaSensory    = data.schema_sensory_parts ?? _tel.schemaSensory;
      _tel.schemaCognitive  = data.schema_cognitive_regions ?? _tel.schemaCognitive;
      _tel.motorOrigin      = data.motor_origin ?? _tel.motorOrigin;
      _tel.predictorCount   = data.predictor_count ?? _tel.predictorCount;
      _tel.sensorimotorPatterns = data.sensorimotor_patterns ?? _tel.sensorimotorPatterns;
      _tel.motorPrimitives = data.motor_primitives ?? _tel.motorPrimitives;
      _tel.cognitiveMotorPrimitives = data.cognitive_motor_primitives ?? _tel.cognitiveMotorPrimitives;
      _tel.motorRepertoireSize = data.motor_repertoire_size ?? _tel.motorRepertoireSize;
      _tel.recurrentPrimitiveCandidates = data.recurrent_primitive_candidates ?? _tel.recurrentPrimitiveCandidates;
      _tel.maxPrimitiveSamples = data.max_primitive_samples ?? _tel.maxPrimitiveSamples;
      _tel.fullCompetenceGateCandidates = data.full_competence_gate_candidates ?? _tel.fullCompetenceGateCandidates;
      _tel.motorReadoutNodes = data.motor_readout_nodes ?? _tel.motorReadoutNodes;
      _tel.primitiveReadoutNodes = data.primitive_readout_nodes ?? _tel.primitiveReadoutNodes;
      _tel.cognitiveMotorOutputEdges = data.cognitive_motor_output_edges ?? _tel.cognitiveMotorOutputEdges;
      _tel.cognitiveConcepts = data.cognitive_concepts ?? _tel.cognitiveConcepts;
      _tel.cognitiveReadouts = data.cognitive_readouts ?? _tel.cognitiveReadouts;
      _tel.predictionError  = data.prediction_error ?? _tel.predictionError;
      _tel.prospective      = data.prospective_selected ?? _tel.prospective;
      _tel.prospectiveEV    = data.prospective_expected_value ?? _tel.prospectiveEV;
      _tel.slmActive        = data.slm_active ?? _tel.slmActive;
      _tel.slmModels        = data.slm_models ?? _tel.slmModels;
      updateTelemetryStrip();
    }

    if (data.type === 'vitals') {
      _tel.tick             = data.tick ?? _tel.tick;
      _tel.alive            = data.alive ?? _tel.alive;
      _tel.jointMotion      = data.joint_motion ?? _tel.jointMotion;
      _tel.activeEffectors  = data.active_effectors ?? _tel.activeEffectors;
      _tel.resourceDistance = data.resource_distance ?? _tel.resourceDistance;
      _tel.resourceProgress = data.resource_progress ?? _tel.resourceProgress;
      _tel.resourceRemaining= data.resource_remaining ?? _tel.resourceRemaining;
      _tel.absorbedEnergy   = data.absorbed_energy ?? _tel.absorbedEnergy;
      _tel.displacement     = data.displacement_from_origin ?? _tel.displacement;
      _tel.mechanicalWork   = data.mechanical_work_joules ?? _tel.mechanicalWork;
      _tel.metabolicCost    = data.metabolic_work_cost ?? _tel.metabolicCost;
      updateTelemetryStrip();
    }
  });

  _organismSse.onerror = () => {
    setWaiting(true, 'SSE /api/organism disconnected — retrying…');
  };
}

/**
 * Connect to /fleet SSE to discover resident instances.
 * Auto-selects the first alive instance unless already connected.
 */
function connectFleetStream() {
  if (_fleetSse) _fleetSse.close();
  try {
    _fleetSse = new EventSource('/fleet');
  } catch (error) {
    setWaiting(true, 'Observatory fleet is unavailable — showing local organism telemetry only.');
    return;
  }

  _fleetSse.onmessage = ev => {
    let payload;
    try { payload = JSON.parse(ev.data); } catch { return; }
    const instances = Array.isArray(payload.instances) ? payload.instances : [];
    const alive = instances.filter(i => i.liveness === 'alive');

    if (_localMindActive) return;

    const current = _activeInstance
      ? alive.find((item) => item.instance_id === _activeInstance)
      : null;

    if (current) {
      const nextRunId = current.run_id ?? null;
      if (nextRunId !== _activeRunId) {
        connectInstanceStream(current.instance_id, nextRunId);
      }
      return;
    }

    if (_activeInstance && _instanceSse) {
      _instanceSse.close();
      _instanceSse = null;
    }
    _activeInstance = null;
    _activeRunId = null;

    if (alive.length > 0) {
      connectInstanceStream(alive[0].instance_id, alive[0].run_id ?? null);
    } else {
      setWaiting(true, 'Waiting for a live Observatory instance…');
    }
  };
  _fleetSse.onerror = () => {
    setWaiting(true, 'Observatory fleet unavailable — fallback to the organism stream is active.');
    if (_fleetSse) {
      try { _fleetSse.close(); } catch (err) {}
      _fleetSse = null;
    }
  };
}

/**
 * Connect to /instance/:id/stream for full snapshots (topology, beliefs, etc.).
 */
function connectInstanceStream(instanceId, runId = null) {
  if (_activeInstance === instanceId && _activeRunId === runId && _instanceSse) return;
  if (_instanceSse) _instanceSse.close();
  _activeInstance = instanceId;
  _activeRunId = runId;

  _instanceSse = new EventSource(`/instances/${instanceId}`);

  _instanceSse.onmessage = ev => {
    let payload;
    try { payload = JSON.parse(ev.data); } catch { return; }

    if (payload.run_id && _activeRunId && payload.run_id !== _activeRunId) return;
    if (payload.run_id && !_activeRunId) _activeRunId = payload.run_id;

    if (payload.snapshot) {
      const ok = ingestSnapshot(payload.snapshot);
      if (ok) refreshSnapshotViews();
    }

    if (payload.topology) {
      _snap.topology = payload.topology;
      if (_activeTab === 'cognition') {
        initGraphPhysics(
          document.getElementById('mind-cognition-canvas')?.width ?? 900,
          document.getElementById('mind-cognition-canvas')?.height ?? 600,
        );
      }
    }
  };

  _instanceSse.onerror = () => {
    setWaiting(true, `Connection to instance ${instanceId} lost — retrying…`);
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mount the Mind view into `root`.
 *
 * @param {HTMLElement} root
 */
export function mount(root) {
  if (!(root instanceof HTMLElement)) {
    throw new TypeError('Mind view requires a valid HTMLElement root');
  }

  // Guard: unmount any previous instance.
  if (_root) unmount();

  _root = root;
  _rootStyleBeforeMount = root.style.cssText;
  _uid = Math.random().toString(36).slice(2, 9);
  _lastUITime = 0;
  _activeTab = 'overview';

  // Reset telemetry + snapshot state
  for (const k of Object.keys(_tel)) _tel[k] = null;
  for (const k of Object.keys(_snap)) _snap[k] = Array.isArray(_snap[k]) ? [] : null;
  _snap.senses = []; _snap.beliefs = []; _snap.sensoryDevelopment = [];
  _snap.sensoryRelations = [];
  _compass.trail = []; _compass.sonarPhase = 0; _compass.lastCoord = null; _compass.velocity = 0;
  _identityHistory.length = 0;
  _mindHistory.length = 0;
  _selfRegionHistory.clear();
  _selfDependencyHistory.clear();
  _graph.cachedPositions.clear(); _graph.alpha = 1; _graph.scale = 1; _graph.panX = 0; _graph.panY = 0;
  _graph.selectedNodeId = null;

  // Build DOM
  buildLayout(root);

  // Show waiting overlay initially
  setWaiting(true, 'Connecting to organism streams…');

  renderOverview();
  updateTelemetryStrip(true);

  // Apply initial tab style
  switchTab('overview');

  // SSE connections
  connectOrganismStream();
  connectFleetStream();

  // ResizeObserver to keep canvases properly sized
  _resizeObs = new ResizeObserver(() => {
    if (_activeTab === 'cognition') {
      const c = document.getElementById('mind-cognition-canvas');
      if (c?.parentElement) {
        const r = c.parentElement.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) { c.width = Math.floor(r.width); c.height = Math.floor(r.height); }
      }
    }
    if (_activeTab === 'regime') {
      const c = document.getElementById('mind-regime-canvas');
      if (c?.parentElement) {
        const r = c.parentElement.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) { c.width = Math.floor(r.width); c.height = Math.floor(r.height); }
      }
    }
    if (_activeTab === 'phenotype') {
      renderPhenotype();
      renderIdentityGap();
      renderSelf();
    }
  });
  _resizeObs.observe(root);
}

/**
 * Unmount the Mind view: stop animations, close SSE streams, clear DOM.
 */
export function unmount() {
  // Stop animations
  if (_rafId !== null) { cancelAnimationFrame(_rafId); _rafId = null; }
  if (_regimRafId !== null) { cancelAnimationFrame(_regimRafId); _regimRafId = null; }
  _graph.isRunning = false;

  // Close SSE connections
  if (_organismSse) { _organismSse.close(); _organismSse = null; }
  if (_fleetSse)    { _fleetSse.close();    _fleetSse    = null; }
  if (_instanceSse) { _instanceSse.close(); _instanceSse = null; }

  // Stop resize observer
  if (_resizeObs) { _resizeObs.disconnect(); _resizeObs = null; }

  // Remove listeners attached to window by the cognition graph.
  if (_graphWindowMouseMove) {
    window.removeEventListener('mousemove', _graphWindowMouseMove);
    _graphWindowMouseMove = null;
  }
  if (_graphWindowMouseUp) {
    window.removeEventListener('mouseup', _graphWindowMouseUp);
    _graphWindowMouseUp = null;
  }

  // Release volatile graph state.
  _graph.nodes = [];
  _graph.edges = [];
  _graph.hoveredNode = null;
  _graph.selectedNodeId = null;
  _graph.cachedPositions.clear();

  // Clear DOM and restore styles owned by the host before mounting.
  if (_root) {
    while (_root.firstChild) _root.removeChild(_root.firstChild);
    _root.style.cssText = _rootStyleBeforeMount;
    _root = null;
  }

  _rootStyleBeforeMount = '';
  _activeInstance = null;
  _activeRunId = null;
  _localMindActive = false;
}
