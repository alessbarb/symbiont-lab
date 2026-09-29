import { escapeHtml } from '../shared/dom.js';
import {
  captureSelfViewDevelopment,
  renderSelfView,
  renderSelfViewDevelopment,
  selfViewSegmentNames,
  selfViewSegmentRecord,
} from './self-view.js';

const MODES = [
  ['compare', 'Compare'],
  ['acquired', 'Acquired'],
  ['development', 'Development'],
];

const LENSES = [
  ['coverage', 'Coverage'],
  ['stability', 'Stability'],
  ['agency', 'Agency'],
  ['uncertainty', 'Uncertainty'],
];

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function pct(value) {
  return `${Math.round(Math.max(0, Math.min(1, finite(value))) * 100)}%`;
}

function shortId(value, max = 30) {
  const text = String(value ?? '—');
  if (text.length <= max) return text;
  return `${text.slice(0, 12)}…${text.slice(-9)}`;
}

function embodimentId(snapshot) {
  return snapshot?.embodiment?.embodiment_id ?? null;
}

function bodyKind(snapshot) {
  return snapshot?.observer_semantics?.morphology?.body_kind
    ?? snapshot?.observer_semantics?.body_kind
    ?? snapshot?.body_kind
    ?? null;
}

function tickOf(snapshot) {
  return Number(snapshot?.tick ?? 0);
}

function statusFor(record, priorRecord = null, afterEmbodimentChange = false) {
  const item = record?.item;
  const prior = priorRecord?.item;
  if (!item || item.learned_channels_mapped <= 0) {
    if (prior?.learned_channels_mapped > 0) return { id: 'stale', label: 'STALE · not currently mapped' };
    return { id: 'unrepresented', label: 'UNREPRESENTED' };
  }
  if (item.confidence < .25 || item.stability < .2) return { id: 'uncertain', label: 'UNCERTAIN' };
  if (prior?.learned_channels_mapped > 0) return { id: 'retained', label: 'RETAINED · current mapping' };
  if (afterEmbodimentChange) return { id: 'novel', label: 'NOVEL · current body' };
  if (item.agency >= .5) return { id: 'agentic', label: 'AGENTIC' };
  if (item.coverage >= .5 && item.stability >= .5) return { id: 'represented', label: 'REPRESENTED' };
  return { id: 'emerging', label: 'EMERGING' };
}

function eventLabel(event) {
  const labels = {
    embodiment: 'Embodiment changed',
    first_representation: 'First representation observed',
    strengthened: 'Correspondence strengthened',
    weakened: 'Correspondence weakened',
    became_stable: 'Correspondence became stable',
    became_uncertain: 'Correspondence became uncertain',
    agency_appeared: 'Agency appeared',
    agency_weakened: 'Agency weakened',
    lost_support: 'Lost current support',
    retained: 'Retained evidence observed',
    novel: 'Novel correspondence observed',
  };
  return event.title || labels[event.kind] || event.kind || 'developmental change';
}

function meaningfulDelta(a, b, threshold = .10) {
  return Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) >= threshold;
}

function classifyRegionChange(previous, current, status, priorStatus = null) {
  if (!previous && current.learned_channels_mapped > 0) return 'first_representation';
  if (previous && previous.learned_channels_mapped > 0 && current.learned_channels_mapped <= 0) return 'lost_support';
  if (priorStatus && priorStatus.id !== status.id) {
    if (status.id === 'uncertain') return 'became_uncertain';
    if (status.id === 'retained') return 'retained';
    if (status.id === 'novel') return 'novel';
    if (status.id === 'represented' && priorStatus.id !== 'represented') return 'became_stable';
    if (status.id === 'agentic' && priorStatus.id !== 'agentic') return 'agency_appeared';
  }
  if (previous) {
    if (previous.agency < .1 && current.agency >= .1) return 'agency_appeared';
    if (previous.agency >= .25 && current.agency < previous.agency - .1) return 'agency_weakened';
    const strengthBefore = (previous.coverage + previous.stability) / 2;
    const strengthNow = (current.coverage + current.stability) / 2;
    if (meaningfulDelta(strengthNow, strengthBefore, .10)) {
      return strengthNow > strengthBefore ? 'strengthened' : 'weakened';
    }
  }
  return null;
}

