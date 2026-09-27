import { escapeHtml } from '../shared/dom.js';
import {
  captureSelfViewDevelopment,
  renderSelfView,
  renderSelfViewDevelopment,
  selfViewSegmentRecord,
} from './self-view.js';

/*
 * Passive UX projection only.
 * canonical ActionAffordance objects come from AffordanceResolver.
 * canonical ActionIntent is never inferred from motor activity.
 * ActionIntent says what consequence is being attempted; ActionCommitment keeps motor authority.
 */

const SELF_TABS = [
  ['overview', 'Overview'],
  ['self', 'Self'],
  ['agency', 'Agency'],
  ['history', 'History'],
];

const SELF_LENSES = [
  ['self-view', 'Self View'],
  ['body-schema', 'Body Schema'],
  ['embodiment', 'Embodiment'],
];

const AGENCY_LENSES = [
  ['acquisition', 'Acquisition'],
  ['capabilities', 'Capabilities'],
  ['affordances', 'Affordances'],
  ['executive', 'Executive'],
];

function finite(value, fallback = null) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function ratio(value) {
  const n = finite(value, 0);
  return Math.max(0, Math.min(1, n));
}

function pct(value) {
  const n = finite(value);
  return n === null ? '—' : `${(ratio(n) * 100).toFixed(0)}%`;
}

function shortId(value, max = 26) {
  const text = String(value ?? '—');
  if (text.length <= max) return text;
  return `${text.slice(0, 12)}…${text.slice(-9)}`;
}

function row(label, value) {
  return `<div class="self-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value ?? '—')}</strong></div>`;
}

function chip(text, tone = '') {
  return `<span class="self-chip ${tone}">${escapeHtml(text)}</span>`;
}

function classRatio(value, classes = 16) {
  const n = finite(value, 0);
  return Math.max(0, Math.min(1, n / Math.max(1, classes - 1)));
}

function average(values) {
  const xs = values.map((value) => finite(value)).filter((value) => value !== null);
  if (!xs.length) return 0;
  return xs.reduce((sum, value) => sum + value, 0) / xs.length;
}

function affordances(snapshot) {
  return (Array.isArray(snapshot?.affordances) ? snapshot.affordances : [])
    .map((item) => ({
      ...item,
      competence_id: String(item.competence_id ?? ''),
      effect_id: String(item.anticipated_effect_id ?? item.effect_id ?? ''),
      prediction_confidence: ratio(item.prediction_confidence),
      controllability: ratio(item.controllability),
      executability_confidence: ratio(item.executability_confidence),
    }))
    .sort((a, b) =>
      (b.prediction_confidence + b.controllability + b.executability_confidence)
      - (a.prediction_confidence + a.controllability + a.executability_confidence)
    );
}

function summary(snapshot) {
  const schema = snapshot?.body_schema ?? {};
  const parts = Array.isArray(schema.parts) ? schema.parts : [];
  const dependencies = Array.isArray(schema.dependencies) ? schema.dependencies : [];
  const dimensions = Array.isArray(snapshot?.action_dimensions) ? snapshot.action_dimensions : [];
  const competences = Array.isArray(snapshot?.motor_competences) ? snapshot.motor_competences : [];
  const effects = Array.isArray(snapshot?.effects) ? snapshot.effects : [];
  const bindings = Array.isArray(snapshot?.embodiment?.bindings) ? snapshot.embodiment.bindings : [];
  const currentAffordances = affordances(snapshot);
  const acquisition = snapshot?.agency_acquisition ?? {};
  const executive = snapshot?.executive_intention ?? {};
  const active = executive?.active ?? null;
  return {
    schemaState: String(schema.state ?? 'undeveloped'),
    parts: parts.length,
    sensoryParts: parts.filter((part) => part.kind === 'sense').length,
    regions: parts.filter((part) => part.kind === 'cognitive_region').length,
    dependencies: dependencies.length,
    dimensions: dimensions.length,
    agenticDimensions: dimensions.filter((item) => item?.agentic === true).length,
    opportunities: finite(acquisition.physical_motor_opportunities, 0),
    attempts: finite(acquisition.action_attempt_count, 0),
    signatures: finite(acquisition.intervention_signature_count, 0),
    recurringSignatures: finite(acquisition.recurring_intervention_signature_count, 0),
    causalRelations: finite(acquisition.causal_relation_count, 0),
    causalEvidence: finite(acquisition.causal_evidence_count, 0),
    competences: competences.length,
    effects: effects.length,
    affordances: currentAffordances.length,
    bindings: bindings.length,
    intentId: active?.intent_id ?? null,
    intentStatus: active?.status ?? 'none',
    embodimentId: snapshot?.embodiment?.embodiment_id ?? null,
    boundaryConfidence: ratio(snapshot?.body_schema_boundary?.confidence),
    boundaryRevisions: finite(snapshot?.body_schema_boundary?.revision_count, 0),
  };
}

