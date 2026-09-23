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

import { PAL } from './mind/config.js';
import { pct } from './mind/util.js';
import { buildMindLayout } from './mind/layout.js';
import { MindStreams } from './mind/streams.js';
import { applyTelemetryEvent } from './mind/telemetry.js';
import { applyMindSnapshot } from './mind/snapshot.js';
import { renderMotorLearning } from './mind/motor-learning.js';
import { renderOverview as renderOverviewPanel } from './mind/overview.js';
import { nearestHistorySnapshot, recordMindHistory, renderHistory as renderHistoryPanel } from './mind/history.js';
import { createIdentitySensoryRenderer } from './mind/identity-sensory.js';
import { createCognitionController } from './mind/cognition-controller.js';
import { currentPhysiologyState } from './mind/derived.js';
import {
  graph as _graph,
  resetMindDataState,
  snap as _snap,
  tel as _tel,
} from './mind/state.js';

// ─────────────────────────────────────────────────────────────────────────────
// Module-level state (single active view by public API contract)
// ─────────────────────────────────────────────────────────────────────────────

let _root           = null;
let _streams        = null;
let _resizeObs      = null;   // ResizeObserver on canvas wrappers
let _activeTab      = 'overview';

// Lifecycle / UI state merged from the instance-oriented refactor.
let _uid                    = 'default';
let _rootStyleBeforeMount   = '';
let _lastUITime             = 0;
const UI_THROTTLE_MS        = 66; // ~15 FPS for text-only telemetry updates

const cognition = createCognitionController({
  getActiveTab: () => _activeTab,
  onSwitchTab: (tabId) => switchTab(tabId),
});

const {
  renderIdentityGap,
  renderPhenotype,
  renderSelf,
  renderSensesPanel,
  renderSensoryMap,
} = createIdentitySensoryRenderer({
  getUid: () => _uid,
  onSelectCognitiveNode: (nodeId) => cognition.selectNode(nodeId),
});

// ─────────────────────────────────────────────────────────────────────────────
// Layout HTML
// ─────────────────────────────────────────────────────────────────────────────

/** Build the complete DOM structure for the Mind view and inject it into root. */
function renderOverview() {
  renderOverviewPanel({ onOpenHistoryTick: openHistoryTick });
}

function renderHistory() {
  renderHistoryPanel({ onOpenHistoryTick: openHistoryTick });
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab switching
// ─────────────────────────────────────────────────────────────────────────────

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
    cognition.start();
    cognition.renderInspector();
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

function openHistoryTick(tick) {
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
    cognition.updateSummary();
    cognition.init(
      document.getElementById('mind-cognition-canvas')?.width ?? 900,
      document.getElementById('mind-cognition-canvas')?.height ?? 600,
    );
    cognition.renderInspector();
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
function ingestTelemetryEvent(data) {
  if (applyTelemetryEvent(data)) updateTelemetryStrip();
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

  // Reset passive view state without changing organism state.
  resetMindDataState();

  // Build DOM. Layout owns structure only; all stateful actions are delegated.
  buildMindLayout(root, {
    activeTab: _activeTab,
    graphDimension: _graph.dimension,
    graphViewMode: _graph.viewMode,
    onTabChange: switchTab,
    onDimensionChange: (dimension) => cognition.setDimension(dimension),
    onViewModeChange: (mode) => cognition.setViewMode(mode),
    onReturnLive: () => cognition.returnLive(),
  });

  // Show waiting overlay initially
  setWaiting(true, 'Connecting to organism streams…');

  renderOverview();
  updateTelemetryStrip(true);

  // Apply initial tab style
  switchTab('overview');

  // SSE transport is isolated from rendering/state interpretation.
  _streams = new MindStreams({
    onTelemetry: ingestTelemetryEvent,
    onSnapshot: (snapshot) => {
      if (applyMindSnapshot(snapshot)) refreshSnapshotViews();
    },
    onTopology: (topology) => {
      _snap.topology = topology;
      if (_activeTab === 'cognition') {
        cognition.init(
          document.getElementById('mind-cognition-canvas')?.width ?? 900,
          document.getElementById('mind-cognition-canvas')?.height ?? 600,
        );
      }
    },
    onWaiting: setWaiting,
  });
  _streams.connect();

  // ResizeObserver to keep canvases properly sized
  _resizeObs = new ResizeObserver(() => {
    if (_activeTab === 'cognition') cognition.resize();
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
  cognition.stop();

  // Close transport coordinator.
  if (_streams) {
    _streams.close();
    _streams = null;
  }

  // Stop resize observer
  if (_resizeObs) { _resizeObs.disconnect(); _resizeObs = null; }

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
}