export class AcquiredSelfWorkspace {
  constructor({
    onSelectPhysical = () => {},
    onModeChange = () => {},
    getPhysicalSegments = () => [],
  } = {}) {
    this.snapshot = {};
    this.mode = 'compare';
    this.lens = 'coverage';
    this.selectedSegment = null;
    this.showMorphology = true;
    this.showObserverLabels = false;
    this.showRegionsFallback = false;
    this.evidenceExpanded = false;
    this.onSelectPhysical = onSelectPhysical;
    this.onModeChange = onModeChange;
    this.getPhysicalSegments = getPhysicalSegments;

    this.development = [];
    this.maxDevelopmentFrames = 120;
    this.events = [];
    this.maxEvents = 80;
    this.previousEmbodimentId = null;
    this.previousBodyKind = null;
    this.priorSegmentRecords = new Map();
    this.hasEmbodimentTransition = false;
    this.lastSegmentSignature = new Map();
    this.lastSegmentState = new Map();
    this.developmentIndex = null;
    this.developmentBodyMode = 'state';
    this.developmentScale = 'detail';
    this._lastCaptureAt = 0;
  }

  update(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') return;

    const nextEmbodiment = embodimentId(snapshot);
    const nextBodyKind = bodyKind(snapshot);
    const previousSnapshot = this.snapshot;

    if (
      previousSnapshot && Object.keys(previousSnapshot).length &&
      this.previousEmbodimentId &&
      nextEmbodiment &&
      nextEmbodiment !== this.previousEmbodimentId
    ) {
      this.priorSegmentRecords = new Map(
        selfViewSegmentNames(previousSnapshot).map((segment) => [
          segment,
          selfViewSegmentRecord(previousSnapshot, segment),
        ])
      );
      this.hasEmbodimentTransition = true;
      this.events.push({
        tick: tickOf(snapshot),
        kind: 'embodiment',
        title: 'Embodiment changed',
        detail: `${shortId(this.previousEmbodimentId)} → ${shortId(nextEmbodiment)}`,
      });
      if (this.events.length > this.maxEvents) this.events.shift();
    }

    this.snapshot = snapshot;
    this.previousEmbodimentId = nextEmbodiment;
    this.previousBodyKind = nextBodyKind;
    this.captureDevelopment();
    this.recordSegmentChanges();
  }

  captureDevelopment() {
    const now = performance.now();
    if (this._lastCaptureAt && now - this._lastCaptureAt < 500) return;
    this._lastCaptureAt = now;
    const frame = captureSelfViewDevelopment(this.snapshot);
    if (!frame?.tick) return;
    const previous = this.development.at(-1);
    const sameBody = previous?.morphology?.bodyKind === frame?.morphology?.bodyKind;
    const signature = (candidate) => [
      Math.round((candidate?.aggregate?.coverage ?? 0) * 1000),
      Math.round((candidate?.aggregate?.stability ?? 0) * 1000),
      Math.round((candidate?.aggregate?.agency ?? 0) * 1000),
      candidate?.aggregate?.representedRegions ?? 0,
      candidate?.aggregate?.agenticRegions ?? 0,
    ].join('|');
    if (previous && sameBody && signature(previous) === signature(frame) && frame.tick - previous.tick < 100) return;
    this.development.push(frame);
    if (this.development.length > this.maxDevelopmentFrames) {
      this.development.splice(0, this.development.length - this.maxDevelopmentFrames);
    }
  }

