/**
 * Live observer projection for the Cognitive Observatory.
 *
 * This module is presentation-only: it derives a compact temporal frame from
 * already observed graph evidence. It never writes to organism state and never
 * claims intent or semantics that are absent from the observation contract.
 */
import { el } from '../shared/dom.js';

const HISTORY_LIMIT = 180;
const EVENT_LIMIT = 24;

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function edgeKey(edge) {
  return `${edge.source?.id ?? edge.sourceId}|${edge.target?.id ?? edge.targetId}|${edge.kind ?? 'edge'}`;
}

function nodeLabel(node) {
  const label = node?.observerLabel ?? node?.label ?? node?.id ?? 'unknown';
  const text = String(label);
  return text.length > 30 ? `${text.slice(0, 26)}…` : text;
}

function snapshotTopology(nodes, edges) {
  return {
    nodes: nodes.map(node => ({
      id: node.id,
      kind: node.kind,
      activation: clamp01(node.activationLevel),
      error: clamp01(node.predictionError ?? node.atlasSignals?.error),
    })),
    edges: edges.map(edge => ({
      key: edgeKey(edge),
      sourceId: edge.source?.id ?? edge.sourceId,
      targetId: edge.target?.id ?? edge.targetId,
      kind: edge.kind ?? 'edge',
      weight: finite(edge.weight),
      support: finite(edge.support),
      plasticity: finite(edge.plasticity),
      lastUseTick: finite(edge.lastUseTick),
    })),
  };
}

function topologyDiff(previous, current) {
  if (!previous) {
    return {
      addedNodes: [],
      removedNodes: [],
      addedEdges: [],
      removedEdges: [],
      strengthenedEdges: [],
      weakenedEdges: [],
    };
  }
  const prevNodes = new Set(previous.nodes.map(node => node.id));
  const nextNodes = new Set(current.nodes.map(node => node.id));
  const prevEdges = new Map(previous.edges.map(edge => [edge.key, edge]));
  const nextEdges = new Map(current.edges.map(edge => [edge.key, edge]));
  const strengthenedEdges = [];
  const weakenedEdges = [];

  for (const [key, edge] of nextEdges.entries()) {
    const prior = prevEdges.get(key);
    if (!prior) continue;
    const deltaWeight = edge.weight - prior.weight;
    const deltaSupport = edge.support - prior.support;
    const deltaPlasticity = edge.plasticity - prior.plasticity;
    const score = deltaWeight + deltaSupport * 0.02 + deltaPlasticity * 0.35;
    if (score > 0.015) strengthenedEdges.push({ ...edge, score });
    if (score < -0.015) weakenedEdges.push({ ...edge, score });
  }

  return {
    addedNodes: [...nextNodes].filter(id => !prevNodes.has(id)),
    removedNodes: [...prevNodes].filter(id => !nextNodes.has(id)),
    addedEdges: [...nextEdges.keys()].filter(key => !prevEdges.has(key)),
    removedEdges: [...prevEdges.keys()].filter(key => !nextEdges.has(key)),
    strengthenedEdges: strengthenedEdges.sort((a,b) => b.score - a.score).slice(0, 8),
    weakenedEdges: weakenedEdges.sort((a,b) => a.score - b.score).slice(0, 8),
  };
}

function activeNodes(nodes, signals) {
  return nodes
    .map(node => {
      const signal = signals?.get?.(node.id);
      const activity = Math.max(
        clamp01(node.activationLevel),
        clamp01(signal?.activity),
        clamp01(node.readoutMagnitude),
      );
      const error = Math.max(
        clamp01(node.predictionError),
        clamp01(signal?.error),
      );
      return { id: node.id, kind: node.kind, label: nodeLabel(node), activity, error, node };
    })
    .filter(item => item.activity > 0.025 || item.error > 0.025)
    .sort((a,b) => (b.activity + b.error * 0.45) - (a.activity + a.error * 0.45));
}

function chooseFocus(active, selectedNodeId) {
  if (selectedNodeId) {
    const selected = active.find(item => item.id === selectedNodeId);
    if (selected) return selected;
  }
  return active[0] ?? null;
}

