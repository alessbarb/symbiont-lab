import { escapeHtml } from '../shared/dom.js';
import { formatNumber, formatPercent } from '../shared/format.js';
import { renderExperimentForm, renderStudyForm } from './forms.js';

function metricRow(label, value) {
  return `<div class="metric-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function chip(text, tone = 'info') {
  return `<span class="chip ${escapeHtml(tone)}">${escapeHtml(text)}</span>`;
}

function completion(current) {
  return current?.step != null && current?.total_steps
    ? `${((current.step / current.total_steps) * 100).toFixed(1)}%`
    : '0.0%';
}

function appendPanelTitle(panel, title) {
  const node = document.createElement('div');
  node.className = 'panel-title';
  node.textContent = title;
  panel.appendChild(node);
}

export function renderLab(root, state) {
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
      <div class="status-line"><span>Study phase</span><strong>${escapeHtml(study?.phase ?? 'idle')}</strong></div>
      <div class="status-line"><span>Completion</span><strong>${completion(current)}</strong></div>
    </div>
  `;
  shell.appendChild(hero);

  const overview = document.createElement('section');
  overview.className = 'panel-grid';
  const cards = [
    { label: 'Progress', value: completion(current), tone: 'primary' },
    { label: 'Curiosity', value: formatNumber(current?.curiosity_focus ?? 0, 2), tone: 'accent' },
    { label: 'Epistemic pressure', value: formatPercent(current?.epistemic_pressure ?? 0), tone: 'warning' },
    { label: 'Self confidence', value: formatPercent(current?.self_confidence ?? 0), tone: 'success' },
    { label: 'Mean novelty', value: formatPercent(current?.mean_novelty ?? 0), tone: 'info' },
    { label: 'Drift FP', value: formatPercent(current?.recent_drift_false_positive_rate ?? 0), tone: 'danger' },
  ];
  for (const card of cards) {
    const item = document.createElement('article');
    item.className = `kpi-card ${card.tone}`;
    item.innerHTML = `<div class="kpi-label">${card.label}</div><div class="kpi-value">${card.value}</div>`;
    overview.appendChild(item);
  }
  shell.appendChild(overview);

  const launcher = document.createElement('section');
  launcher.className = 'lab-launcher';

  const experimentPanel = document.createElement('article');
  experimentPanel.className = 'panel card-panel';
  appendPanelTitle(experimentPanel, 'Single experiment');
  experimentPanel.appendChild(renderExperimentForm(spec));

  const studyPanel = document.createElement('article');
  studyPanel.className = 'panel card-panel';
  appendPanelTitle(studyPanel, 'Comparative study');
  studyPanel.appendChild(renderStudyForm());

  launcher.append(experimentPanel, studyPanel);
  shell.appendChild(launcher);

  const detail = document.createElement('section');
  detail.className = 'two-column';

  const mainPanel = document.createElement('article');
  mainPanel.className = 'panel card-panel';
  mainPanel.innerHTML = `
    <div class="panel-title">Live experiment summary</div>
    <div class="meta-grid">
      <div><label>Title</label><strong>${escapeHtml(spec.title || 'Untitled experiment')}</strong></div>
      <div><label>Seed</label><strong>${spec.seed ?? '—'}</strong></div>
      <div><label>Hosts</label><strong>${spec.hosts ?? '—'}</strong></div>
      <div><label>Steps</label><strong>${spec.steps ?? '—'}</strong></div>
      <div><label>Threat rate</label><strong>${formatNumber(spec.threat_rate ?? 0, 3)}</strong></div>
      <div><label>Poison fraction</label><strong>${formatNumber(spec.poison_fraction ?? 0, 3)}</strong></div>
      <div><label>Heterogeneity</label><strong>${formatNumber(spec.heterogeneity ?? 0, 3)}</strong></div>
      <div><label>Drift step</label><strong>${spec.drift_step ?? '—'}</strong></div>
    </div>
    <div class="block-copy"><h4>Hypothesis</h4><p>${escapeHtml(spec.hypothesis || 'No hypothesis recorded.')}</p></div>
  `;

  const sidePanel = document.createElement('aside');
  sidePanel.className = 'panel card-panel';
  sidePanel.innerHTML = `
    <div class="panel-title">Current run</div>
    ${metricRow('Detection', formatPercent(current?.detection_rate ?? 0))}
    ${metricRow('Precision', formatPercent(current?.precision ?? 0))}
    ${metricRow('Open questions', current?.open_questions ?? 0)}
    ${metricRow('Signals', current?.curiosity_probes?.length ?? 0)}
    ${metricRow('Adaptations', current?.drift_adaptations ?? 0)}
    ${metricRow('Memory', current?.consolidated_episodes ?? 0)}
    <div class="block-copy"><h4>Study status</h4><p>${escapeHtml(study?.phase ? `${study.phase}` : 'No study active.')}</p></div>
  `;

  detail.append(mainPanel, sidePanel);
  shell.appendChild(detail);
  root.appendChild(shell);
}
