import { el, svgEl } from '../shared/dom.js';
import { PAL, REGIMES } from './config.js';
import { inspectorMetric, panelSection } from './components.js';
import { currentMotorOutputEdges, currentPhysiologyState } from './derived.js';
import { computeObserverMapCoordinates, evaluateObserverRegime } from './observer-map-model.js';
import {
  historySnapshots,
  milestones,
  mindHistory,
  selfDependencyHistory,
  selfRegionHistory,
  snap,
  tel,
} from './state.js';
import { finiteNumber, pct } from './util.js';
import { deriveCognitiveEpisodes } from './cognitive-temporal.js';
import { episodeImpact } from './cognitive-refinement.js';

let activeEpisodeId = null;

function episodeEventWeight(event) {
  const diff = event?.diff;
  const structural = diff ? (
    (diff.addedNodes?.length ?? 0) * 2 +
    (diff.removedNodes?.length ?? 0) * 2 +
    (diff.addedEdges?.length ?? 0) * 0.45 +
    (diff.removedEdges?.length ?? 0) * 0.45 +
    (diff.changedEdges?.length ?? 0) * 0.16 +
    (diff.predictionErrorChanges?.length ?? 0) * 0.4
  ) : 0;
  return structural + (event?.contextChanges?.length ?? 0) * 3;
}

function episodeFocusTick(episode) {
  const event = [...(episode?.events ?? [])]
    .sort((a,b) => episodeEventWeight(b) - episodeEventWeight(a))[0];
  return event?.endTick ?? episode?.endTick ?? null;
}

function sparklineSvg(points, key, color, width = 900, height = 90) {
  const svg = svgEl('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img' });
  svg.style.cssText = 'width:100%;height:90px;display:block;';
  if (points.length < 2) return svg;

  const values = points.map((point) => finiteNumber(point[key], 0));
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (Math.abs(hi - lo) < 1e-9) hi = lo + 1;

  const t0 = points[0].tick;
  const t1 = points[points.length - 1].tick || t0 + 1;
  const coords = points.map((point, index) => {
    const x = ((point.tick - t0) / Math.max(1, t1 - t0)) * (width - 20) + 10;
    const y = height - 10 - ((values[index] - lo) / (hi - lo)) * (height - 20);
    return [x, y];
  });
  const path = svgEl('path', {
    d: coords.map((point, index) =>
      `${index ? 'L' : 'M'} ${point[0].toFixed(1)} ${point[1].toFixed(1)}`
    ).join(' '),
    fill: 'none',
    stroke: color,
    'stroke-width': '1.5',
  });
  svg.appendChild(path);
  return svg;
}