  recordSegmentChanges() {
    const tick = tickOf(this.snapshot);
    if (!tick) return;
    for (const segment of selfViewSegmentNames(this.snapshot)) {
      const record = selfViewSegmentRecord(this.snapshot, segment);
      if (!record?.item) continue;
      const current = {
        coverage: finite(record.item.coverage),
        stability: finite(record.item.stability),
        agency: finite(record.item.agency),
        confidence: finite(record.item.confidence),
        learned_channels_mapped: finite(record.item.learned_channels_mapped),
      };
      const previous = this.lastSegmentState.get(segment) ?? null;
      const priorStatus = previous?.status ?? null;
      const currentStatus = statusFor(record, this.priorSegmentRecords.get(segment), this.hasEmbodimentTransition);
      const kind = classifyRegionChange(previous, current, currentStatus, priorStatus);

      if (kind) {
        const detail = previous
          ? [
              meaningfulDelta(current.coverage, previous.coverage, .01) ? `coverage ${pct(previous.coverage)} → ${pct(current.coverage)}` : null,
              meaningfulDelta(current.stability, previous.stability, .01) ? `stability ${pct(previous.stability)} → ${pct(current.stability)}` : null,
              meaningfulDelta(current.agency, previous.agency, .01) ? `agency ${pct(previous.agency)} → ${pct(current.agency)}` : null,
              current.learned_channels_mapped !== previous.learned_channels_mapped ? `mapped ${previous.learned_channels_mapped} → ${current.learned_channels_mapped}` : null,
            ].filter(Boolean).join(' · ')
          : `coverage ${pct(current.coverage)} · stability ${pct(current.stability)} · agency ${pct(current.agency)}`;

        const recentSame = this.events.at(-1);
        const duplicate = recentSame &&
          recentSame.kind === kind &&
          recentSame.segment === segment &&
          tick - recentSame.tick < 20;
        if (!duplicate) {
          this.events.push({
            tick,
            kind,
            segment,
            title: `${record.displayId} · ${eventLabel({ kind })}`,
            detail,
          });
        }
      }

      this.lastSegmentState.set(segment, { ...current, status: currentStatus });
    }
    if (this.events.length > this.maxEvents) {
      this.events.splice(0, this.events.length - this.maxEvents);
    }
  }

  openCompare(segment = null) {
    this.mode = 'compare';
    if (segment) this.selectSegment(segment);
    this.onModeChange(this.mode);
  }

  setMode(mode) {
    if (!MODES.some(([id]) => id === mode)) return;
    this.mode = mode;
    this.onModeChange(mode);
  }

  setLens(lens) {
    if (!LENSES.some(([id]) => id === lens)) return;
    this.lens = lens;
  }

  selectSegment(segment, { notifyPhysical = true } = {}) {
    this.selectedSegment = segment || null;
    if (notifyPhysical) this.onSelectPhysical(this.selectedSegment);
  }

  clearSelection() {
    this.selectedSegment = null;
    this.onSelectPhysical(null);
  }

