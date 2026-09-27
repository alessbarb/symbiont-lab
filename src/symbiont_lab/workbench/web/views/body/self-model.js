import { escapeHtml } from '../shared/dom.js';

const SELF_TABS = [
  ['overview', 'Overview'],
  ['body-schema', 'Body Schema'],
  ['agency', 'Agency'],
  ['capabilities', 'Capabilities'],
  ['affordances', 'Affordances'],
  ['embodiment', 'Embodiment'],
  ['history', 'History'],
];

function finite(value, fallback = null) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function ratio(value) {
  const n = finite(value, 0);
  return Math.max(0, Math.min(1, n));
}

function mean(values) {
  const xs = values.map((value) => finite(value)).filter((value) => value !== null);
  if (!xs.length) return 0;
  return xs.reduce((total, value) => total + value, 0) / xs.length;
}

function pct(value) {
  const n = finite(value);
  return n === null ? '—' : `${(ratio(n) * 100).toFixed(0)}%`;
}

function shortId(value, max = 24) {
  const text = String(value ?? '—');
  if (text.length <= max) return text;
  return `${text.slice(0, 11)}…${text.slice(-9)}`;
}

function row(label, value, cls = '') {
  return `<div class="self-row ${cls}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value ?? '—')}</strong></div>`;
}

function chip(text, tone = '') {
  return `<span class="self-chip ${tone}">${escapeHtml(text)}</span>`;
}

function confidenceClass(value) {
  const n = ratio(value);
  if (n >= .75) return 'strong';
  if (n >= .45) return 'probable';
  if (n > 0) return 'tentative';
  return 'unknown';
}

function classRatio(value, classes = 16) {
  const n = finite(value, 0);
  return Math.max(0, Math.min(1, n / Math.max(1, classes - 1)));
}

function svgEscape(value) {
  return escapeHtml(String(value ?? '')).replaceAll("'", '&#39;');
}

function layoutNodes(nodes, width = 820, height = 420) {
  const groups = new Map();
  for (const node of nodes) {
    const key = node.group ?? 'other';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  }
  const columns = [...groups.entries()];
  const positioned = new Map();
  const colGap = width / Math.max(1, columns.length);
  columns.forEach(([group, items], ci) => {
    const x = colGap * (ci + .5);
    const gap = height / Math.max(1, items.length + 1);
    items.forEach((item, i) => {
      positioned.set(item.id, { ...item, x, y: gap * (i + 1), group });
    });
  });
  return positioned;
}

