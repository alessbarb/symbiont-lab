/**
 * mind.js — Cognitive ("Mind") view for Symbiont Lab.
 *
 * ES module.  Public API:
 *   mount(root: HTMLElement)  → void
 *   unmount()                 → void
 *
 * Displays one live symbiont organism across five sub-tabs:
 *   Phenotype · Sensory Map · Cognition Graph · Self · Regime Compass
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

// Regime basins (copied from observatory regime-compass.js for self-contained rendering)
const REGIMES = [
  { id: 'quiescence',       name: 'Quiescencia',        icon: '🌙', x: -160, y:  130, color: PAL.cyan,   radius: 95,  description: 'Minimal basal load — stable, predictable signals.' },
  { id: 'sustained_compute',name: 'Carga Sostenida',    icon: '⚙️', x:  170, y:  110, color: PAL.mint,   radius: 100, description: 'Intensive but well-anticipated cognitive activity.' },
  { id: 'burst_io',         name: 'Ráfagas E/S',        icon: '⚡', x:  -40, y:  -50, color: PAL.amber,  radius: 90,  description: 'Rapid context-switching and transient I/O bursts.' },
  { id: 'desync_stress',    name: 'Desincronización',   icon: '🚨', x:  180, y: -170, color: PAL.coral,  radius: 95,  description: 'High prediction error and elevated environmental dissent.' },
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
let _rafId          = null;   // cognition-graph animation frame
let _regimRafId     = null;   // regime-compass animation frame
let _resizeObs      = null;   // ResizeObserver on canvas wrappers
let _activeTab      = 'phenotype';

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
};

// Snapshot-derived state (updated by /instance/:id/stream)
const _snap = {
  senses:           [],
  beliefs:          [],
  sensoryDevelopment: [],
  sensoryRelations: [],
  cognition:        null,
  topology:         null,
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
    { id: 'phenotype',  label: 'Phenotype' },
    { id: 'sensory',    label: 'Sensory Map' },
    { id: 'cognition',  label: 'Cognition' },
    { id: 'self',       label: 'Self' },
    { id: 'regime',     label: 'Regime' },
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

  // Main canvas area
  const canvasArea = el('div', 'mind-canvas-area');
  canvasArea.style.cssText = 'position: relative; overflow: hidden; min-height: 0;';

  // Phenotype SVG
  const phenotypeSvg = svgEl('svg', {
    id: 'mind-phenotype-svg',
    viewBox: '0 0 900 720',
    role: 'img',
    'aria-label': 'Live Phenotype of the Symbiont organism',
  });
  phenotypeSvg.style.cssText = 'width: 100%; height: 100%; display: block;';

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
  const cognitionControls = el('div', '');
  cognitionControls.style.cssText = `
    position: absolute; bottom: 14px; right: 14px;
    display: flex; gap: 6px;
  `;
  const btnFmri  = makeControlBtn('⚡', 'Toggle fMRI', true);  btnFmri.id = 'mind-fmri-btn';
  const btnZoomIn= makeControlBtn('+', 'Zoom in', false);       btnZoomIn.id = 'mind-zoom-in';
  const btnZoomOut=makeControlBtn('−', 'Zoom out', false);      btnZoomOut.id = 'mind-zoom-out';
  const btnReset = makeControlBtn('⟲', 'Reset', false);         btnReset.id = 'mind-graph-reset';
  cognitionControls.append(btnFmri, btnZoomIn, btnZoomOut, btnReset);
  cognitionWrap.appendChild(cognitionCanvas);
  cognitionWrap.appendChild(cognitionControls);

  // Self panel
  const selfPanel = el('div', 'mind-self-panel hidden');
  selfPanel.id = 'mind-self-panel';
  selfPanel.style.cssText = `
    position: absolute; inset: 0; overflow-y: auto;
    padding: 24px 28px 60px;
    background: var(--bg-deep, ${PAL.bg});
  `;

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
  canvasArea.append(phenotypeSvg, sensoryWrap, cognitionWrap, selfPanel, regimeWrap, waitingOverlay);
  workspace.append(sensesPanel, canvasArea);
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
    { id: 'mind-t-alive',    label: 'Status',      init: '—' },
    { id: 'mind-t-schema',   label: 'Schema conf', init: '—' },
    { id: 'mind-t-preds',    label: 'Predictors',  init: '—' },
    { id: 'mind-t-motor',    label: 'Motor',       init: '—' },
    { id: 'mind-t-error',    label: 'Pred. error', init: '—' },
    { id: 'mind-t-resource', label: 'Resource',    init: '—' },
    { id: 'mind-t-instance', label: 'Instance',    init: '—' },
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
        <span>Novelty</span><strong id="mind-compass-novelty">—</strong>
      </div>
      <div class="mind-compass-meter">
        <div class="mind-compass-meter-fill" id="mind-compass-novelty-bar" style="width:0%;background:${PAL.mint}"></div>
      </div>
    </div>
    <div class="mind-compass-metric" style="margin-top:8px">
      <div class="mind-compass-metric-head">
        <span>Drift</span><strong id="mind-compass-drift">0.0 px/tick</strong>
      </div>
    </div>
    <p class="mind-compass-exp" id="mind-compass-exp">Awaiting real-time data…</p>
  `;
  return hud;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab switching
// ─────────────────────────────────────────────────────────────────────────────

function switchTab(tabId) {
  _activeTab = tabId;

  // Update button states
  document.querySelectorAll('.mind-tab').forEach(btn => {
    const active = btn.dataset.tab === tabId;
    btn.setAttribute('aria-pressed', String(active));
    btn.style.color = active ? `var(--cyan, ${PAL.cyan})` : `var(--muted, ${PAL.muted})`;
    btn.style.borderBottomColor = active ? `var(--cyan, ${PAL.cyan})` : 'transparent';
  });

  // Show/hide panels
  const phenotypeSvg = document.querySelector('#mind-phenotype-svg');
  const sensoryWrap  = document.querySelector('#mind-sensory-wrap');
  const cognitionWrap= document.querySelector('#mind-cognition-wrap');
  const selfPanel    = document.querySelector('#mind-self-panel');
  const regimeWrap   = document.querySelector('#mind-regime-wrap');

  if (phenotypeSvg) phenotypeSvg.classList.toggle('hidden', tabId !== 'phenotype');
  if (sensoryWrap)  sensoryWrap.classList.toggle('hidden',  tabId !== 'sensory');
  if (cognitionWrap)cognitionWrap.classList.toggle('hidden', tabId !== 'cognition');
  if (selfPanel)    selfPanel.classList.toggle('hidden',    tabId !== 'self');
  if (regimeWrap)   regimeWrap.classList.toggle('hidden',   tabId !== 'regime');

  // Tab-specific render / animation triggers
  if (tabId === 'phenotype') renderPhenotype();
  if (tabId === 'sensory')   renderSensoryMap();
  if (tabId === 'cognition') startCognitionGraph();
  if (tabId === 'self')      renderSelf();
  if (tabId === 'regime')    startRegimeCompass();
}

// ─────────────────────────────────────────────────────────────────────────────
// Telemetry strip update
// ─────────────────────────────────────────────────────────────────────────────

function updateTelemetryStrip(force = false) {
  const now = performance.now();
  if (!force && now - _lastUITime < UI_THROTTLE_MS) return;

  setTelem('mind-t-tick',     _tel.tick != null ? `t${_tel.tick}` : '—');
  setTelem('mind-t-alive',    _tel.alive === true ? '● Alive' : (_tel.alive === false ? '○ Dead' : '—'),
    _tel.alive === true ? PAL.mint : (_tel.alive === false ? PAL.coral : null));
  setTelem('mind-t-schema',   _tel.schemaConf != null ? `${(_tel.schemaConf * 100).toFixed(0)}%` : '—');
  setTelem('mind-t-preds',    _tel.predictorCount != null ? String(_tel.predictorCount) : '—');
  setTelem('mind-t-motor',    _tel.motorOrigin ?? '—');
  setTelem('mind-t-error',    _tel.predictionError != null ? _tel.predictionError.toFixed(4) : '—');
  setTelem('mind-t-resource', _tel.resourceProgress != null ? `${(_tel.resourceProgress * 100).toFixed(0)}%` : '—');
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

function renderSensesPanel() {
  const list = document.getElementById('mind-senses-list');
  if (!list) return;
  list.innerHTML = '';

  if (!_snap.senses.length) {
    const empty = el('p', '');
    empty.style.cssText = 'padding: 12px; font-size: 11px; color: var(--muted);';
    empty.textContent = 'No sensory data yet.';
    list.appendChild(empty);
    return;
  }

  for (const sense of _snap.senses) {
    const dev = (_snap.sensoryDevelopment ?? []).find(d => d.name === sense.id || d.name === sense.name);
    const row = el('div', sense.active ? 'mind-sense-row active' : 'mind-sense-row');
    if (!sense.active) row.style.opacity = '0.72';

    const icon = el('span', 'mind-sense-icon');
    icon.textContent = sense.icon ?? '●';

    const copy = el('div', 'mind-sense-copy');
    const name = document.createElement('strong');
    name.textContent = sense.name ?? sense.id;
    const status = document.createElement('small');

    let utilPct = 0;
    let barColor = PAL.muted;
    if (dev) {
      const tier = dev.tier ?? 'dormant';
      utilPct = Math.min(100, Math.max(2, (dev.utility ?? 0) * 2500));
      barColor = tier === 'active' ? PAL.cyan : tier === 'probing' ? PAL.amber : PAL.muted;
      status.textContent = `${tier.toUpperCase()} · util ${(dev.utility ?? 0).toFixed(3)}`;
    } else {
      utilPct = sense.active ? 25 : 0;
      barColor = sense.active ? PAL.cyan : PAL.muted;
      status.textContent = sense.active ? 'ACTIVE' : 'DORMANT';
    }

    const barWrap = el('div', 'mind-sense-bar');
    const barFill = el('div', 'mind-sense-fill');
    barFill.style.width = `${utilPct}%`;
    barFill.style.background = barColor;
    barWrap.appendChild(barFill);

    copy.append(name, status, barWrap);
    row.append(icon, copy);
    list.appendChild(row);
  }
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

    // Label
    const label = svgEl('text', { x: x + 12, y: y + 3, 'font-size': '10', fill: sense.active ? PAL.text : PAL.muted });
    label.textContent = (sense.name ?? sense.id).slice(0, 22);
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
    const errorCls = cognition?.predictionErrors?.[anchor.id];
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
  const actClass = cognition?.activationClasses?.[id] ?? 0;
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
  if (!mapSvg) return;
  mapSvg.innerHTML = '';

  const senses = _snap.senses ?? [];
  const devs   = _snap.sensoryDevelopment ?? [];
  const rels   = _snap.sensoryRelations ?? [];

  if (!senses.length) {
    const msg = svgEl('text', { x: '450', y: '300', 'text-anchor': 'middle', fill: PAL.muted, 'font-size': '14' });
    msg.textContent = 'No sensory data — awaiting snapshot…';
    mapSvg.appendChild(msg);
    return;
  }

  const W = 900, H = 600;
  const colW = 180;  // left column: world signals
  const midX = 450;  // receptor column
  const rightX = 720;// downstream / cognition column
  const cols = Math.max(1, senses.length);
  const step = Math.min(50, (H - 80) / cols);

  // Column headings
  for (const [x, label] of [[colW / 2, 'World Signals'], [midX, 'Receptors'], [rightX, 'Cognition']]) {
    const t = svgEl('text', { x, y: '30', 'text-anchor': 'middle', fill: PAL.muted, 'font-size': '10', 'font-weight': '600', 'text-transform': 'uppercase' });
    t.textContent = label;
    mapSvg.appendChild(t);
    mapSvg.appendChild(svgEl('line', { x1: x - 60, y1: '38', x2: x + 60, y2: '38', stroke: PAL.line, 'stroke-width': '1' }));
  }

  senses.forEach((sense, i) => {
    const y = 60 + i * step;
    const dev = devs.find(d => d.name === sense.id || d.name === sense.name);
    const isActive = sense.active;
    const tier = dev?.tier ?? (isActive ? 'active' : 'dormant');
    const utility = dev?.utility ?? (isActive ? 0.25 : 0.02);

    const signalColor = isActive ? PAL.cyan : PAL.muted;
    const opacity = isActive ? '0.85' : '0.3';

    // World signal node (left)
    const wx = colW / 2;
    mapSvg.appendChild(svgEl('circle', { cx: wx, cy: y, r: '5', fill: signalColor, opacity }));
    const wLabel = svgEl('text', { x: wx + 10, y: y + 3, 'font-size': '10', fill: signalColor, opacity });
    wLabel.textContent = (sense.name ?? sense.id).slice(0, 20);
    mapSvg.appendChild(wLabel);

    // Connection to receptor
    mapSvg.appendChild(svgEl('path', {
      d: `M ${wx + 6} ${y} Q ${midX - 50} ${y} ${midX - 12} ${y}`,
      fill: 'none', stroke: signalColor, 'stroke-width': tier === 'active' ? '1.4' : '0.7',
      'stroke-dasharray': tier === 'dormant' ? '3 3' : 'none', opacity,
    }));

    // Receptor node (middle)
    const rColor = tier === 'active' ? PAL.cyan : tier === 'probing' ? PAL.amber : PAL.muted;
    const rR = 5 + Math.min(8, utility * 18);
    mapSvg.appendChild(svgEl('circle', { cx: midX, cy: y, r: rR.toFixed(1), fill: rColor, opacity }));
    // Utility arc
    const arcAngle = Math.PI * 2 * utility;
    const arcX = midX + rR * 1.8 * Math.cos(-Math.PI / 2 + arcAngle);
    const arcY = y + rR * 1.8 * Math.sin(-Math.PI / 2 + arcAngle);
    const largeArc = arcAngle > Math.PI ? 1 : 0;
    mapSvg.appendChild(svgEl('path', {
      d: `M ${midX} ${y - rR * 1.8} A ${rR * 1.8} ${rR * 1.8} 0 ${largeArc} 1 ${arcX.toFixed(1)} ${arcY.toFixed(1)}`,
      fill: 'none', stroke: PAL.mint, 'stroke-width': '1.5', opacity: String(0.35 + utility * 0.55),
    }));

    // Connection from receptor to cognition
    mapSvg.appendChild(svgEl('path', {
      d: `M ${midX + rR + 2} ${y} Q ${rightX - 50} ${y} ${rightX - 10} ${y}`,
      fill: 'none', stroke: rColor, 'stroke-width': '0.9', opacity,
    }));

    // Cognition badge (right)
    mapSvg.appendChild(svgEl('circle', { cx: rightX, cy: y, r: '6', fill: PAL.violet, opacity }));
    const cLabel = svgEl('text', { x: rightX + 10, y: y + 3, 'font-size': '9', fill: PAL.muted });
    cLabel.textContent = tier.toUpperCase();
    mapSvg.appendChild(cLabel);
  });

  // Sensory relations (dotted arcs between signals)
  rels.forEach(rel => {
    if ((rel.samples ?? 0) < 3) return;
    const sA = senses.findIndex(s => s.id === rel.senseA || s.name === rel.senseA);
    const sB = senses.findIndex(s => s.id === rel.senseB || s.name === rel.senseB);
    if (sA < 0 || sB < 0) return;
    const yA = 60 + sA * step;
    const yB = 60 + sB * step;
    const sync = rel.synchronous ?? 0;
    const stroke = sync >= 0 ? PAL.mint : PAL.coral;
    const midY = (yA + yB) / 2;
    const arcOffset = 30 * (0.5 + 0.5 * Math.abs(sync));
    mapSvg.appendChild(svgEl('path', {
      d: `M ${colW / 2} ${yA} Q ${colW / 2 - arcOffset} ${midY} ${colW / 2} ${yB}`,
      fill: 'none', stroke, 'stroke-width': '0.9', 'stroke-dasharray': sync < 0 ? '3 3' : 'none',
      opacity: String(0.25 + Math.abs(sync) * 0.55),
    }));
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Self view (adapted from observatory/render/self.js)
// ─────────────────────────────────────────────────────────────────────────────

function renderSelf() {
  const panel = document.getElementById('mind-self-panel');
  if (!panel) return;
  panel.innerHTML = '';

  const schema = _snap.bodySchema;
  if (!schema || !schema.parts?.length) {
    const h = el('h2', 'mind-self-heading');
    h.textContent = 'Body schema not yet developed';
    const p = el('p', 'mind-self-body');
    p.textContent = 'This organism does not yet export a self-model. Once available, this view will show only what the organism itself believes about its parts and their relationships — never reconstructed from external Observatory observations.';
    panel.append(h, p);
    return;
  }

  const parts = schema.parts ?? [];
  const sensoryParts   = parts.filter(p => p.kind === 'sense');
  const cognitiveRegions = parts.filter(p => p.kind === 'cognitive_region');
  const dependencies   = schema.dependencies ?? [];

  const h = el('h2', 'mind-self-heading');
  h.textContent = 'Self-known functional body';
  const body = el('p', 'mind-self-body');
  body.textContent = `The organism currently represents ${sensoryParts.length} sensory part${sensoryParts.length !== 1 ? 's' : ''} and ${cognitiveRegions.length} learned cognitive region${cognitiveRegions.length !== 1 ? 's' : ''} as belonging to itself.`;
  panel.append(h, body);

  // Sensory parts section
  if (sensoryParts.length) {
    const sec = el('div', 'mind-section-title');
    sec.textContent = `Sensory parts · ${sensoryParts.length}`;
    panel.appendChild(sec);
    const grid = el('div', 'mind-self-grid');
    sensoryParts.forEach((part, i) => grid.appendChild(buildSelfCard(`Sensory part ${i + 1}`, part)));
    panel.appendChild(grid);
  }

  // Cognitive regions section
  const regionLabels = new Map();
  if (cognitiveRegions.length) {
    const sec = el('div', 'mind-section-title');
    sec.textContent = `Cognitive regions · ${cognitiveRegions.length}`;
    panel.appendChild(sec);
    const grid = el('div', 'mind-self-grid');
    cognitiveRegions.forEach((region, i) => {
      const label = `Cognitive region ${i + 1}`;
      regionLabels.set(region.id, label);
      grid.appendChild(buildSelfCard(label, region));
    });
    panel.appendChild(grid);
  }

  // Dependencies section
  if (dependencies.length) {
    const sec = el('div', 'mind-section-title');
    sec.textContent = `Functional dependencies · ${dependencies.length}`;
    panel.appendChild(sec);
    for (const dep of dependencies) {
      const src = regionLabels.get(dep.sourceId) ?? 'Unknown';
      const tgt = regionLabels.get(dep.targetId) ?? 'Unknown';
      const rel = dep.relation === 'co_acts_with' ? 'co-acts with' : 'precedes';
      const row = el('div', 'mind-dep-row');
      const desc = el('div', '');
      const str = document.createElement('strong');
      str.textContent = `${src} ${rel} ${tgt}`;
      const note = document.createElement('small');
      note.textContent = 'Organism-inferred relationship; not an Observatory topology edge.';
      desc.append(str, note);
      const measures = el('div', '');
      measures.style.cssText = 'display:grid;gap:4px;min-width:120px;';
      measures.appendChild(buildMetricRow('Confidence', dep.confidence));
      measures.appendChild(buildMetricRow('Support', dep.support));
      row.append(desc, measures);
      panel.appendChild(row);
    }
  }
}

function buildSelfCard(title, part) {
  const card = el('div', 'mind-self-card');
  const h4 = document.createElement('h4');
  h4.textContent = title;
  const code = document.createElement('code');
  code.textContent = part.id ?? '';
  const metrics = el('div', '');
  metrics.style.cssText = 'display:grid;gap:6px;margin-top:10px;';
  metrics.appendChild(buildMetricRow('Existence',  part.existence));
  metrics.appendChild(buildMetricRow('Health',     part.health));
  metrics.appendChild(buildMetricRow('Confidence', part.confidence));
  metrics.appendChild(buildMetricRow('Maturity',   part.maturity));
  card.append(h4, code, metrics);
  return card;
}

function buildMetricRow(label, value) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  const row = el('div', 'mind-metric-row');
  const lbl = document.createElement('span');
  lbl.textContent = label;
  const prog = document.createElement('progress');
  prog.max = 1; prog.value = v;
  prog.setAttribute('aria-label', label);
  const val = document.createElement('strong');
  val.textContent = pct(v);
  row.append(lbl, prog, val);
  return row;
}

// ─────────────────────────────────────────────────────────────────────────────
// Cognition Graph (force-directed canvas; adapted from observatory/render/cognition-graph.js)
// ─────────────────────────────────────────────────────────────────────────────

function buildGraphModel() {
  const topology = _snap.topology;
  const cognition = _snap.cognition;

  if (!topology?.nodes?.length) {
    // Demo / fallback sparse graph from beliefs
    const beliefs = (_snap.beliefs ?? []).slice(0, 8);
    const senses  = (_snap.senses ?? []).slice(0, 4);
    const nodes = [
      ...senses.map(s => ({ id: s.id, label: s.name ?? s.id, kind: 'sense', color: PAL.cyan, radius: 8, activationLevel: s.active ? 0.8 : 0.1 })),
      ...beliefs.map(b => ({ id: b.id, label: b.title ?? b.id, kind: 'concept', color: PAL.violet, radius: 7, activationLevel: (b.certainty ?? 0.3) })),
    ];
    const edges = [];
    senses.forEach((s, si) => {
      beliefs.slice(si * 2, si * 2 + 2).forEach(b => {
        edges.push({ sourceId: s.id, targetId: b.id, kind: 'excitatory' });
      });
    });
    return { nodes, edges };
  }

  const errors    = cognition?.predictionErrors ?? {};
  const readouts  = cognition?.readouts ?? {};
  const actClass  = cognition?.activationClasses ?? {};
  const stranded  = cognition?.strandedConcepts ?? [];

  const nodes = topology.nodes.map(n => {
    const ac = actClass[n.id] ?? 0;
    const kind = n.kind ?? 'concept';
    const colorMap = { sense: PAL.cyan, readout: PAL.mint, state: '#4ecdc4', predictor: PAL.amber, gate: '#e09f3e', concept: PAL.violet };
    const radiusMap = { sense: 8, readout: 10, state: 8, predictor: 9, gate: 8.5, concept: 7 };
    return {
      id:   n.id,
      label: n.id,
      kind,
      color: colorMap[kind] ?? PAL.violet,
      radius: radiusMap[kind] ?? 7,
      activationLevel: ac / 15,
      errorCls: errors[n.id] ?? null,
      readoutVal: readouts[n.id] != null ? Number(readouts[n.id]).toFixed(3) : null,
      isStranded: stranded.includes(n.id),
    };
  });

  const nodeSet = new Set(nodes.map(n => n.id));
  const edges = (topology.edges ?? [])
    .filter(e => nodeSet.has(e.sourceId) && nodeSet.has(e.targetId))
    .map(e => ({ sourceId: e.sourceId, targetId: e.targetId, kind: e.kind ?? 'excitatory' }));

  return { nodes, edges };
}

function initGraphPhysics(width, height) {
  const { nodes: rawNodes, edges: rawEdges } = buildGraphModel();
  const cx = width / 2, cy = height / 2;
  const nodeMap = new Map();

  _graph.nodes = rawNodes.map((raw, i) => {
    let node = _graph.cachedPositions.get(raw.id);
    if (!node) {
      const seed = hashStr(raw.id);
      const angle = i * 2.399 + ((seed % 100) / 100) * 0.2;
      const radius = 60 + (seed % 7) * 35;
      node = { ...raw, x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius, vx: 0, vy: 0, pinned: false };
      _graph.cachedPositions.set(raw.id, node);
    } else {
      Object.assign(node, raw);
    }
    nodeMap.set(node.id, node);
    return node;
  });

  _graph.edges = rawEdges
    .map(e => ({ source: nodeMap.get(e.sourceId), target: nodeMap.get(e.targetId), kind: e.kind }))
    .filter(e => e.source && e.target);

  _graph.alpha = 1.0;
}

function stepGraphPhysics(width, height) {
  const { nodes, edges } = _graph;
  const n = nodes.length;
  if (!n) return;
  const cx = width / 2, cy = height / 2;
  const alpha = _graph.alpha;

  // Repulsion
  for (let i = 0; i < n; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < n; j++) {
      const b = nodes[j];
      const dx = b.x - a.x, dy = b.y - a.y;
      const distSq = dx * dx + dy * dy + 100;
      if (distSq > 360000) continue;
      const dist = Math.sqrt(distSq);
      const force = (REPULSION / distSq) * alpha;
      const fx = (dx / dist) * force, fy = (dy / dist) * force;
      if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
      if (!b.pinned) { b.vx += fx; b.vy += fy; }
    }
  }
  // Springs
  for (const e of edges) {
    const dx = e.target.x - e.source.x, dy = e.target.y - e.source.y;
    const dist = Math.hypot(dx, dy) || 1;
    const disp = dist - SPRING_LEN;
    const force = disp * SPRING_K * alpha;
    const fx = (dx / dist) * force, fy = (dy / dist) * force;
    if (!e.source.pinned) { e.source.vx += fx; e.source.vy += fy; }
    if (!e.target.pinned) { e.target.vx -= fx; e.target.vy -= fy; }
  }
  // Gravity + integration
  for (const node of nodes) {
    if (node.pinned) continue;
    node.vx += (cx - node.x) * CENTER_G * alpha;
    node.vy += (cy - node.y) * CENTER_G * alpha;
    node.vx *= DAMPING; node.vy *= DAMPING;
    node.x += node.vx; node.y += node.vy;
  }
  _graph.alpha = Math.max(ALPHA_MIN, _graph.alpha * ALPHA_DECAY);
}

function drawGraphFrame(canvas) {
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  const { nodes, edges, scale, panX, panY, hoveredNode, fmriEnabled } = _graph;
  ctx.clearRect(0, 0, width, height);
  if (!nodes.length) return;

  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(scale, scale);

  const now = performance.now();
  const focusId = hoveredNode?.id ?? _graph.selectedNodeId;
  const connectedIds = focusId ? new Set([focusId]) : null;
  if (connectedIds) {
    for (const e of edges) {
      if (e.source.id === focusId) connectedIds.add(e.target.id);
      if (e.target.id === focusId) connectedIds.add(e.source.id);
    }
  }

  // Edges
  for (const edge of edges) {
    const isConn = focusId && (edge.source.id === focusId || edge.target.id === focusId);
    const dimmed = focusId && !isConn;
    let color;
    if (edge.kind === 'inhibitory')  color = `rgba(255,127,131,${isConn ? .95 : dimmed ? .04 : .35})`;
    else if (edge.kind === 'predictive') color = `rgba(255,189,84,${isConn ? .95 : dimmed ? .04 : .40})`;
    else if (edge.kind === 'gating') color = `rgba(224,159,62,${isConn ? .95 : dimmed ? .04 : .38})`;
    else                             color = `rgba(80,217,255,${isConn ? .95 : dimmed ? .04 : .28})`;
    ctx.beginPath();
    ctx.moveTo(edge.source.x, edge.source.y);
    ctx.lineTo(edge.target.x, edge.target.y);
    ctx.strokeStyle = color;
    ctx.lineWidth   = isConn ? 2.5 : 1.1;
    ctx.setLineDash(edge.kind === 'inhibitory' ? [4, 4] : edge.kind === 'gating' ? [2, 3] : []);
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
    const isConn = connectedIds && connectedIds.has(node.id);
    const dimmed = focusId && !isConn;
    const breath = (fmriEnabled && node.activationLevel > 0) ? Math.sin(now * 0.003 + hashStr(node.id)) * (node.activationLevel * 2.2) : 0;
    const r = (isHovered ? node.radius * 1.35 : node.radius) + breath;

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fillStyle = isHovered ? '#fff' : node.color;
    ctx.shadowColor = node.color;
    ctx.shadowBlur  = isConn ? 14 : (fmriEnabled && node.activationLevel > 0 ? 4 + node.activationLevel * 12 : 3);
    ctx.globalAlpha = dimmed ? 0.15 : (fmriEnabled ? 0.5 + node.activationLevel * 0.48 : 0.75);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.shadowBlur  = 0;

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
    if (!dimmed && (isConn || scale >= 1.1 || node.kind === 'readout' || node.kind === 'sense')) {
      ctx.font = '10px -apple-system, sans-serif';
      ctx.fillStyle = isConn ? '#fff' : 'rgba(175,199,220,.7)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      const lbl = node.label.length > 14 ? node.label.slice(0, 6) + '…' + node.label.slice(-4) : node.label;
      ctx.fillText(lbl, node.x, node.y + r + 10);
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
    if (draggedNode) { draggedNode.pinned = false; draggedNode = null; }
    isDragging = false; isPanning = false;
    canvas.style.cursor = 'grab';
  };

  window.addEventListener('mousemove', _graphWindowMouseMove);
  window.addEventListener('mouseup', _graphWindowMouseUp);
}

// ─────────────────────────────────────────────────────────────────────────────
// Regime Compass (adapted from observatory/render/regime-compass.js)
// ─────────────────────────────────────────────────────────────────────────────

function computeRegimeCoords() {
  const senses  = _snap.senses ?? [];
  const devs    = _snap.sensoryDevelopment ?? [];
  const cognition = _snap.cognition;

  const activeSenses = devs.length > 0 ? devs.filter(d => d.tier === 'active') : senses.filter(s => s.active);
  const totalSenses  = Math.max(1, devs.length || senses.length || 8);
  const activeRatio  = activeSenses.length / totalSenses;
  const meanUtil     = devs.length > 0
    ? devs.reduce((a, d) => a + (d.utility ?? 0), 0) / devs.length
    : senses.reduce((a, s) => a + (s.quality ?? 0.3), 0) / Math.max(1, senses.length);

  const roValues   = Object.values(cognition?.readouts ?? {});
  const meanReadout = roValues.length > 0 ? roValues.reduce((a, b) => a + Math.abs(b), 0) / roValues.length : 0.4;
  const fluxNorm   = activeRatio * 0.4 + meanUtil * 0.35 + meanReadout * 0.25;
  const targetX    = (fluxNorm - 0.48) * 520;

  const errMap  = { zero: 0.05, trace: 0.15, low: 0.35, medium: 0.65, high: 0.85, extreme: 1.0 };
  const errVals = Object.values(cognition?.predictionErrors ?? {});
  const meanErr = errVals.length > 0 ? errVals.reduce((a, c) => a + (errMap[c] ?? 0.2), 0) / errVals.length : 0.2;
  const beliefs = _snap.beliefs ?? [];
  const dissentRatio = beliefs.length > 0 ? beliefs.filter(b => b.dissent).length / beliefs.length : 0;
  const safetyPenalty = Math.min(1, (cognition?.safetyState?.consecutiveFailures ?? 0) * 0.25);
  const surpriseNorm = meanErr * 0.55 + dissentRatio * 0.3 + safetyPenalty * 0.15;
  const targetY = (0.5 - surpriseNorm) * 440;

  return { x: targetX, y: targetY, fluxNorm, surpriseNorm };
}

function evaluateRegime(pos) {
  let minD = Infinity, nearest = REGIMES[0];
  for (const r of REGIMES) {
    const d = Math.hypot(pos.x - r.x, pos.y - r.y);
    if (d < minD) { minD = d; nearest = r; }
  }
  const affinity    = Math.max(0, Math.min(100, Math.round((1 - minD / (nearest.radius * 1.8)) * 100)));
  const isUnexplored = minD > nearest.radius * 1.35;
  const noveltyPct  = isUnexplored
    ? Math.min(100, Math.round(55 + ((minD - nearest.radius * 1.35) / 140) * 45))
    : Math.max(0,  Math.round((minD / (nearest.radius * 1.35)) * 50));
  return { nearest, affinity, isUnexplored, noveltyPct };
}

function updateRegimeHud(analysis) {
  const { nearest, affinity, isUnexplored, noveltyPct } = analysis;
  const titleEl  = document.getElementById('mind-compass-title');
  const subEl    = document.getElementById('mind-compass-sub');
  const badgeEl  = document.getElementById('mind-compass-badge');
  const novEl    = document.getElementById('mind-compass-novelty');
  const novBar   = document.getElementById('mind-compass-novelty-bar');
  const driftEl  = document.getElementById('mind-compass-drift');
  const expEl    = document.getElementById('mind-compass-exp');
  if (!titleEl) return;

  if (isUnexplored) {
    if (titleEl) titleEl.textContent = 'Territorio Inexplorado';
    if (subEl)   subEl.textContent = `Nearest: ${nearest.name} (${affinity}%)`;
    if (badgeEl) { badgeEl.textContent = 'INÉDITO'; badgeEl.className = 'mind-compass-badge alert'; }
    if (novBar)  { novBar.style.background = PAL.coral; }
  } else {
    if (titleEl) titleEl.textContent = nearest.name;
    if (subEl)   subEl.textContent = `Active attractor · Affinity ${affinity}%`;
    const isMedium = noveltyPct > 35;
    if (badgeEl) { badgeEl.textContent = isMedium ? 'MODERATE DRIFT' : 'FAMILIAR'; badgeEl.className = `mind-compass-badge ${isMedium ? 'moderate' : 'familiar'}`; }
    if (novBar)  { novBar.style.background = isMedium ? PAL.amber : PAL.mint; }
  }
  if (novEl)   novEl.textContent = `${noveltyPct}%`;
  if (novBar)  novBar.style.width = `${Math.max(3, noveltyPct)}%`;
  if (driftEl) driftEl.textContent = `${_compass.velocity.toFixed(1)} px/tick`;
  if (expEl)   expEl.textContent = isUnexplored
    ? `Regime Alert: Host state vector falls outside learned attractors. Plasticity pressure is increasing.`
    : `${nearest.description}`;
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
  ctx.fillText('▲ PREDICTIVE TENSION', 0, -272);
  ctx.fillText('STABILITY ▼', 0, 277);
  ctx.textAlign = 'left';
  ctx.fillText('HOST ACTIVITY ►', 200, -8);
  ctx.textAlign = 'right';
  ctx.fillText('◄ QUIESCENCE', -200, -8);

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
      ctx.fillText(r.icon, r.x, r.y - 14);
      ctx.font = 'bold 10px -apple-system, sans-serif';
      ctx.fillStyle = '#fff'; ctx.fillText(r.name, r.x, r.y + 22);
    }
  }

  // Trail
  const coord = computeRegimeCoords();
  if (_compass.lastCoord) {
    _compass.velocity = Math.hypot(coord.x - _compass.lastCoord.x, coord.y - _compass.lastCoord.y);
  }
  const tick = _tel.tick ?? 0;
  if (!_compass.trail.length || _compass.trail[_compass.trail.length - 1].tick !== tick) {
    _compass.trail.push({ x: coord.x, y: coord.y, tick });
    if (_compass.trail.length > 30) _compass.trail.shift();
  }
  _compass.lastCoord = coord;

  const analysis = evaluateRegime(coord);
  updateRegimeHud(analysis);

  if (_compass.showTrail && _compass.trail.length > 1) {
    for (let i = 1; i < _compass.trail.length; i++) {
      const p0 = _compass.trail[i - 1], p1 = _compass.trail[i];
      const alpha = (i / _compass.trail.length) * 0.85;
      ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y);
      ctx.strokeStyle = analysis.isUnexplored ? `rgba(255,127,131,${alpha})` : `rgba(80,217,255,${alpha})`;
      ctx.lineWidth = 2; ctx.stroke();
    }
  }

  // Current state particle
  _compass.sonarPhase = (_compass.sonarPhase + 0.04) % 1;
  const { x: px, y: py } = coord;
  const pointColor = analysis.isUnexplored ? PAL.coral : (analysis.noveltyPct > 35 ? PAL.amber : PAL.mint);
  if (analysis.isUnexplored) {
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
  ctx.fillText('HOST STATE', px + 14, py - 6);

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
  return true;
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

    // A selected Observatory instance is authoritative. Runtime telemetry is
    // only a fallback unless it explicitly belongs to the same organism/run.
    if (_activeInstance && data.instance_id !== _activeInstance) return;
    if (_activeRunId && data.run_id && data.run_id !== _activeRunId) return;
    if (!_activeInstance) setWaiting(false, null);

    if (data.type === 'cognition') {
      _tel.tick             = data.tick ?? _tel.tick;
      _tel.schemaConf       = data.schema_confidence ?? _tel.schemaConf;
      _tel.schemaParts      = data.schema_parts ?? _tel.schemaParts;
      _tel.schemaSensory    = data.schema_sensory_parts ?? _tel.schemaSensory;
      _tel.schemaCognitive  = data.schema_cognitive_regions ?? _tel.schemaCognitive;
      _tel.motorOrigin      = data.motor_origin ?? _tel.motorOrigin;
      _tel.predictorCount   = data.predictor_count ?? _tel.predictorCount;
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
      _tel.resourceProgress = data.resource_progress ?? _tel.resourceProgress;
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

    // Auto-connect to the first alive instance if none is active
    if (!_activeInstance && alive.length > 0) {
      connectInstanceStream(alive[0].instance_id, alive[0].run_id ?? null);
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
      if (ok) {
        setWaiting(false, null);
        renderSensesPanel();
        updateTelemetryStrip();
        if (_activeTab === 'phenotype')  renderPhenotype();
        if (_activeTab === 'sensory')    renderSensoryMap();
        if (_activeTab === 'self')       renderSelf();
        if (_activeTab === 'cognition')  {
          initGraphPhysics(
            document.getElementById('mind-cognition-canvas')?.width ?? 900,
            document.getElementById('mind-cognition-canvas')?.height ?? 600,
          );
        }
      }
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
  _activeTab = 'phenotype';

  // Reset telemetry + snapshot state
  for (const k of Object.keys(_tel)) _tel[k] = null;
  for (const k of Object.keys(_snap)) _snap[k] = Array.isArray(_snap[k]) ? [] : null;
  _snap.senses = []; _snap.beliefs = []; _snap.sensoryDevelopment = [];
  _snap.sensoryRelations = [];
  _compass.trail = []; _compass.sonarPhase = 0; _compass.lastCoord = null; _compass.velocity = 0;
  _graph.cachedPositions.clear(); _graph.alpha = 1; _graph.scale = 1; _graph.panX = 0; _graph.panY = 0;

  // Build DOM
  buildLayout(root);

  // Show waiting overlay initially
  setWaiting(true, 'Connecting to organism streams…');

  // Render initial (empty) phenotype and initial telemetry immediately.
  renderPhenotype();
  updateTelemetryStrip(true);

  // Apply initial tab style
  switchTab('phenotype');

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
    if (_activeTab === 'phenotype') renderPhenotype();
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
}
