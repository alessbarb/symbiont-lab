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
  root.innerHTML = '';

  const heading = el('h2', '');
  heading.style.cssText = 'font-size:16px;margin:0 0 4px;';
  heading.textContent = 'History';
  const copy = el('p', '');
  copy.style.cssText = 'font-size:10px;color:var(--muted);margin:0 0 14px;';
  copy.textContent = 'Bounded observer-side history for this browser session. Click a milestone to inspect the nearest captured graph.';
  root.append(heading, copy);

  const charts = el('div', '');
  charts.style.cssText = 'display:grid;grid-template-columns:1fr 1fr;gap:10px;';
  const energy = panelSection('Energy / physiology');
  energy.appendChild(sparklineSvg(mindHistory.filter((point) => point.energy != null), 'energy', PAL.coral));
  const edges = panelSection('Cognitive edges');
  edges.appendChild(sparklineSvg(mindHistory, 'edges', PAL.violet));
  const concepts = panelSection('Concept growth');
  concepts.appendChild(sparklineSvg(mindHistory, 'concepts', PAL.cyan));
  const predictors = panelSection('Predictor growth');
  predictors.appendChild(sparklineSvg(mindHistory, 'predictors', PAL.amber));
  const resource = panelSection('Resource progress');
  resource.appendChild(sparklineSvg(mindHistory, 'resourceProgress', PAL.mint));
  const motor = panelSection('Motor-output edges');
  motor.appendChild(sparklineSvg(mindHistory, 'motorEdges', '#e09f3e'));
  charts.append(energy, edges, concepts, predictors, resource, motor);
  root.appendChild(charts);

  const timeline = panelSection('Milestones');
  timeline.style.marginTop = '10px';
  if (!milestones.length) {
    const empty = el('div', '');
    empty.style.cssText = 'font-size:9px;color:var(--muted);';
    empty.textContent = 'No milestones yet.';
    timeline.appendChild(empty);
  } else {
    for (const milestone of milestones) {
      const row = el('button', '');
      row.type = 'button';
      row.style.cssText = 'width:100%;display:grid;grid-template-columns:60px 1fr;gap:10px;text-align:left;padding:8px 0;border:0;border-top:1px solid rgba(98,120,136,.14);background:none;color:var(--text);cursor:pointer;';
      const tick = el('strong', '');
      tick.textContent = `t${milestone.tick}`;
      tick.style.color = PAL.cyan;
      const label = el('span', '');
      label.textContent = milestone.label;
      label.style.cssText = 'font-size:9px;';
      row.append(tick, label);
      row.addEventListener('click', () => onOpenHistoryTick(milestone.tick));
      timeline.appendChild(row);
    }
  }
  root.appendChild(timeline);

  if (mindHistory.length) {
    const observer = panelSection(
      'Observer analysis',
      'Secondary analytical projection; not part of the organism.',
    );
    observer.style.marginTop = '10px';
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
}

function snapshotForHistory() {
  return {
    topology: snap.topology ? JSON.parse(JSON.stringify(snap.topology)) : null,
    cognition: snap.cognition ? JSON.parse(JSON.stringify(snap.cognition)) : null,
    observerAnalysis: snap.observerAnalysis ? JSON.parse(JSON.stringify(snap.observerAnalysis)) : null,
    observerSemantics: snap.observerSemantics ? JSON.parse(JSON.stringify(snap.observerSemantics)) : null,
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
    motorPrimitives: finiteNumber(tel.motorPrimitives ?? sensorimotor.primitives, 0),
    cognitivePrimitives: finiteNumber(tel.cognitiveMotorPrimitives ?? sensorimotor.cognitive_primitives, 0),
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
    historySnapshots.push({ tick, snapshot: snapshotForHistory() });
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
  if (last.motorPrimitives === 0 && point.motorPrimitives > 0) {
    registerMilestone('first-primitive', 'Motor primitives became available', tick, 'cyan');
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
