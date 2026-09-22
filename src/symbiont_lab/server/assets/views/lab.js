/**
 * Lab view for the unified Symbiont Lab interface.
 * Provides a working experiment/study launch form connected to the server API.
 */

function kv(label, value) {
  const row = document.createElement('div');
  row.className = 'metric-row';
  row.innerHTML = `
    <span>${label}</span>
    <strong>${value}</strong>
  `;
  return row;
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatNumber(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(digits);
}

function chip(text, tone = 'info') {
  const node = document.createElement('span');
  node.className = `chip ${tone}`;
  node.textContent = text;
  return node;
}

function valueOf(obj, key, fallback = '') {
  const value = obj?.[key];
  return value ?? fallback;
}

function readFormValues(form) {
  const output = {};
  new FormData(form).forEach((value, key) => {
    output[key] = value;
  });
  return output;
}

async function submitExperiment(form) {
  const payload = readFormValues(form);
  const body = {
    title: payload.title || 'Untitled experiment',
    hypothesis: payload.hypothesis || '',
    success_criteria: payload.success_criteria || '',
    notes: payload.notes || '',
    hosts: Number(payload.hosts || 100),
    steps: Number(payload.steps || 300),
    seed: Number(payload.seed || 7),
    threat_rate: Number(payload.threat_rate || 0.018),
    poison_fraction: Number(payload.poison_fraction || 0.08),
    heterogeneity: Number(payload.heterogeneity || 0.12),
    drift_step: payload.drift_step === '' ? null : Number(payload.drift_step || 0),
    drift_fraction: Number(payload.drift_fraction || 0.35),
    drift_magnitude: Number(payload.drift_magnitude || 0.22),
    delay: Number(payload.delay || 0.04),
  };

  const response = await fetch('/api/experiments/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || 'Unable to start experiment.');
  }

  return data;
}

async function submitStudy(form) {
  const payload = readFormValues(form);
  const body = {
    title: payload.title || 'Untitled experiment',
    hypothesis: payload.hypothesis || '',
    success_criteria: payload.success_criteria || '',
    notes: payload.notes || '',
    hosts: Number(payload.hosts || 100),
    steps: Number(payload.steps || 300),
    seed: Number(payload.seed || 7),
    threat_rate: Number(payload.threat_rate || 0.018),
    poison_fraction: Number(payload.poison_fraction || 0.08),
    heterogeneity: Number(payload.heterogeneity || 0.12),
    drift_step: payload.drift_step === '' ? null : Number(payload.drift_step || 0),
    drift_fraction: Number(payload.drift_fraction || 0.35),
    drift_magnitude: Number(payload.drift_magnitude || 0.22),
    delay: Number(payload.delay || 0.04),
    study_title: payload.study_title || 'Comparative study',
    parameter: payload.parameter || 'poison_fraction',
    baseline: Number(payload.baseline || 0),
    variant: Number(payload.variant || 0.12),
    seeds: (payload.seeds || '3,7,11').split(',').map((item) => Number(item.trim())).filter((item) => Number.isFinite(item)),
  };

  const response = await fetch('/api/studies/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || 'Unable to start study.');
  }

  return data;
}

function createField({ name, label, type = 'text', value, min, step, placeholder, options = [] }) {
  const wrap = document.createElement('label');
  wrap.className = 'field';

  const text = document.createElement('span');
  text.className = 'field-label';
  text.textContent = label;
  wrap.appendChild(text);

  if (type === 'select') {
    const select = document.createElement('select');
    select.name = name;
    select.value = value || '';
    for (const option of options) {
      const node = document.createElement('option');
      node.value = option.value;
      node.textContent = option.label;
      if (String(option.value) === String(value)) node.selected = true;
      select.appendChild(node);
    }
    wrap.appendChild(select);
  } else {
    const input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
    input.name = name;
    if (type !== 'textarea') {
      input.setAttribute('type', type);
    } else {
      input.setAttribute('type', 'text');
    }
    input.value = value ?? '';
    if (min !== undefined) input.min = String(min);
    if (step !== undefined) input.step = String(step);
    if (placeholder) input.placeholder = placeholder;
    if (type === 'textarea') {
      input.rows = 3;
    }
    wrap.appendChild(input);
  }

  return wrap;
}

function renderExperimentForm(spec) {
  const form = document.createElement('form');
  form.className = 'lab-form';

  const grid = document.createElement('div');
  grid.className = 'field-grid';

  const fields = [
    { name: 'title', label: 'Title', value: valueOf(spec, 'title', 'Curiosity under drift') },
    { name: 'hosts', label: 'Hosts', type: 'number', value: valueOf(spec, 'hosts', 100), min: 1 },
    { name: 'steps', label: 'Steps', type: 'number', value: valueOf(spec, 'steps', 300), min: 1 },
    { name: 'seed', label: 'Seed', type: 'number', value: valueOf(spec, 'seed', 7), min: 0 },
    { name: 'threat_rate', label: 'Threat rate', type: 'number', value: valueOf(spec, 'threat_rate', 0.018), min: 0, step: 0.001 },
    { name: 'poison_fraction', label: 'Poison fraction', type: 'number', value: valueOf(spec, 'poison_fraction', 0.08), min: 0, step: 0.01 },
    { name: 'heterogeneity', label: 'Heterogeneity', type: 'number', value: valueOf(spec, 'heterogeneity', 0.12), min: 0, step: 0.01 },
    { name: 'drift_step', label: 'Drift step', type: 'number', value: spec?.drift_step ?? '', min: -1, step: 1 },
    { name: 'drift_fraction', label: 'Drift fraction', type: 'number', value: valueOf(spec, 'drift_fraction', 0.35), min: 0, step: 0.01 },
    { name: 'drift_magnitude', label: 'Drift magnitude', type: 'number', value: valueOf(spec, 'drift_magnitude', 0.22), min: 0, step: 0.01 },
    { name: 'delay', label: 'Delay / step', type: 'number', value: valueOf(spec, 'delay', 0.04), min: 0, step: 0.01 },
    { name: 'hypothesis', label: 'Hypothesis', type: 'textarea', value: valueOf(spec, 'hypothesis', '') },
    { name: 'success_criteria', label: 'Success criteria', type: 'textarea', value: valueOf(spec, 'success_criteria', '') },
    { name: 'notes', label: 'Notes', type: 'textarea', value: valueOf(spec, 'notes', '') },
  ];

  for (const field of fields) {
    grid.appendChild(createField(field));
  }

  const actions = document.createElement('div');
  actions.className = 'button-row';

  const button = document.createElement('button');
  button.type = 'submit';
  button.className = 'btn btn-primary';
  button.textContent = 'Launch experiment';

  button.addEventListener('click', async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = 'Launching…';
    try {
      await submitExperiment(form);
      if (window.fetchState) window.fetchState();
    } catch (error) {
      window.alert(error.message || 'Unable to launch experiment.');
    } finally {
      button.disabled = false;
      button.textContent = 'Launch experiment';
    }
  });

  actions.appendChild(button);
  form.appendChild(grid);
  form.appendChild(actions);
  return form;
}