function graphSvg(nodes, edges, { width = 820, height = 420, empty = 'No learned structure yet.' } = {}) {
  if (!nodes.length) return `<div class="self-empty">${escapeHtml(empty)}</div>`;
  const pos = layoutNodes(nodes, width, height);
  const lines = edges.map((edge) => {
    const a = pos.get(edge.source);
    const b = pos.get(edge.target);
    if (!a || !b) return '';
    const strength = ratio(edge.strength ?? .4);
    return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="self-graph-edge" style="--edge-opacity:${(.18 + strength * .7).toFixed(2)}"/>`;
  }).join('');
  const circles = [...pos.values()].map((n) => {
    const conf = ratio(n.confidence ?? .5);
    const r = 13 + conf * 8;
    return `<g class="self-graph-node ${escapeHtml(n.group)}" data-self-id="${svgEscape(n.id)}">
      <circle cx="${n.x}" cy="${n.y}" r="${r.toFixed(1)}" style="--node-confidence:${conf.toFixed(2)}"/>
      <text x="${n.x}" y="${n.y + r + 15}" text-anchor="middle">${svgEscape(shortId(n.label ?? n.id, 20))}</text>
    </g>`;
  }).join('');
  return `<svg class="self-graph" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-label="Learned self-model graph">
    <g>${lines}</g><g>${circles}</g>
  </svg>`;
}

function bodySchemaNodes(snapshot) {
  const schema = snapshot?.body_schema ?? {};
  const parts = Array.isArray(schema.parts) ? schema.parts : [];
  return parts.map((part) => ({
    id: String(part.part_id),
    label: String(part.part_id),
    group: part.kind === 'cognitive_region' ? 'region' : 'sense',
    confidence: classRatio(part.existence_confidence_class),
    data: part,
  }));
}

function bodySchemaEdges(snapshot) {
  const deps = Array.isArray(snapshot?.body_schema?.dependencies)
    ? snapshot.body_schema.dependencies : [];
  return deps.map((dep) => ({
    source: String(dep.source_id),
    target: String(dep.target_id),
    strength: classRatio(dep.confidence_class),
    relation: dep.relation,
  }));
}

function capabilityNodes(snapshot) {
  const dims = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions : [];
  const comps = Array.isArray(snapshot?.motor_competences) ? snapshot.motor_competences : [];
  const effects = Array.isArray(snapshot?.effects) ? snapshot.effects : [];
  return [
    ...dims.map((d) => ({ id:String(d.dimension_id), label:String(d.dimension_id), group:'dimension', confidence:ratio(d.confidence), data:d })),
    ...comps.map((c) => ({ id:String(c.competence_id), label:String(c.competence_id), group:'competence', confidence:ratio(c.reproducibility ?? c.controllability), data:c })),
    ...effects.map((e) => ({ id:String(e.effect_id), label:String(e.effect_id), group:'effect', confidence:ratio(e.confidence), data:e })),
  ];
}

function capabilityEdges(snapshot) {
  const edges = [];
  for (const c of Array.isArray(snapshot?.motor_competences) ? snapshot.motor_competences : []) {
    if (c.effect_id) edges.push({ source:String(c.competence_id), target:String(c.effect_id), strength:ratio(c.controllability ?? c.reproducibility) });
  }
  return edges;
}

function affordances(snapshot) {
  const comps = Array.isArray(snapshot?.motor_competences) ? snapshot.motor_competences : [];
  const effects = new Map((Array.isArray(snapshot?.effects) ? snapshot.effects : []).map((e) => [String(e.effect_id), e]));
  const bindings = Array.isArray(snapshot?.embodiment?.bindings) ? snapshot.embodiment.bindings : [];
  const bindingByCompetence = new Map(bindings.map((b) => [String(b.competence_id), b]));
  const controls = Array.isArray(snapshot?.controllability_estimates) ? snapshot.controllability_estimates : [];
  const controlByPair = new Map(controls.map((c) => [`${c.competence_id}|${c.effect_id}`, c]));
  const runtimeCompetences = Array.isArray(snapshot?.sensorimotor?.v2?.competences)
    ? snapshot.sensorimotor.v2.competences : [];
  const executableByCompetence = new Map(
    runtimeCompetences.map((item) => [String(item.competence_id), Boolean(item.executable)])
  );
  const result = [];
  for (const c of comps) {
    if (!c.effect_id) continue;
    const binding = bindingByCompetence.get(String(c.competence_id));
    if (!binding) continue;
    const hasCanonicalExecutability = executableByCompetence.has(String(c.competence_id));
    if (hasCanonicalExecutability && !executableByCompetence.get(String(c.competence_id))) continue;
    const control = controlByPair.get(`${c.competence_id}|${c.effect_id}`);
    result.push({
      competence_id:String(c.competence_id),
      effect_id:String(c.effect_id),
      prediction_confidence:ratio(effects.get(String(c.effect_id))?.confidence),
      controllability:ratio(control?.confidence ?? c.controllability),
      reliability:ratio(control?.reliability ?? c.reproducibility),
      binding,
    });
  }
  return result.sort((a,b) => (b.controllability + b.reliability) - (a.controllability + a.reliability));
}

function selfSummary(snapshot) {
  const schema = snapshot?.body_schema ?? {};
  const parts = Array.isArray(schema.parts) ? schema.parts : [];
  const deps = Array.isArray(schema.dependencies) ? schema.dependencies : [];
  const boundary = snapshot?.body_schema_boundary ?? {};
  const dims = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions : [];
  const comps = Array.isArray(snapshot?.motor_competences) ? snapshot.motor_competences : [];
  const effects = Array.isArray(snapshot?.effects) ? snapshot.effects : [];
  const agencies = Array.isArray(snapshot?.agency_estimates) ? snapshot.agency_estimates : [];
  const bindings = Array.isArray(snapshot?.embodiment?.bindings) ? snapshot.embodiment.bindings : [];
  const aff = affordances(snapshot);
  return {
    schemaState:String(schema.state ?? 'undeveloped'),
    parts:parts.length,
    senses:parts.filter((x) => x.kind === 'sense').length,
    regions:parts.filter((x) => x.kind === 'cognitive_region').length,
    dependencies:deps.length,
    boundaryConfidence:ratio(boundary.confidence),
    boundaryRevisions:finite(boundary.revision_count, 0),
    dimensions:dims.length,
    competences:comps.length,
    effects:effects.length,
    agencies:agencies.length,
    agencyMean:ratio(mean(agencies.map((x) => x.confidence))),
    capabilityMean:ratio(mean(comps.map((x) => x.controllability ?? x.reproducibility))),
    bindings:bindings.length,
    bindingMean:ratio(mean(bindings.map((x) => x.controllability ?? x.reliability))),
    affordances:aff.length,
    affordanceMean:ratio(mean(aff.map((x) => (x.controllability + x.reliability) / 2))),
  };
}

export class SelfModelWorkspace {
  constructor() {
    this.snapshot = {};
    this.activeTab = 'overview';
    this.selectedId = null;
    this.history = [];
    this.maxHistory = 180;
    this.lastSignature = '';
  }

  update(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') return;
    this.snapshot = snapshot;
    const tick = finite(snapshot.tick);
    const summary = selfSummary(snapshot);
    const signature = JSON.stringify([
      summary.schemaState, summary.parts, summary.dependencies, summary.dimensions,
      summary.competences, summary.effects, summary.agencies, summary.bindings,
      summary.affordances, summary.boundaryRevisions,
    ]);
    if (tick !== null && signature !== this.lastSignature) {
      this.history.push({ tick, ...summary });
      if (this.history.length > this.maxHistory) this.history.shift();
      this.lastSignature = signature;
    }
  }

  setTab(tab) {
    if (SELF_TABS.some(([id]) => id === tab)) this.activeTab = tab;
  }

  render(overlay, panel) {
    if (!overlay || !panel) return;
    overlay.innerHTML = this.renderOverlay();
    panel.innerHTML = this.renderInspector();
    overlay.querySelectorAll('[data-self-tab]').forEach((button) => {
      button.addEventListener('click', () => {
        this.setTab(button.dataset.selfTab);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-id]').forEach((node) => {
      node.addEventListener('click', () => {
        this.selectedId = node.dataset.selfId;
        panel.innerHTML = this.renderInspector();
      });
    });
  }

  shell(body) {
    const tabs = SELF_TABS.map(([id,label]) =>
      `<button type="button" class="self-subtab ${this.activeTab===id?'active':''}" data-self-tab="${id}">${label}</button>`
    ).join('');
    return `<div class="self-model-view">
      <div class="self-model-head">
        <div><div class="body-view-title">Self-Model</div>
        <div class="body-view-sub">Organism-owned learned self-knowledge. Passive observer projection; never fed back.</div></div>
        <span class="body-chip">organism knowledge · live</span>
      </div>
      <div class="self-subtabs" role="tablist">${tabs}</div>
      ${body}
    </div>`;
  }

  renderOverlay() {
    switch (this.activeTab) {
      case 'body-schema': return this.shell(this.bodySchema());
      case 'agency': return this.shell(this.agency());
      case 'capabilities': return this.shell(this.capabilities());
      case 'affordances': return this.shell(this.affordanceView());
      case 'embodiment': return this.shell(this.embodiment());
      case 'history': return this.shell(this.historyView());
      default: return this.shell(this.overview());
    }
  }

  overview() {
    const s = selfSummary(this.snapshot);
    const nodes = [
      {id:'self.body',label:'Body schema',group:'sense',confidence:s.boundaryConfidence},
      {id:'self.agency',label:'Agency',group:'agency',confidence:s.agencyMean},
      {id:'self.capability',label:'Capabilities',group:'competence',confidence:s.capabilityMean},
      {id:'self.affordance',label:'Affordances',group:'effect',confidence:s.affordanceMean},
      {id:'self.embodiment',label:'Embodiment',group:'dimension',confidence:s.bindingMean},
    ];
    const edges = [
      {source:'self.body',target:'self.agency',strength:.6},
      {source:'self.agency',target:'self.capability',strength:.7},
      {source:'self.capability',target:'self.affordance',strength:.7},
      {source:'self.embodiment',target:'self.affordance',strength:.65},
    ];
    return `<div class="self-overview-grid">
      <div class="self-hero-card">
        <div class="self-card-title">Learned self structure</div>
        ${graphSvg(nodes,edges,{height:330})}
      </div>
      <div class="self-summary-cards">
        <div class="self-stat"><span>Body schema</span><strong>${escapeHtml(s.schemaState)}</strong><small>${s.parts} learned parts · ${s.dependencies} relations</small></div>
        <div class="self-stat"><span>Agency</span><strong>${s.agencies}</strong><small>${pct(s.boundaryConfidence)} body-boundary confidence</small></div>
        <div class="self-stat"><span>Capabilities</span><strong>${s.competences}</strong><small>${s.dimensions} action dimensions · ${s.effects} effects</small></div>
        <div class="self-stat"><span>Current affordances</span><strong>${s.affordances}</strong><small>${s.bindings} embodiment bindings</small></div>
      </div>
    </div>
    ${this.perceptualSelfModel()}
    <div class="self-boundary-note">Self-Model is not physical ground truth. Opaque organism-owned relations are shown without anatomical labels.</div>`;
  }

  perceptualSelfModel() {
    const entries = Object.entries(
      this.snapshot?.self_model && typeof this.snapshot.self_model === 'object'
        ? this.snapshot.self_model : {}
    );
    if (!entries.length) {
      return '<div class="self-list-card self-perceptual"><div class="self-card-title">Perceptual apparatus self-estimates</div><div class="self-empty">No established per-sense self-estimate yet.</div></div>';
    }
    const rows = entries.slice(0,48).map(([senseId, state]) => {
      const confidence = classRatio(state?.confidence_class);
      const health = classRatio(state?.health_class);
      const maturity = classRatio(state?.maturity_class, 8);
      return `<div class="self-perceptual-row">
        <code>${escapeHtml(shortId(senseId,30))}</code>
        <div class="self-bars">${this.bar('confidence',confidence)}${this.bar('health',health)}${this.bar('maturity',maturity)}</div>
      </div>`;
    }).join('');
    return `<div class="self-list-card self-perceptual"><div class="self-card-title">Perceptual apparatus self-estimates</div>
      <div class="body-inspector-sub">Existing organism self-model of per-sense cost, health, confidence and maturity.</div>
      <div class="self-perceptual-list">${rows}</div></div>`;
  }

  bodySchema() {
    const schema = this.snapshot?.body_schema ?? {};
    const boundary = this.snapshot?.body_schema_boundary ?? {};
    const nodes = bodySchemaNodes(this.snapshot);
    const edges = bodySchemaEdges(this.snapshot);
    return `<div class="self-lens-toolbar">
      ${chip(`state: ${schema.state ?? 'undeveloped'}`, confidenceClass(boundary.confidence))}
      ${chip(`boundary ${pct(boundary.confidence)}`)}
      ${chip(`${nodes.length} parts`)}
      ${chip(`${edges.length} dependencies`)}
    </div>
    <div class="self-hero-card"><div class="self-card-title">Learned functional body topology</div>
      ${graphSvg(nodes,edges,{empty:'No BodySchema parts have emerged yet.'})}
    </div>
    <div class="self-three-cols">
      <div class="self-list-card"><div class="self-card-title">Self-caused channels</div>${this.idList(boundary.self_caused_channels)}</div>
      <div class="self-list-card"><div class="self-card-title">Somatic-correlated</div>${this.idList(boundary.somatic_correlated_channels)}</div>
      <div class="self-list-card"><div class="self-card-title">External / unowned</div>${this.idList(boundary.external_channels)}</div>
    </div>`;
  }

  agency() {
    const agencies = Array.isArray(this.snapshot?.agency_estimates) ? [...this.snapshot.agency_estimates] : [];
    agencies.sort((a,b) => finite(b.confidence,0)-finite(a.confidence,0));
    const controls = new Map((Array.isArray(this.snapshot?.controllability_estimates) ? this.snapshot.controllability_estimates : [])
      .map((x)=>[`${x.competence_id}|${x.effect_id}`,x]));
    const cards = agencies.map((a) => {
      const c = controls.get(`${a.competence_id}|${a.effect_id}`) ?? {};
      return `<button type="button" class="self-relation-card" data-self-id="${escapeHtml(`agency|${a.competence_id}|${a.effect_id}`)}">
        <div class="self-relation-top"><strong>${escapeHtml(shortId(a.competence_id))}</strong>${chip(pct(a.confidence),confidenceClass(a.confidence))}</div>
        <div class="self-arrow">→</div><div class="self-effect">${escapeHtml(shortId(a.effect_id))}</div>
        <div class="self-bars">
          ${this.bar('agency',a.confidence)}
          ${this.bar('specificity',a.causal_specificity)}
          ${this.bar('controllability',c.confidence)}
          ${this.bar('reliability',c.reliability)}
        </div>
      </button>`;
    }).join('');
    return `<div class="self-lens-toolbar">${chip(`${agencies.length} agentic relations`)}${chip('prediction match ≠ agency')}</div>
      <div class="self-relation-grid">${cards || '<div class="self-empty">No agentic relation has enough evidence yet.</div>'}</div>`;
  }

  capabilities() {
    const nodes = capabilityNodes(this.snapshot);
    const edges = capabilityEdges(this.snapshot);
    const dims = nodes.filter((x)=>x.group==='dimension').length;
    const comps = nodes.filter((x)=>x.group==='competence').length;
    const effects = nodes.filter((x)=>x.group==='effect').length;
    return `<div class="self-lens-toolbar">${chip(`${dims} dimensions`)}${chip(`${comps} competences`)}${chip(`${effects} effects`)}</div>
      <div class="self-hero-card"><div class="self-card-title">I can: learned action → consequence structure</div>
      ${graphSvg(nodes,edges,{empty:'No learned motor capability structure yet.'})}</div>`;
  }

  affordanceView() {
    const items = affordances(this.snapshot);
    const cards = items.map((a) => `<button type="button" class="self-affordance-card" data-self-id="${escapeHtml(`affordance|${a.competence_id}|${a.effect_id}`)}">
      <div class="self-affordance-label">CURRENTLY AVAILABLE</div>
      <strong>${escapeHtml(shortId(a.competence_id))}</strong>
      <div class="self-arrow">→</div>
      <span>${escapeHtml(shortId(a.effect_id))}</span>
      <div class="self-bars">${this.bar('control',a.controllability)}${this.bar('reliability',a.reliability)}${this.bar('effect confidence',a.prediction_confidence)}</div>
    </button>`).join('');
    return `<div class="self-lens-toolbar">${chip(`${items.length} current affordances`)}${chip('derived · ephemeral')}</div>
      <div class="self-boundary-note">Affordances are observer-side derivations from organism-owned competence/effect knowledge plus current execution bindings. They are not stored as facts and do not authorize action.</div>
      <div class="self-relation-grid">${cards || '<div class="self-empty">No currently executable learned affordances.</div>'}</div>`;
  }

  embodiment() {
    const e = this.snapshot?.embodiment ?? {};
    const bindings = Array.isArray(e.bindings) ? e.bindings : [];
    const rows = bindings.map((b) => `<div class="self-binding">
      <strong>${escapeHtml(shortId(b.competence_id))}</strong>
      <span>${escapeHtml(shortId(b.effect_id ?? 'effect unknown'))}</span>
      ${chip(pct(b.controllability ?? b.reliability),confidenceClass(b.controllability ?? b.reliability))}
    </div>`).join('');
    return `<div class="self-two-cols">
      <div class="self-list-card"><div class="self-card-title">Current embodiment</div>
        ${row('Embodiment',shortId(e.embodiment_id ?? e.id))}
        ${row('Body',shortId(e.body_id))}
        ${row('Epoch',String(e.epoch ?? '—'))}
        ${row('State',String(e.state ?? '—'))}
        ${row('Reacclimating',String(Boolean(e.reacclimating)))}
        ${row('Bindings',String(bindings.length))}
      </div>
      <div class="self-list-card"><div class="self-card-title">Current execution bindings</div>
        <div class="self-binding-list">${rows || '<div class="self-empty">No current competence binding.</div>'}</div>
      </div>
    </div>
    <div class="self-boundary-note">Durable competence knowledge and current-body executability remain separate. A historical competence is not assumed executable after re-embodiment.</div>`;
  }

  historyView() {
    const items = [...this.history].reverse();
    const rows = items.map((h) => `<div class="self-history-row">
      <span>t${h.tick}</span>
      <strong>${escapeHtml(h.schemaState)}</strong>
      <span>${h.parts} parts</span><span>${h.agencies} agency</span>
      <span>${h.competences} competences</span><span>${h.affordances} affordances</span>
    </div>`).join('');
    return `<div class="self-boundary-note">Bounded observer history records only changes in the passive Self-Model projection during this attached browser session.</div>
      <div class="self-history-list">${rows || '<div class="self-empty">No self-model change observed yet.</div>'}</div>`;
  }

  idList(values) {
    const items = Array.isArray(values) ? values : [];
    return items.length
      ? `<div class="self-id-list">${items.slice(0,32).map((x)=>`<code>${escapeHtml(shortId(x,30))}</code>`).join('')}</div>`
      : '<div class="self-empty">none</div>';
  }

  bar(label, value) {
    const width = Math.round(ratio(value)*100);
    return `<div class="self-bar"><span>${escapeHtml(label)}</span><div><i style="width:${width}%"></i></div><strong>${width}%</strong></div>`;
  }

  selectedRecord() {
    const id = this.selectedId;
    if (!id) return null;
    if (id.startsWith('agency|')) {
      const [, competenceId, effectId] = id.split('|');
      const item = (Array.isArray(this.snapshot?.agency_estimates) ? this.snapshot.agency_estimates : [])
        .find((candidate) => String(candidate?.competence_id) === competenceId && String(candidate?.effect_id) === effectId);
      if (item) return { kind: 'agency relation', item, displayId: `${competenceId} → ${effectId}` };
    }
    if (id.startsWith('affordance|')) {
      const [, competenceId, effectId] = id.split('|');
      const item = affordances(this.snapshot)
        .find((candidate) => candidate.competence_id === competenceId && candidate.effect_id === effectId);
      if (item) return { kind: 'current affordance', item, displayId: `${competenceId} → ${effectId}` };
    }
    const sources = [
      ['body part', this.snapshot?.body_schema?.parts, 'part_id'],
      ['action dimension', this.snapshot?.action_dimensions, 'dimension_id'],
      ['motor competence', this.snapshot?.motor_competences, 'competence_id'],
      ['effect', this.snapshot?.effects, 'effect_id'],
      ['agency relation', this.snapshot?.agency_estimates, 'competence_id'],
      ['controllability relation', this.snapshot?.controllability_estimates, 'competence_id'],
      ['embodiment binding', this.snapshot?.embodiment?.bindings, 'competence_id'],
    ];
    for (const [kind, items, key] of sources) {
      if (!Array.isArray(items)) continue;
      const item = items.find((candidate) => String(candidate?.[key]) === id);
      if (item) return { kind, item };
    }
    const currentAffordance = affordances(this.snapshot).find((item) => item.competence_id === id);
    if (currentAffordance) return { kind: 'current affordance', item: currentAffordance };
    return null;
  }

  selectedInspector() {
    if (!this.selectedId) return '';
    const selected = this.selectedRecord();
    if (!selected) {
      return `<div class="body-section"><div class="body-section-title">Selection</div>
        ${row('ID',shortId(this.selectedId,34))}
        <div class="body-inspector-sub">No additional canonical record is available for this projected node.</div></div>`;
    }
    const entries = Object.entries(selected.item ?? {})
      .filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
      .slice(0, 12)
      .map(([key, value]) => row(key.replaceAll('_',' '), typeof value === 'number' ? String(Number(value.toFixed?.(4) ?? value)) : String(value)))
      .join('');
    const arrays = Object.entries(selected.item ?? {})
      .filter(([, value]) => Array.isArray(value) && value.length)
      .slice(0, 4)
      .map(([key, value]) => `<div class="self-selected-array"><span>${escapeHtml(key.replaceAll('_',' '))}</span>${value.slice(0,8).map((x)=>`<code>${escapeHtml(shortId(x,28))}</code>`).join('')}</div>`)
      .join('');
    return `<div class="body-section"><div class="body-section-title">Selection · ${escapeHtml(selected.kind)}</div>
      ${row('ID',shortId(selected.displayId ?? this.selectedId,34))}
      ${entries}
      ${arrays}
      <div class="body-inspector-sub">Read-only organism evidence. Selection and observer labels never feed back into Symbiont.</div>
    </div>`;
  }

  renderInspector() {
    const s = selfSummary(this.snapshot);
    const executive = this.snapshot?.executive_state ?? {};
    const selected = this.selectedInspector();
    return `<div class="body-inspector-head">
      <div class="body-inspector-kicker">SELF-MODEL</div>
      <div class="body-inspector-title">Learned model of self</div>
      <div class="body-inspector-sub">What the organism has inferred about its own structure, agency and capabilities.</div>
    </div>
    <div class="body-section"><div class="body-section-title">Structure</div>
      ${row('Schema state',s.schemaState)}
      ${row('Learned parts',String(s.parts))}
      ${row('Dependencies',String(s.dependencies))}
      ${row('Boundary confidence',pct(s.boundaryConfidence))}
      ${row('Boundary revisions',String(s.boundaryRevisions))}
    </div>
    <div class="body-section"><div class="body-section-title">Agency & capability</div>
      ${row('Agentic relations',String(s.agencies))}
      ${row('Action dimensions',String(s.dimensions))}
      ${row('Motor competences',String(s.competences))}
      ${row('Known effects',String(s.effects))}
      ${row('Current affordances',String(s.affordances))}
    </div>
    <div class="body-section"><div class="body-section-title">Executive bridge</div>
      ${row('Action source',String(executive.action_source ?? 'none'))}
      ${row('Active commitment',shortId(executive.active_commitment_id))}
      ${row('Active competence',shortId(executive.competence_id))}
      <div class="body-inspector-sub">ActionIntent will appear here when the executive-intention domain is implemented; this view does not fabricate it from motor activity.</div>
    </div>
    ${selected}
    <div class="body-section"><div class="body-section-title">Epistemic boundary</div>
      <div class="body-inspector-sub">Physical anatomy, joint labels and simulator truth are deliberately excluded from the organism-owned Self-Model graph.</div>
    </div>`;
  }
}
