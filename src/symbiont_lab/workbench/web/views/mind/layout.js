/**
 * Mind DOM composition.
 *
 * This module owns structure and control wiring only. Cognition state,
 * streaming and rendering are delegated through callbacks.
 */
import { el, svgEl } from '../shared/dom.js';
import { ATLAS_MODES } from './cognitive-atlas.js';

export function buildMindLayout(root, {
  activeTab = 'overview',
  graphDimension = '2d',
  graph3DMode = 'relational',
  graphAtlasMode = 'structure',
  showEmbodiment = false,
  onTabChange = () => {},
  on3DModeChange = () => {},
  onAtlasModeChange = () => {},
  onShowEmbodimentChange = () => {},
  onReturnLive = () => {},
} = {}) {
  root.replaceChildren();
  root.classList.add('mind-view-root');

  // ── Tab bar ─────────────────────────────────────────────────────────────────
  const tabBar = el('div', 'mind-tab-bar');
  tabBar.setAttribute('role', 'tablist');
  tabBar.setAttribute('aria-label', 'Mind view tabs');

  const TABS = [
    { id: 'overview',  label: 'Overview',       panelId: 'mind-overview-wrap' },
    { id: 'phenotype', label: 'Identity',       panelId: 'mind-identity-wrap' },
    { id: 'sensory',   label: 'Sensory',        panelId: 'mind-sensory-wrap' },
    { id: 'cognition', label: 'Cognition',      panelId: 'mind-cognition-wrap' },
    { id: 'motor',     label: 'Motor Learning', panelId: 'mind-motor-wrap' },
    { id: 'history',   label: 'History',        panelId: 'mind-history-wrap' },
  ];

  for (const tab of TABS) {
    const btn = el('button', 'mind-tab');
    btn.dataset.tab = tab.id;
    btn.id = `mind-tab-${tab.id}`;
    btn.textContent = tab.label;
    btn.setAttribute('role', 'tab');
    btn.setAttribute('aria-selected', String(tab.id === activeTab));
    btn.setAttribute('aria-controls', tab.panelId);
    btn.tabIndex = tab.id === activeTab ? 0 : -1;
    btn.addEventListener('click', () => onTabChange(tab.id));
    tabBar.appendChild(btn);
  }
  root.appendChild(tabBar);

  // ── Workspace: senses panel + canvas ────────────────────────────────────────
  const workspace = el('div', 'mind-workspace');
  workspace.id = 'mind-workspace';
  workspace.dataset.activeTab = activeTab;

  // Left senses panel
  const sensesPanel = el('aside', 'mind-senses-panel');
  sensesPanel.id = 'mind-senses-panel';
  sensesPanel.hidden = activeTab !== 'sensory';
  const sensesHeading = el('div', 'mind-side-heading');
  sensesHeading.textContent = 'Sensory State';
  const sensesList = el('div', 'mind-side-list');
  sensesList.id = 'mind-senses-list';
  sensesPanel.appendChild(sensesHeading);
  sensesPanel.appendChild(sensesList);

  // Contextual cognition inspector. Reuses the left rail only on Cognition so
  // sensory inventory does not consume space where it adds no analytical value.
  const cognitionInspector = el('aside', 'mind-cognition-inspector');
  cognitionInspector.id = 'mind-cognition-inspector';
  cognitionInspector.hidden = activeTab !== 'cognition';
  const cognitionInspectorHeading = el('div', 'mind-side-heading');
  cognitionInspectorHeading.textContent = 'Cognitive Observatory';
  const cognitionInspectorBody = el('div', 'mind-cognition-inspector-body');
  cognitionInspectorBody.id = 'mind-cognition-inspector-body';
  cognitionInspector.append(cognitionInspectorHeading, cognitionInspectorBody);

  // Main canvas area
  const canvasArea = el('div', 'mind-canvas-area');

  // Phenotype / Self comparison — observed expression vs organism-owned self-model
  const identityWrap = el('div', 'mind-identity-wrap');
  identityWrap.id = 'mind-identity-wrap';
  identityWrap.setAttribute('role', 'tabpanel');
  identityWrap.setAttribute('aria-labelledby', 'mind-tab-phenotype');

  const phenotypePane = el('section', 'mind-identity-pane');
  const phenotypeHeading = el('header', 'mind-identity-heading');
  const phenotypeTitle = el('strong', 'mind-identity-title');
  phenotypeTitle.textContent = 'Observed organism';
  const phenotypeSub = el('small', 'mind-identity-subtitle');
  phenotypeSub.textContent = 'Externally measurable functional expression.';
  phenotypeHeading.append(phenotypeTitle, phenotypeSub);

  const phenotypeSvg = svgEl('svg', {
    id: 'mind-phenotype-svg',
    viewBox: '0 0 900 720',
    role: 'img',
    'aria-label': 'Observed functional phenotype of the Symbiont organism',
    class: 'mind-phenotype-svg',
  });
  phenotypePane.append(phenotypeHeading, phenotypeSvg);

  const selfPane = el('section', 'mind-identity-pane');
  const selfHeading = el('header', 'mind-identity-heading');
  const selfTitle = el('strong', 'mind-identity-title');
  selfTitle.textContent = 'Self-model';
  const selfSub = el('small', 'mind-identity-subtitle');
  selfSub.textContent = 'Organism-owned representation of what belongs to self.';
  selfHeading.append(selfTitle, selfSub);

  const selfPanel = el('div', 'mind-self-panel');
  selfPanel.id = 'mind-self-panel';
  selfPane.append(selfHeading, selfPanel);

  const gapPane = el('aside', 'mind-identity-gap');
  gapPane.id = 'mind-identity-gap';

  identityWrap.append(phenotypePane, gapPane, selfPane);

  // Sensory Intelligence Workbench — one live scene with analytical lenses.
  const sensoryWrap = el('div', 'mind-sensory-wrap hidden');
  sensoryWrap.id = 'mind-sensory-wrap';
  sensoryWrap.setAttribute('role', 'tabpanel');
  sensoryWrap.setAttribute('aria-labelledby', 'mind-tab-sensory');

  const sensoryHeader = el('header', 'mind-sensory-header');
  const sensoryHeading = el('div', 'mind-sensory-heading');
  const sensoryTitle = el('strong', 'mind-sensory-title');
  sensoryTitle.textContent = 'Sensory Intelligence';
  const sensorySubtitle = el('span', 'mind-sensory-subtitle');
  sensorySubtitle.textContent = 'Perception · integration · prediction · discovery';
  sensoryHeading.append(sensoryTitle, sensorySubtitle);

  const sensoryMetrics = el('div', 'mind-sensory-metrics');
  sensoryMetrics.id = 'mind-sensory-metrics';

  const sensoryLenses = el('div', 'mind-sensory-lenses');
  sensoryLenses.setAttribute('role', 'group');
  sensoryLenses.setAttribute('aria-label', 'Sensory analytical lens');
  for (const [id, label, title] of [
    ['topology', 'Topology', 'Learned sensory topology'],
    ['activity', 'Activity', 'Emphasize currently sampled and active pathways'],
    ['prediction', 'Prediction', 'Emphasize predictors and predictive pathways'],
    ['novelty', 'Novelty', 'Emphasize uncertain, immature and weakly integrated receptors'],
    ['sensorimotor', 'Sensorimotor', 'Emphasize readouts and sensor-to-action paths'],
  ]) {
    const button = makeControlBtn(label, title, id === 'topology');
    button.dataset.sensoryLens = id;
    sensoryLenses.appendChild(button);
  }
  sensoryHeader.append(sensoryHeading, sensoryMetrics, sensoryLenses);

  const sensoryStage = el('div', 'mind-sensory-stage');
  const sensoryMapSvg = svgEl('svg', {
    id: 'mind-sensory-map-svg',
    viewBox: '0 0 1100 650',
    role: 'img',
    'aria-label': 'Sensory intelligence map — receptors, concepts, predictors and readouts',
    class: 'mind-sensory-map-svg',
  });

  const sensoryInspector = el('aside', 'mind-sensory-inspector');
  sensoryInspector.id = 'mind-sensory-inspector';
  sensoryInspector.setAttribute('aria-label', 'Sensory selection inspector');
  sensoryStage.append(sensoryMapSvg, sensoryInspector);

  const sensoryTimeline = el('div', 'mind-sensory-timeline');
  sensoryTimeline.id = 'mind-sensory-timeline';
  sensoryTimeline.setAttribute('aria-label', 'Recent sensory evolution');

  const sensoryDetail = el('div', 'mind-sensory-detail');
  sensoryDetail.id = 'mind-sensory-detail';
  sensoryDetail.textContent = 'Sensory funnel: awaiting live sensory evidence.';

  sensoryWrap.append(sensoryHeader, sensoryStage, sensoryTimeline, sensoryDetail);

  // Cognition canvas
  const cognitionWrap = el('div', 'mind-cognition-wrap hidden');
  cognitionWrap.id = 'mind-cognition-wrap';
  cognitionWrap.setAttribute('role', 'tabpanel');
  cognitionWrap.setAttribute('aria-labelledby', 'mind-tab-cognition');
  const cognitionCanvas = document.createElement('canvas');
  cognitionCanvas.id = 'mind-cognition-canvas';
  cognitionCanvas.className = 'mind-cognition-canvas';
  const cognitionSummary = el('div', 'mind-cognition-summary');
  cognitionSummary.id = 'mind-cognition-summary';

  const cognitionLiveFocus = el('aside', 'mind-cognition-live-focus');
  cognitionLiveFocus.id = 'mind-cognition-live-focus';
  cognitionLiveFocus.setAttribute('aria-label', 'Current cognitive activity focus');

  const cognitionEventStream = el('aside', 'mind-cognition-event-stream');
  cognitionEventStream.id = 'mind-cognition-event-stream';
  cognitionEventStream.setAttribute('aria-label', 'Recent cognitive events');

  const cognitionLiveTimeline = el('div', 'mind-cognition-live-timeline');
  cognitionLiveTimeline.id = 'mind-cognition-live-timeline';
  cognitionLiveTimeline.setAttribute('aria-label', 'Recent live cognitive activity');

  const cognitionModeControls = el('div', 'mind-cognition-mode-controls');
  const viewModeGroup = el('div', 'mind-cognition-view-modes');
  const activeViewMode = graphDimension === '3d' && graph3DMode === 'physicalized'
    ? 'physicalized'
    : 'relational';
  for (const [viewMode, label, title] of [
    ['relational', 'Relational', 'Relational observer cartography'],
    ['physicalized', 'Physicalized', 'Physicalized 3D observer projection'],
  ]) {
    const button = makeControlBtn(label, title, viewMode === activeViewMode);
    button.dataset.graph3dMode = viewMode;
    button.addEventListener('click', () => {
      viewModeGroup.querySelectorAll('button').forEach(item => {
        item.classList.toggle('active', item.dataset.graph3dMode === viewMode);
      });
      on3DModeChange(viewMode);
    });
    viewModeGroup.appendChild(button);
  }
  cognitionModeControls.appendChild(viewModeGroup);

  // Independent of the 2D/3D layout mode above: adds embodiment_binding
  // boundary nodes (organism knowledge <-> current body) to the Atlas.
  const embodimentGroup = el('div', 'mind-cognition-embodiment-group');
  const embodimentBtn = makeControlBtn(
    'Show embodiment',
    'Reveal embodiment_binding nodes: current-body boundary for learned motor competences',
    showEmbodiment,
  );
  embodimentBtn.id = 'mind-cognition-show-embodiment';
  embodimentBtn.addEventListener('click', () => {
    const next = !embodimentBtn.classList.contains('active');
    embodimentBtn.classList.toggle('active', next);
    onShowEmbodimentChange(next);
  });
  embodimentGroup.appendChild(embodimentBtn);
  cognitionModeControls.appendChild(embodimentGroup);

  const atlasModeGroup = el('div', 'mind-atlas-mode-group');
  for (const mode of ATLAS_MODES) {
    const button = makeControlBtn(
      mode.label,
      `Cognitive Atlas: ${mode.description}`,
      mode.id === graphAtlasMode,
    );
    button.dataset.atlasMode = mode.id;
    button.addEventListener('click', () => {
      atlasModeGroup.querySelectorAll('[data-atlas-mode]').forEach(item => {
        item.classList.toggle('active', item.dataset.atlasMode === mode.id);
      });
      onAtlasModeChange(mode.id);
    });
    atlasModeGroup.appendChild(button);
  }
  cognitionModeControls.appendChild(atlasModeGroup);

  const atlasTimeline = el('div', 'mind-atlas-timeline');
  atlasTimeline.id = 'mind-atlas-timeline-wrap';
  const timelineLabel = el('span', 'mind-atlas-timeline-label');
  timelineLabel.id = 'mind-atlas-timeline-label';
  timelineLabel.textContent = 'timeline · LIVE';
  const timelineInput = document.createElement('input');
  timelineInput.id = 'mind-atlas-timeline';
  timelineInput.type = 'range';
  timelineInput.min = '0';
  timelineInput.max = '0';
  timelineInput.value = '0';
  timelineInput.step = '1';
  timelineInput.disabled = true;
  timelineInput.setAttribute('aria-label', 'Cognitive Atlas captured history');
  timelineInput.className = 'mind-atlas-timeline-input';
  const diffBtn = makeControlBtn('Δ', 'Compare current Atlas with previous captured snapshot', false);
  diffBtn.id = 'mind-atlas-diff-btn';
  const liveTimelineBtn = makeControlBtn('LIVE', 'Return Atlas timeline to live state', false);
  liveTimelineBtn.id = 'mind-atlas-timeline-live';
  atlasTimeline.append(timelineLabel, timelineInput, diffBtn, liveTimelineBtn);

  const cognition3DNote = el('div', 'mind-cognition-3d-note');
  cognition3DNote.id = 'mind-cognition-3d-note';
  cognition3DNote.textContent = '2D observer cartography';

  const cognitionControls = el('div', 'mind-cognition-controls');
  const btnFlow  = makeControlBtn('Trace', 'Trace recently observed cognitive flow', false); btnFlow.id = 'mind-flow-trace-btn';
  const btnFmri  = makeControlBtn('⚡', 'Toggle activity glow', true);  btnFmri.id = 'mind-fmri-btn';
  const btnZoomIn= makeControlBtn('+', 'Zoom in', false);       btnZoomIn.id = 'mind-zoom-in';
  const btnZoomOut=makeControlBtn('−', 'Zoom out', false);      btnZoomOut.id = 'mind-zoom-out';
  const btnReset = makeControlBtn('⟲', 'Reset', false);         btnReset.id = 'mind-graph-reset';
  const btnLive = makeControlBtn('LIVE', 'Return to live cognition', false); btnLive.id = 'mind-graph-live';
  btnLive.addEventListener('click', onReturnLive);
  cognitionControls.append(btnLive, btnFlow, btnFmri, btnZoomIn, btnZoomOut, btnReset);
  cognitionWrap.append(
    cognitionCanvas,
    cognitionSummary,
    cognitionLiveFocus,
    cognitionEventStream,
    cognitionModeControls,
    atlasTimeline,
    cognitionLiveTimeline,
    cognition3DNote,
    cognitionControls,
  );

  const overviewWrap = el('div', 'mind-overview-wrap hidden');
  overviewWrap.id = 'mind-overview-wrap';
  overviewWrap.setAttribute('role', 'tabpanel');
  overviewWrap.setAttribute('aria-labelledby', 'mind-tab-overview');

  const motorWrap = el('div', 'mind-motor-wrap hidden');
  motorWrap.id = 'mind-motor-wrap';
  motorWrap.setAttribute('role', 'tabpanel');
  motorWrap.setAttribute('aria-labelledby', 'mind-tab-motor');

  const historyWrap = el('div', 'mind-history-wrap hidden');
  historyWrap.id = 'mind-history-wrap';
  historyWrap.setAttribute('role', 'tabpanel');
  historyWrap.setAttribute('aria-labelledby', 'mind-tab-history');

  // Waiting overlay (when no organism is active yet)
  const waitingOverlay = el('div', 'mind-waiting');
  waitingOverlay.id = 'mind-waiting';
  const waitSpinner = el('div', 'mind-wait-spinner');
  const waitText = el('span', '');
  waitText.id = 'mind-wait-text';
  waitText.textContent = 'Waiting for live organism…';
  waitingOverlay.append(waitSpinner, waitText);

  // Assemble canvas area
  canvasArea.append(overviewWrap, identityWrap, sensoryWrap, cognitionWrap, motorWrap, historyWrap, waitingOverlay);
  workspace.append(sensesPanel, cognitionInspector, canvasArea);
  root.appendChild(workspace);

  // ── Bottom telemetry strip ───────────────────────────────────────────────────
  const telemStrip = el('footer', 'mind-telemetry-strip');
  telemStrip.id = 'mind-telem-strip';
  buildTelemNodes(telemStrip);
  root.appendChild(telemStrip);


}

function makeControlBtn(text, title, active) {
  const btn = el('button', `mind-ctrl-btn${active ? ' active' : ''}`);
  btn.textContent = text;
  btn.title = title;
  btn.setAttribute('aria-label', title);
  return btn;
}

function buildTelemNodes(parent) {
  const items = [
    { id: 'mind-t-tick',      label: 'Tick',       init: '—' },
    { id: 'mind-t-phase',     label: 'Physiology', init: '—' },
    { id: 'mind-t-energy',    label: 'Energy',     init: '—' },
    { id: 'mind-t-resource',  label: 'Resource Δ', init: '—' },
    { id: 'mind-t-cognition', label: 'Cognition',  init: '—' },
    { id: 'mind-t-motor',     label: 'Motor',      init: '—' },
    { id: 'mind-t-instance',  label: 'Instance',   init: '—' },
  ];

  for (const item of items) {
    const wrap = el('span', 'mind-telem-item');
    const label = el('span', '');
    label.textContent = `${item.label}: `;
    const value = el('b', '');
    value.id = item.id;
    value.textContent = item.init;
    wrap.append(label, value);
    parent.appendChild(wrap);
  }
}