function processingRows(situation) {
  return (situation?.stages ?? []).map(stage => ({
    id: stage.id,
    label: stage.label,
    active: finite(stage.active),
    total: finite(stage.total),
    ratio: stage.total ? clamp01(stage.active / stage.total) : 0,
  }));
}

export function buildCognitiveFrame({
  nodes = [],
  edges = [],
  regions = [],
  signals = new Map(),
  flow = null,
  situation = null,
  previousFrame = null,
  tick = 0,
  selectedNodeId = null,
  motorOrigin = 'none',
  activeEffectors = 0,
  jointMotion = 0,
  regionEvents = [],
} = {}) {
  const topology = snapshotTopology(nodes, edges);
  const diff = topologyDiff(previousFrame?.topology ?? null, topology);
  const active = activeNodes(nodes, signals);
  const focus = chooseFocus(active, selectedNodeId);
  const related = focus
    ? edges
        .filter(edge => (edge.source?.id ?? edge.sourceId) === focus.id || (edge.target?.id ?? edge.targetId) === focus.id)
        .map(edge => {
          const otherId = (edge.source?.id ?? edge.sourceId) === focus.id
            ? (edge.target?.id ?? edge.targetId)
            : (edge.source?.id ?? edge.sourceId);
          const other = nodes.find(node => node.id === otherId);
          return {
            id: otherId,
            label: nodeLabel(other ?? { id: otherId }),
            kind: other?.kind ?? 'unknown',
            support: finite(edge.support),
            weight: finite(edge.weight),
          };
        })
        .sort((a,b) => b.support - a.support || Math.abs(b.weight) - Math.abs(a.weight))
        .slice(0, 5)
    : [];

  const recentPaths = flow?.paths ?? [];
  const dominantPath = [...recentPaths]
    .sort((a,b) => (b.nodeIds?.length ?? 0) - (a.nodeIds?.length ?? 0))[0] ?? null;

  return {
    tick: finite(tick),
    topology,
    regions: regions.map(region => ({
      id: region.id,
      label: region.label,
      interpretation: region.interpretation,
      activity: clamp01(region.activity),
      total: finite(region.total),
    })),
    activity: {
      activeCount: active.length,
      top: active.slice(0, 12),
    },
    flow: {
      recentRelations: finite(flow?.recentEdgeCount),
      paths: recentPaths,
      dominantPath,
    },
    prediction: {
      pressure: clamp01(situation?.prediction?.pressure),
      highestErrors: situation?.prediction?.highestErrors ?? [],
    },
    learning: {
      zones: finite(situation?.learning?.zones),
      frontierNodes: finite(situation?.learning?.nodes),
      ...diff,
    },
    processing: processingRows(situation),
    focus: focus ? {
      id: focus.id,
      label: focus.label,
      kind: focus.kind,
      activity: focus.activity,
      error: focus.error,
      region: nodes.find(node => node.id === focus.id)?.sectorLabel ?? null,
      related,
    } : null,
    bodyCoupling: {
      motorOrigin: motorOrigin ?? 'none',
      activeEffectors: finite(activeEffectors),
      jointMotion: finite(jointMotion),
      motorPaths: finite(situation?.flow?.motorPaths),
      sensoryStarts: finite(situation?.flow?.sensoryStarts),
    },
    regionEvents: (regionEvents ?? []).slice(-8),
    provenance: {
      owner: 'observer',
      feedsBack: false,
      claimsIntent: false,
      projection: 'cognitive-live-frame-v1',
    },
  };
}

function eventSignature(event) {
  return [event.type, event.tick, event.nodeId, event.edgeKey, event.label].filter(v => v != null).join('|');
}