export function renderHistory({ onOpenHistoryTick = () => {} } = {}) {
  const root = document.getElementById('mind-history-wrap');
  if (!root) return;
  const prevScroll = root.scrollTop;
  root.replaceChildren();

  const current = mindHistory.at(-1) ?? null;
  const previous = mindHistory.length > 1 ? mindHistory.at(-2) : null;
  const episodes = deriveCognitiveEpisodes(historySnapshots, mindHistory, 160);

  const head = el('div', 'mind-development-head');
  const copy = el('div', '');
  const eyebrow = el('div', 'mind-live-eyebrow');
  eyebrow.textContent = 'MIND · DEVELOPMENT';
  const title = el('h2', '');
  title.textContent = 'How cognition is changing';
  const sub = el('p', '');
  sub.textContent = 'Observed developmental events and structural episodes in organism time. Charts are supporting evidence, not the story itself.';
  copy.append(eyebrow, title, sub);
  const now = el('strong', 'mind-live-state');
  now.textContent = current?.tick != null ? `t${Number(current.tick).toLocaleString()}` : 'NO HISTORY';
  head.append(copy, now);
  root.appendChild(head);

  const changeStrip = el('div', 'mind-live-metrics');
  const diff = (key) => {
    const a = Number(current?.[key]);
    const b = Number(previous?.[key]);
    if (!Number.isFinite(a) || !Number.isFinite(b)) return '—';
    const d = a - b;
    return d === 0 ? '0' : `${d > 0 ? '+' : ''}${d}`;
  };
  const compact = (label, value) => {
    const card = el('div', 'mind-live-metric');
    card.innerHTML = `<span class="mind-live-metric-label">${label}</span><strong class="mind-live-metric-value">${value}</strong>`;
    return card;
  };
  changeStrip.append(
    compact('Concepts Δ', diff('concepts')),
    compact('Predictors Δ', diff('predictors')),
    compact('Relations Δ', diff('edges')),
    compact('Motor links Δ', diff('motorEdges')),
    compact('Self regions', current?.selfRegions ?? '—'),
    compact('Episodes', episodes.length),
  );
  root.appendChild(changeStrip);

  const narrative = panelSection(
    'Developmental narrative',
    'First-observed milestones in organism time. Selecting an event opens the nearest captured cognitive state.',
  );
  narrative.classList.add('mind-development-narrative');
  if (!milestones.length) {
    const empty = el('div', 'mind-live-empty');
    empty.textContent = 'No developmental milestones have been observed in this browser session yet.';
    narrative.appendChild(empty);
  } else {
    const line = el('div', 'mind-development-line');
    for (const milestone of milestones) {
      const event = el('button', 'mind-development-event');
      event.type = 'button';
      event.innerHTML = `
        <span>t${milestone.tick}</span>
        <i></i>
        <strong>${milestone.label}</strong>
      `;
      event.addEventListener('click', () => onOpenHistoryTick(milestone.tick));
      line.appendChild(event);
    }
    narrative.appendChild(line);
  }
  root.appendChild(narrative);

  const episodePanel = panelSection(
    'Cognitive episodes',
    'Observer-derived windows where structural, predictive or contextual change clustered together.',
  );
  episodePanel.classList.add('mind-development-episodes');
  if (!episodes.length) {
    const empty = el('div', 'mind-live-empty');
    empty.textContent = 'No structural episodes captured yet.';
    episodePanel.appendChild(empty);
  } else {
    for (const episode of episodes.slice(-10).reverse()) {
      const impact = episodeImpact(episode);
      const totals = episode.totals;
      const row = el('button', 'mind-development-episode');
      row.type = 'button';
      row.classList.toggle('active', episode.id === activeEpisodeId);
      const changes = [
        totals.addedNodes ? `+${totals.addedNodes} nodes` : null,
        totals.removedNodes ? `−${totals.removedNodes} nodes` : null,
        totals.addedEdges ? `+${totals.addedEdges} relations` : null,
        totals.removedEdges ? `−${totals.removedEdges} relations` : null,
        totals.predictionErrorChanges ? `${totals.predictionErrorChanges} prediction-error changes` : null,
        totals.motorTransitions ? `${totals.motorTransitions} motor transitions` : null,
        totals.physiologyTransitions ? `${totals.physiologyTransitions} physiology transitions` : null,
      ].filter(Boolean);
      row.innerHTML = `
        <div class="mind-development-episode-time">t${episode.startTick}–${episode.endTick}</div>
        <div class="mind-development-episode-body">
          <strong>${impact.dominant || 'structural change'} · ${impact.label} impact</strong>
          <span>${changes.join(' · ') || 'contextual change'}</span>
        </div>
        <div class="mind-development-episode-score">${Math.round(impact.score * 100)}%</div>
      `;
      row.addEventListener('click', () => {
        activeEpisodeId = episode.id;
        const tick = episodeFocusTick(episode);
        if (tick != null) onOpenHistoryTick(tick);
      });
      episodePanel.appendChild(row);
    }
  }
  root.appendChild(episodePanel);

  const measures = document.createElement('details');
  measures.className = 'mind-development-measures';
  const summary = document.createElement('summary');
  summary.textContent = 'Longitudinal measures';
  measures.appendChild(summary);
  const charts = el('div', 'mind-development-charts');
  const energy = panelSection('Energy / physiology');
  energy.appendChild(sparklineSvg(mindHistory.filter(point => point.energy != null), 'energy', PAL.coral));
  const edges = panelSection('Cognitive relations');
  edges.appendChild(sparklineSvg(mindHistory, 'edges', PAL.violet));
  const concepts = panelSection('Concept growth');
  concepts.appendChild(sparklineSvg(mindHistory, 'concepts', PAL.cyan));
  const predictors = panelSection('Predictor growth');
  predictors.appendChild(sparklineSvg(mindHistory, 'predictors', PAL.amber));
  const motor = panelSection('Motor-output relations');
  motor.appendChild(sparklineSvg(mindHistory, 'motorEdges', '#e09f3e'));
  charts.append(energy, edges, concepts, predictors, motor);
  measures.appendChild(charts);
  root.appendChild(measures);

  if (mindHistory.length) {
    const observer = panelSection(
      'Observer analysis',
      'Secondary analytical projection. It is not part of the organism and is never fed back.',
    );
    observer.classList.add('mind-development-observer');
    const coord = computeObserverMapCoordinates({
      senses: snap.senses,
      cognition: snap.cognition,
      observerAnalysis: snap.observerAnalysis,
    });
    const analysis = evaluateObserverRegime(coord, REGIMES);
    inspectorMetric(observer, 'Measured activity', pct(coord.activityNorm));
    inspectorMetric(observer, 'Predictive tension', pct(coord.predictiveTension));
    inspectorMetric(observer, 'Nearest reference zone', analysis.nearest?.name ?? '—');
    root.appendChild(observer);
  }

  if (prevScroll > 0) {
    root.scrollTop = prevScroll;
    requestAnimationFrame(() => { root.scrollTop = prevScroll; });
  }
}

