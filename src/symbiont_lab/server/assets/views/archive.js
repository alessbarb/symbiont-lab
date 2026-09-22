/**
 * Archive view for the unified Symbiont Lab interface.
 * Displays completed recordings and comparative studies.
 */

function trunc(value, max = 58) {
  const text = value == null ? '—' : String(value);
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function percent(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function renderTable(rows, emptyMessage) {
  if (!rows || rows.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = emptyMessage;
    return empty;
  }

  const table = document.createElement('table');
  table.className = 'data-table';
  const head = document.createElement('thead');
  head.innerHTML = `
    <tr>
      <th>ID</th>
      <th>Title</th>
      <th>Seed</th>
      <th>Detection</th>
      <th>Precision</th>
      <th>Drift FP</th>
    </tr>
  `;

  const body = document.createElement('tbody');
  for (const row of rows) {
    const metrics = row?.metrics ?? {};
    const spec = row?.spec ?? {};
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${trunc(row?.record_id ?? '—', 18)}</td>
      <td>${trunc(spec?.title ?? 'Unnamed run', 28)}</td>
      <td>${spec?.seed ?? '—'}</td>
      <td>${percent(metrics?.detection_rate)}</td>
      <td>${percent(metrics?.precision)}</td>
      <td>${percent(metrics?.recent_drift_false_positive_rate)}</td>
    `;
    body.appendChild(tr);
  }

  table.appendChild(head);
  table.appendChild(body);
  return table;
}

function renderStudyTable(rows, emptyMessage) {
  if (!rows || rows.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = emptyMessage;
    return empty;
  }

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
            <td>${trunc(study?.title ?? 'Study', 24)}</td>
            <td>${trunc(study?.parameter ?? '—', 18)}</td>
            <td>${Array.isArray(study?.seeds) ? study.seeds.length : 0}</td>
            <td>${trunc(row?.record_id ?? '—', 16)}</td>
            <td>${trunc(interpretation?.summary ?? 'No interpretation yet.', 60)}</td>
          </tr>
        `;
      }).join('')}
    </tbody>
  `;
  return table;
}

export function mount(root, state = null) {
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

  const runPanel = document.createElement('article');
  runPanel.className = 'panel card-panel';
  runPanel.innerHTML = `
    <div class="panel-title">Recorded runs</div>
  `;
  runPanel.appendChild(renderTable(state?.records ?? [], 'No experiments recorded yet.'));

  const studyPanel = document.createElement('article');
  studyPanel.className = 'panel card-panel';
  studyPanel.innerHTML = `
    <div class="panel-title">Comparative studies</div>
  `;
  studyPanel.appendChild(renderStudyTable(state?.study?.records ?? [], 'No comparative studies recorded yet.'));

  grid.appendChild(runPanel);
  grid.appendChild(studyPanel);
  shell.appendChild(grid);
  root.appendChild(shell);
}

export function update(root, state) {
  mount(root, state);
}
