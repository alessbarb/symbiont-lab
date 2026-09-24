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
  contact_count: 'Ground contacts',
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

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
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
    this.style = null;
    this.renderQueued = false;
  }

  mount(root, canvasWrap, panel) {
    this.injectStyle();
    this.nav = node('div', 'body-tabs');
    for (const [id, label] of TABS) {
      const b = node('button', 'body-tab', label);
      b.type = 'button';
      b.dataset.tab = id;
      b.addEventListener('click', () => this.setTab(id));
      this.nav.appendChild(b);
    }
    root.appendChild(this.nav);

    this.overlay = node('div', 'body-data-overlay');
    this.overlayContent = node('div', 'body-data-overlay-content');
    this.overlay.appendChild(this.overlayContent);
    canvasWrap.appendChild(this.overlay);

    this.panel = panel;
    panel.classList.add('body-inspector');
    this.setTab('overview');
  }

  injectStyle() {
    if (document.getElementById('body-workspace-style')) return;
    const s = document.createElement('style');
    s.id = 'body-workspace-style';
    s.textContent = `
      .body-tabs{grid-column:1/-1;grid-row:1;display:flex;align-items:end;gap:2px;height:40px;padding:0 12px;background:#0d1a25;border-bottom:1px solid var(--line,#243342);z-index:9}
      .body-tab{height:40px;padding:0 15px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--muted,#8293a4);font:12px var(--mono,monospace);cursor:pointer}
      .body-tab:hover{color:var(--text,#e6edf3)}
      .body-tab.active{color:var(--cyan,#56d6ff);border-bottom-color:var(--cyan,#56d6ff)}
      .body-inspector{grid-column:2;grid-row:2;background:linear-gradient(180deg,rgba(14,25,37,.97),rgba(8,17,25,.99));border-left:1px solid var(--line,#243342);padding:14px;overflow:auto;min-width:0;font-family:var(--mono,monospace);color:var(--text,#e0e6eb)}
      .body-inspector-head{margin-bottom:14px;padding-bottom:11px;border-bottom:1px solid var(--line,#243342)}
      .body-inspector-kicker{font-size:9px;letter-spacing:.13em;text-transform:uppercase;color:var(--cyan,#56d6ff)}
      .body-inspector-title{font:600 15px/1.3 system-ui,sans-serif;margin-top:4px}
      .body-inspector-sub{font:11px/1.45 var(--mono,monospace);color:var(--muted,#8293a4);margin-top:4px}
      .body-section{margin:14px 0 0}
      .body-section-title{font-size:9px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted,#8293a4);margin-bottom:7px}
      .body-row{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid rgba(118,145,167,.09);font-size:11px}
      .body-row span:first-child{color:var(--muted,#8293a4)}
      .body-row strong{font-weight:500;text-align:right}
      .body-mini-chart{margin-top:7px;height:46px;color:var(--mint,#61e6b4)}
      .body-spark{display:block;width:100%;height:100%}
      .body-empty-line{display:flex;align-items:center;height:100%;font-size:10px;color:var(--muted,#8293a4)}
      .body-segment-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px}
      .body-segment{border:1px solid rgba(118,145,167,.18);background:rgba(255,255,255,.025);color:var(--muted,#8293a4);border-radius:6px;padding:7px;text-align:left;font:10px var(--mono,monospace);cursor:pointer}
      .body-segment.active{border-color:var(--cyan,#56d6ff);color:var(--cyan,#56d6ff);background:rgba(86,214,255,.08)}
      .body-data-overlay{position:absolute;inset:0;z-index:5;display:none;overflow:auto;background:#07111a;padding:18px}
      .body-data-overlay.visible{display:block}
      .body-data-overlay-content{max-width:1280px;margin:0 auto}
      .body-view-head{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:14px}
      .body-view-title{font:600 18px system-ui,sans-serif;color:var(--text,#e6edf3)}
      .body-view-sub{font:11px/1.45 var(--mono,monospace);color:var(--muted,#8293a4);margin-top:4px}
      .body-card-grid{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:8px;margin:10px 0 14px}
      .body-metric-card,.body-chart-card,.body-episode{border:1px solid rgba(118,145,167,.17);background:rgba(12,27,40,.72);border-radius:8px}
      .body-metric-card{padding:11px 12px}
      .body-metric-label{font:9px var(--mono,monospace);text-transform:uppercase;letter-spacing:.08em;color:var(--muted,#8293a4)}
      .body-metric-value{font:600 18px/1.2 system-ui,sans-serif;margin-top:4px}
      .body-chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
      .body-chart-card{padding:11px 12px;min-height:125px}
      .body-chart-title{font:600 11px system-ui,sans-serif;margin-bottom:7px}
      .body-chart-wrap{height:78px;color:var(--cyan,#56d6ff)}
      .body-chart-card.mint .body-chart-wrap{color:var(--mint,#61e6b4)}
      .body-chart-card.amber .body-chart-wrap{color:var(--amber,#f5c45b)}
      .body-chart-card.violet .body-chart-wrap{color:var(--violet,#a58bff)}
      .body-episodes{display:grid;gap:6px;margin-top:8px}
      .body-episode{display:grid;grid-template-columns:110px 1fr auto;gap:12px;padding:10px 12px;align-items:center}
      .body-episode-tick{font:10px var(--mono,monospace);color:var(--cyan,#56d6ff)}
      .body-episode-title{font:600 11px system-ui,sans-serif}
      .body-episode-detail{font:10px var(--mono,monospace);color:var(--muted,#8293a4);margin-top:2px}
      .body-chip{display:inline-flex;padding:3px 6px;border:1px solid rgba(118,145,167,.18);border-radius:999px;color:var(--muted,#8293a4);font-size:9px}
      @media(max-width:1100px){.body-card-grid{grid-template-columns:repeat(2,1fr)}.body-chart-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(s);
    this.style = s;
  }

  setTab(tab) {
    if (!TABS.some(([id]) => id === tab)) return;
    this.activeTab = tab;
    this.nav?.querySelectorAll('.body-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    const dataView = tab === 'physiology' || tab === 'history';
    this.overlay?.classList.toggle('visible', dataView);
    if (tab !== 'anatomy') this.clearSegmentHighlight();
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
      this.rows(['motor_activity','active_joints','active_effectors','contact_count','distance_travelled','displacement']) +
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
    this.panel.innerHTML = this.head('Body · Anatomy', 'Inspectable morphology', 'Select a body region to inspect its current physical expression.') +
      `<div class="body-section"><div class="body-section-title">Body regions</div><div class="body-segment-grid">${names.map(name => `<button class="body-segment ${selected===name?'active':''}" data-segment="${escapeHtml(name)}">${escapeHtml(name.replaceAll('_',' '))}</button>`).join('')}</div></div>` +
      `<div class="body-section"><div class="body-section-title">Selection</div><div class="body-row"><span>Region</span><strong>${escapeHtml(selected ?? 'none')}</strong></div><div class="body-row"><span>Associated joints</span><strong>${joints.length}</strong></div><div class="body-row"><span>Currently active</span><strong>${active}</strong></div></div>`;
    this.panel.querySelectorAll('[data-segment]').forEach(b => b.addEventListener('click', () => this.selectSegment(b.dataset.segment)));
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
    this.panel.innerHTML = this.head('Body · Motion', 'Movement evidence', 'Distinguish motion, displacement and emerging coordination.') +
      '<div class="body-section"><div class="body-section-title">Current motion</div>' +
      this.rows(['motor_activity','active_joints','contact_count','distance_travelled','displacement','locomotion_efficiency']) +
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
      this.rows(['contact_count','active_effectors','displacement']) +
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
    const contacts = this.history.map(x=>x.contacts).filter(Number.isFinite);
    const active = this.history.map(x=>x.activeJoints).filter(Number.isFinite);
    const progress = this.history.map(x=>x.progress).filter(Number.isFinite);
    this.overlayContent.innerHTML = this.viewHeader('Physiology', 'How physical activity, contact and reserve evolve together.') +
      `<div class="body-card-grid">${metricCard('Reserve',this.m('metabolic_reserve'))}${metricCard('Reserve trend',this.m('reserve_trend'))}${metricCard('Motor activity',this.m('motor_activity'))}${metricCard('Ground contacts',this.m('contact_count'))}</div>` +
      `<div class="body-chart-grid">${this.chart('Metabolic reserve',reserve,'mint')}${this.chart('Active joints',active)}${this.chart('Ground contacts',contacts,'amber')}${this.chart('Resource progress',progress,'violet')}</div>`;
    this.panel.innerHTML = this.head('Body · Physiology', 'Physical cost and state', 'Live evidence from the body, without introducing goals or reward.') +
      this.rows(['alive','metabolic_reserve','reserve_trend','motor_activity','active_joints','contact_count']);
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
    this.style?.remove();
    this.nav = null;
    this.overlay = null;
    this.overlayContent = null;
    this.panel = null;
    this.history = [];
  }
}
