import { el } from '../shared/dom.js';
import { PAL } from './config.js';
import { panelSection } from './components.js';
import { currentMotorOutputEdges, currentPhysiologyState } from './derived.js';
import { graph, milestones, mindHistory, snap, tel } from './state.js';
import { pct } from './util.js';

function nodeActivity(node) {
  const candidates = [node?.activity, node?.activation, node?.salience, node?.strength];
  for (const value of candidates) {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return 0;
}

function metric(label, value, tone = 'neutral') {
  const card = el('div', `mind-live-metric ${tone}`);
  const l = el('span', 'mind-live-metric-label');
  l.textContent = label;
  const v = el('strong', 'mind-live-metric-value');
  v.textContent = String(value ?? '—');
  card.append(l, v);
  return card;
}

function deltaText(current, previous) {
  if (!Number.isFinite(current) || !Number.isFinite(previous)) return '—';
  const d = current - previous;
  return d === 0 ? 'no change' : `${d > 0 ? '+' : ''}${d}`;
}

function cognitiveLabel(node) {
  return node?.observer_label || node?.semantic_label || node?.label || node?.id || node?.kind || 'unknown';
}

export function renderOverview({ onOpenHistoryTick = () => {} } = {}) {
  const root = document.getElementById('mind-overview-wrap');
  if (!root) return;
  const prevScroll = root.scrollTop;
  root.replaceChildren();

  const topology = snap.topology ?? { nodes: [], edges: [] };
  const nodes = topology.nodes ?? [];
  const edges = topology.edges ?? [];
  const concepts = nodes.filter(node => node.kind === 'concept').length;
  const predictors = nodes.filter(node => node.kind === 'predictor').length;
  const readouts = nodes.filter(node => node.kind === 'readout').length;
  const activeNodes = [...nodes]
    .filter(node => nodeActivity(node) > 0)
    .sort((a,b) => nodeActivity(b) - nodeActivity(a))
    .slice(0, 6);
  const physiology = currentPhysiologyState();
  const currentPoint = mindHistory.at(-1) ?? null;
  const previousPoint = mindHistory.length > 1 ? mindHistory.at(-2) : null;
  const latestMilestone = milestones.at(-1) ?? null;
  const recentEvents = (graph.cognitiveEvents ?? []).slice(-5).reverse();
  const energy = tel.metabolicReserve;
  const motorEdges = currentMotorOutputEdges(topology);

  const head = el('div', 'mind-live-head');
  const copy = el('div', '');
  const eyebrow = el('div', 'mind-live-eyebrow');
  eyebrow.textContent = 'MIND · LIVE';
  const title = el('h2', '');
  title.textContent = 'What is happening now';
  const sub = el('p', '');
  sub.textContent = 'Current cognitive activity, recent structural change and what the organism can presently reuse.';
  copy.append(eyebrow, title, sub);
  const state = el('strong', 'mind-live-state');
  state.textContent = [
    String(physiology || 'unknown').toUpperCase(),
    tel.embodimentEpoch != null ? `E${tel.embodimentEpoch}` : null,
    tel.tick != null ? `t${Number(tel.tick).toLocaleString()}` : null,
  ].filter(Boolean).join(' · ');
  head.append(copy, state);
  root.appendChild(head);

  const metrics = el('div', 'mind-live-metrics');
  metrics.append(
    metric('Concepts', concepts, 'violet'),
    metric('Predictors', predictors, 'amber'),
    metric('Relations', edges.length, 'cyan'),
    metric('Readouts', readouts, 'mint'),
    metric('Motor links', motorEdges, 'mint'),
    metric('Energy', energy != null ? pct(energy) : '—', energy != null && energy < .2 ? 'coral' : 'mint'),
  );
  root.appendChild(metrics);

  const grid = el('div', 'mind-live-grid');

  const active = panelSection('Active now', 'Most active cognitive structures in the current observer projection.');
  active.classList.add('mind-live-panel');
  if (!activeNodes.length) {
    const empty = el('div', 'mind-live-empty');
    empty.textContent = 'No currently active cognitive nodes are exported in this frame.';
    active.appendChild(empty);
  } else {
    const list = el('div', 'mind-live-list');
    for (const item of activeNodes) {
      const row = el('div', 'mind-live-row');
      const left = el('div', '');
      const kind = el('span', '');
      kind.textContent = item.kind || 'node';
      const name = el('strong', '');
      name.textContent = cognitiveLabel(item);
      left.append(kind, name);
      const amount = el('b', '');
      amount.textContent = nodeActivity(item).toFixed(2);
      row.append(left, amount);
      list.appendChild(row);
    }
    active.appendChild(list);
  }

  const change = panelSection('Recent change', 'Difference between the latest two observed Mind frames.');
  change.classList.add('mind-live-panel');
  const changeGrid = el('div', 'mind-live-change-grid');
  changeGrid.append(
    metric('Concepts Δ', deltaText(currentPoint?.concepts, previousPoint?.concepts)),
    metric('Predictors Δ', deltaText(currentPoint?.predictors, previousPoint?.predictors)),
    metric('Relations Δ', deltaText(currentPoint?.edges, previousPoint?.edges)),
    metric('Motor edges Δ', deltaText(currentPoint?.motorEdges, previousPoint?.motorEdges)),
  );
  change.appendChild(changeGrid);
  const origin = el('div', 'mind-live-context-line');
  origin.innerHTML = `<span>Motor origin</span><strong>${String(tel.motorOrigin ?? 'none')}</strong><span>Prediction error</span><strong>${Number.isFinite(Number(tel.predictionError)) ? Number(tel.predictionError).toFixed(3) : '—'}</strong>`;
  change.appendChild(origin);

  grid.append(active, change);
  root.appendChild(grid);

  const flow = el('div', 'mind-live-grid');

  const eventsPanel = panelSection('Recent cognitive events', 'Observer-visible structural events; they are not instructions to the organism.');
  eventsPanel.classList.add('mind-live-panel');
  if (!recentEvents.length) {
    const empty = el('div', 'mind-live-empty');
    empty.textContent = 'No recent cognitive events are currently exported.';
    eventsPanel.appendChild(empty);
  } else {
    const list = el('div', 'mind-live-events');
    for (const event of recentEvents) {
      const row = el('div', 'mind-live-event');
      const when = el('span', '');
      when.textContent = event.tick != null ? `t${event.tick}` : 'live';
      const text = el('strong', '');
      text.textContent = event.label || event.title || event.kind || event.type || 'cognitive change';
      row.append(when, text);
      list.appendChild(row);
    }
    eventsPanel.appendChild(list);
  }

  const development = panelSection('Current developmental position', 'Capability exists only when evidence supports it; absence here is not filled from observer truth.');
  development.classList.add('mind-live-panel');
  const dev = el('div', 'mind-development-now');
  const sensoryCount = snap.sensoryPhenotype?.sensors?.length ?? nodes.filter(node => node.kind === 'sense').length;
  const patterns = Number(tel.sensorimotorPatterns ?? snap.sensorimotor?.known_patterns ?? 0);
  const competences = Number(tel.motorCompetences ?? snap.sensorimotor?.competence_chunks ?? 0);
  for (const [label, value, detail] of [
    ['Perception', sensoryCount, 'senses represented'],
    ['Regularities', patterns, 'sensorimotor patterns'],
    ['Prediction', predictors, 'current predictor structures'],
    ['Competence', competences, 'motor competences'],
  ]) {
    const row = el('div', 'mind-development-step');
    row.innerHTML = `<span>${label}</span><strong>${value}</strong><small>${detail}</small>`;
    dev.appendChild(row);
  }
  development.appendChild(dev);
  if (latestMilestone) {
    const milestone = el('button', 'mind-live-milestone');
    milestone.type = 'button';
    milestone.innerHTML = `<span>Latest milestone · t${latestMilestone.tick}</span><strong>${latestMilestone.label}</strong>`;
    milestone.addEventListener('click', () => onOpenHistoryTick(latestMilestone.tick));
    development.appendChild(milestone);
  }

  flow.append(eventsPanel, development);
  root.appendChild(flow);

  const context = el('div', 'mind-live-context');
  context.innerHTML = `
    <span>Physiology <strong>${String(physiology || '—')}</strong></span>
    <span>Embodiment <strong>${tel.embodimentEpoch != null ? 'e' + tel.embodimentEpoch : '—'}</strong></span>
    <span>Reacclimation <strong>${tel.reacclimating ? (tel.reacclimationRemaining ?? 'active') : 'no'}</strong></span>
    <span>Observer <strong>passive</strong></span>
  `;
  root.appendChild(context);

  if (prevScroll > 0) {
    root.scrollTop = prevScroll;
    requestAnimationFrame(() => { root.scrollTop = prevScroll; });
  }
}