function stage(label, value, detail, tone = '', route = '') {
  const routeAttr = route ? ` data-self-route="${escapeHtml(route)}"` : '';
  return `<button type="button" class="self-stage ${tone}"${routeAttr}>
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(String(value))}</strong>
    <small>${escapeHtml(detail)}</small>
  </button>`;
}

function funnelStep(label, value, detail, state = '') {
  return `<div class="self-funnel-step ${state}">
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(String(value))}</strong>
    <small>${escapeHtml(detail)}</small>
  </div>`;
}

export class SelfModelWorkspace {
  constructor() {
    this.snapshot = {};
    this.activeTab = 'overview';
    this.selfLens = 'self-view';
    this.selfViewMode = 'composite';
    this.selfViewPane = 'composite';
    this.selfViewDevelopment = [];
    this.maxSelfViewFrames = 120;
    this.selfViewDevelopmentIndex = null;
    this.selfViewDevelopmentBodyMode = 'state';
    this.selfViewDevelopmentScale = 'detail';
    this.agencyLens = 'acquisition';
    this.selectedId = null;
    this.events = [];
    this.maxEvents = 80;
    this.lastSummary = null;
  }

  update(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') return;
    this.snapshot = snapshot;
    this.recordEvents();
    this.recordSelfViewDevelopment();
  }

  recordSelfViewDevelopment() {
    const now = performance.now();
    if (this._lastSelfViewCompute && now - this._lastSelfViewCompute < 500) return;
    this._lastSelfViewCompute = now;

    const frame = captureSelfViewDevelopment(this.snapshot);
    if (!frame?.tick) return;
    const previous = this.selfViewDevelopment[this.selfViewDevelopment.length - 1];
    const signature = (candidate) => [
      Math.round((candidate?.aggregate?.coverage ?? 0) * 1000),
      Math.round((candidate?.aggregate?.stability ?? 0) * 1000),
      Math.round((candidate?.aggregate?.agency ?? 0) * 1000),
      candidate?.aggregate?.representedRegions ?? 0,
      candidate?.aggregate?.agenticRegions ?? 0,
    ].join('|');
    const materiallyChanged = !previous || signature(previous) !== signature(frame);
    const cadenceReached = !previous || frame.tick - previous.tick >= 100;
    if (!materiallyChanged && !cadenceReached) return;
    this.selfViewDevelopment.push(frame);
    if (this.selfViewDevelopment.length > this.maxSelfViewFrames) {
      this.selfViewDevelopment.splice(
        0,
        this.selfViewDevelopment.length - this.maxSelfViewFrames
      );
    }
  }

  recordEvents() {
    const tick = finite(this.snapshot?.tick);
    if (tick === null) return;
    const current = summary(this.snapshot);
    const previous = this.lastSummary;
    if (!previous) {
      this.events.push({ tick, kind: 'observe', title: 'Self-Model observation attached', detail: current.schemaState });
      this.lastSummary = current;
      return;
    }
    const push = (kind, title, detail) => {
      const last = this.events[this.events.length - 1];
      if (last?.tick === tick && last?.title === title && last?.detail === detail) return;
      this.events.push({ tick, kind, title, detail });
    };

    if (current.schemaState !== previous.schemaState) {
      push('schema', `Body schema → ${current.schemaState}`, `${current.parts} learned parts`);
    }
    if (current.dimensions > previous.dimensions) {
      push('agency', 'Action dimension discovered', `${previous.dimensions} → ${current.dimensions}`);
    }
    if (current.agenticDimensions > previous.agenticDimensions) {
      push('agency', 'Action dimension became agentic', `${previous.agenticDimensions} → ${current.agenticDimensions}`);
    }
    if (current.competences > previous.competences) {
      push('capability', 'Motor competence established', `${previous.competences} → ${current.competences}`);
    }
    if (current.affordances > previous.affordances) {
      push('affordance', 'Current affordance became available', `${previous.affordances} → ${current.affordances}`);
    } else if (current.affordances < previous.affordances) {
      push('affordance', 'Current affordance no longer available', `${previous.affordances} → ${current.affordances}`);
    }
    if (current.intentId !== previous.intentId || current.intentStatus !== previous.intentStatus) {
      if (current.intentId) {
        push('executive', `Intent ${current.intentStatus}`, shortId(current.intentId, 36));
      } else if (previous.intentId) {
        push('executive', 'Executive intention cleared', `previously ${previous.intentStatus}`);
      }
    }
    if (current.boundaryRevisions > previous.boundaryRevisions) {
      push('schema', 'Body boundary revised', `revision ${current.boundaryRevisions}`);
    }
    if (current.embodimentId && current.embodimentId !== previous.embodimentId) {
      push('embodiment', 'Embodiment changed', shortId(current.embodimentId, 36));
    }

    if (this.events.length > this.maxEvents) {
      this.events.splice(0, this.events.length - this.maxEvents);
    }
    this.lastSummary = current;
  }

