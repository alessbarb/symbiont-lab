/**
 * Identity and sensory renderers.
 *
 * This subsystem reads the shared passive snapshot and delegates navigation
 * back to the Mind coordinator through an explicit callback.
 */
import { el, svgEl } from '../shared/dom.js';
import { PAL } from './config.js';
import { observerContextForNode, sensorySemantic } from './semantics.js';
import {
  identityHistory,
  selfDependencyHistory,
  selfRegionHistory,
  snap,
  tel,
} from './state.js';
import {
  classRatio,
  clamp01,
  finiteNumber,
  hashStr,
  pct,
  shortId,
} from './util.js';

export function createIdentitySensoryRenderer({
  getUid = () => 'default',
  onSelectCognitiveNode = () => {},
} = {}) {
  const sensoryView = {
    lens: 'topology',
    filter: 'all',
    query: '',
    selectedNodeId: null,
    history: [],
  };

  function sensoryFacts() {
    const phenotype = snap.sensoryPhenotype ?? {};
    const sensors = Array.isArray(phenotype.sensors) ? phenotype.sensors : [];
    const topology = snap.topology ?? { nodes: [], edges: [] };
    const degree = new Map((topology.nodes ?? []).map(node => [node.id, 0]));
    for (const edge of topology.edges ?? []) {
      degree.set(edge.sourceId, (degree.get(edge.sourceId) ?? 0) + 1);
      degree.set(edge.targetId, (degree.get(edge.targetId) ?? 0) + 1);
    }
    const sampledIds = new Set((snap.senses ?? []).filter(sense => sense.active).map(sense => sense.id));
    return sensors.map(sensor => {
      const cognitiveId = sensor.downstream_name ?? sensor.sensor_id;
      return {
        ...sensor,
        cognitiveId,
        sampled: sampledIds.has(cognitiveId) || sampledIds.has(sensor.sensor_id),
        degree: degree.get(cognitiveId) ?? 0,
        integrated: (degree.get(cognitiveId) ?? 0) > 0,
        utility: finiteNumber(sensor.utility, 0),
        confidence: clamp01(sensor.confidence),
        health: clamp01(sensor.health),
        maturity: String(sensor.maturity ?? 'unknown'),
      };
    });
  }
  
  function renderSensesPanel() {
    const list = document.getElementById('mind-senses-list');
    if (!list) return;
    list.replaceChildren();

    const sensors = sensoryFacts();
    if (!sensors.length) {
      const empty = el('p', 'mind-senses-empty');
      empty.textContent = 'No sensory phenotype yet.';
      list.appendChild(empty);
      return;
    }

    const sampled = sensors.filter(sensor => sensor.sampled).length;
    const useful = sensors.filter(sensor => sensor.utility > 0).length;
    const integrated = sensors.filter(sensor => sensor.integrated).length;
    const novel = sensors.filter(sensor =>
      !sensor.integrated && (sensor.confidence < 0.45 || sensor.maturity === 'candidate' || sensor.maturity === 'immature')
    ).length;

    const summary = el('div', 'mind-senses-summary mind-senses-summary-rich');
    const summaryTitle = el('strong', '');
    summaryTitle.textContent = `${sensors.length} receptors`;
    const summaryDetail = el('span', '');
    summaryDetail.textContent = `${sampled} sampled · ${useful} useful · ${integrated} integrated · ${novel} frontier`;
    summary.append(summaryTitle, summaryDetail);
    list.appendChild(summary);

    const search = document.createElement('input');
    search.className = 'mind-sensory-search';
    search.type = 'search';
    search.placeholder = 'Filter receptors…';
    search.value = sensoryView.query;
    search.setAttribute('aria-label', 'Filter sensory receptors');
    search.addEventListener('input', () => {
      sensoryView.query = search.value.trim().toLowerCase();
      renderSensesPanel();
    });
    list.appendChild(search);

    const filters = el('div', 'mind-sensory-filter-row');
    for (const [id, label, count] of [
      ['all', 'All', sensors.length],
      ['sampled', 'Active', sampled],
      ['useful', 'Useful', useful],
      ['integrated', 'Integrated', integrated],
      ['frontier', 'Frontier', novel],
    ]) {
      const button = el('button', `mind-sensory-filter${sensoryView.filter === id ? ' active' : ''}`);
      button.type = 'button';
      button.dataset.filter = id;
      button.textContent = `${label} ${count}`;
      button.addEventListener('click', () => {
        sensoryView.filter = id;
        renderSensesPanel();
        renderSensoryMap();
      });
      filters.appendChild(button);
    }
    list.appendChild(filters);

    const header = el('div', 'mind-senses-header');
    for (const label of ['receptor', 'now', 'util', 'deg']) {
      const cell = el('span', '');
      cell.textContent = label;
      header.appendChild(cell);
    }
    list.appendChild(header);

    const visible = sensors.filter(sensor => {
      if (sensoryView.query && !String(sensor.cognitiveId).toLowerCase().includes(sensoryView.query)) return false;
      if (sensoryView.filter === 'sampled') return sensor.sampled;
      if (sensoryView.filter === 'useful') return sensor.utility > 0;
      if (sensoryView.filter === 'integrated') return sensor.integrated;
      if (sensoryView.filter === 'frontier') {
        return !sensor.integrated && (sensor.confidence < 0.45 || sensor.maturity === 'candidate' || sensor.maturity === 'immature');
      }
      return true;
    });

    [...visible]
      .sort((a,b) =>
        Number(b.sampled)-Number(a.sampled) ||
        Number(b.integrated)-Number(a.integrated) ||
        b.utility-a.utility ||
        b.degree-a.degree ||
        String(a.cognitiveId).localeCompare(String(b.cognitiveId))
      )
      .slice(0, 160)
      .forEach(sensor => {
        const row=el('button',`mind-sense-table-row${sensoryView.selectedNodeId === sensor.cognitiveId ? ' selected' : ''}`);
        row.type='button';
        const name=el('span','mind-sense-table-name');
        name.textContent=shortId(sensor.cognitiveId,11,5);
        name.title=`${sensor.cognitiveId}\nmaturity ${sensor.maturity} · health ${pct(sensor.health)} · confidence ${pct(sensor.confidence)}`;
        const sampledCell=el('span','');
        sampledCell.textContent=sensor.sampled?'●':'○';
        sampledCell.style.color=sensor.sampled?PAL.cyan:PAL.muted;
        const utility=el('span','');
        utility.textContent=sensor.utility.toFixed(2);
        utility.style.color=sensor.utility>0?PAL.mint:PAL.muted;
        const degree=el('span','');
        degree.textContent=String(sensor.degree);
        degree.style.color=sensor.integrated?PAL.violet:PAL.muted;
        row.append(name,sampledCell,utility,degree);
        row.addEventListener('click',()=>{
          sensoryView.selectedNodeId=sensor.cognitiveId;
          renderSensesPanel();
          renderSensoryMap();
        });
        list.appendChild(row);
      });

    if (visible.length > 160) {
      const more = el('div', 'mind-senses-empty');
      more.textContent = `${visible.length - 160} additional receptors hidden — refine the filter.`;
      list.appendChild(more);
    }
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Phenotype SVG rendering (adapted from observatory/render/organism.js)
  // ─────────────────────────────────────────────────────────────────────────────
  
  function renderPhenotype() {
    const canvas = document.getElementById('mind-phenotype-svg');
    if (!canvas) return;
    canvas.replaceChildren();
  
    const senses   = snap.senses ?? [];
    const beliefs  = snap.beliefs ?? [];
    const cognition = snap.cognition;
    const health   = cognition?.topologyHealth;
    const isFrozen = cognition?.safetyState?.frozen;
    const isStressed = Array.isArray(snap.details?.regimeChanges) && snap.details.regimeChanges.length > 0;
    const isAdaptive = health === 'adaptive' || health === 'connected';
  
    // Waiting state
    if (!senses.length && !beliefs.length) {
      const waiting = svgEl('text', { x: '450', y: '360', 'text-anchor': 'middle', 'dominant-baseline': 'middle', fill: PAL.muted, 'font-size': '14' });
      waiting.textContent = 'No snapshot data — connect a live organism';
      canvas.appendChild(waiting);
      return;
    }
  
    const defs = svgEl('defs');
  
    // Radial gradient
    let coreColor = '#17274e', midColor = '#0a2632', edgeColor = PAL.mint;
    if (isFrozen) { coreColor = '#1a212b'; midColor = '#141920'; edgeColor = '#627382'; }
    else if (isStressed) { coreColor = '#2d1628'; midColor = '#1f1422'; edgeColor = PAL.coral; }
    else if (isAdaptive) { coreColor = '#0d2b38'; midColor = '#0a262e'; edgeColor = PAL.mint; }
  
    const gradientId = `mind-cell-fill-${getUid()}`;
    const grad = svgEl('radialGradient', { id: gradientId });
    grad.append(
      svgEl('stop', { offset: '0',   'stop-color': coreColor, 'stop-opacity': '.52' }),
      svgEl('stop', { offset: '.72', 'stop-color': midColor,  'stop-opacity': '.20' }),
      svgEl('stop', { offset: '1',   'stop-color': edgeColor, 'stop-opacity': '.10' }),
    );
    defs.appendChild(grad);
  
    // Arrow markers
    [{ id: `mind-arr-exc-${getUid()}`, color: 'rgba(80,217,255,.8)' },
     { id: `mind-arr-inh-${getUid()}`, color: 'rgba(255,127,131,.8)' },
     { id: `mind-arr-mod-${getUid()}`, color: 'rgba(255,189,84,.8)'  }].forEach(m => {
      const marker = svgEl('marker', { id: m.id, viewBox: '0 0 6 6', refX: '5', refY: '3', markerWidth: '4', markerHeight: '4', orient: 'auto' });
      marker.appendChild(svgEl('path', { d: 'M 0 1 L 5 3 L 0 5 z', fill: m.color }));
      defs.appendChild(marker);
    });
    canvas.appendChild(defs);
  
    const group = svgEl('g', { class: 'mind-organism' });
  
    // Build a simplified boundary path (ellipse-like)
    const boundaryPath = buildBoundaryPath(450, 360, 280, 260, senses.length, isFrozen);
  
    // World signal nodes on left margin
    const sensePositions = new Map();
    const usable = senses.slice(0, 16);
    usable.forEach((sense, i) => {
      const y = 120 + (i * 490 / Math.max(1, usable.length - 1));
      const x = 80;
      sensePositions.set(sense.id, { x, y });
  
      // World signal dot
      const dot = svgEl('circle', { cx: x, cy: y, r: '4', class: `mind-world-signal ${sense.active ? 'active' : 'inactive'}`,
        fill: sense.active ? PAL.cyan : PAL.muted, opacity: sense.active ? '0.85' : '0.35' });
      group.appendChild(dot);
  
      // Dual semantic label: apparatus truth is observer-only; the opaque
      // organism label remains available in the tooltip.
      const semantic = sensorySemantic(snap.observerSemantics, sense.id);
      const label = svgEl('text', { x: x + 12, y: y + 3, 'font-size': '10', fill: sense.active ? PAL.text : PAL.muted });
      label.textContent = (semantic?.observerSummary ?? sense.name ?? sense.id).slice(0, 28);
      const labelTitle = svgEl('title');
      labelTitle.textContent = semantic?.observerSummary
        ? `Observer: ${semantic.observerSummary}\nSelf: ${semantic.selfLabel ?? sense.id}`
        : `Self: ${sense.name ?? sense.id}\nObserver: unresolved`;
      label.appendChild(labelTitle);
      group.appendChild(label);
  
      // Connection to boundary
      const bx = 170, by = y;
      const path = svgEl('path', {
        d: `M ${x + 5} ${y} Q ${bx - 20} ${y} ${bx} ${by}`,
        fill: 'none', stroke: sense.active ? PAL.cyan : PAL.muted,
        'stroke-width': sense.active ? '1.2' : '0.5',
        opacity: sense.active ? '0.55' : '0.15',
      });
      group.appendChild(path);
    });
  
    // Membrane boundary
    const bndryClasses = ['mind-boundary'];
    if (isStressed)       bndryClasses.push('mind-boundary-stressed');
    else if (isAdaptive)  bndryClasses.push('mind-boundary-adaptive');
    else if (health === 'recovering') bndryClasses.push('mind-boundary-recovering');
  
    group.appendChild(svgEl('path', { d: boundaryPath, fill: `url(#${gradientId})`, class: bndryClasses.join(' '),
      stroke: edgeColor, 'stroke-width': '1.5', 'stroke-opacity': '0.55' }));
  
    // Internal nodes from topology
    const topology = snap.topology;
    const internalAnchors = topology?.nodes ? layoutInternalAnchors(topology.nodes) : [];
    internalAnchors.forEach(anchor => {
      const errorCls = (snap.observerAnalysis?.predictionErrors ?? cognition?.predictionErrors)?.[anchor.id];
      if (errorCls && ['medium', 'high', 'extreme'].includes(errorCls)) {
        group.appendChild(svgEl('circle', { cx: anchor.x, cy: anchor.y, r: (anchor.r + 6),
          fill: 'none', stroke: PAL.coral, 'stroke-width': '1.2', 'stroke-dasharray': '3 2', opacity: '0.7' }));
      }
      group.appendChild(makeInternalNode(anchor, cognition));
    });
  
    // Synaptic fibres
    if (topology?.edges && internalAnchors.length) {
      const anchorMap = new Map(internalAnchors.map(a => [a.id, a]));
      for (const edge of topology.edges) {
        const src = anchorMap.get(edge.sourceId);
        const tgt = anchorMap.get(edge.targetId);
        if (!src || !tgt) continue;
        const isExc = edge.kind === 'excitatory';
        const isMod = ['predictive', 'gating'].includes(edge.kind);
        const strokeColor = isExc ? 'rgba(80,217,255,.55)' : isMod ? 'rgba(255,189,84,.55)' : 'rgba(255,127,131,.55)';
        const marker = isExc
          ? `url(#mind-arr-exc-${getUid()})`
          : isMod
            ? `url(#mind-arr-mod-${getUid()})`
            : `url(#mind-arr-inh-${getUid()})`;
        group.appendChild(svgEl('line', {
          x1: src.x, y1: src.y, x2: tgt.x, y2: tgt.y,
          stroke: strokeColor, 'stroke-width': '1', 'marker-end': marker,
        }));
      }
    }
  
    // Belief nodes
    beliefs.forEach((belief, i) => {
      const pos = resolveBeliefPos(belief, i, sensePositions);
      const evidence = Number(belief.evidence) || 0;
      const certainty = Number(belief.certainty) || 0;
      const r = Math.max(5, Math.min(13, 5 + Math.sqrt(evidence) * 1.3));
      if (belief.dissent || belief.contested) {
        group.appendChild(svgEl('circle', { cx: pos.x, cy: pos.y, r: r + 5,
          fill: 'none', stroke: PAL.coral, 'stroke-dasharray': '3 2', 'stroke-width': '1.2',
          class: 'mind-belief-contested-halo' }));
      }
      group.appendChild(svgEl('circle', { cx: pos.x, cy: pos.y, r, fill: PAL.violet,
        opacity: String(Math.max(0.3, certainty)) }));
    });
  
    // HUD bar
    const samplingActive  = snap.sampling?.active ?? senses.filter(s => s.active).length;
    const samplingProbing = snap.sampling?.probing ?? 0;
    const acclPct = Math.round((snap.details?.acclimation ?? 0) * 100);
    const hud = svgEl('g', { transform: 'translate(280, 692)' });
    const hudBg = svgEl('rect', { x: '-12', y: '-14', width: '340', height: '22', rx: '4', fill: 'rgba(6,14,24,0.75)' });
    const hudText = svgEl('text', { 'font-size': '10', fill: PAL.muted, y: '0' });
    hudText.textContent = `Acclimation: ${acclPct}% · Signals: ${senses.length} · Active: ${samplingActive} · Probing: ${samplingProbing}`;
    hud.append(hudBg, hudText);
    group.appendChild(hud);
  
    canvas.appendChild(group);
  }
  
  /** Build an approximate organic boundary path for the cell membrane. */
  function buildBoundaryPath(cx, cy, rx, ry, senseCount, frozen) {
    const pts = 32;
    const coords = [];
    for (let i = 0; i <= pts; i++) {
      const angle = (i / pts) * Math.PI * 2;
      const jitter = frozen ? 0 : (Math.sin(angle * 3) * 12 + Math.sin(angle * 7) * 5);
      const x = cx + (rx + jitter) * Math.cos(angle);
      const y = cy + (ry + jitter * 0.6) * Math.sin(angle);
      coords.push(`${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`);
    }
    return coords.join(' ') + ' Z';
  }
  
  /** Layout internal topology nodes inside the membrane area (450±180, 360±140). */
  function layoutInternalAnchors(nodes) {
    const result = [];
    nodes.forEach((node, i) => {
      const seed = hashStr(node.id);
      const angle = (i * 2.399) + ((seed % 100) / 100) * 0.2;
      const spread = 55 + ((seed % 7) * 22);
      const x = 450 + Math.cos(angle) * Math.min(spread, 180);
      const y = 360 + Math.sin(angle) * Math.min(spread * 0.75, 130);
      const r = node.kind === 'readout' ? 11 : node.kind === 'sense' ? 7 : 8;
      result.push({ id: node.id, kind: node.kind ?? 'concept', x, y, r });
    });
    return result;
  }
  
  function makeInternalNode(anchor, cognition) {
    const { id, kind, x, y, r } = anchor;
    const actClass = (snap.observerAnalysis?.activationClasses ?? cognition?.activationClasses)?.[id] ?? 0;
    const actLevel = actClass / 15;
    const color = { sense: PAL.cyan, readout: PAL.mint, state: '#4ecdc4', predictor: PAL.amber, gate: '#e09f3e', concept: PAL.violet }[kind] ?? PAL.violet;
    const opacity = String(0.55 + actLevel * 0.4);
    let node;
    if (kind === 'sense') {
      const pts = `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`;
      node = svgEl('polygon', { points: pts, fill: color, opacity });
    } else if (kind === 'state') {
      node = svgEl('rect', { x: x - r, y: y - r, width: r * 2, height: r * 2, rx: '3', fill: color, opacity });
    } else if (kind === 'predictor') {
      const pts = `${x},${y - r * 1.3} ${x + r},${y + r * 0.85} ${x - r},${y + r * 0.85}`;
      node = svgEl('polygon', { points: pts, fill: color, opacity });
    } else if (kind === 'gate') {
      const pts = Array.from({ length: 6 }, (_, i) => {
        const a = (Math.PI / 3) * i;
        return `${(x + r * 1.1 * Math.cos(a)).toFixed(1)},${(y + r * 1.1 * Math.sin(a)).toFixed(1)}`;
      }).join(' ');
      node = svgEl('polygon', { points: pts, fill: color, opacity });
    } else if (kind === 'readout') {
      const g = svgEl('g');
      g.appendChild(svgEl('circle', { cx: x, cy: y, r, fill: color, opacity }));
      g.appendChild(svgEl('circle', { cx: x, cy: y, r: r * 0.6, fill: 'none', stroke: color, 'stroke-width': '1.2', opacity: '0.8' }));
      return g;
    } else {
      node = svgEl('circle', { cx: x, cy: y, r, fill: color, opacity });
    }
    return node;
  }
  
  function resolveBeliefPos(belief, index, sensePositions) {
    for (const [senseId, pos] of sensePositions.entries()) {
      if (belief.id.includes(senseId) || (senseId.length > 5 && belief.id.includes(senseId.slice(0, 16)))) {
        const dx = pos.x - 450, dy = pos.y - 360;
        const dist = Math.hypot(dx, dy) || 1;
        const targetDist = 95 + (index % 4) * 28;
        return { x: Math.round(450 + (dx / dist) * targetDist), y: Math.round(360 + (dy / dist) * targetDist * 0.82) };
      }
    }
    if (belief.x != null && belief.y != null) return { x: belief.x, y: belief.y };
    const angle = index * 2.399;
    const radius = 52 + (index % 5) * 38;
    return { x: Math.round(450 + Math.cos(angle) * radius), y: Math.round(360 + Math.sin(angle) * radius * 0.82) };
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Sensory Map (simplified receptor / sense map)
  // ─────────────────────────────────────────────────────────────────────────────
  
  function renderSensoryMap() {
    const mapSvg = document.getElementById('mind-sensory-map-svg');
    const detail = document.getElementById('mind-sensory-detail');
    const metrics = document.getElementById('mind-sensory-metrics');
    const inspector = document.getElementById('mind-sensory-inspector');
    const timeline = document.getElementById('mind-sensory-timeline');
    if (!mapSvg) return;
    mapSvg.replaceChildren();

    const senses = snap.senses ?? [];
    const topology = snap.topology ?? { nodes: [], edges: [] };
    const topoNodes = Array.isArray(topology.nodes) ? topology.nodes : [];
    const topoEdges = Array.isArray(topology.edges) ? topology.edges : [];

    bindSensoryControls();

    if (!senses.length && !topoNodes.length) {
      const msg = svgEl('text', { x: '550', y: '320', 'text-anchor': 'middle', fill: PAL.muted, 'font-size': '14' });
      msg.textContent = 'No sensory topology yet — awaiting snapshot…';
      mapSvg.appendChild(msg);
      if (detail) detail.textContent = 'Sensory funnel: awaiting live body-derived sensory channels.';
      if (inspector) renderSensoryInspector(inspector, null, topology, []);
      return;
    }

    const W = 1100, H = 650;
    const sensorNodes = topoNodes.filter(n => n.kind === 'sense');
    const internalNodes = topoNodes.filter(n => n.kind !== 'sense');
    const sensory = sensoryFacts();
    const sampledSensors = sensory.filter(sensor => sensor.sampled);
    const usefulSensors = sensory.filter(sensor => sensor.utility > 0);
    const concepts = internalNodes.filter(n => n.kind === 'concept');
    const predictors = internalNodes.filter(n => n.kind === 'predictor');
    const readouts = internalNodes.filter(n => n.kind === 'readout');
    const activationClasses = snap.observerAnalysis?.activationClasses ?? snap.cognition?.activationClasses ?? {};
    const predictionErrors = snap.observerAnalysis?.predictionErrors ?? snap.cognition?.predictionErrors ?? {};

    const outgoing = new Map();
    const incoming = new Map();
    for (const edge of topoEdges) {
      if (!outgoing.has(edge.sourceId)) outgoing.set(edge.sourceId, []);
      if (!incoming.has(edge.targetId)) incoming.set(edge.targetId, []);
      outgoing.get(edge.sourceId).push(edge);
      incoming.get(edge.targetId).push(edge);
    }
    const connectedSensors = sensorNodes.filter(n => (outgoing.get(n.id) ?? []).length > 0);
    const sampledIds = new Set(sampledSensors.map(sensor => sensor.cognitiveId));
    const usefulIds = new Set(usefulSensors.map(sensor => sensor.cognitiveId));

    recordSensoryHistory({
      tick: finiteNumber(tel.tick, 0),
      sampled: sampledSensors.length,
      useful: usefulSensors.length,
      integrated: connectedSensors.length,
      concepts: concepts.length,
      predictors: predictors.length,
      error: Object.values(predictionErrors).filter(value => ['medium','high','extreme'].includes(String(value))).length,
    });

    if (metrics) {
      metrics.replaceChildren();
      const metricData = [
        ['Perception', `${sampledSensors.length}/${sensory.length || sensorNodes.length}`],
        ['Useful', String(usefulSensors.length)],
        ['Integrated', String(connectedSensors.length)],
        ['Concepts', String(concepts.length)],
        ['Predictors', String(predictors.length)],
      ];
      for (const [label, value] of metricData) {
        const cell = el('span', 'mind-sensory-metric');
        const key = el('small', '');
        key.textContent = label;
        const val = el('b', '');
        val.textContent = value;
        cell.append(key, val);
        metrics.appendChild(cell);
      }
    }

    const title = svgEl('text', { x: 30, y: 30, fill: PAL.text, 'font-size': '14', 'font-weight': '650' });
    title.textContent = {
      topology: 'Learned sensory topology',
      activity: 'Live perceptual activity',
      prediction: 'Predictive sensory pathways',
      novelty: 'Sensory discovery frontier',
      sensorimotor: 'Sensorimotor consequence map',
    }[sensoryView.lens] ?? 'Body-derived sensory topology';
    mapSvg.appendChild(title);
    const summary = svgEl('text', { x: 30, y: 49, fill: PAL.muted, 'font-size': '9' });
    summary.textContent = `${sensory.length || sensorNodes.length} available · ${sampledSensors.length} sampled · ${usefulSensors.length} useful · ${connectedSensors.length} cognition-integrated · ${concepts.length} concepts`;
    mapSvg.appendChild(summary);

    const funnelY = 72;
    const funnelStages = [
      ['AVAILABLE', sensory.length || sensorNodes.length, PAL.muted],
      ['SAMPLED', sampledSensors.length, PAL.cyan],
      ['USEFUL', usefulSensors.length, PAL.mint],
      ['INTEGRATED', connectedSensors.length, PAL.violet],
      ['PREDICTORS', predictors.length, PAL.amber],
      ['READOUTS', readouts.length, PAL.mint],
    ];
    const stageW = 128;
    funnelStages.forEach(([label,count,color], index) => {
      const x = 30 + index * 148;
      mapSvg.appendChild(svgEl('line', {
        x1: x + stageW, y1: funnelY + 10, x2: x + 142, y2: funnelY + 10,
        stroke: PAL.muted, 'stroke-width': '0.7', opacity: index === funnelStages.length - 1 ? '0' : '0.3',
      }));
      const box = svgEl('g');
      box.appendChild(svgEl('rect', {
        x, y: funnelY - 3, width: stageW, height: 27, rx: '5',
        fill: 'rgba(255,255,255,.018)', stroke: color, 'stroke-opacity': '0.22',
      }));
      const labelNode = svgEl('text', { x: x + 9, y: funnelY + 8, fill: PAL.muted, 'font-size': '7' });
      labelNode.textContent = label;
      const countNode = svgEl('text', { x: x + stageW - 9, y: funnelY + 14, fill: color, 'font-size': '11', 'text-anchor': 'end', 'font-weight': '650' });
      countNode.textContent = String(count);
      box.append(labelNode, countNode);
      mapSvg.appendChild(box);
    });

    const sensorArea = { x: 40, y: 135, w: 330, h: 435 };
    const conceptArea = { x: 490, y: 135, w: 330, h: 435 };
    const outputArea = { x: 915, y: 135, w: 140, h: 435 };
    const sensorPos = new Map();
    const internalPos = new Map();

    const sensorCols = 18;
    const sensorRows = Math.max(1, Math.ceil(Math.max(1, sensorNodes.length) / sensorCols));
    const sx = sensorArea.w / Math.max(1, sensorCols - 1);
    const sy = Math.min(27, sensorArea.h / Math.max(1, sensorRows - 1));
    sensorNodes.forEach((node, index) => {
      sensorPos.set(node.id, {
        x: sensorArea.x + (index % sensorCols) * sx,
        y: sensorArea.y + Math.floor(index / sensorCols) * sy,
      });
    });

    const conceptLike = internalNodes.filter(n => !['predictor','readout'].includes(n.kind));
    const conceptCols = Math.min(9, Math.max(1, Math.ceil(Math.sqrt(conceptLike.length * 1.4))));
    const conceptRows = Math.max(1, Math.ceil(conceptLike.length / conceptCols));
    conceptLike.forEach((node, index) => {
      const seed = hashStr(node.id);
      const jitterX = ((seed % 11) - 5) * 1.7;
      const jitterY = (((seed >> 4) % 11) - 5) * 1.4;
      internalPos.set(node.id, {
        x: conceptArea.x + (index % conceptCols) * (conceptArea.w / Math.max(1, conceptCols - 1)) + jitterX,
        y: conceptArea.y + Math.floor(index / conceptCols) * (conceptArea.h / Math.max(1, conceptRows - 1)) + jitterY,
      });
    });

    const outputNodes = [...predictors, ...readouts];
    outputNodes.forEach((node, index) => {
      internalPos.set(node.id, {
        x: outputArea.x + (node.kind === 'readout' ? 92 : 22),
        y: outputArea.y + 22 + index * Math.min(46, outputArea.h / Math.max(1, outputNodes.length)),
      });
    });

    const allPos = new Map([...sensorPos, ...internalPos]);

    const lensKeepsNode = (node) => {
      const active = finiteNumber(activationClasses[node.id], 0) > 0;
      if (sensoryView.lens === 'activity') return node.kind === 'sense' ? sampledIds.has(node.id) : active;
      if (sensoryView.lens === 'prediction') return node.kind === 'predictor' || (outgoing.get(node.id) ?? []).some(e => e.kind === 'predictive') || (incoming.get(node.id) ?? []).some(e => e.kind === 'predictive');
      if (sensoryView.lens === 'sensorimotor') return node.kind === 'readout' || node.kind === 'sense' || (outgoing.get(node.id) ?? []).some(e => readouts.some(r => r.id === e.targetId));
      if (sensoryView.lens === 'novelty' && node.kind === 'sense') {
        const fact = sensory.find(item => item.cognitiveId === node.id);
        return !fact?.integrated || (fact?.confidence ?? 0) < 0.5;
      }
      return true;
    };

    for (const edge of topoEdges) {
      const source = allPos.get(edge.sourceId);
      const target = allPos.get(edge.targetId);
      if (!source || !target) continue;
      const sourceNode = topoNodes.find(n => n.id === edge.sourceId);
      const targetNode = topoNodes.find(n => n.id === edge.targetId);
      const highlighted = (sourceNode && lensKeepsNode(sourceNode)) || (targetNode && lensKeepsNode(targetNode));
      const selected = sensoryView.selectedNodeId && (edge.sourceId === sensoryView.selectedNodeId || edge.targetId === sensoryView.selectedNodeId);
      const color =
        edge.kind === 'inhibitory' ? PAL.coral :
        edge.kind === 'predictive' ? PAL.amber :
        edge.kind === 'gating' ? '#e09f3e' : PAL.cyan;
      mapSvg.appendChild(svgEl('line', {
        x1: source.x, y1: source.y, x2: target.x, y2: target.y,
        stroke: color,
        'stroke-width': selected ? '2.2' : edge.sourceId.startsWith('sensor.') ? '0.75' : '1.05',
        opacity: selected ? '0.9' : highlighted ? '0.32' : '0.055',
      }));
    }

    const kindColor = {
      sense: PAL.cyan,
      concept: PAL.violet,
      predictor: PAL.amber,
      readout: PAL.mint,
      state: '#4ecdc4',
      gate: '#e09f3e',
    };

    for (const node of topoNodes) {
      const pos = allPos.get(node.id);
      if (!pos) continue;
      const degree = (outgoing.get(node.id) ?? []).length + (incoming.get(node.id) ?? []).length;
      const actLevel = clamp01(finiteNumber(activationClasses[node.id], 0) / 15);
      const fact = node.kind === 'sense' ? sensory.find(item => item.cognitiveId === node.id) : null;
      const isSampled = fact?.sampled ?? sampledIds.has(node.id);
      const isUseful = fact?.utility > 0 || usefulIds.has(node.id);
      const focus = lensKeepsNode(node);
      const selected = sensoryView.selectedNodeId === node.id;
      const uncertainty = fact ? 1 - clamp01(fact.confidence) : 0;
      let radius = node.kind === 'sense' ? 3.0 : node.kind === 'readout' ? 8 : 5.5;
      radius += Math.min(4, degree * 0.18) + actLevel * 2.5;
      if (selected) radius += 2;

      if ((sensoryView.lens === 'novelty' && uncertainty > 0.5) || predictionErrors[node.id]) {
        mapSvg.appendChild(svgEl('circle', {
          cx: pos.x, cy: pos.y, r: radius + 4.5,
          fill: 'none',
          stroke: predictionErrors[node.id] ? PAL.coral : PAL.amber,
          'stroke-width': '0.8',
          'stroke-dasharray': '2.5 2',
          opacity: String(0.24 + uncertainty * 0.55),
        }));
      }

      const circle = svgEl('circle', {
        cx: pos.x, cy: pos.y,
        r: radius.toFixed(1),
        fill: kindColor[node.kind] ?? PAL.violet,
        opacity: selected ? '1' : focus ? String(0.45 + Math.max(actLevel, isSampled ? 0.45 : 0) * 0.5) : '0.13',
        stroke: selected ? 'rgba(255,255,255,.8)' : isUseful ? 'rgba(255,255,255,.18)' : 'none',
        'stroke-width': selected ? '1.5' : '0.7',
      });
      const tooltip = svgEl('title');
      const semantic = sensorySemantic(snap.observerSemantics, node.id);
      const observerContext = observerContextForNode(topology, snap.observerSemantics, node.id, 2);
      const observerText = semantic?.observerSummary ?? observerContext.summary ?? 'observer unresolved';
      tooltip.textContent = `${node.kind} · Self: ${node.id} · ${observerText} · degree ${degree} · activation ${Math.round(actLevel * 100)}%`;
      circle.appendChild(tooltip);
      circle.style.cursor = 'pointer';
      circle.addEventListener('click', () => {
        sensoryView.selectedNodeId = node.id;
        renderSensesPanel();
        renderSensoryMap();
      });
      mapSvg.appendChild(circle);
    }

    const sensorLabel = svgEl('text', { x: sensorArea.x, y: H - 34, fill: PAL.muted, 'font-size': '9' });
    sensorLabel.textContent = 'RECEPTOR FIELD · brightness = present relevance';
    const conceptLabel = svgEl('text', { x: conceptArea.x, y: H - 34, fill: PAL.muted, 'font-size': '9' });
    conceptLabel.textContent = 'LEARNED REPRESENTATION · concepts / state / gates';
    const outputLabel = svgEl('text', { x: outputArea.x, y: H - 34, fill: PAL.muted, 'font-size': '9' });
    outputLabel.textContent = 'EXPECTATION / OUTPUT';
    mapSvg.append(sensorLabel, conceptLabel, outputLabel);

    const selectedNode = topoNodes.find(node => node.id === sensoryView.selectedNodeId) ??
      topoNodes.find(node => finiteNumber(activationClasses[node.id], 0) > 0) ??
      null;
    if (inspector) renderSensoryInspector(inspector, selectedNode, topology, sensory);

    if (timeline) renderSensoryTimeline(timeline);

    if (detail) {
      const discovery = snap.details?.sensoryDiscoveryCounts ?? {};
      const discoveryText = Object.entries(discovery)
        .sort((a,b) => b[1]-a[1])
        .map(([state,count]) => `${state} ${count}`)
        .join(' · ');
      detail.textContent =
        `Sensory funnel: available ${sensory.length || sensorNodes.length} → sampled ${sampledSensors.length} → useful-now ${usefulSensors.length} → cognition-integrated ${connectedSensors.length}. ` +
        (discoveryText ? `Discovery hypotheses: ${discoveryText}. ` : '') +
        'Lens changes presentation only — organism state and learning remain untouched.';
    }
  }

  function bindSensoryControls() {
    const controls = document.querySelectorAll('[data-sensory-lens]');
    controls.forEach(button => {
      button.classList.toggle('active', button.dataset.sensoryLens === sensoryView.lens);
      if (button.dataset.sensoryBound === 'true') return;
      button.dataset.sensoryBound = 'true';
      button.addEventListener('click', () => {
        sensoryView.lens = button.dataset.sensoryLens ?? 'topology';
        controls.forEach(item => item.classList.toggle('active', item === button));
        renderSensoryMap();
      });
    });
  }

  function recordSensoryHistory(point) {
    const last = sensoryView.history[sensoryView.history.length - 1];
    if (last?.tick === point.tick) return;
    sensoryView.history.push(point);
    while (sensoryView.history.length > 72) sensoryView.history.shift();
  }

  function renderSensoryTimeline(container) {
    container.replaceChildren();
    const label = el('span', 'mind-sensory-timeline-label');
    label.textContent = 'RECENT PERCEPTION';
    const bars = el('div', 'mind-sensory-timeline-bars');
    const max = Math.max(1, ...sensoryView.history.map(point => point.sampled + point.error * 2));
    for (const point of sensoryView.history) {
      const bar = el('i', `mind-sensory-timeline-bar${point.error ? ' error' : point.predictors ? ' learning' : ''}`);
      bar.style.height = `${Math.max(8, Math.round(((point.sampled + point.error * 2) / max) * 100))}%`;
      bar.title = `tick ${point.tick} · sampled ${point.sampled} · useful ${point.useful} · integrated ${point.integrated} · concepts ${point.concepts} · predictors ${point.predictors}`;
      bars.appendChild(bar);
    }
    const now = el('span', 'mind-sensory-timeline-now');
    now.textContent = sensoryView.history.length ? `t${sensoryView.history[sensoryView.history.length - 1].tick}` : '—';
    container.append(label, bars, now);
  }

  function renderSensoryInspector(container, node, topology, sensory) {
    container.replaceChildren();
    const heading = el('div', 'mind-sensory-inspector-heading');
    heading.textContent = 'INSPECTOR';
    container.appendChild(heading);

    if (!node) {
      const empty = el('div', 'mind-sensory-inspector-empty');
      empty.textContent = 'Select a receptor, concept, predictor or readout to inspect its evidence and role.';
      container.appendChild(empty);
      return;
    }

    const topoEdges = Array.isArray(topology.edges) ? topology.edges : [];
    const incoming = topoEdges.filter(edge => edge.targetId === node.id);
    const outgoing = topoEdges.filter(edge => edge.sourceId === node.id);
    const activation = clamp01(finiteNumber((snap.observerAnalysis?.activationClasses ?? snap.cognition?.activationClasses ?? {})[node.id], 0) / 15);
    const fact = node.kind === 'sense' ? sensory.find(item => item.cognitiveId === node.id) : null;
    const semantic = sensorySemantic(snap.observerSemantics, node.id);
    const observerContext = observerContextForNode(topology, snap.observerSemantics, node.id, 2);

    const title = el('strong', 'mind-sensory-inspector-title');
    title.textContent = shortId(node.id, 20, 10);
    const kind = el('span', 'mind-sensory-inspector-kind');
    kind.textContent = String(node.kind ?? 'concept').toUpperCase();
    container.append(title, kind);

    const observer = el('p', 'mind-sensory-inspector-copy');
    observer.textContent = semantic?.observerSummary ?? observerContext.summary ?? 'Observer semantics unresolved.';
    container.appendChild(observer);

    const rows = [
      ['Activation', pct(activation)],
      ['Incoming', String(incoming.length)],
      ['Outgoing', String(outgoing.length)],
    ];
    if (fact) {
      rows.push(
        ['Sampled now', fact.sampled ? 'yes' : 'no'],
        ['Utility', fact.utility.toFixed(3)],
        ['Confidence', pct(fact.confidence)],
        ['Health', pct(fact.health)],
        ['Maturity', fact.maturity],
      );
    }
    for (const [key,value] of rows) {
      const row = el('div', 'mind-sensory-inspector-row');
      const k = el('span', '');
      k.textContent = key;
      const v = el('b', '');
      v.textContent = value;
      row.append(k,v);
      container.appendChild(row);
    }

    const relTitle = el('div', 'mind-sensory-inspector-section');
    relTitle.textContent = 'PATHWAYS';
    container.appendChild(relTitle);
    const relations = [...incoming.slice(0,4).map(edge => ['←', edge.sourceId, edge.kind]), ...outgoing.slice(0,5).map(edge => ['→', edge.targetId, edge.kind])];
    if (!relations.length) {
      const none = el('div', 'mind-sensory-inspector-empty');
      none.textContent = 'No learned cognitive path yet.';
      container.appendChild(none);
    } else {
      for (const [arrow,id,edgeKind] of relations) {
        const rel = el('button', 'mind-sensory-path');
        rel.type = 'button';
        rel.textContent = `${arrow} ${shortId(id,14,7)} · ${edgeKind}`;
        rel.addEventListener('click', () => {
          sensoryView.selectedNodeId = id;
          renderSensoryMap();
          renderSensesPanel();
        });
        container.appendChild(rel);
      }
    }

    const why = el('div', 'mind-sensory-why');
    const whyTitle = el('strong', '');
    whyTitle.textContent = node.kind === 'sense' ? 'Why this receptor matters' : 'Why this node is here';
    const whyCopy = el('span', '');
    if (fact) {
      whyCopy.textContent = fact.integrated
        ? `It participates in ${fact.degree} learned relation${fact.degree === 1 ? '' : 's'} with utility ${fact.utility.toFixed(2)}.`
        : fact.sampled
          ? 'It is currently sampled but has not yet acquired a learned cognitive path.'
          : 'It is available to the organism but is neither active nor integrated in the current snapshot.';
    } else {
      whyCopy.textContent = `${incoming.length} incoming and ${outgoing.length} outgoing learned relations are currently observable.`;
    }
    why.append(whyTitle, whyCopy);
    container.appendChild(why);
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Self-model projection — organism-owned BodySchema
  // ─────────────────────────────────────────────────────────────────────────────
  
  function identityMetrics() {
    const phenotype = snap.sensoryPhenotype ?? {};
    const phenotypeSensors = Array.isArray(phenotype.sensors) ? phenotype.sensors : [];
    const schema = snap.bodySchema ?? {};
    const parts = Array.isArray(schema.parts) ? schema.parts : [];
    const sensoryParts = parts.filter(part => part.kind === 'sense');
    const cognitiveRegions = parts.filter(part => part.kind === 'cognitive_region');
    const dependencies = Array.isArray(schema.dependencies) ? schema.dependencies : [];
  
    const topology = snap.topology ?? {};
    const topoNodes = Array.isArray(topology.nodes) ? topology.nodes : [];
    const topoEdges = Array.isArray(topology.edges) ? topology.edges : [];
    const graphCounts = {
      sense: topoNodes.filter(node => node.kind === 'sense').length,
      concept: topoNodes.filter(node => node.kind === 'concept').length,
      predictor: topoNodes.filter(node => node.kind === 'predictor').length,
      readout: topoNodes.filter(node => node.kind === 'readout').length,
    };
  
    const mean = (values) => values.length
      ? values.reduce((sum, value) => sum + value, 0) / values.length
      : 0;
  
    const existence = mean(sensoryParts.map(part => classRatio(part.existence_confidence_class, 15)));
    const confidence = mean(sensoryParts.map(part => classRatio(part.confidence_class, 15)));
    const maturity = mean(sensoryParts.map(part => classRatio(part.maturity_class, 7)));
    const health = mean(sensoryParts.map(part => classRatio(part.health_class, 15)));
  
    const observedSensorCount = phenotypeSensors.length || graphCounts.sense || (snap.senses ?? []).length;
    const sensoryCoverage = observedSensorCount > 0
      ? Math.min(1, sensoryParts.length / observedSensorCount)
      : 0;
  
    return {
      tick: finiteNumber(tel.tick, 0),
      observedSensorCount,
      sensoryPartCount: sensoryParts.length,
      sensoryCoverage,
      existence,
      confidence,
      maturity,
      health,
      cognitiveRegions: cognitiveRegions.length,
      dependencies: dependencies.length,
      schemaState: schema.state ?? 'unknown',
      graphCounts,
      graphEdges: topoEdges.length,
    };
  }
  
  function recordIdentityHistory(metrics) {
    const last = identityHistory[identityHistory.length - 1];
    if (last?.tick === metrics.tick) return;
    identityHistory.push({ ...metrics });
    while (identityHistory.length > 180) identityHistory.shift();
  }
  
  function deltaText(value, previous, unit = '') {
    const delta = finiteNumber(value, 0) - finiteNumber(previous, 0);
    if (Math.abs(delta) < 1e-9) return 'stable';
    return `${delta > 0 ? '+' : ''}${Number.isInteger(delta) ? delta : delta.toFixed(2)}${unit}`;
  }
  
  function renderIdentityGap() {
    const panel = document.getElementById('mind-identity-gap');
    if (!panel) return;
    panel.replaceChildren();
  
    const metrics = identityMetrics();
    recordIdentityHistory(metrics);
    const baseline = identityHistory[0] ?? metrics;
  
    const title = el('h3', 'mind-identity-gap-title');
    title.textContent = 'Difference';
    const subtitle = el('p', 'mind-identity-gap-subtitle');
    subtitle.textContent = 'What can be compared without breaking the organism’s opaque self-identities.';
    panel.append(title, subtitle);
  
    const metric = (label, left, right, note = '') => {
      const card = el('div', 'mind-identity-metric-card');
      const head = el('div', 'mind-identity-metric-head');
      head.textContent = label;
      const values = el('div', 'mind-identity-metric-values');
      const l = el('strong', 'mind-identity-metric-left');
      l.textContent = String(left);
      const arrow = el('span', 'mind-identity-metric-arrow');
      arrow.textContent = '⇄';
      const r = el('strong', 'mind-identity-metric-right');
      r.textContent = String(right);
      values.append(l, arrow, r);
      card.append(head, values);
      if (note) {
        const small = el('div', 'mind-identity-metric-note');
        small.textContent = note;
        card.appendChild(small);
      }
      panel.appendChild(card);
    };
  
    metric(
      'Sensory presence',
      metrics.observedSensorCount,
      metrics.sensoryPartCount,
      `Self representation coverage: ${pct(metrics.sensoryCoverage)}`,
    );
  
    metric(
      'Internal structure',
      `${metrics.graphCounts.concept}C · ${metrics.graphCounts.predictor}P · ${metrics.graphEdges}E`,
      `${metrics.cognitiveRegions} regions · ${metrics.dependencies} deps`,
      'These are different representational spaces; counts are shown side by side, not treated as one-to-one matches.',
    );
  
    const certainty = el('div', 'mind-self-certainty');
    const certaintyTitle = el('div', 'mind-self-certainty-title');
    certaintyTitle.textContent = 'How certain is the self-model?';
    certainty.appendChild(certaintyTitle);
    for (const [label, value] of [
      ['existence', metrics.existence],
      ['confidence', metrics.confidence],
      ['maturity', metrics.maturity],
      ['health', metrics.health],
    ]) {
      const row = el('div', 'mind-self-certainty-row');
      const name = el('span', 'mind-self-certainty-name'); name.textContent = label;
      const bar = el('div', 'mind-self-certainty-bar');
      const fill = el('div','mind-self-certainty-fill'); fill.style.width = pct(value);
      bar.appendChild(fill);
      const val = el('strong','mind-self-certainty-value'); val.textContent=pct(value);
      row.append(name,bar,val); certainty.appendChild(row);
    }
    panel.appendChild(certainty);
  
    const change = el('div', 'mind-identity-change');
    const spanTicks = Math.max(0, metrics.tick - baseline.tick);
    const changeTitle = el('strong', '');
    changeTitle.textContent = 'Recent self-model change';
    const changeDetail = el('span', '');
    changeDetail.textContent =
      `over ${spanTicks} ticks · sensory parts ${deltaText(metrics.sensoryPartCount, baseline.sensoryPartCount)} · ` +
      `regions ${deltaText(metrics.cognitiveRegions, baseline.cognitiveRegions)} · dependencies ${deltaText(metrics.dependencies, baseline.dependencies)} · ` +
      `existence ${deltaText(Math.round(metrics.existence*100), Math.round(baseline.existence*100), '%')}`;
    change.append(changeTitle, changeDetail);
    panel.appendChild(change);
  
    const opaque = el('div', 'mind-self-opaque-note');
    opaque.textContent =
      'Per-sensor identity correspondence is intentionally unknown here: BodySchema exposes opaque part IDs, so the observer cannot claim which external sensor equals which self-part.';
    panel.appendChild(opaque);
  }
  
  function renderSelf() {
    const panel = document.getElementById('mind-self-panel');
    if (!panel) return;
    panel.replaceChildren();
  
    const schema = snap.bodySchema;
    if (!schema || !schema.parts?.length) {
      const h = el('h2', 'mind-self-heading');
      h.textContent = 'Self-model not yet developed';
      const p = el('p', 'mind-self-body');
      p.textContent = 'No organism-owned body representation is available yet.';
      panel.append(h, p);
      return;
    }
  
    const parts = schema.parts ?? [];
    const sensoryParts = parts.filter(part => part.kind === 'sense');
    const cognitiveRegions = parts.filter(part => part.kind === 'cognitive_region');
    const dependencies = schema.dependencies ?? [];
  
    const perceptualSelf = snap.selfModel ?? {};
    const selfEntries = Object.entries(perceptualSelf);
  
    const h = el('h2', 'mind-self-heading');
    h.textContent = 'How it represents itself';
    const body = el('p', 'mind-self-body');
    body.textContent =
      'Organism-owned BodySchema only: sensory parts, cognitive regions and functional dependencies treated as self.';
    panel.append(h, body);
  
    const perceptual = el('section', 'mind-perceptual-self');
    const ptitle = el('strong','mind-perceptual-self-title');
    ptitle.textContent='Perceptual self-model';
    const pcopy = el('div','mind-perceptual-self-copy');
    pcopy.textContent=`${selfEntries.length} established self-modeled receptors · organism-owned cost/health/confidence/maturity/recency classes`;
    perceptual.append(ptitle,pcopy);
  
    if (selfEntries.length) {
      const dots=el('div','mind-perceptual-self-dots');
      selfEntries.slice(0,64).forEach(([id,entry])=>{
        const dot=el('span','');
        const confidence=classRatio(entry?.confidence_class,15);
        const health=classRatio(entry?.health_class,15);
        const maturity=classRatio(entry?.maturity_class,7);
        dot.style.cssText=`width:${4+Math.round(maturity*5)}px;height:${4+Math.round(maturity*5)}px;border-radius:50%;display:block;background:${health>.7?PAL.cyan:health>.4?PAL.amber:PAL.coral};opacity:${0.25+confidence*0.7};`;
        dot.title=`${id}\nhealth ${pct(health)} · confidence ${pct(confidence)} · maturity ${pct(maturity)} · recency class ${entry?.recency_class ?? '—'}`;
        dots.appendChild(dot);
      });
      perceptual.appendChild(dots);
    }
    panel.appendChild(perceptual);
  
    const schemaLabel=el('strong','mind-self-schema-label');
    schemaLabel.textContent='Functional BodySchema';
    panel.appendChild(schemaLabel);
  
    const summary = el('div', 'mind-self-summary');
    summary.textContent =
      `${sensoryParts.length} sensory parts · ${cognitiveRegions.length} cognitive regions · ${dependencies.length} learned dependencies · state ${schema.state ?? 'unknown'}`;
    panel.appendChild(summary);
  
    const portrait = svgEl('svg', {
      viewBox: '0 0 1000 650',
      role: 'img',
      'aria-label': 'Symbiont organism-owned self-model',
      class: 'mind-self-portrait',
    });
    panel.appendChild(portrait);
  
    const cx = 500, cy = 325;
    const regionRadius = 135;
    const senseRadius = 270;
  
    // Self boundary is only an epistemic envelope, not anatomy. Individual
    // parts move inward/outward according to organism-owned certainty.
    const boundary = svgEl('ellipse', {
      cx, cy, rx: '330', ry: '265',
      fill: 'rgba(113,233,186,.025)',
      stroke: 'rgba(113,233,186,.34)',
      'stroke-width': '1.5',
      'stroke-dasharray': '6 7',
    });
    portrait.appendChild(boundary);
  
    const selfTitle = svgEl('text', {
      x: cx, y: cy + 4,
      'text-anchor': 'middle',
      fill: PAL.mint,
      'font-size': '15',
      'font-weight': '700',
    });
    selfTitle.textContent = 'SELF';
    portrait.appendChild(selfTitle);
    const selfSub = svgEl('text', {
      x: cx, y: cy + 23,
      'text-anchor': 'middle',
      fill: PAL.muted,
      'font-size': '9',
    });
    selfSub.textContent = 'organism-owned body schema';
    portrait.appendChild(selfSub);
  
    const regionPos = new Map();
    cognitiveRegions.forEach((region, index) => {
      const confidence = classRatio(region.confidence_class, 15);
      const maturity = classRatio(region.maturity_class, 7);
      const seed = hashStr(region.part_id);
      const angle = ((seed % 3600) / 3600) * Math.PI * 2;
      const inward = 1 - (0.55 * confidence + 0.45 * maturity);
      const radius = 50 + regionRadius * (0.35 + inward * 0.65);
      regionPos.set(region.part_id, {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius * 0.78,
      });
    });
  
    // Functional dependencies are temporally smoothed on the observer side:
    // current evidence is solid, recurrent-but-intermittent evidence remains faint.
    const nowTick = finiteNumber(tel.tick, 0);
    const dependencyViews = [...selfDependencyHistory.values()]
      .filter(state => state.current || (state.observations > 1 && nowTick - state.lastTick <= 256));
    for (const state of dependencyViews) {
      const dep = state.dep;
      const source = regionPos.get(dep.source_id);
      const target = regionPos.get(dep.target_id);
      if (!source || !target) continue;
      const confidence = classRatio(dep.confidence_class, 15);
      const support = classRatio(dep.support_class, 15);
      const persistent = state.observations >= 8;
      const recentBirth = nowTick - state.firstTick <= 32;
      const opacity = state.current
        ? Math.min(0.95, 0.28 + support * 0.55 + (persistent ? 0.12 : 0))
        : 0.12;
      const line = svgEl('line', {
        x1: source.x, y1: source.y,
        x2: target.x, y2: target.y,
        stroke: dep.relation === 'precedes' ? PAL.amber : PAL.violet,
        'stroke-width': String(state.current ? 1 + confidence * 3 : 0.8),
        opacity: String(opacity),
        'stroke-dasharray': !state.current ? '2 5' : dep.relation === 'precedes' ? '4 4' : 'none',
      });
      if (recentBirth && state.current) line.setAttribute('stroke-width', String(2 + confidence * 3));
      const title = svgEl('title');
      title.textContent =
        `${dep.relation} · confidence ${pct(confidence)} · support ${pct(support)} · ` +
        `${state.current ? 'current' : 'recurrent/intermittent'} · observed ${state.observations} snapshots`;
      line.appendChild(title);
      portrait.appendChild(line);
    }
  
    // Cognitive regions are the inner learned functional self.
    cognitiveRegions.forEach((region, index) => {
      const pos = regionPos.get(region.part_id);
      if (!pos) return;
      const existence = classRatio(region.existence_confidence_class, 15);
      const confidence = classRatio(region.confidence_class, 15);
      const activity = classRatio(region.activity_class, 15);
      const maturity = classRatio(region.maturity_class, 7);
      const persistence = selfRegionHistory.get(region.part_id);
      const persistenceScore = persistence
        ? clamp01(persistence.observations / Math.max(8, identityHistory.length || 8))
        : 0;
      const radius = 7 + 8 * Math.sqrt(Math.max(activity, maturity * 0.6)) + persistenceScore * 4;
      const node = svgEl('circle', {
        cx: pos.x, cy: pos.y, r: radius.toFixed(1),
        fill: PAL.violet,
        opacity: String(0.35 + existence * 0.6),
        stroke: confidence > 0.7 ? PAL.mint : 'rgba(167,119,255,.45)',
        'stroke-width': String(1 + confidence * 1.6 + persistenceScore * 1.5),
      });
      const title = svgEl('title');
      title.textContent =
        `Cognitive region ${index + 1}\nexistence ${pct(existence)} · confidence ${pct(confidence)} · activity ${pct(activity)} · maturity ${pct(maturity)} · persistence ${pct(persistenceScore)}\n${region.part_id}`;
      node.appendChild(title);
      portrait.appendChild(node);
    });
  
    // Sensory parts form the outer perceived boundary of self. Their positions
    // are deliberately non-anatomical because BodySchema contains no spatial
    // anatomy and inventing one would contaminate interpretation.
    sensoryParts.forEach((part, index) => {
      const existence = classRatio(part.existence_confidence_class, 15);
      const health = classRatio(part.health_class, 15);
      const confidence = classRatio(part.confidence_class, 15);
      const maturity = classRatio(part.maturity_class, 7);
      const seed = hashStr(part.part_id ?? String(index));
      const angle = ((seed % 10000) / 10000) * Math.PI * 2;
      const uncertainty = 1 - (existence * 0.55 + confidence * 0.25 + maturity * 0.20);
      const radialNoise = (((seed >>> 4) % 101) / 100 - 0.5) * 38;
      const r = 190 + senseRadius * 0.18 + uncertainty * 72 + radialNoise;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r * 0.78;
      const radius = 2.5 + 5.5 * Math.sqrt(Math.max(confidence, maturity * 0.5));
      const healthColor =
        health > 0.75 ? PAL.cyan :
        health > 0.45 ? PAL.amber : PAL.coral;
  
      const spoke = svgEl('line', {
        x1: cx, y1: cy, x2: x, y2: y,
        stroke: healthColor,
        'stroke-width': '0.55',
        opacity: String(0.035 + confidence * 0.11),
      });
      portrait.appendChild(spoke);
  
      const node = svgEl('circle', {
        cx: x, cy: y, r: radius.toFixed(1),
        fill: healthColor,
        opacity: String(0.22 + existence * 0.75),
        stroke: confidence > 0.75 ? 'rgba(255,255,255,.38)' : 'none',
        'stroke-width': '0.8',
      });
      const title = svgEl('title');
      title.textContent =
        `Sensory part ${index + 1}\nexistence ${pct(existence)} · health ${pct(health)} · confidence ${pct(confidence)} · maturity ${pct(maturity)}\n${part.part_id}`;
      node.appendChild(title);
      portrait.appendChild(node);
    });
  
    const legend = svgEl('text', {
      x: '26', y: '625',
      fill: PAL.muted,
      'font-size': '10',
    });
    legend.textContent =
      'Outer ring = self-known sensory parts · inner nodes = learned cognitive regions · lines = organism-inferred functional dependencies · size/opacity = organism-owned confidence/activity/maturity';
    portrait.appendChild(legend);
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Cognition Graph (force-directed canvas; adapted from observatory/render/cognition-graph.js)
  // ─────────────────────────────────────────────────────────────────────────────

  return {
    renderIdentityGap,
    renderPhenotype,
    renderSelf,
    renderSensesPanel,
    renderSensoryMap,
  };
}