function snapshotForHistory(tick) {
  return {
    tick,
    topology: snap.topology ? JSON.parse(JSON.stringify(snap.topology)) : null,
    cognition: snap.cognition ? JSON.parse(JSON.stringify(snap.cognition)) : null,
    observerAnalysis: snap.observerAnalysis ? JSON.parse(JSON.stringify(snap.observerAnalysis)) : null,
    observerSemantics: snap.observerSemantics ? JSON.parse(JSON.stringify(snap.observerSemantics)) : null,
    sensorimotor: snap.sensorimotor ? JSON.parse(JSON.stringify(snap.sensorimotor)) : null,
    outcome: snap.outcome ? JSON.parse(JSON.stringify(snap.outcome)) : null,
    provenance: snap.provenance ? JSON.parse(JSON.stringify(snap.provenance)) : null,
  };
}

function registerMilestone(kind, label, tick, tone = 'info') {
  if (!Number.isFinite(tick) || tick <= 0) return;
  if (milestones.some((item) => item.kind === kind)) return;
  milestones.push({ kind, label, tick, tone });
  milestones.sort((a, b) => a.tick - b.tick);
}

function recordSelfPersistence(tick) {
  const schema = snap.bodySchema ?? {};
  const parts = Array.isArray(schema.parts) ? schema.parts : [];
  const dependencies = Array.isArray(schema.dependencies) ? schema.dependencies : [];

  for (const region of parts.filter((part) => part.kind === 'cognitive_region')) {
    const key = String(region.part_id ?? '');
    if (!key) continue;
    const state = selfRegionHistory.get(key) ?? {
      firstTick: tick,
      lastTick: tick,
      observations: 0,
    };
    state.lastTick = tick;
    state.observations += 1;
    selfRegionHistory.set(key, state);
  }

  const currentKeys = new Set();
  for (const dependency of dependencies) {
    const key = `${dependency.source_id}→${dependency.target_id}:${dependency.relation ?? 'related'}`;
    currentKeys.add(key);
    const state = selfDependencyHistory.get(key) ?? {
      firstTick: tick,
      lastTick: tick,
      observations: 0,
      dep: { ...dependency },
    };
    state.lastTick = tick;
    state.observations += 1;
    state.dep = { ...dependency };
    selfDependencyHistory.set(key, state);
  }

  for (const [key, state] of selfDependencyHistory.entries()) {
    state.current = currentKeys.has(key);
    if (tick - state.lastTick > 512) selfDependencyHistory.delete(key);
  }
}