  setTab(tab) {
    if (!SELF_TABS.some(([id]) => id === tab)) return;
    this.activeTab = tab;
    this.selectedId = null;
  }

  setLens(group, lens) {
    if (group === 'self' && SELF_LENSES.some(([id]) => id === lens)) this.selfLens = lens;
    if (group === 'agency' && AGENCY_LENSES.some(([id]) => id === lens)) this.agencyLens = lens;
    this.selectedId = null;
  }

  route(route) {
    const [tab, lens] = String(route ?? '').split(':');
    if (!tab) return;
    this.setTab(tab);
    if (lens) this.setLens(tab, lens);
  }

  render(overlay, panel) {
    if (!overlay || !panel) return;
    const root = panel.closest('.body-view-root');
    root?.classList.add('self-model-mode');
    root?.classList.toggle('self-model-inspector-open', Boolean(this.selectedId));

    overlay.innerHTML = this.renderOverlay();
    panel.innerHTML = this.renderInspector();

    overlay.querySelectorAll('[data-self-tab]').forEach((button) => {
      button.addEventListener('click', () => {
        this.setTab(button.dataset.selfTab);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-lens]').forEach((button) => {
      button.addEventListener('click', () => {
        this.setLens(button.dataset.selfLensGroup, button.dataset.selfLens);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-route]').forEach((button) => {
      button.addEventListener('click', () => {
        this.route(button.dataset.selfRoute);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-view-pane]').forEach((button) => {
      button.addEventListener('click', () => {
        this.selfViewPane = button.dataset.selfViewPane || 'composite';
        this.selectedId = null;
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-view-mode]').forEach((button) => {
      button.addEventListener('click', () => {
        this.selfViewMode = button.dataset.selfViewMode || 'composite';
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-body-mode]').forEach((button) => {
      button.addEventListener('click', () => {
        this.selfViewDevelopmentBodyMode = button.dataset.selfDevBodyMode || 'state';
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-scale]').forEach((button) => {
      button.addEventListener('click', () => {
        this.selfViewDevelopmentScale = button.dataset.selfDevScale || 'detail';
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-frame]').forEach((button) => {
      button.addEventListener('click', () => {
        this.selfViewDevelopmentIndex = Number(button.dataset.selfDevFrame);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-index]').forEach((input) => {
      input.addEventListener('input', () => {
        this.selfViewDevelopmentIndex = Number(input.value);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-id]').forEach((node) => {
      node.addEventListener('click', () => {
        this.selectedId = node.dataset.selfId;
        this.render(overlay, panel);
      });
    });
    panel.querySelector('[data-self-clear]')?.addEventListener('click', () => {
      this.selectedId = null;
      this.render(overlay, panel);
    });
  }

  shell(body) {
    const tabs = SELF_TABS.map(([id, label]) =>
      `<button type="button" class="self-subtab ${this.activeTab === id ? 'active' : ''}" data-self-tab="${id}">${label}</button>`
    ).join('');
    return `<div class="self-model-view">
      <div class="self-model-head">
        <div>
          <div class="body-view-title">Self-Model</div>
          <div class="body-view-sub">What the organism has learned about itself — structure, agency and current executive state.</div>
        </div>
        <span class="body-chip">live · read only</span>
      </div>
      <div class="self-subtabs" role="tablist">${tabs}</div>
      ${body}
    </div>`;
  }

  lensNav(group, items, active) {
    return `<div class="self-lens-nav">${items.map(([id, label]) =>
      `<button type="button" class="${active === id ? 'active' : ''}" data-self-lens-group="${group}" data-self-lens="${id}">${label}</button>`
    ).join('')}</div>`;
  }

  renderOverlay() {
    if (this.activeTab === 'self') return this.shell(this.selfView());
    if (this.activeTab === 'agency') return this.shell(this.agencyView());
    if (this.activeTab === 'history') return this.shell(this.historyView());
    return this.shell(this.overview());
  }

  overview() {
    const s = summary(this.snapshot);
    const executiveDetail = s.intentId ? shortId(s.intentId) : 'no active intent';
    return `<div class="self-focus">
      <div class="self-focus-title">Current self-model</div>
      <div class="self-pipeline">
        ${stage('Body', s.schemaState, `${s.parts} learned parts`, '', 'self:body-schema')}
        <div class="self-pipeline-arrow">→</div>
        ${stage('Agency', `${s.agenticDimensions}/${s.dimensions}`, `${s.causalRelations} causal relations`, '', 'agency:acquisition')}
        <div class="self-pipeline-arrow">→</div>
        ${stage('Can do', s.competences, 'learned competences', '', 'agency:capabilities')}
        <div class="self-pipeline-arrow">→</div>
        ${stage('Can now', s.affordances, 'current affordances', s.affordances ? 'live' : '', 'agency:affordances')}
        <div class="self-pipeline-arrow">→</div>
        ${stage('Intent', s.intentStatus, executiveDetail, s.intentId ? 'live' : '', 'agency:executive')}
      </div>
    </div>
    <div class="self-overview-strip">
      <div><span>Attempts</span><strong>${s.attempts}</strong></div>
      <div><span>Recurring patterns</span><strong>${s.recurringSignatures}</strong></div>
      <div><span>Known effects</span><strong>${s.effects}</strong></div>
      <div><span>Current body bindings</span><strong>${s.bindings}</strong></div>
    </div>
    ${this.recentEvent()}
    <div class="self-boundary-note compact">Overview is deliberately compressed. Open Self or Agency for evidence; select an item only when you need raw IDs and provenance.</div>`;
  }

  recentEvent() {
    const event = this.events[this.events.length - 1];
    if (!event) return '';
    return `<button type="button" class="self-recent-event" data-self-tab="history">
      <span>Recent change</span>
      <strong>${escapeHtml(event.title)}</strong>
      <small>t${event.tick} · ${escapeHtml(event.detail)}</small>
    </button>`;
  }

  selfView() {
    let body = this.bodySchema();
    if (this.selfLens === 'self-view') {
      const selected = this.selectedId?.startsWith('segment|')
        ? this.selectedId.slice('segment|'.length)
        : null;
      const paneNav = `<div class="self-view-pane-nav">
        <button type="button" class="${this.selfViewPane === 'composite' ? 'active' : ''}" data-self-view-pane="composite">Composite</button>
        <button type="button" class="${this.selfViewPane === 'development' ? 'active' : ''}" data-self-view-pane="development">Development</button>
      </div>`;
      const developmentIndex = this.selfViewDevelopmentIndex === null
        ? Math.max(0, this.selfViewDevelopment.length - 1)
        : this.selfViewDevelopmentIndex;
      body = this.selfViewPane === 'development'
        ? `${paneNav}${renderSelfViewDevelopment(this.selfViewDevelopment, {
            index: developmentIndex,
            bodyMode: this.selfViewDevelopmentBodyMode,
            scaleMode: this.selfViewDevelopmentScale,
          })}`
        : `${paneNav}${renderSelfView(this.snapshot, this.selfViewMode, selected)}`;
    } else if (this.selfLens === 'embodiment') {
      body = this.embodiment();
    }
    return `${this.lensNav('self', SELF_LENSES, this.selfLens)}${body}`;
  }

  bodySchema() {
    const schema = this.snapshot?.body_schema ?? {};
    const parts = Array.isArray(schema.parts) ? [...schema.parts] : [];
    const deps = Array.isArray(schema.dependencies) ? [...schema.dependencies] : [];
    const boundary = this.snapshot?.body_schema_boundary ?? {};
    const senses = parts.filter((part) => part.kind === 'sense');
    const regions = parts.filter((part) => part.kind === 'cognitive_region');
    const stable = parts.filter((part) => classRatio(part.existence_confidence_class) >= .65).length;
    const uncertain = parts.length - stable;

    regions.sort((a, b) =>
      finite(b.confidence_class, 0) - finite(a.confidence_class, 0)
      || finite(b.maturity_class, 0) - finite(a.maturity_class, 0)
    );

    const regionCards = regions.slice(0, 10).map((region) => `<button type="button" class="self-compact-item" data-self-id="${escapeHtml(String(region.part_id))}">
      <strong>${escapeHtml(shortId(region.part_id, 30))}</strong>
      <span>confidence ${pct(classRatio(region.confidence_class))}</span>
      <small>maturity ${finite(region.maturity_class, 0)} · activity ${finite(region.activity_class, 0)}</small>
    </button>`).join('');

    const relationRows = deps.slice(0, 8).map((dep) => `<div class="self-dependency">
      <span>${escapeHtml(shortId(dep.source_id, 22))}</span>
      <b>${escapeHtml(String(dep.relation ?? 'related'))}</b>
      <span>${escapeHtml(shortId(dep.target_id, 22))}</span>
    </div>`).join('');

    return `<div class="self-kpi-row">
      <div><span>Sensory parts</span><strong>${senses.length}</strong></div>
      <div><span>Cognitive regions</span><strong>${regions.length}</strong></div>
      <div><span>Stable parts</span><strong>${stable}</strong></div>
      <div><span>Uncertain</span><strong>${uncertain}</strong></div>
      <div><span>Dependencies</span><strong>${deps.length}</strong></div>
    </div>
    <div class="self-two-cols weighted">
      <div class="self-list-card">
        <div class="self-section-head"><div><span>Learned regions</span><small>Top evidence only · select to inspect</small></div><strong>${regions.length}</strong></div>
        <div class="self-compact-list">${regionCards || '<div class="self-empty">No cognitive region has emerged yet.</div>'}</div>
        ${regions.length > 10 ? `<div class="self-more">+${regions.length - 10} regions hidden to reduce visual noise</div>` : ''}
      </div>
      <div class="self-list-card">
        <div class="self-section-head"><div><span>Strongest dependencies</span><small>Raw topology stays on demand</small></div><strong>${deps.length}</strong></div>
        <div class="self-dependency-list">${relationRows || '<div class="self-empty">No learned dependencies yet.</div>'}</div>
      </div>
    </div>
    <div class="self-three-cols compact">
      ${this.channelSummary('Self-caused', boundary.self_caused_channels)}
      ${this.channelSummary('Somatic-correlated', boundary.somatic_correlated_channels)}
      ${this.channelSummary('External / unowned', boundary.external_channels)}
    </div>
    ${this.perceptualSummary()}
    <div class="self-boundary-note compact">Boundary confidence: ${pct(boundary.confidence)} · ${finite(boundary.revision_count, 0)} revisions. Opaque organism IDs remain separate from observer anatomy.</div>`;
  }

  channelSummary(label, values) {
    const items = Array.isArray(values) ? values : [];
    return `<div class="self-mini-summary"><span>${escapeHtml(label)}</span><strong>${items.length}</strong><small>${items.length ? shortId(items[0], 28) : 'none'}</small></div>`;
  }

  perceptualSummary() {
    const entries = Object.entries(
      this.snapshot?.self_model && typeof this.snapshot.self_model === 'object'
        ? this.snapshot.self_model : {}
    );
    if (!entries.length) return '';
    const confidence = average(entries.map(([, state]) => classRatio(state?.confidence_class)));
    const health = average(entries.map(([, state]) => classRatio(state?.health_class)));
    const maturity = average(entries.map(([, state]) => classRatio(state?.maturity_class, 8)));
    const issues = entries
      .map(([id, state]) => ({
        id,
        score: Math.min(classRatio(state?.confidence_class), classRatio(state?.health_class)),
      }))
      .filter((item) => item.score < .8)
      .sort((a, b) => a.score - b.score)
      .slice(0, 5);

    return `<div class="self-perception-summary">
      <div><span>Perceptual self-model</span><strong>${entries.length} senses</strong></div>
      <div><span>Confidence</span><strong>${pct(confidence)}</strong></div>
      <div><span>Health</span><strong>${pct(health)}</strong></div>
      <div><span>Maturity</span><strong>${pct(maturity)}</strong></div>
      <div class="self-perception-issues"><span>Needs attention</span><strong>${issues.length}</strong><small>${issues.length ? issues.map((item) => shortId(item.id, 16)).join(' · ') : 'none'}</small></div>
    </div>`;
  }

  embodiment() {
    const e = this.snapshot?.embodiment ?? {};
    const bindings = Array.isArray(e.bindings) ? e.bindings : [];
    const competenceState = e.embodied_competences ?? {};
    const bindingCards = bindings.slice(0, 8).map((binding) => `<button type="button" class="self-compact-item" data-self-id="${escapeHtml(String(binding.competence_id))}">
      <strong>${escapeHtml(shortId(binding.competence_id, 30))}</strong>
      <span>effect ${escapeHtml(shortId(binding.effect_id, 24))}</span>
      <small>reliability ${pct(binding.reliability)} · controllability ${pct(binding.controllability)}</small>
    </button>`).join('');

    return `<div class="self-kpi-row">
      <div><span>Epoch</span><strong>${escapeHtml(String(e.epoch ?? '—'))}</strong></div>
      <div><span>State</span><strong>${escapeHtml(String(e.state ?? '—'))}</strong></div>
      <div><span>Bindings</span><strong>${bindings.length}</strong></div>
      <div><span>Executable</span><strong>${finite(competenceState.executable, 0)}</strong></div>
    </div>
    <div class="self-two-cols">
      <div class="self-list-card">
        <div class="self-section-head"><div><span>Current embodiment</span><small>Current-body context</small></div></div>
        ${row('Embodiment', shortId(e.embodiment_id, 34))}
        ${row('Body', shortId(e.body_id, 34))}
        ${row('Tick', String(e.embodiment_tick ?? '—'))}
        ${row('Prior authority', String(e.prior?.authority ?? '—'))}
      </div>
      <div class="self-list-card">
        <div class="self-section-head"><div><span>Execution bindings</span><small>Only current-body bindings</small></div><strong>${bindings.length}</strong></div>
        <div class="self-compact-list">${bindingCards || '<div class="self-empty">No current execution binding.</div>'}</div>
      </div>
    </div>
    <div class="self-boundary-note compact">Durable competence knowledge does not imply executability in this body. Re-embodiment must revalidate bindings.</div>`;
  }

  agencyView() {
    let body = this.acquisition();
    if (this.agencyLens === 'capabilities') body = this.capabilities();
    else if (this.agencyLens === 'affordances') body = this.affordanceView();
    else if (this.agencyLens === 'executive') body = this.executive();
    return `${this.lensNav('agency', AGENCY_LENSES, this.agencyLens)}${body}`;
  }

  acquisition() {
    const s = summary(this.snapshot);
    const dimensions = Array.isArray(this.snapshot?.action_dimensions) ? [...this.snapshot.action_dimensions] : [];
    dimensions.sort((a, b) =>
      Number(Boolean(b.agentic)) - Number(Boolean(a.agentic))
      || finite(b.controllability, 0) - finite(a.controllability, 0)
    );
    const dimensionCards = dimensions.slice(0, 8).map((item) => `<button type="button" class="self-compact-item" data-self-id="${escapeHtml(String(item.dimension_id))}">
      <strong>${escapeHtml(shortId(item.dimension_id, 30))}</strong>
      <span>${item.agentic ? 'agentic' : 'candidate'} · control ${pct(item.controllability)}</span>
      <small>${item.usage_count ?? 0} uses · confidence ${pct(item.confidence)}</small>
    </button>`).join('');

    return `<div class="self-funnel">
      ${funnelStep('Opportunities', s.opportunities, 'physical motor surface')}
      <div>→</div>
      ${funnelStep('Attempts', s.attempts, 'executed interventions')}
      <div>→</div>
      ${funnelStep('Signatures', s.signatures, `${s.recurringSignatures} recurring`)}
      <div>→</div>
      ${funnelStep('Causal', s.causalRelations, `${s.causalEvidence} evidence records`)}
      <div>→</div>
      ${funnelStep('Dimensions', s.dimensions, `${s.agenticDimensions} agentic`, s.agenticDimensions ? 'live' : '')}
    </div>
    <div class="self-list-card self-dimension-panel">
      <div class="self-section-head"><div><span>Action dimensions</span><small>Only discovered dimensions are listed</small></div><strong>${s.agenticDimensions}/${s.dimensions} agentic</strong></div>
      <div class="self-compact-list grid">${dimensionCards || '<div class="self-empty">No action dimension has emerged yet. Attempts and causal evidence are still accumulating.</div>'}</div>
    </div>`;
  }

  capabilities() {
    const competences = Array.isArray(this.snapshot?.motor_competences) ? [...this.snapshot.motor_competences] : [];
    const effects = new Map((Array.isArray(this.snapshot?.effects) ? this.snapshot.effects : []).map((effect) => [String(effect.effect_id), effect]));
    competences.sort((a, b) =>
      finite(b.controllability, 0) - finite(a.controllability, 0)
      || finite(b.reproducibility, 0) - finite(a.reproducibility, 0)
    );
    const cards = competences.map((competence) => {
      const effect = effects.get(String(competence.effect_id)) ?? {};
      return `<button type="button" class="self-competence-card" data-self-id="${escapeHtml(String(competence.competence_id))}">
        <div class="self-competence-top"><strong>${escapeHtml(shortId(competence.competence_id, 34))}</strong>${chip(String(competence.maturity ?? 'unknown'))}</div>
        <div class="self-bars">
          ${this.bar('controllability', competence.controllability)}
          ${this.bar('reproducibility', competence.reproducibility)}
          ${this.bar('effect confidence', effect.confidence)}
        </div>
        <div class="self-competence-effect"><span>Known effect</span><strong>${escapeHtml(shortId(competence.effect_id, 32))}</strong></div>
      </button>`;
    }).join('');

    return `<div class="self-kpi-row">
      <div><span>Competences</span><strong>${competences.length}</strong></div>
      <div><span>Known effects</span><strong>${effects.size}</strong></div>
      <div><span>Current affordances</span><strong>${affordances(this.snapshot).length}</strong></div>
    </div>
    <div class="self-section-head spacious"><div><span>What it knows how to do</span><small>Competence-first view; hundreds of effects stay hidden until relevant</small></div></div>
    <div class="self-competence-grid">${cards || '<div class="self-empty">No acquired motor competence yet.</div>'}</div>`;
  }

  affordanceView() {
    const items = affordances(this.snapshot);
    const s = summary(this.snapshot);
    if (!items.length) {
      let reason = 'No competence currently satisfies the canonical affordance thresholds.';
      if (!s.competences) reason = 'No learned motor competence exists yet.';
      else if (!s.effects) reason = 'No learned consequence is available for a competence.';
      else if (!s.bindings) reason = 'Known competences have no current embodiment execution binding.';
      return `<div class="self-empty-state">
        <div class="self-empty-symbol">∅</div>
        <h3>No current affordance</h3>
        <p>${escapeHtml(reason)}</p>
        <div class="self-blocker-grid">
          <div><span>Known competences</span><strong>${s.competences}</strong></div>
          <div><span>Known effects</span><strong>${s.effects}</strong></div>
          <div><span>Current bindings</span><strong>${s.bindings}</strong></div>
          <div><span>Agentic dimensions</span><strong>${s.agenticDimensions}</strong></div>
        </div>
        <small>ActionAffordance is canonical · derived · ephemeral · never motor authority.</small>
      </div>`;
    }

    const cards = items.map((item) => `<button type="button" class="self-affordance-card" data-self-id="${escapeHtml(`affordance|${item.affordance_id}`)}">
      <div class="self-affordance-label">CAN PROBABLY DO NOW</div>
      <strong>${escapeHtml(shortId(item.competence_id, 34))}</strong>
      <span>→ ${escapeHtml(shortId(item.effect_id, 32))}</span>
      <div class="self-bars">
        ${this.bar('prediction', item.prediction_confidence)}
        ${this.bar('control', item.controllability)}
        ${this.bar('executability', item.executability_confidence)}
      </div>
    </button>`).join('');
    return `<div class="self-section-head spacious"><div><span>Current possibilities</span><small>Only canonical ActionAffordance objects</small></div><strong>${items.length}</strong></div>
      <div class="self-competence-grid">${cards}</div>`;
  }

  executive() {
    const executive = this.snapshot?.executive_intention ?? {};
    const active = executive?.active ?? null;
    const counts = executive?.counts ?? {};
    const trace = executive?.trace ?? null;

    const chain = active ? [
      ['AFFORDANCE', active.supporting_affordance_id, active.admission],
      ['INTENT', active.intent_id, active.status],
      ['COMPETENCE', active.competence_id, `effect ${shortId(active.anticipated_effect_id, 20)}`],
      ['COMMITMENT', active.commitment_id, active.commitment_id ? 'motor authority' : 'not committed'],
    ] : [];

    const chainHtml = chain.length ? chain.map(([label, id, detail], index) =>
      `${index ? '<div class="self-exec-arrow">→</div>' : ''}<div class="self-exec-node"><span>${escapeHtml(label)}</span><strong>${escapeHtml(shortId(id, 26))}</strong><small>${escapeHtml(String(detail ?? '—'))}</small></div>`
    ).join('') : '<div class="self-empty">No pending or active ActionIntent.</div>';

    const traceHtml = trace ? `<div class="self-trace-line">
      ${this.traceStep('Proposal', trace.proposal_id)}
      ${this.traceStep('Commit', trace.commitment_id)}
      ${this.traceStep('Command', trace.command_id)}
      ${this.traceStep('Attempt', trace.attempt_id)}
      ${this.traceStep('Effect', trace.observed_effect_id)}
      ${this.traceStep('Result', trace.result ?? trace.match)}
    </div>` : '<div class="self-empty">No completed causal action trace yet.</div>';

    return `<div class="self-list-card">
      <div class="self-section-head"><div><span>Current executive chain</span><small>What → authority, never actuator detail</small></div></div>
      <div class="self-exec-chain">${chainHtml}</div>
    </div>
    <div class="self-list-card self-trace-card">
      <div class="self-section-head"><div><span>Latest action trace</span><small>Execution evidence</small></div></div>
      ${traceHtml}
    </div>
    <div class="self-outcome-strip">
      ${['satisfied','failed','rejected','interrupted','invalidated'].map((status) =>
        `<div><span>${status}</span><strong>${finite(counts[status], 0)}</strong></div>`
      ).join('')}
    </div>`;
  }

  traceStep(label, value) {
    return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(shortId(value, 24))}</strong></div>`;
  }

  historyView() {
    const items = [...this.events].reverse();
    const rows = items.map((event) => `<div class="self-event ${escapeHtml(event.kind)}">
      <span>t${event.tick}</span>
      <div><strong>${escapeHtml(event.title)}</strong><small>${escapeHtml(event.detail)}</small></div>
    </div>`).join('');
    return `<div class="self-section-head spacious"><div><span>Meaningful self-model changes</span><small>Raw per-tick changes are intentionally suppressed</small></div><strong>${items.length}</strong></div>
      <div class="self-event-list">${rows || '<div class="self-empty">No meaningful self-model event observed in this browser session.</div>'}</div>`;
  }

  bar(label, value) {
    const width = Math.round(ratio(value) * 100);
    return `<div class="self-bar"><span>${escapeHtml(label)}</span><div><i style="width:${width}%"></i></div><strong>${width}%</strong></div>`;
  }

  selectedRecord() {
    const id = this.selectedId;
    if (!id) return null;
    if (id.startsWith('segment|')) {
      return selfViewSegmentRecord(this.snapshot, id.slice('segment|'.length));
    }
    if (id.startsWith('affordance|')) {
      const affordanceId = id.slice('affordance|'.length);
      const item = affordances(this.snapshot).find((candidate) => String(candidate.affordance_id) === affordanceId);
      if (item) return { kind: 'ActionAffordance', item, displayId: item.affordance_id };
    }
    const sources = [
      ['BodySchema part', this.snapshot?.body_schema?.parts, 'part_id'],
      ['ActionDimension', this.snapshot?.action_dimensions, 'dimension_id'],
      ['MotorCompetence', this.snapshot?.motor_competences, 'competence_id'],
      ['Effect', this.snapshot?.effects, 'effect_id'],
      ['Embodiment binding', this.snapshot?.embodiment?.bindings, 'competence_id'],
    ];
    for (const [kind, items, key] of sources) {
      if (!Array.isArray(items)) continue;
      const item = items.find((candidate) => String(candidate?.[key]) === id);
      if (item) return { kind, item, displayId: id };
    }
    return null;
  }

  renderInspector() {
    if (!this.selectedId) return '';
    const selected = this.selectedRecord();
    if (!selected) return `<button type="button" class="self-inspector-close" data-self-clear>×</button>
      <div class="body-inspector-head"><div class="body-inspector-kicker">SELF-MODEL</div><div class="body-inspector-title">No evidence record</div></div>`;

    const scalarRows = Object.entries(selected.item ?? {})
      .filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
      .slice(0, 14)
      .map(([key, value]) => row(key.replaceAll('_', ' '), typeof value === 'number' ? String(Number(value.toFixed?.(4) ?? value)) : String(value)))
      .join('');

    const listRows = Object.entries(selected.item ?? {})
      .filter(([, value]) => Array.isArray(value) && value.length)
      .slice(0, 3)
      .map(([key, value]) => `<div class="self-inspector-list"><span>${escapeHtml(key.replaceAll('_', ' '))}</span>${value.slice(0, 8).map((item) => `<code>${escapeHtml(shortId(item, 30))}</code>`).join('')}</div>`)
      .join('');

    return `<button type="button" class="self-inspector-close" data-self-clear aria-label="Close inspector">×</button>
      <div class="body-inspector-head">
        <div class="body-inspector-kicker">${escapeHtml(selected.kind)}</div>
        <div class="body-inspector-title">${escapeHtml(shortId(selected.displayId, 34))}</div>
        <div class="body-inspector-sub">Raw organism-owned evidence. Observer selection never feeds back.</div>
      </div>
      <div class="body-section">${scalarRows}${listRows}</div>`;
  }
}
