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
  
    const summary = el('div', 'mind-senses-summary');
    const sampled = sensors.filter(sensor => sensor.sampled).length;
    const useful = sensors.filter(sensor => sensor.utility > 0).length;
    const integrated = sensors.filter(sensor => sensor.integrated).length;
    const summaryTitle = el('strong', '');
    summaryTitle.textContent = `${sensors.length} receptors`;
    const summaryDetail = el('span', '');
    summaryDetail.textContent =
      `${sampled} sampled now · ${useful} utility > 0 · ${integrated} cognition-integrated`;
    summary.append(summaryTitle, summaryDetail);
    list.appendChild(summary);
  
    const header = el('div', 'mind-senses-header');
    for (const label of ['receptor', 'now', 'util', 'deg']) {
      const cell = el('span', '');
      cell.textContent = label;
      header.appendChild(cell);
    }
    list.appendChild(header);
  
    [...sensors]
      .sort((a,b) =>
        Number(b.integrated)-Number(a.integrated) ||
        b.utility-a.utility ||
        b.degree-a.degree ||
        String(a.cognitiveId).localeCompare(String(b.cognitiveId))
      )
      .forEach(sensor => {
        const row=el('button','mind-sense-table-row');
        row.type='button';
        const name=el('span','mind-sense-table-name');
        name.textContent=shortId(sensor.cognitiveId,9,5);
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
        row.addEventListener('click',()=>onSelectCognitiveNode(sensor.cognitiveId));
        list.appendChild(row);
      });
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
    if (!mapSvg) return;
    mapSvg.replaceChildren();
  
    const senses = snap.senses ?? [];
    const topology = snap.topology ?? { nodes: [], edges: [] };
    const topoNodes = Array.isArray(topology.nodes) ? topology.nodes : [];
    const topoEdges = Array.isArray(topology.edges) ? topology.edges : [];
  
    if (!senses.length && !topoNodes.length) {
      const msg = svgEl('text', { x: '450', y: '300', 'text-anchor': 'middle', fill: PAL.muted, 'font-size': '14' });
      msg.textContent = 'No sensory topology yet — awaiting snapshot…';
      mapSvg.appendChild(msg);
      if (detail) detail.textContent = 'This view shows the real cognitive paths learned from body-derived sensory channels.';
      return;
    }
  
    const W = 900, H = 600;
    const sensorNodes = topoNodes.filter(n => n.kind === 'sense');
    const internalNodes = topoNodes.filter(n => n.kind !== 'sense');
    const nodeById = new Map(topoNodes.map(n => [n.id, n]));
  
    const outgoing = new Map();
    for (const edge of topoEdges) {
      if (!outgoing.has(edge.sourceId)) outgoing.set(edge.sourceId, []);
      outgoing.get(edge.sourceId).push(edge);
    }
  
    const connectedSensors = sensorNodes.filter(n => (outgoing.get(n.id) ?? []).length > 0);
    const sensory = sensoryFacts();
    const sampledSensors = sensory.filter(sensor => sensor.sampled);
    const usefulSensors = sensory.filter(sensor => sensor.utility > 0);
    const concepts = internalNodes.filter(n => n.kind === 'concept');
    const predictors = internalNodes.filter(n => n.kind === 'predictor');
    const readouts = internalNodes.filter(n => n.kind === 'readout');
  
    const title = svgEl('text', { x: 28, y: 28, fill: PAL.text, 'font-size': '13', 'font-weight': '600' });
    title.textContent = 'Body-derived sensory topology';
    mapSvg.appendChild(title);
    const summary = svgEl('text', { x: 28, y: 47, fill: PAL.muted, 'font-size': '10' });
    summary.textContent = `${sensory.length || sensorNodes.length} available · ${sampledSensors.length} sampled now · ${usefulSensors.length} utility > 0 · ${connectedSensors.length} cognition-integrated · ${concepts.length} concepts`;
    mapSvg.appendChild(summary);
  
    const sensorArea = { x: 45, y: 80, w: 300, h: 470 };
    const internalArea = { x: 500, y: 80, w: 340, h: 470 };
  
    const sensorCols = 16;
    const sensorRows = Math.max(1, Math.ceil(Math.max(1, sensorNodes.length) / sensorCols));
    const sx = sensorArea.w / Math.max(1, sensorCols - 1);
    const sy = Math.min(34, sensorArea.h / Math.max(1, sensorRows - 1));
    const sensorPos = new Map();
  
    sensorNodes.forEach((node, index) => {
      const col = index % sensorCols;
      const row = Math.floor(index / sensorCols);
      sensorPos.set(node.id, {
        x: sensorArea.x + col * sx,
        y: sensorArea.y + row * sy,
      });
    });
  
    const kinds = ['concept', 'predictor', 'state', 'gate', 'readout'];
    const internalPos = new Map();
    let cursorY = internalArea.y;
    for (const kind of kinds) {
      const group = internalNodes.filter(n => n.kind === kind);
      if (!group.length) continue;
      const heading = svgEl('text', {
        x: internalArea.x,
        y: cursorY,
        fill: PAL.muted,
        'font-size': '9',
        'font-weight': '600',
      });
      heading.textContent = `${kind.toUpperCase()} · ${group.length}`;
      mapSvg.appendChild(heading);
      cursorY += 16;
      const cols = Math.min(8, Math.max(1, group.length));
      const rows = Math.ceil(group.length / cols);
      const gx = internalArea.w / Math.max(1, cols - 1);
      const gy = Math.min(30, Math.max(18, 88 / Math.max(1, rows)));
      group.forEach((node, index) => {
        internalPos.set(node.id, {
          x: internalArea.x + (index % cols) * gx,
          y: cursorY + Math.floor(index / cols) * gy,
        });
      });
      cursorY += rows * gy + 28;
    }
  
    const allPos = new Map([...sensorPos, ...internalPos]);
  
    // Real learned topology edges first, behind nodes.
    for (const edge of topoEdges) {
      const source = allPos.get(edge.sourceId);
      const target = allPos.get(edge.targetId);
      if (!source || !target) continue;
      const color =
        edge.kind === 'inhibitory' ? PAL.coral :
        edge.kind === 'predictive' ? PAL.amber :
        edge.kind === 'gating' ? '#e09f3e' : PAL.cyan;
      mapSvg.appendChild(svgEl('line', {
        x1: source.x, y1: source.y, x2: target.x, y2: target.y,
        stroke: color,
        'stroke-width': edge.sourceId.startsWith('sensor.') ? '0.8' : '1.1',
        opacity: edge.sourceId.startsWith('sensor.') ? '0.22' : '0.38',
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
      const isSense = node.kind === 'sense';
      const degree = topoEdges.reduce((count, e) => count + (e.sourceId === node.id || e.targetId === node.id ? 1 : 0), 0);
      const circle = svgEl('circle', {
        cx: pos.x, cy: pos.y,
        r: isSense ? (degree ? 4.5 : 3.2) : Math.min(9, 5 + degree * 0.35),
        fill: kindColor[node.kind] ?? PAL.violet,
        opacity: isSense && !degree ? '0.32' : '0.9',
        stroke: degree ? 'rgba(255,255,255,.18)' : 'none',
        'stroke-width': '0.7',
      });
      const tooltip = svgEl('title');
      const semantic = sensorySemantic(snap.observerSemantics, node.id);
      const observerContext = observerContextForNode(
        topology,
        snap.observerSemantics,
        node.id,
        2,
      );
      const observerText = semantic?.observerSummary
        ? `Observer: ${semantic.observerSummary}`
        : observerContext.summary
          ? `Observer context: ${observerContext.summary}`
          : 'Observer: unresolved';
      tooltip.textContent = `${node.kind} · Self: ${node.id} · ${observerText} · degree ${degree}`;
      circle.appendChild(tooltip);
      circle.style.cursor = 'pointer';
      circle.addEventListener('click', () => onSelectCognitiveNode(node.id));
      mapSvg.appendChild(circle);
    }
  
    const sensorLabel = svgEl('text', { x: sensorArea.x, y: H - 24, fill: PAL.muted, 'font-size': '10' });
    sensorLabel.textContent = 'Sensors: brighter = participates in learned topology';
    mapSvg.appendChild(sensorLabel);
  
    if (detail) {
      const discovery = snap.details?.sensoryDiscoveryCounts ?? {};
      const discoveryText = Object.entries(discovery)
        .sort((a,b) => b[1]-a[1])
        .map(([state,count]) => `${state} ${count}`)
        .join(' · ');
      detail.textContent =
        `Sensory funnel: available ${sensory.length || sensorNodes.length} → sampled ${sampledSensors.length} → useful-now ${usefulSensors.length} → cognition-integrated ${connectedSensors.length}. ` +
        (discoveryText ? `Discovery hypotheses: ${discoveryText}. ` : '') +
        'These sets overlap; the arrows are a reading aid, not a claim that every stage is a strict subset.';
    }
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