function frameEvents(frame, previousFrame) {
  const events = [];
  const add = (type, text, tone = 'neutral', extra = {}) => {
    events.push({ type, text, tone, tick: frame.tick, ...extra });
  };

  for (const id of frame.learning.addedNodes.slice(0, 3)) {
    add('node-born', `New cognitive node · ${id}`, 'learning', { nodeId: id });
  }
  for (const key of frame.learning.addedEdges.slice(0, 3)) {
    add('edge-born', `New relation · ${key.replaceAll('|', ' → ')}`, 'learning', { edgeKey: key });
  }
  for (const edge of frame.learning.strengthenedEdges.slice(0, 3)) {
    add('edge-strengthened', `Strengthened · ${edge.sourceId} → ${edge.targetId}`, 'learning', { edgeKey: edge.key });
  }
  for (const edge of frame.learning.weakenedEdges.slice(0, 2)) {
    add('edge-weakened', `Weakened · ${edge.sourceId} → ${edge.targetId}`, 'warning', { edgeKey: edge.key });
  }
  for (const regionEvent of frame.regionEvents) {
    add(regionEvent.type, `${String(regionEvent.type).replace('region-', 'Region ')} · ${regionEvent.label ?? ''}`, 'structure');
  }

  const previousError = previousFrame?.focus?.error;
  if (frame.focus && previousFrame?.focus?.id === frame.focus.id && previousError != null) {
    const delta = frame.focus.error - previousError;
    if (Math.abs(delta) >= 0.03) {
      add(
        'prediction-error',
        `Prediction error ${delta < 0 ? 'decreased' : 'increased'} · ${previousError.toFixed(2)} → ${frame.focus.error.toFixed(2)}`,
        delta < 0 ? 'prediction-good' : 'prediction-bad',
        { nodeId: frame.focus.id },
      );
    }
  }

  return events;
}

export function recordCognitiveFrame(graph, frame) {
  const previous = graph.liveFrame ?? null;
  graph.liveFrame = frame;
  graph.liveFrameHistory ??= [];
  graph.cognitiveEvents ??= [];

  graph.liveFrameHistory.push(frame);
  if (graph.liveFrameHistory.length > HISTORY_LIMIT) graph.liveFrameHistory.shift();

  const existing = new Set(graph.cognitiveEvents.map(eventSignature));
  for (const event of frameEvents(frame, previous)) {
    const signature = eventSignature(event);
    if (existing.has(signature)) continue;
    graph.cognitiveEvents.unshift(event);
    existing.add(signature);
  }
  if (graph.cognitiveEvents.length > EVENT_LIMIT) {
    graph.cognitiveEvents.length = EVENT_LIMIT;
  }
}

function metricRow(label, value, ratio = null) {
  const row = el('div', 'mind-live-metric');
  const name = el('span', 'mind-live-metric-label');
  name.textContent = label;
  const right = el('span', 'mind-live-metric-value');
  right.textContent = value;
  row.append(name, right);
  if (ratio != null) {
    const meter = el('span', 'mind-live-meter');
    const fill = el('i', 'mind-live-meter-fill');
    fill.style.width = `${Math.round(clamp01(ratio) * 100)}%`;
    meter.appendChild(fill);
    row.appendChild(meter);
  }
  return row;
}

