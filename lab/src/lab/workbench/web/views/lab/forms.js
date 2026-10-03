import { submitExperiment, submitStudy } from './api.js';

function valueOf(obj, key, fallback = '') {
  return obj?.[key] ?? fallback;
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
    return wrap;
  }

  const input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
  input.name = name;
  input.value = value ?? '';
  if (type !== 'textarea') input.type = type;
  if (min !== undefined) input.min = String(min);
  if (step !== undefined) input.step = String(step);
  if (placeholder) input.placeholder = placeholder;
  if (type === 'textarea') input.rows = 3;
  wrap.appendChild(input);
  return wrap;
}

function launchButton({ form, idleText, pendingText, action, failureText }) {
  const actions = document.createElement('div');
  actions.className = 'button-row';

  const button = document.createElement('button');
  button.type = 'submit';
  button.className = 'btn btn-primary';
  button.textContent = idleText;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = pendingText;
    try {
      await action(form);
      if (window.fetchState) window.fetchState();
    } catch (error) {
      window.alert(error.message || failureText);
    } finally {
      button.disabled = false;
      button.textContent = idleText;
    }
  });

  actions.appendChild(button);
  return actions;
}

export function renderExperimentForm(spec = {}) {
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
  for (const field of fields) grid.appendChild(createField(field));

  form.appendChild(grid);
  form.appendChild(launchButton({
    form,
    idleText: 'Launch experiment',
    pendingText: 'Launching…',
    action: submitExperiment,
    failureText: 'Unable to launch experiment.',
  }));
  return form;
}

export function renderStudyForm() {
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
  for (const field of fields) grid.appendChild(createField(field));

  form.appendChild(grid);
  form.appendChild(launchButton({
    form,
    idleText: 'Launch comparative study',
    pendingText: 'Launching…',
    action: submitStudy,
    failureText: 'Unable to launch study.',
  }));
  return form;
}