  render(overlay, panel) {
    if (!overlay || !panel) return;
    const root = panel.closest('.body-view-root');
    root?.classList.add('self-model-mode', 'acquired-self-v2-mode');
    root?.classList.toggle('acquired-self-compare-mode', this.mode === 'compare');
    root?.classList.toggle('self-model-inspector-open', Boolean(this.selectedSegment));

    const scrollParent = overlay.closest('.body-data-overlay') || overlay;
    const previousOverlayScroll = scrollParent.scrollTop;
    const previousPanelScroll = panel.scrollTop;

    overlay.innerHTML = this.renderOverlay();
    panel.innerHTML = this.renderInspector();

    overlay.querySelectorAll('[data-acquired-self-mode]').forEach((button) => {
      button.addEventListener('click', () => {
        this.setMode(button.dataset.acquiredSelfMode);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-acquired-self-lens]').forEach((button) => {
      button.addEventListener('click', () => {
        this.setLens(button.dataset.acquiredSelfLens);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-id]').forEach((node) => {
      node.addEventListener('click', () => {
        const id = node.dataset.selfId || '';
        if (id.startsWith('segment|')) this.selectSegment(id.slice('segment|'.length));
        else this.selectedSegment = null;
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-physical-segment]').forEach((button) => {
      button.addEventListener('click', () => {
        this.selectSegment(button.dataset.physicalSegment);
        this.render(overlay, panel);
      });
    });
    overlay.querySelector('[data-toggle-observer-morphology]')?.addEventListener('click', () => {
      this.showMorphology = !this.showMorphology;
      this.render(overlay, panel);
    });
    overlay.querySelector('[data-toggle-observer-labels]')?.addEventListener('click', () => {
      this.showObserverLabels = !this.showObserverLabels;
      this.render(overlay, panel);
    });
    overlay.querySelector('[data-toggle-regions]')?.addEventListener('click', () => {
      this.showRegionsFallback = !this.showRegionsFallback;
      this.render(overlay, panel);
    });
    panel.querySelector('[data-toggle-evidence]')?.addEventListener('click', () => {
      this.evidenceExpanded = !this.evidenceExpanded;
      this.render(overlay, panel);
    });
    overlay.querySelectorAll('[data-self-dev-body-mode]').forEach((button) => {
      button.addEventListener('click', () => {
        this.developmentBodyMode = button.dataset.selfDevBodyMode || 'state';
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-scale]').forEach((button) => {
      button.addEventListener('click', () => {
        this.developmentScale = button.dataset.selfDevScale || 'detail';
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-development-tick]').forEach((button) => {
      button.addEventListener('click', () => {
        const tick = Number(button.dataset.developmentTick);
        const segment = button.dataset.developmentSegment || null;
        let bestIndex = this.development.findIndex((frame) => frame.tick >= tick);
        if (bestIndex < 0) bestIndex = Math.max(0, this.development.length - 1);
        this.developmentIndex = bestIndex;
        if (segment) this.selectSegment(segment);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-frame]').forEach((button) => {
      button.addEventListener('click', () => {
        this.developmentIndex = Number(button.dataset.selfDevFrame);
        this.render(overlay, panel);
      });
    });
    overlay.querySelectorAll('[data-self-dev-index]').forEach((input) => {
      input.addEventListener('input', () => {
        this.developmentIndex = Number(input.value);
        this.render(overlay, panel);
      });
    });
    panel.querySelector('[data-self-clear]')?.addEventListener('click', () => {
      this.clearSelection();
      this.render(overlay, panel);
    });

    if (previousOverlayScroll > 0) {
      scrollParent.scrollTop = previousOverlayScroll;
      requestAnimationFrame(() => { scrollParent.scrollTop = previousOverlayScroll; });
    }
    if (previousPanelScroll > 0) {
      panel.scrollTop = previousPanelScroll;
      requestAnimationFrame(() => { panel.scrollTop = previousPanelScroll; });
    }
  }

  renderOverlay() {
    const tabs = MODES.map(([id, label]) =>
      `<button type="button" class="self-subtab ${this.mode === id ? 'active' : ''}" data-acquired-self-mode="${id}">${label}</button>`
    ).join('');
    const tick = tickOf(this.snapshot);
    const epoch = this.snapshot?.embodiment?.epoch ?? '—';

    let body = this.compareView();
    if (this.mode === 'acquired') body = this.acquiredView();
    if (this.mode === 'development') body = this.developmentView();

    return `<div class="self-model-view acquired-self-v2">
      <div class="self-model-head">
        <div>
          <div class="body-view-title">Acquired Self</div>
          <div class="body-view-sub">What Symbiont has acquired about acting through this body, projected onto observer morphology.</div>
        </div>
        <span class="body-chip">t${tick || '—'} · e${escapeHtml(String(epoch))} · read only</span>
      </div>
      <div class="self-subtabs acquired-self-modes" role="tablist">${tabs}</div>
      ${body}
    </div>`;
  }

  lensNav() {
    return `<div class="acquired-self-lenses">
      ${LENSES.map(([id, label]) =>
        `<button type="button" class="${this.lens === id ? 'active' : ''}" data-acquired-self-lens="${id}">${label}</button>`
      ).join('')}
    </div>`;
  }

  physicalSegmentList() {
    const physical = this.getPhysicalSegments?.() ?? [];
    if (!physical.length) return '<div class="self-empty">No physical region list is available for this morphology.</div>';
    return `<div class="acquired-self-physical-regions">
      ${physical.map((segment) => {
        const record = selfViewSegmentRecord(this.snapshot, segment);
        const status = statusFor(record, this.priorSegmentRecords.get(segment), this.hasEmbodimentTransition);
        return `<button type="button" class="${this.selectedSegment === segment ? 'selected' : ''}" data-physical-segment="${escapeHtml(segment)}">
          <span>${escapeHtml(segment.replaceAll('_', ' '))}</span>
          <strong class="${status.id}">${status.label}</strong>
        </button>`;
      }).join('')}
    </div>`;
  }

  compareView() {
    const selected = this.selectedSegment;
    const record = selected ? selfViewSegmentRecord(this.snapshot, selected) : null;
    const prior = selected ? this.priorSegmentRecords.get(selected) : null;
    const status = statusFor(record, prior, this.hasEmbodimentTransition);
    const acquired = record?.item;
    const priorItem = prior?.item;

    return `<div class="acquired-self-compare">
      <section class="acquired-self-physical-column">
        <div class="acquired-self-column-head">
          <div><span>APPARATUS TRUTH</span><strong>Physical body</strong><small>Physics3D / observer morphology</small></div>
          <em>observer authority</em>
        </div>
        <div class="acquired-self-physical-stage-copy compact">
          <strong>Select the body itself.</strong>
          <p>The live 3D apparatus is the primary selector. Region names are observer metadata and stay hidden unless requested.</p>
          <button type="button" data-toggle-regions>${this.showRegionsFallback ? 'Hide' : 'Regions'} fallback</button>
        </div>
        ${this.showRegionsFallback ? this.physicalSegmentList() : ''}
      </section>

      <section class="acquired-self-acquired-column">
        <div class="acquired-self-column-head">
          <div><span>ACQUIRED SELF</span><strong>Evidence-supported structure</strong><small>organism evidence × observer correspondence</small></div>
          <em class="${status.id}">${status.label}</em>
        </div>
        <div class="acquired-self-toolbar">
          ${this.lensNav()}
          <button type="button" class="${this.showMorphology ? 'active' : ''}" data-toggle-observer-morphology>Observer morphology</button>
          <button type="button" class="${this.showObserverLabels ? 'active' : ''}" data-toggle-observer-labels>Observer labels</button>
        </div>
        <div class="acquired-self-mini-projection ${this.showMorphology ? '' : 'morphology-hidden'} ${this.showObserverLabels ? 'labels-visible' : 'labels-hidden'}">
          ${renderSelfView(this.snapshot, this.lens, selected)}
        </div>
        ${selected ? this.selectedSummary(selected, acquired, priorItem, status) :
          '<div class="acquired-self-selection-empty">Select a physical or acquired region to inspect its correspondence.</div>'}
      </section>
    </div>`;
  }

  selectedSummary(segment, item, priorItem, status) {
    if (!item) {
      return `<div class="acquired-self-selected-summary">
        <div><span>Selected correspondence</span><strong>${escapeHtml(segment.replaceAll('_',' '))}</strong></div>
        <div><span>Status</span><strong class="${status.id}">${status.label}</strong></div>
        <p>No current acquired correspondence is exported for this physical region.</p>
      </div>`;
    }
    return `<div class="acquired-self-selected-summary">
      <div><span>Selected correspondence</span><strong>${escapeHtml(item.observer_region || segment)}</strong></div>
      <div><span>Status</span><strong class="${status.id}">${status.label}</strong></div>
      <div class="acquired-self-metrics">
        <div><span>Physical channels</span><strong>${item.physical_channels_expected}</strong></div>
        <div><span>Mapped</span><strong>${item.learned_channels_mapped}</strong></div>
        <div><span>Coverage</span><strong>${pct(item.coverage)}</strong></div>
        <div><span>Stability</span><strong>${pct(item.stability)}</strong></div>
        <div><span>Agency</span><strong>${pct(item.agency)}</strong></div>
        <div><span>Confidence</span><strong>${pct(item.confidence)}</strong></div>
      </div>
      ${priorItem ? `<div class="acquired-self-prior">
        <span>Previous embodiment evidence</span>
        <strong>coverage ${pct(priorItem.coverage)} · stability ${pct(priorItem.stability)} · agency ${pct(priorItem.agency)}</strong>
        <small>Retained evidence is historical. Reacquisition is not claimed unless explicit current evidence supports it.</small>
      </div>` : ''}
    </div>`;
  }

  acquiredView() {
    const segments = selfViewSegmentNames(this.snapshot);
    const records = segments.map((segment) => ({
      segment,
      record: selfViewSegmentRecord(this.snapshot, segment),
    }));
    const represented = records.filter(({ record }) => (record?.item?.learned_channels_mapped ?? 0) > 0).length;
    const stable = records.filter(({ record }) => (record?.item?.stability ?? 0) >= .5).length;
    const agentic = records.filter(({ record }) => (record?.item?.agency ?? 0) >= .5).length;
    const uncertain = records.filter(({ record }) => {
      const item = record?.item;
      return item && item.learned_channels_mapped > 0 && (item.confidence < .25 || item.stability < .2);
    }).length;

    return `
      <div class="acquired-self-acquired-head">
        ${this.lensNav()}
        <div class="acquired-self-toolbar">
          <button type="button" class="acquired-self-morphology-toggle ${this.showMorphology ? 'active' : ''}" data-toggle-observer-morphology>Observer morphology</button>
          <button type="button" class="acquired-self-morphology-toggle ${this.showObserverLabels ? 'active' : ''}" data-toggle-observer-labels>Observer labels</button>
        </div>
      </div>
      <div class="acquired-self-summary-strip">
        <div><span>Represented regions</span><strong>${represented} / ${segments.length}</strong></div>
        <div><span>Stable regions</span><strong>${stable}</strong></div>
        <div><span>Agentic regions</span><strong>${agentic}</strong></div>
        <div><span>Uncertain regions</span><strong>${uncertain}</strong></div>
      </div>
      <div class="acquired-self-full-projection ${this.showMorphology ? '' : 'morphology-hidden'} ${this.showObserverLabels ? 'labels-visible' : 'labels-hidden'}">
        ${renderSelfView(this.snapshot, this.lens, this.selectedSegment)}
      </div>
      <div class="self-boundary-note compact" data-observer-correspondence>
        Observer correspondence only. Anatomical labels and morphology are presentation metadata; Symbiont retains opaque evidence and relations.
      </div>`;
  }

  developmentView() {
    const index = this.developmentIndex === null
      ? Math.max(0, this.development.length - 1)
      : Math.max(0, Math.min(this.development.length - 1, this.developmentIndex));
    const events = this.events.slice(-12).reverse();
    const eventHtml = events.length
      ? events.map((event) => `<button type="button" class="acquired-self-development-event ${escapeHtml(event.kind)}" data-development-tick="${event.tick}" data-development-segment="${escapeHtml(event.segment || '')}">
          <span>t${event.tick}</span>
          <strong>${escapeHtml(eventLabel(event))}</strong>
          <small>${escapeHtml(event.detail || '')}</small>
        </button>`).join('')
      : '<div class="self-empty">No developmental correspondence changes captured yet.</div>';

    const currentFrame = this.development.at(-1);
    const currentSummary = currentFrame?.aggregate ?? {};
    const observerStart = this.development.at(0)?.tick ?? tickOf(this.snapshot);
    return `<div class="acquired-self-development-context">
      <div><span>Current acquired structure</span><strong>${currentSummary.representedRegions ?? 0} represented · ${currentSummary.agenticRegions ?? 0} agentic</strong></div>
      <div><span>Observation window</span><strong>t${observerStart} → t${tickOf(this.snapshot)}</strong></div>
      <div><span>Session-observed events</span><strong>${this.events.length}</strong></div>
      <small>Structure may predate observer attachment. This timeline only narrates changes captured in the current observer history.</small>
    </div>
    <div class="acquired-self-development-layout">
      <section class="acquired-self-development-events">
        <div class="self-section-head">
          <div><span>Developmental events</span><small>Lifetime tick · observer-side interpretation of acquired evidence</small></div>
        </div>
        ${eventHtml}
      </section>
      <section class="acquired-self-development-evidence">
        ${renderSelfViewDevelopment(this.development, {
          index,
          bodyMode: this.developmentBodyMode,
          scaleMode: this.developmentScale,
        })}
      </section>
    </div>`;
  }

  renderInspector() {
    if (!this.selectedSegment) {
      return `<div class="body-inspector-head">
        <div class="body-inspector-kicker">Acquired Self</div>
        <div class="body-inspector-title">Select a correspondence</div>
        <div class="body-inspector-sub">Physical apparatus and acquired evidence remain distinct authorities.</div>
      </div>
      <div class="body-section">
        <div class="body-section-title">Epistemic boundary</div>
        <div class="body-inspector-sub">Observer anatomy is only a projection surface. It never becomes organism semantics.</div>
      </div>`;
    }

    const record = selfViewSegmentRecord(this.snapshot, this.selectedSegment);
    const prior = this.priorSegmentRecords.get(this.selectedSegment);
    const status = statusFor(record, prior, this.hasEmbodimentTransition);
    const item = record?.item;

    if (!item) {
      return `<button type="button" class="self-inspector-close" data-self-clear>×</button>
        <div class="body-inspector-head">
          <div class="body-inspector-kicker">Correspondence</div>
          <div class="body-inspector-title">${escapeHtml(this.selectedSegment.replaceAll('_',' '))}</div>
          <div class="body-inspector-sub">Physical region selected; no acquired mapping is currently exported.</div>
        </div>`;
    }

    const receptors = item.receptor_ids.map((id) => `<code>${escapeHtml(shortId(id, 26))}</code>`).join('');
    const dimensions = item.dimension_ids.map((id) => `<code>${escapeHtml(shortId(id, 26))}</code>`).join('');

    return `<button type="button" class="self-inspector-close" data-self-clear>×</button>
      <div class="body-inspector-head">
        <div class="body-inspector-kicker">Correspondence</div>
        <div class="body-inspector-title">${escapeHtml(item.observer_region)}</div>
        <div class="body-inspector-sub">Observer region ↔ opaque organism evidence.</div>
      </div>
      <div class="body-section">
        <div class="body-section-title">Status</div>
        <div class="body-row"><span>Classification</span><strong class="${status.id}">${status.label}</strong></div>
        <div class="body-row"><span>Physical channels</span><strong>${item.physical_channels_expected}</strong></div>
        <div class="body-row"><span>Mapped learned channels</span><strong>${item.learned_channels_mapped}</strong></div>
        <div class="body-row"><span>Coverage</span><strong>${pct(item.coverage)}</strong></div>
        <div class="body-row"><span>Stability</span><strong>${pct(item.stability)}</strong></div>
        <div class="body-row"><span>Agency</span><strong>${pct(item.agency)}</strong></div>
        <div class="body-row"><span>Confidence</span><strong>${pct(item.confidence)}</strong></div>
      </div>
      <div class="body-section">
        <div class="body-section-title">Evidence</div>
        <div class="body-row"><span>Receptors</span><strong>${item.receptor_ids.length}</strong></div>
        <div class="body-row"><span>Action dimensions</span><strong>${item.dimension_ids.length}</strong></div>
        <button type="button" class="body-segment self-evidence-toggle" data-toggle-evidence>${this.evidenceExpanded ? 'Hide evidence' : 'Inspect evidence →'}</button>
        ${this.evidenceExpanded ? `<div class="self-evidence-expanded">
          <div class="self-inspector-list"><span>Receptors</span>${receptors || '<code>none</code>'}</div>
          <div class="self-inspector-list"><span>Action dimensions</span>${dimensions || '<code>none</code>'}</div>
        </div>` : ''}
      </div>
      <div class="body-section">
        <div class="body-section-title">Epistemic status</div>
        <div class="body-inspector-sub">observer correspondence only · never fed back to Symbiont</div>
      </div>`;
  }
}
