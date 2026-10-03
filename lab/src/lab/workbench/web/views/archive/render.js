import { escapeHtml } from '../shared/dom.js';
import { truncateHtml } from '../shared/format.js';

const KIND_LABELS = {
  'acquisition.embodiment': 'Embodiment Experience',
  'acquisition.vision': 'Vision Experience',
  'world.challenge': 'World · Challenge',
  'world.open': 'World · Open',
};

function emptyState(message) {
  const empty = document.createElement('div');
  empty.className = 'empty-state';
  empty.textContent = message;
  return empty;
}

function organismName(run, organisms) {
  const item = organisms.find(org => org.ref === run?.organism_ref);
  return item?.alias || run?.organism_alias || run?.organism_id || item?.organism_id || run?.organism_ref || 'Symbiont';
}

function runTick(run) {
  if (run?.end_tick != null) return Number(run.end_tick);
  if (run?.start_tick != null) return Number(run.start_tick);
  return null;
}

function runSortValue(run) {
  const date = Date.parse(run?.started_at || run?.created_at || '');
  if (Number.isFinite(date)) return date;
  return runTick(run) ?? 0;
}

function eventTone(run) {
  const reason = String(run?.termination_reason || '').toLowerCase();
  if (reason === 'body_non_viable') return 'death';
  if (reason === 'protected_recovery') return 'protected';
  if (String(run?.run_kind || '').startsWith('world.')) return 'world';
  if (run?.run_kind === 'acquisition.vision') return 'vision';
  return 'embodiment';
}

function developmentSummary(run) {
  const bits = [
    KIND_LABELS[run?.run_kind] || run?.run_kind || 'Run',
    run?.body_kind,
    run?.embodiment_mode,
  ].filter(Boolean);
  return bits.join(' · ');
}

function routeForRun(run) {
  if (run?.run_kind === 'acquisition.vision') return 'vision';
  if (run?.run_kind === 'acquisition.embodiment') return 'embodiment';
  if (String(run?.run_kind || '').startsWith('world.')) return 'world';
  return 'home';
}

function renderDevelopmentTimeline(runs, organisms) {
  if (!runs?.length) return emptyState('No managed Experience or World runs have been persisted yet.');

  const wrap = document.createElement('div');
  wrap.className = 'archive-development-timeline';

  const ordered = [...runs].sort((a,b) => runSortValue(a) - runSortValue(b));
  let previousEpoch = null;
  let previousOrganism = null;

  for (const run of ordered) {
    const epoch = run?.embodiment_epoch ?? null;
    const org = run?.organism_ref ?? run?.organism_id ?? 'unknown';
    const boundary = previousOrganism !== null && (org !== previousOrganism || (epoch != null && previousEpoch != null && epoch !== previousEpoch));
    if (boundary) {
      const divider = document.createElement('div');
      divider.className = 'archive-epoch-divider';
      divider.innerHTML = `<span></span><strong>${org !== previousOrganism ? 'Organism continuity boundary' : `Embodiment epoch e${escapeHtml(epoch)}`}</strong>`;
      wrap.appendChild(divider);
    }

    const item = document.createElement('article');
    item.className = `archive-development-event ${eventTone(run)}`;
    const tick = runTick(run);
    const reason = run?.termination_reason || run?.status || 'recorded';
    item.innerHTML = `
      <div class="archive-event-marker"></div>
      <div class="archive-event-body">
        <div class="archive-event-top">
          <span>${tick != null ? 't' + Number(tick).toLocaleString() : escapeHtml(run?.started_at || '—')}</span>
          <span>${epoch != null ? 'embodiment e' + escapeHtml(epoch) : ''}</span>
        </div>
        <h3>${escapeHtml(organismName(run, organisms))}</h3>
        <p>${escapeHtml(developmentSummary(run))}</p>
        <div class="archive-event-meta">
          <span>${escapeHtml(reason)}</span>
          <code>${truncateHtml(run?.run_id || '—', 34)}</code>
        </div>
        <div class="archive-event-actions">
          <button type="button" data-archive-open="${routeForRun(run)}">Open context</button>
          <button type="button" data-archive-open="mind">Open Mind</button>
        </div>
      </div>
    `;
    item.querySelectorAll('[data-archive-open]').forEach(button => {
      button.addEventListener('click', () => window.routeToView?.(button.dataset.archiveOpen));
    });
    wrap.appendChild(item);
    previousEpoch = epoch;
    previousOrganism = org;
  }
  return wrap;
}

