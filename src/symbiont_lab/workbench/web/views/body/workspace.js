import { escapeHtml } from '../shared/dom.js';

/**
 * BODY research workspace.
 *
 * Observer-only presentation layer: six coordinated views over the existing
 * Physics3D telemetry. Nothing in this module writes back to Symbiont.
 */

const TABS = [
  ['overview', 'Overview'],
  ['anatomy', 'Anatomy'],
  ['motion', 'Motion'],
  ['physiology', 'Physiology'],
  ['interaction', 'Interaction'],
  ['history', 'History'],
];

const METRIC_LABELS = {
  tick: 'Tick',
  alive: 'Life',
  metabolic_reserve: 'Reserve',
  reserve_trend: 'Reserve trend',
  motor_activity: 'Motor activity',
  active_joints: 'Active joints',
  active_effectors: 'Active effectors',
  contact_count: 'Body contacts',
  peak_contact_force: 'Peak contact force',
  com_height: 'COM height',
  ground_contact_count: 'Ground contacts',
  self_contact_count: 'Self contacts',
  resource_contact_count: 'Resource contacts',
  distance_travelled: 'Path travelled',
  displacement: 'Net displacement',
  locomotion_efficiency: 'Path efficiency',
  resource_distance: 'Resource distance',
  resource_progress: 'Resource progress',
  motion_effectiveness: 'Approach efficiency',
  motor_origin: 'Motor origin',
  cognitive_context: 'Cognitive context',
};

function node(tag, className = '', text = '') {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== '') n.textContent = text;
  return n;
}