function renderFocus(frame) {
  const root = document.getElementById('mind-cognition-live-focus');
  if (!root) return;
  root.replaceChildren();

  const head = el('div', 'mind-live-card-head');
  const title = el('strong', '');
  title.textContent = 'Current activity focus';
  const live = el('span', 'mind-live-badge');
  live.textContent = 'LIVE';
  head.append(title, live);
  root.appendChild(head);

  if (!frame?.focus) {
    const empty = el('div', 'mind-live-empty');
    empty.textContent = 'No active cognitive focus observed in this frame.';
    root.appendChild(empty);
    return;
  }

  const focus = frame.focus;
  const identity = el('div', 'mind-live-focus-id');
  const dot = el('span', `mind-live-focus-dot kind-${focus.kind}`);
  const copy = el('div', '');
  const label = el('strong', '');
  label.textContent = focus.label;
  const meta = el('small', '');
  meta.textContent = `${focus.kind}${focus.region ? ` · ${focus.region}` : ''}`;
  copy.append(label, meta);
  identity.append(dot, copy);
  root.appendChild(identity);

  root.append(
    metricRow('Activation', focus.activity.toFixed(2), focus.activity),
    metricRow('Prediction error', focus.error.toFixed(2), focus.error),
    metricRow('Prediction pressure', frame.prediction.pressure.toFixed(2), frame.prediction.pressure),
  );

  const processingTitle = el('div', 'mind-live-section-title');
  processingTitle.textContent = 'Current processing';
  root.appendChild(processingTitle);
  const processing = el('div', 'mind-live-processing');
  for (const stage of frame.processing) {
    const row = el('div', `mind-live-stage ${stage.active > 0 ? 'active' : ''}`);
    const name = el('span', '');
    name.textContent = stage.label;
    const count = el('b', '');
    count.textContent = `${stage.active}/${stage.total}`;
    const meter = el('i', '');
    const fill = el('em', '');
    fill.style.width = `${Math.round(stage.ratio * 100)}%`;
    meter.appendChild(fill);
    row.append(name, meter, count);
    processing.appendChild(row);
  }
  root.appendChild(processing);

  const couplingTitle = el('div', 'mind-live-section-title');
  couplingTitle.textContent = 'Body coupling';
  root.appendChild(couplingTitle);
  root.append(
    metricRow('Motor origin', String(frame.bodyCoupling.motorOrigin)),
    metricRow('Observed motor paths', String(frame.bodyCoupling.motorPaths)),
    metricRow('Active effectors', String(frame.bodyCoupling.activeEffectors)),
  );

  if (focus.related.length) {
    const relatedTitle = el('div', 'mind-live-section-title');
    relatedTitle.textContent = 'Top related nodes';
    root.appendChild(relatedTitle);
    const related = el('div', 'mind-live-related');
    for (const item of focus.related) {
      const row = el('div', 'mind-live-related-row');
      const name = el('span', '');
      name.textContent = item.label;
      const value = el('b', '');
      value.textContent = item.support ? `s${Math.round(item.support)}` : item.weight.toFixed(2);
      row.append(name, value);
      related.appendChild(row);
    }
    root.appendChild(related);
  }
}

function renderEvents(graph) {
  const root = document.getElementById('mind-cognition-event-stream');
  if (!root) return;
  root.replaceChildren();
  const head = el('div', 'mind-live-card-head');
  const title = el('strong', '');
  title.textContent = 'Recent cognitive events';
  const count = el('span', 'mind-live-badge');
  count.textContent = String(graph.cognitiveEvents?.length ?? 0);
  head.append(title, count);
  root.appendChild(head);

  const events = (graph.cognitiveEvents ?? []).slice(0, 7);
  if (!events.length) {
    const empty = el('div', 'mind-live-empty');
    empty.textContent = 'Waiting for observable structural or predictive changes.';
    root.appendChild(empty);
    return;
  }
  for (const event of events) {
    const row = el('div', `mind-live-event tone-${event.tone ?? 'neutral'}`);
    const tick = el('span', 'mind-live-event-tick');
    tick.textContent = `t${event.tick}`;
    const text = el('span', 'mind-live-event-text');
    text.textContent = event.text;
    row.append(tick, text);
    root.appendChild(row);
  }
}

function renderTimeline(graph) {
  const root = document.getElementById('mind-cognition-live-timeline');
  if (!root) return;
  root.replaceChildren();
  const frames = (graph.liveFrameHistory ?? []).slice(-90);
  if (!frames.length) return;

  const label = el('span', 'mind-live-timeline-title');
  label.textContent = 'Live activity';
  const bars = el('span', 'mind-live-timeline-bars');
  for (const frame of frames) {
    const bar = el('i', 'mind-live-timeline-bar');
    const activity = clamp01((frame.activity?.activeCount ?? 0) / 24);
    const learning = Math.min(
      1,
      ((frame.learning?.addedNodes?.length ?? 0) +
       (frame.learning?.addedEdges?.length ?? 0) +
       (frame.learning?.strengthenedEdges?.length ?? 0)) / 5,
    );
    const error = clamp01(frame.prediction?.pressure);
    bar.style.height = `${4 + Math.round(Math.max(activity, learning, error) * 12)}px`;
    if (learning > 0.15) bar.classList.add('learning');
    else if (error > 0.45) bar.classList.add('error');
    else if (frame.bodyCoupling?.motorPaths > 0) bar.classList.add('motor');
    bars.appendChild(bar);
  }
  root.append(label, bars);
}

export function renderCognitiveLivePanels(graph) {
  renderFocus(graph.liveFrame);
  renderEvents(graph);
  renderTimeline(graph);
}