function renderOrganismContinuity(organisms) {
  if (!organisms?.length) return emptyState('No persisted Symbiont identities found.');

  const wrap = document.createElement('div');
  wrap.className = 'archive-organism-grid';
  for (const item of organisms) {
    const card = document.createElement('article');
    card.className = 'archive-organism-card';
    card.innerHTML = `
      <p class="eyebrow">Persistent identity</p>
      <h3>${escapeHtml(item?.alias || item?.organism_id || item?.ref || 'Symbiont')}</h3>
      <div class="archive-organism-facts">
        <span>tick <strong>${item?.tick != null ? Number(item.tick).toLocaleString() : '—'}</strong></span>
        <span>epoch <strong>${item?.embodiment_epoch != null ? 'e' + escapeHtml(item.embodiment_epoch) : '—'}</strong></span>
        <span>lifecycle <strong>${escapeHtml(item?.symbiont_state || '—')}</strong></span>
        <span>body <strong>${escapeHtml(item?.body_kind || '—')}</strong></span>
      </div>
    `;
    wrap.appendChild(card);
  }
  return wrap;
}

function renderStudies(rows) {
  if (!rows?.length) return emptyState('No comparative scientific studies recorded yet.');
  const list = document.createElement('div');
  list.className = 'archive-study-list';
  for (const row of rows) {
    const study = row?.study ?? {};
    const interpretation = row?.interpretation ?? {};
    const item = document.createElement('article');
    item.className = 'archive-study-card';
    item.innerHTML = `
      <div>
        <p class="eyebrow">Scientific study</p>
        <h3>${escapeHtml(study?.title || 'Study')}</h3>
        <p>${escapeHtml(interpretation?.summary || 'No interpretation yet.')}</p>
      </div>
      <div class="archive-study-meta">
        <span>${escapeHtml(study?.parameter || '—')}</span>
        <span>${Array.isArray(study?.seeds) ? study.seeds.length : 0} seeds</span>
        <code>${truncateHtml(row?.record_id || '—', 22)}</code>
      </div>
    `;
    list.appendChild(item);
  }
  return list;
}

function archivePanel(title, subtitle, content) {
  const panel = document.createElement('article');
  panel.className = 'panel card-panel archive-v2-panel';
  panel.innerHTML = `
    <div class="panel-title">${escapeHtml(title)}</div>
    ${subtitle ? `<p class="archive-panel-sub">${escapeHtml(subtitle)}</p>` : ''}
  `;
  panel.appendChild(content);
  return panel;
}

export function renderArchive(root, state = null, catalog = { runs: [], organisms: [] }, error = null) {
  const prevScroll = root.querySelector('.view-shell')?.scrollTop ?? 0;
  root.replaceChildren();

  const shell = document.createElement('div');
  shell.className = 'view-shell archive-shell archive-v2';

  const header = document.createElement('header');
  header.className = 'view-header';
  header.innerHTML = `
    <div>
      <p class="eyebrow">Archive</p>
      <h1>Developmental history</h1>
      <p class="view-subtitle">The persistent biography of each Symbiont: embodiments, Experiences, Worlds and scientific evidence.</p>
    </div>
  `;
  shell.appendChild(header);

  if (error) {
    const note = document.createElement('div');
    note.className = 'archive-load-warning';
    note.textContent = `Persisted run catalog could not be refreshed: ${error.message}`;
    shell.appendChild(note);
  }

  shell.appendChild(archivePanel(
    'Symbiont continuity',
    'Identity persists across bodies; the current body is one epoch in that history.',
    renderOrganismContinuity(catalog.organisms ?? []),
  ));

  shell.appendChild(archivePanel(
    'Developmental timeline',
    'Experience and World runs ordered as organism history. Termination is evidence, not a score.',
    renderDevelopmentTimeline(catalog.runs ?? [], catalog.organisms ?? []),
  ));

  shell.appendChild(archivePanel(
    'Scientific studies',
    'Observer-side comparative evidence and preregistered analyses.',
    renderStudies(state?.study?.records ?? []),
  ));

  root.appendChild(shell);

  if (prevScroll > 0) {
    shell.scrollTop = prevScroll;
    requestAnimationFrame(() => { shell.scrollTop = prevScroll; });
  }
}
