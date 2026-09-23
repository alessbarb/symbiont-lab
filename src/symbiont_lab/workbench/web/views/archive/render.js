import { escapeHtml } from '../shared/dom.js';
import { formatPercent, truncateHtml } from '../shared/format.js';

function emptyState(message) {
  const empty = document.createElement('div');
  empty.className = 'empty-state';
  empty.textContent = message;
  return empty;
}

function renderRunTable(rows, emptyMessage) {
  if (!rows?.length) return emptyState(emptyMessage);

  const table = document.createElement('table');
  table.className = 'data-table';
  table.innerHTML = `
    <thead>
      <tr>
        <th>ID</th>
        <th>Title</th>
        <th>Seed</th>
        <th>Detection</th>
        <th>Precision</th>
        <th>Drift FP</th>
      </tr>
    </thead>
  `;

  const body = document.createElement('tbody');
  for (const row of rows) {
    const metrics = row?.metrics ?? {};
    const spec = row?.spec ?? {};
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${truncateHtml(row?.record_id ?? '—', 18)}</td>
      <td>${truncateHtml(spec?.title ?? 'Unnamed run', 28)}</td>
      <td>${escapeHtml(spec?.seed ?? '—')}</td>
      <td>${formatPercent(metrics?.detection_rate)}</td>
      <td>${formatPercent(metrics?.precision)}</td>
      <td>${formatPercent(metrics?.recent_drift_false_positive_rate)}</td>
    `;
    body.appendChild(tr);
  }
  table.appendChild(body);
  return table;
}

function renderStudyTable(rows, emptyMessage) {
  if (!rows?.length) return emptyState(emptyMessage);

  const table = document.createElement('table');
  table.className = 'data-table';
  table.innerHTML = `
    <thead>
      <tr>
        <th>Study</th>
        <th>Parameter</th>
        <th>Seeds</th>
        <th>Status</th>
        <th>Summary</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map((row) => {
        const study = row?.study ?? {};
        const interpretation = row?.interpretation ?? {};
        return `
          <tr>
            <td>${truncateHtml(study?.title ?? 'Study', 24)}</td>
            <td>${truncateHtml(study?.parameter ?? '—', 18)}</td>
            <td>${Array.isArray(study?.seeds) ? study.seeds.length : 0}</td>
            <td>${truncateHtml(row?.record_id ?? '—', 16)}</td>
            <td>${truncateHtml(interpretation?.summary ?? 'No interpretation yet.', 60)}</td>
          </tr>
        `;
      }).join('')}
    </tbody>
  `;
  return table;
}

function archivePanel(title, content) {
  const panel = document.createElement('article');
  panel.className = 'panel card-panel';
  panel.innerHTML = `<div class="panel-title">${escapeHtml(title)}</div>`;
  panel.appendChild(content);
  return panel;
}

export function renderArchive(root, state = null) {
  root.innerHTML = '';

  const shell = document.createElement('div');
  shell.className = 'view-shell archive-shell';

  const header = document.createElement('header');
  header.className = 'view-header';
  header.innerHTML = `
    <div>
      <p class="eyebrow">Archive</p>
      <h1>Experiment and study history</h1>
    </div>
  `;
  shell.appendChild(header);

  const grid = document.createElement('div');
  grid.className = 'archive-grid';
  grid.append(
    archivePanel(
      'Recorded runs',
      renderRunTable(state?.records ?? [], 'No experiments recorded yet.'),
    ),
    archivePanel(
      'Comparative studies',
      renderStudyTable(
        state?.study?.records ?? [],
        'No comparative studies recorded yet.',
      ),
    ),
  );

  shell.appendChild(grid);
  root.appendChild(shell);
}