function renderStudyForm(spec) {
  const form = document.createElement('form');
  form.className = 'lab-form';

  const grid = document.createElement('div');
  grid.className = 'field-grid';

  const fields = [
    { name: 'study_title', label: 'Study title', value: 'Poisoning resilience' },
    { name: 'parameter', label: 'Parameter', type: 'select', value: 'poison_fraction', options: [
      { label: 'poison_fraction', value: 'poison_fraction' },
      { label: 'threat_rate', value: 'threat_rate' },
      { label: 'heterogeneity', value: 'heterogeneity' },
      { label: 'drift_fraction', value: 'drift_fraction' },
      { label: 'drift_magnitude', value: 'drift_magnitude' },
    ] },
    { name: 'baseline', label: 'Baseline', type: 'number', value: 0, min: -1, step: 0.01 },
    { name: 'variant', label: 'Variant', type: 'number', value: 0.12, min: -1, step: 0.01 },
    { name: 'seeds', label: 'Seeds', value: '3,7,11,17,23' },
  ];

  for (const field of fields) {
    grid.appendChild(createField(field));
  }

  const actions = document.createElement('div');
  actions.className = 'button-row';

  const button = document.createElement('button');
  button.type = 'submit';
  button.className = 'btn btn-primary';
  button.textContent = 'Launch comparative study';

  button.addEventListener('click', async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = 'Launching…';
    try {
      await submitStudy(form);
      if (window.fetchState) window.fetchState();
    } catch (error) {
      window.alert(error.message || 'Unable to launch study.');
    } finally {
      button.disabled = false;
      button.textContent = 'Launch comparative study';
    }
  });

  actions.appendChild(button);
  form.appendChild(grid);
  form.appendChild(actions);
  return form;
}