export function recordMindHistory() {
  const tick = finiteNumber(tel.tick ?? snap.tick, 0);
  if (tick <= 0) return;

  recordSelfPersistence(tick);
  const topology = snap.topology ?? { nodes: [], edges: [] };
  const nodes = topology.nodes ?? [];
  const sensorimotor = snap.sensorimotor ?? {};
  const outcome = snap.outcome ?? {};
  const point = {
    tick,
    concepts: nodes.filter((node) => node.kind === 'concept').length,
    predictors: nodes.filter((node) => node.kind === 'predictor').length,
    readouts: nodes.filter((node) => node.kind === 'readout').length,
    motorEdges: finiteNumber(tel.cognitiveMotorOutputEdges ?? currentMotorOutputEdges(topology), 0),
    edges: (topology.edges ?? []).length,
    schemaConfidence: finiteNumber(tel.schemaConf, 0),
    predictionError: finiteNumber(tel.predictionError, 0),
    motorOrigin: tel.motorOrigin ?? 'none',
    energy: tel.metabolicReserve,
    physiology: currentPhysiologyState(),
    resourceProgress: finiteNumber(tel.resourceProgress ?? outcome.resource_progress, 0),
    sensorimotorPatterns: finiteNumber(tel.sensorimotorPatterns ?? sensorimotor.known_patterns, 0),
    motorCompetences: finiteNumber(tel.motorCompetences ?? sensorimotor.competence_chunks, 0),
    cognitiveCompetences: finiteNumber(tel.cognitiveMotorCompetences ?? sensorimotor.established_competences, 0),
    repertoire: finiteNumber(
      tel.motorRepertoireSize ?? (
        Array.isArray(sensorimotor.active_motor_repertoire)
          ? sensorimotor.active_motor_repertoire.length
          : 0
      ),
      0,
    ),
    selfRegions: (snap.bodySchema?.parts ?? []).filter((part) => part.kind === 'cognitive_region').length,
    selfDependencies: (snap.bodySchema?.dependencies ?? []).length,
  };

  const last = mindHistory[mindHistory.length - 1];
  if (last?.tick === point.tick) return;
  mindHistory.push(point);
  while (mindHistory.length > 2048) mindHistory.shift();

  if (!historySnapshots.length || tick - historySnapshots[historySnapshots.length - 1].tick >= 64) {
    historySnapshots.push({ tick, snapshot: snapshotForHistory(tick) });
    while (historySnapshots.length > 96) historySnapshots.shift();
  }

  if (!last) {
    registerMilestone('observer-attached', 'Observer attached', tick, 'info');
    return;
  }

  if (last.concepts === 0 && point.concepts > 0) {
    registerMilestone('first-concept', 'First observed concept birth', tick, 'violet');
  }
  if (last.predictors === 0 && point.predictors > 0) {
    registerMilestone('first-predictor', 'First observed predictor birth', tick, 'amber');
  }
  if (last.motorCompetences === 0 && point.motorCompetences > 0) {
    registerMilestone('first-primitive', 'Motor competences became available', tick, 'cyan');
  }
  if (last.repertoire === 0 && point.repertoire > 0) {
    registerMilestone('first-repertoire', 'Motor repertoire became available', tick, 'mint');
  }
  if (last.motorEdges === 0 && point.motorEdges > 0) {
    registerMilestone('first-motor-edge', 'First observed cognition → motor edge', tick, 'mint');
  }

  const lastCognitiveUse =
    ['cognition','mixed'].includes(last.motorOrigin) ||
    String(last.motorOrigin).includes('primitive');
  const cognitiveUse =
    ['cognition','mixed'].includes(point.motorOrigin) ||
    String(point.motorOrigin).includes('primitive');
  if (!lastCognitiveUse && cognitiveUse) {
    registerMilestone(
      'first-cognitive-motor-use',
      'First observed cognitive motor use',
      tick,
      'mint',
    );
  }

  if (last.physiology !== point.physiology) {
    if (point.physiology === 'stressed') {
      registerMilestone('stressed', 'Physiology → stressed', tick, 'coral');
    }
    if (point.physiology === 'dormant') {
      registerMilestone('dormant', 'Physiology → dormant', tick, 'amber');
    }
    if (point.physiology === 'dead') {
      registerMilestone('death', 'Death', tick, 'coral');
    }
  }
}

export function nearestHistorySnapshot(tick) {
  let best = null;
  let distance = Infinity;
  for (const item of historySnapshots) {
    const candidateDistance = Math.abs(item.tick - tick);
    if (candidateDistance < distance) {
      best = item;
      distance = candidateDistance;
    }
  }
  return best;
}
