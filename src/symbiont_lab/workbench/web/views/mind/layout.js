/**
 * Mind DOM composition.
 *
 * This module owns structure and control wiring only. Cognition state,
 * streaming and rendering are delegated through callbacks.
 */
import { el, svgEl } from '../shared/dom.js';
import { PAL } from './config.js';
import { ATLAS_MODES } from './cognitive-atlas.js';

export function buildMindLayout(root, {
  activeTab = 'overview',
  graphDimension = '2d',
  graph3DMode = 'relational',
  graphAtlasMode = 'structure',
  onTabChange = () => {},
  on3DModeChange = () => {},
  onAtlasModeChange = () => {},
  onReturnLive = () => {},
} = {}) {
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
    btn.setAttribute('aria-pressed', tab.id === activeTab ? 'true' : 'false');
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
    btn.addEventListener('click', () => onTabChange(tab.id));
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
  cognitionInspectorHeading.textContent = 'Cognitive Observatory';
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
    display:flex;gap:4px;max-width:min(980px,calc(100% - 360px));flex-wrap:wrap;justify-content:flex-end;
  `;
  const viewModeGroup = el('div', '');
  viewModeGroup.style.cssText = 'display:flex;gap:4px;margin-right:8px;padding-right:8px;border-right:1px solid rgba(98,120,136,.22);';
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

  const atlasModeGroup = el('div', '');
  atlasModeGroup.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;';
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

  const atlasTimeline = el('div', '');
  atlasTimeline.id = 'mind-atlas-timeline-wrap';
  atlasTimeline.style.cssText = `
    position:absolute;left:50%;bottom:14px;transform:translateX(-50%);z-index:3;
    display:flex;align-items:center;gap:7px;min-width:360px;max-width:48%;
    padding:5px 7px;border:1px solid rgba(98,120,136,.22);border-radius:7px;
    background:rgba(6,14,24,.84);backdrop-filter:blur(4px);
  `;
  const timelineLabel = el('span', '');
  timelineLabel.id = 'mind-atlas-timeline-label';
  timelineLabel.style.cssText = 'font-size:8px;color:var(--muted);min-width:72px;white-space:nowrap;';
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
  timelineInput.style.cssText = 'flex:1;min-width:120px;accent-color:var(--cyan);';
  const diffBtn = makeControlBtn('Δ', 'Compare current Atlas with previous captured snapshot', false);
  diffBtn.id = 'mind-atlas-diff-btn';
  const liveTimelineBtn = makeControlBtn('LIVE', 'Return Atlas timeline to live state', false);
  liveTimelineBtn.id = 'mind-atlas-timeline-live';
  atlasTimeline.append(timelineLabel, timelineInput, diffBtn, liveTimelineBtn);

  const cognition3DNote = el('div', '');
  cognition3DNote.id = 'mind-cognition-3d-note';
  cognition3DNote.style.cssText = `
    position:absolute;left:12px;bottom:14px;z-index:2;
    max-width:360px;padding:6px 8px;border:1px solid rgba(98,120,136,.18);
    border-radius:6px;background:rgba(6,14,24,.78);font-size:8px;line-height:1.35;
    color:var(--muted);pointer-events:none;
  `;
  cognition3DNote.textContent = '2D observer cartography';

    const cognitionControls = el('div', '');
  cognitionControls.style.cssText = `
    position: absolute; bottom: 14px; right: 14px;
    display: flex; gap: 6px;
  `;
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
    cognitionModeControls,
    atlasTimeline,
    cognition3DNote,
    cognitionControls,
  );

  const overviewWrap = el('div', 'mind-overview-wrap hidden');
  overviewWrap.id = 'mind-overview-wrap';
  overviewWrap.style.cssText = 'position:absolute;inset:0;overflow:auto;background:var(--bg-deep);padding:18px 20px 28px;';

  const motorWrap = el('div', 'mind-motor-wrap hidden');
  motorWrap.id = 'mind-motor-wrap';
  motorWrap.style.cssText = 'position:absolute;inset:0;overflow:auto;background:var(--bg-deep);padding:18px 20px 28px;';

  const historyWrap = el('div', 'mind-history-wrap hidden');
  historyWrap.id = 'mind-history-wrap';
  historyWrap.style.cssText = 'position:absolute;inset:0;overflow:auto;background:var(--bg-deep);padding:18px 20px 28px;';

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
  canvasArea.append(overviewWrap, identityWrap, sensoryWrap, cognitionWrap, motorWrap, historyWrap, waitingOverlay);
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