function numeric(text) {
  if (text == null) return null;
  const match = String(text).replace(',', '.').match(/[-+]?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}


function sparkline(values, width = 250, height = 46) {
  const finite = values.filter(Number.isFinite);
  if (finite.length < 2) {
    return '<div class="body-empty-line">insufficient trend</div>';
  }
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  const span = Math.max(1e-9, max - min);
  const pts = finite.map((v, i) => {
    const x = (i / Math.max(1, finite.length - 1)) * width;
    const y = height - 3 - ((v - min) / span) * (height - 6);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" class="body-spark">
    <polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.8" vector-effect="non-scaling-stroke"/>
  </svg>`;
}

function metricCard(label, value, tone = '') {
  return `<div class="body-metric-card ${tone}">
    <div class="body-metric-label">${escapeHtml(label)}</div>
    <div class="body-metric-value">${escapeHtml(value ?? '—')}</div>
  </div>`;
}

export class BodyWorkspace {
  constructor(viewer) {
    this.viewer = viewer;
    this.activeTab = 'overview';
    this.metrics = new Map();
    this.colors = new Map();
    this.history = [];
    this.maxHistory = 220;
    this.selectedSegment = null;
    this.nav = null;
    this.panel = null;
    this.overlay = null;
    this.overlayContent = null;
    this.renderQueued = false;
  }

  mount(root, canvasWrap, panel) {
    this.nav = node('div', 'body-tabs');
    this.nav.setAttribute('role', 'tablist');
    this.nav.setAttribute('aria-label', 'Body view tabs');
    for (const [id, label] of TABS) {
      const b = node('button', 'body-tab', label);
      b.type = 'button';
      b.id = `body-tab-${id}`;
      b.dataset.tab = id;
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-controls', 'body-inspector-panel');
      b.setAttribute('aria-selected', String(id === this.activeTab));
      b.tabIndex = id === this.activeTab ? 0 : -1;
      b.addEventListener('click', () => this.setTab(id));
      b.addEventListener('keydown', (event) => this.handleTabKey(event, id));
      this.nav.appendChild(b);
    }
    root.appendChild(this.nav);

    this.overlay = node('div', 'body-data-overlay');
    this.overlayContent = node('div', 'body-data-overlay-content');
    this.overlay.appendChild(this.overlayContent);
    canvasWrap.appendChild(this.overlay);

    this.panel = panel;
    panel.id = 'body-inspector-panel';
    panel.classList.add('body-inspector');
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', 'body-tab-overview');
    this.setTab('overview');
  }


  setTab(tab) {
    if (!TABS.some(([id]) => id === tab)) return;
    this.activeTab = tab;
    this.nav?.querySelectorAll('.body-tab').forEach((button) => {
      const active = button.dataset.tab === tab;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
    });
    this.panel?.setAttribute('aria-labelledby', `body-tab-${tab}`);
    const dataView = tab === 'physiology' || tab === 'history';
    this.overlay?.classList.toggle('visible', dataView);
    if (tab !== 'anatomy') this.clearSegmentHighlight();
    this.viewer.setObserverMode?.(tab);
    this.render();
  }

  updateMetric(id, text, color = null) {
    this.metrics.set(id, text);
    if (color) this.colors.set(id, color);
    if (id === 'tick') this.recordSample();
    this.requestRender();
  }

  recordSample() {
    const tick = numeric(this.metrics.get('tick'));
    if (!Number.isFinite(tick)) return;
    const last = this.history[this.history.length - 1];
    if (last?.tick === tick) return;
    this.history.push({
      tick,
      reserve: numeric(this.metrics.get('metabolic_reserve')),
      contacts: numeric(this.metrics.get('contact_count')),
      groundContacts: numeric(this.metrics.get('ground_contact_count')),
      selfContacts: numeric(this.metrics.get('self_contact_count')),
      resourceContacts: numeric(this.metrics.get('resource_contact_count')),
      displacement: numeric(this.metrics.get('displacement')),
      path: numeric(this.metrics.get('distance_travelled')),
      resource: numeric(this.metrics.get('resource_distance')),
      progress: numeric(this.metrics.get('resource_progress')),
      activeJoints: numeric(this.metrics.get('active_joints')),
      motorOrigin: this.metrics.get('motor_origin') ?? '—',
    });
    if (this.history.length > this.maxHistory) this.history.shift();
  }

  requestRender() {
    if (this.renderQueued) return;
    this.renderQueued = true;
    requestAnimationFrame(() => {
      this.renderQueued = false;
      this.render();
    });
  }

  m(id, fallback = '—') { return this.metrics.get(id) ?? fallback; }

  render() {
    if (!this.panel) return;
    if (this.activeTab === 'overview') this.renderOverview();
    else if (this.activeTab === 'anatomy') this.renderAnatomy();
    else if (this.activeTab === 'motion') this.renderMotion();
    else if (this.activeTab === 'interaction') this.renderInteraction();
    else if (this.activeTab === 'physiology') this.renderPhysiology();
    else if (this.activeTab === 'history') this.renderHistory();
  }

  head(kicker, title, sub) {
    return `<div class="body-inspector-head"><div class="body-inspector-kicker">${kicker}</div><div class="body-inspector-title">${title}</div><div class="body-inspector-sub">${sub}</div></div>`;
  }

  rows(ids) {
    return ids.map(id => `<div class="body-row"><span>${METRIC_LABELS[id] ?? id}</span><strong style="color:${this.colors.get(id) ?? 'inherit'}">${escapeHtml(this.m(id))}</strong></div>`).join('');
  }

  renderOverview() {
    const reserve = this.history.map(x => x.reserve).filter(Number.isFinite);
    this.panel.innerHTML = this.head('Body', 'Physical overview', 'What the organism is doing now.') +
      '<div class="body-section"><div class="body-section-title">Vitality</div>' +
      this.rows(['alive','metabolic_reserve','reserve_trend']) +
      `<div class="body-mini-chart">${sparkline(reserve)}</div></div>` +
      '<div class="body-section"><div class="body-section-title">Movement</div>' +
      this.rows(['motor_activity','active_joints','active_effectors','contact_count','peak_contact_force','com_height','ground_contact_count','self_contact_count','distance_travelled','displacement']) +
      '</div><div class="body-section"><div class="body-section-title">Environment</div>' +
      this.rows(['resource_distance','resource_progress','motion_effectiveness']) +
      '</div><div class="body-section"><div class="body-section-title">Control</div>' +
      this.rows(['motor_origin','cognitive_context']) + '</div>';
  }

  renderAnatomy() {
    const names = Object.keys(this.viewer.bodyModel?.segments ?? {});
    const selected = this.selectedSegment;
    const joints = selected ? (this.viewer.bodyModel?.segmentActivityJoints?.[selected] ?? []) : [];
    const active = joints.filter(j => (this.viewer.jointActivity.get(j) ?? 0) > .13).length;
    const flexion = this.viewer.jointFlexionSummary?.(10) ?? { flexed: 0, max: null, joints: [] };
    const selectedJointRows = joints.map((name) => {
      const degrees = this.viewer.jointAngleDegrees?.(name);
      const value = Number.isFinite(degrees) ? `${degrees >= 0 ? '+' : ''}${degrees.toFixed(1)}°` : '—';
      return `<div class="body-row"><span>${escapeHtml(name.replaceAll('_',' '))}</span><strong>${value}</strong></div>`;
    }).join('');
    const leading = flexion.joints.slice(0, 8).map((joint) => {
      const value = `${joint.degrees >= 0 ? '+' : ''}${joint.degrees.toFixed(1)}°`;
      return `<div class="body-row"><span>${escapeHtml(joint.name.replaceAll('_',' '))}</span><strong>${value}</strong></div>`;
    }).join('');
    const diagnosticLabel = this.viewer.articulationDiagnostic ? 'Return to live pose' : 'Visual articulation check';

    this.panel.innerHTML = this.head('Body · Anatomy', 'Inspectable morphology', 'Real joint angles from Physics3D. Activity and flexion are shown separately.') +
      `<div class="body-section"><div class="body-section-title">Articulation</div>
        <div class="body-row"><span>Flexed joints ≥10°</span><strong>${flexion.flexed} / ${flexion.joints.length}</strong></div>
        <div class="body-row"><span>Largest absolute angle</span><strong>${flexion.max ? `${escapeHtml(flexion.max.name.replaceAll('_',' '))} · ${flexion.max.degrees.toFixed(1)}°` : '—'}</strong></div>
        <button type="button" class="body-segment ${this.viewer.articulationDiagnostic ? 'active' : ''}" data-articulation-diagnostic>${diagnosticLabel}</button>
        <div class="body-inspector-sub">The articulation check changes only the observer pose. Physics and Symbiont continue untouched.</div>
      </div>` +
      `<div class="body-section"><div class="body-section-title">Largest current angles</div>${leading || '<div class="body-inspector-sub">No joint-angle telemetry yet.</div>'}</div>` +
      `<div class="body-section"><div class="body-section-title">Body regions</div><div class="body-segment-grid">${names.map(name => `<button class="body-segment ${selected===name?'active':''}" data-segment="${escapeHtml(name)}">${escapeHtml(name.replaceAll('_',' '))}</button>`).join('')}</div></div>` +
      `<div class="body-section"><div class="body-section-title">Selection</div><div class="body-row"><span>Region</span><strong>${escapeHtml(selected ?? 'none')}</strong></div><div class="body-row"><span>Associated joints</span><strong>${joints.length}</strong></div><div class="body-row"><span>Currently active</span><strong>${active}</strong></div>${selectedJointRows}</div>`;

    this.panel.querySelectorAll('[data-segment]').forEach(b => b.addEventListener('click', () => this.selectSegment(b.dataset.segment)));
    this.panel.querySelector('[data-articulation-diagnostic]')?.addEventListener('click', () => {
      this.viewer.setArticulationDiagnostic?.(!this.viewer.articulationDiagnostic);
    });
  }

  selectSegment(name) {
    this.clearSegmentHighlight();
    this.selectedSegment = name;
    const mesh = this.viewer.segmentMeshes?.[name];
    if (mesh?.material?.emissive) {
      mesh.userData.bodyOriginalEmissive = mesh.material.emissive.getHex();
      mesh.material.emissive.setHex(0x135f72);
      mesh.material.emissiveIntensity = .72;
    }
    this.renderAnatomy();
  }

  clearSegmentHighlight() {
    if (!this.selectedSegment) return;
    const mesh = this.viewer.segmentMeshes?.[this.selectedSegment];
    if (mesh?.material?.emissive) {
      mesh.material.emissive.setHex(mesh.userData.bodyOriginalEmissive ?? 0x000000);
      mesh.material.emissiveIntensity = 1;
    }
    this.selectedSegment = null;
  }

  renderMotion() {
    const disp = this.history.map(x => x.displacement).filter(Number.isFinite);
    const path = this.history.map(x => x.path).filter(Number.isFinite);
    const flexion = this.viewer.jointFlexionSummary?.(10) ?? { flexed: 0, max: null, joints: [] };
    const flexionRows =
      `<div class="body-row"><span>Flexed joints ≥10°</span><strong>${flexion.flexed} / ${flexion.joints.length}</strong></div>` +
      `<div class="body-row"><span>Largest joint angle</span><strong>${flexion.max ? `${escapeHtml(flexion.max.name.replaceAll('_',' '))} · ${flexion.max.degrees.toFixed(1)}°` : '—'}</strong></div>`;
    this.panel.innerHTML = this.head('Body · Motion', 'Movement evidence', 'Activity means motion; flexion shows how bent the body actually is.') +
      '<div class="body-section"><div class="body-section-title">Current motion</div>' +
      this.rows(['motor_activity','active_joints','contact_count','ground_contact_count','self_contact_count','distance_travelled','displacement','locomotion_efficiency']) +
      flexionRows +
      `<div class="body-mini-chart">${sparkline(disp.length ? disp : path)}</div></div>` +
      '<div class="body-section"><div class="body-section-title">Control transition</div>' +
      this.rows(['motor_origin','cognitive_context']) + '</div>';
  }

  renderInteraction() {
    const resource = this.history.map(x => x.resource).filter(Number.isFinite);
    this.panel.innerHTML = this.head('Body · Interaction', 'Body ↔ world', 'Observable physical relationship with the current environment.') +
      '<div class="body-section"><div class="body-section-title">Resource</div>' +
      this.rows(['resource_distance','resource_progress','motion_effectiveness']) +
      `<div class="body-mini-chart">${sparkline(resource)}</div></div>` +
      '<div class="body-section"><div class="body-section-title">Contact</div>' +
      this.rows(['contact_count','peak_contact_force','com_height','ground_contact_count','self_contact_count','resource_contact_count','active_effectors','displacement']) +
      '</div><div class="body-section"><div class="body-section-title">Interpretation boundary</div><div class="body-inspector-sub">This view reports observed relationships only. It does not infer intention or feed labels back into Symbiont.</div></div>';
  }

  viewHeader(title, sub) {
    return `<div class="body-view-head"><div><div class="body-view-title">${title}</div><div class="body-view-sub">${sub}</div></div><span class="body-chip">observer-side · live</span></div>`;
  }

  chart(title, values, tone = '') {
    return `<div class="body-chart-card ${tone}"><div class="body-chart-title">${title}</div><div class="body-chart-wrap">${sparkline(values, 520, 76)}</div></div>`;
  }

  renderPhysiology() {
    if (!this.overlayContent) return;
    const reserve = this.history.map(x=>x.reserve).filter(Number.isFinite);
    const contacts = this.history.map(x=>x.groundContacts).filter(Number.isFinite);
    const active = this.history.map(x=>x.activeJoints).filter(Number.isFinite);
    const progress = this.history.map(x=>x.progress).filter(Number.isFinite);
    this.overlayContent.innerHTML = this.viewHeader('Physiology', 'How physical activity, contact and reserve evolve together.') +
      `<div class="body-card-grid">${metricCard('Reserve',this.m('metabolic_reserve'))}${metricCard('Reserve trend',this.m('reserve_trend'))}${metricCard('Motor activity',this.m('motor_activity'))}${metricCard('Ground contacts',this.m('ground_contact_count'))}</div>` +
      `<div class="body-chart-grid">${this.chart('Metabolic reserve',reserve,'mint')}${this.chart('Active joints',active)}${this.chart('Ground contacts',contacts,'amber')}${this.chart('Resource progress',progress,'violet')}</div>`;
    this.panel.innerHTML = this.head('Body · Physiology', 'Physical cost and state', 'Live evidence from the body, without introducing goals or reward.') +
      this.rows(['alive','metabolic_reserve','reserve_trend','motor_activity','active_joints','contact_count','ground_contact_count','self_contact_count']);
  }

  deriveEpisodes() {
    if (this.history.length < 2) return [];
    const episodes = [];
    for (let i = 1; i < this.history.length; i++) {
      const a = this.history[i-1], b = this.history[i];
      if (Number.isFinite(a.reserve) && Number.isFinite(b.reserve) && a.reserve - b.reserve >= 4) {
        episodes.push({tick:b.tick,title:'Reserve drop',detail:`${a.reserve.toFixed(0)}% → ${b.reserve.toFixed(0)}%`,kind:'physiology'});
      }
      if (Number.isFinite(a.resource) && Number.isFinite(b.resource) && a.resource - b.resource >= .08) {
        episodes.push({tick:b.tick,title:'Approach interval',detail:`resource Δ -${(a.resource-b.resource).toFixed(2)} m`,kind:'interaction'});
      }
      if (Number.isFinite(a.displacement) && Number.isFinite(b.displacement) && b.displacement - a.displacement >= .05) {
        episodes.push({tick:b.tick,title:'Net displacement',detail:`+${(b.displacement-a.displacement).toFixed(2)} m`,kind:'motion'});
      }
      if (a.motorOrigin !== b.motorOrigin && b.motorOrigin && b.motorOrigin !== '—') {
        episodes.push({tick:b.tick,title:'Motor source changed',detail:`${a.motorOrigin} → ${b.motorOrigin}`,kind:'control'});
      }
    }
    return episodes.slice(-12).reverse();
  }

  renderHistory() {
    if (!this.overlayContent) return;
    const reserve = this.history.map(x=>x.reserve).filter(Number.isFinite);
    const displacement = this.history.map(x=>x.displacement).filter(Number.isFinite);
    const resource = this.history.map(x=>x.resource).filter(Number.isFinite);
    const contacts = this.history.map(x=>x.contacts).filter(Number.isFinite);
    const episodes = this.deriveEpisodes();
    this.overlayContent.innerHTML = this.viewHeader('Physical history', 'Bounded observer-side history for this browser session.') +
      `<div class="body-chart-grid">${this.chart('Energy / reserve',reserve,'mint')}${this.chart('Net displacement',displacement)}${this.chart('Resource distance',resource,'violet')}${this.chart('Ground contacts',contacts,'amber')}</div>` +
      `<div class="body-section"><div class="body-section-title">Physical episodes</div><div class="body-episodes">${episodes.length ? episodes.map(e=>`<div class="body-episode"><div class="body-episode-tick">t${e.tick}</div><div><div class="body-episode-title">${e.title}</div><div class="body-episode-detail">${escapeHtml(e.detail)}</div></div><span class="body-chip">${e.kind}</span></div>`).join('') : '<div class="body-inspector-sub">No bounded episode detected yet.</div>'}</div></div>`;
    this.panel.innerHTML = this.head('Body · History', 'Physical episodes', 'Observer-derived changes over the current attached session.') +
      `<div class="body-section"><div class="body-row"><span>Captured frames</span><strong>${this.history.length}</strong></div><div class="body-row"><span>Episodes</span><strong>${episodes.length}</strong></div></div>`;
  }

  dispose() {
    this.clearSegmentHighlight();
    this.nav?.remove();
    this.overlay?.remove();
    this.nav = null;
    this.overlay = null;
    this.overlayContent = null;
    this.panel = null;
    this.history = [];
  }
}