function renderPanel(root, state) {
  root.innerHTML = '';

  const current = state?.current ?? {};
  const spec = state?.spec ?? {};
  const study = state?.study ?? {};
  const status = state?.running ? 'Live' : state?.finished ? 'Completed' : 'Ready';

  const shell = document.createElement('div');
  shell.className = 'view-shell lab-shell';

  const heading = document.createElement('header');
  heading.className = 'view-header';
  heading.innerHTML = `
    <div>
      <p class="eyebrow">Lab</p>
      <h1>Unified experiment workbench</h1>
    </div>
    <div class="header-actions">
      ${chip(status, state?.running ? 'success' : 'info')}
      ${chip(`Run #${state?.experiment_number ?? 0}`, 'muted')}
    </div>
  `;
  shell.appendChild(heading);

  const hero = document.createElement('section');
  hero.className = 'lab-hero';
  hero.innerHTML = `
    <div class="hero-copy">
      <p class="eyebrow">Organism status</p>
      <h2>Single-body analysis loop</h2>
      <p>Launch experiments, monitor the embodied agent, and inspect the live cognitive state from one local workbench.</p>
    </div>
    <div class="hero-stats">
      <div class="status-line">
        <span><span class="dot ${state?.running ? 'running' : 'live'}"></span> ${state?.running ? 'Running' : 'Ready'}</span>
        <strong>${state?.experiment_number ?? 0}</strong>
      </div>
      <div class="status-line">
        <span>Study phase</span>
        <strong>${study?.phase ?? 'idle'}</strong>
      </div>
      <div class="status-line">
        <span>Completion</span>
        <strong>${current?.step != null && current?.total_steps ? `${((current.step / current.total_steps) * 100).toFixed(1)}%` : '0.0%'}</strong>
      </div>
    </div>
  `;
  shell.appendChild(hero);

  const overview = document.createElement('section');
  overview.className = 'panel-grid';

  const cards = [
    { label: 'Progress', value: current?.step != null && current?.total_steps ? `${((current.step / current.total_steps) * 100).toFixed(1)}%` : '0.0%', tone: 'primary' },
    { label: 'Curiosity', value: formatNumber(current?.curiosity_focus ?? 0, 2), tone: 'accent' },
    { label: 'Epistemic pressure', value: formatPercent(current?.epistemic_pressure ?? 0), tone: 'warning' },
    { label: 'Self confidence', value: formatPercent(current?.self_confidence ?? 0), tone: 'success' },
    { label: 'Mean novelty', value: formatPercent(current?.mean_novelty ?? 0), tone: 'info' },
    { label: 'Drift FP', value: formatPercent(current?.recent_drift_false_positive_rate ?? 0), tone: 'danger' },
  ];

  for (const card of cards) {
    const item = document.createElement('article');
    item.className = `kpi-card ${card.tone}`;
    item.innerHTML = `
      <div class="kpi-label">${card.label}</div>
      <div class="kpi-value">${card.value}</div>
    `;
    overview.appendChild(item);
  }

  shell.appendChild(overview);

  const launcher = document.createElement('section');
  launcher.className = 'lab-launcher';

  const experimentPanel = document.createElement('article');
  experimentPanel.className = 'panel card-panel';
  const exTitle = document.createElement('div');
  exTitle.className = 'panel-title';
  exTitle.textContent = 'Single experiment';
  experimentPanel.appendChild(exTitle);
  experimentPanel.appendChild(renderExperimentForm(spec));

  const studyPanel = document.createElement('article');
  studyPanel.className = 'panel card-panel';
  const stTitle = document.createElement('div');
  stTitle.className = 'panel-title';
  stTitle.textContent = 'Comparative study';
  studyPanel.appendChild(stTitle);
  studyPanel.appendChild(renderStudyForm(spec));

  launcher.appendChild(experimentPanel);
  launcher.appendChild(studyPanel);
  shell.appendChild(launcher);

  const detail = document.createElement('section');
  detail.className = 'two-column';

  const mainPanel = document.createElement('article');
  mainPanel.className = 'panel card-panel';
  mainPanel.innerHTML = `
    <div class="panel-title">Live experiment summary</div>
    <div class="meta-grid">
      <div><label>Title</label><strong>${spec.title || 'Untitled experiment'}</strong></div>
      <div><label>Seed</label><strong>${spec.seed ?? '—'}</strong></div>
      <div><label>Hosts</label><strong>${spec.hosts ?? '—'}</strong></div>
      <div><label>Steps</label><strong>${spec.steps ?? '—'}</strong></div>
      <div><label>Threat rate</label><strong>${formatNumber(spec.threat_rate ?? 0, 3)}</strong></div>
      <div><label>Poison fraction</label><strong>${formatNumber(spec.poison_fraction ?? 0, 3)}</strong></div>
      <div><label>Heterogeneity</label><strong>${formatNumber(spec.heterogeneity ?? 0, 3)}</strong></div>
      <div><label>Drift step</label><strong>${spec.drift_step ?? '—'}</strong></div>
    </div>
    <div class="block-copy">
      <h4>Hypothesis</h4>
      <p>${spec.hypothesis || 'No hypothesis recorded.'}</p>
    </div>
  `;

  const sidePanel = document.createElement('aside');
  sidePanel.className = 'panel card-panel';
  sidePanel.innerHTML = `
    <div class="panel-title">Current run</div>
    ${kv('Detection', formatPercent(current?.detection_rate ?? 0))}
    ${kv('Precision', formatPercent(current?.precision ?? 0))}
    ${kv('Open questions', current?.open_questions ?? 0)}
    ${kv('Signals', current?.curiosity_probes?.length ?? 0)}
    ${kv('Adaptations', current?.drift_adaptations ?? 0)}
    ${kv('Memory', current?.consolidated_episodes ?? 0)}
    <div class="block-copy">
      <h4>Study status</h4>
      <p>${study?.phase ? `${study.phase}` : 'No study active.'}</p>
    </div>
  `;

  detail.appendChild(mainPanel);
  detail.appendChild(sidePanel);
  shell.appendChild(detail);
  root.appendChild(shell);
}

export function mount(root, state = null) {
  root.innerHTML = '';
  renderPanel(root, state);
}

export function update(root, state) {
  renderPanel(root, state);
}
