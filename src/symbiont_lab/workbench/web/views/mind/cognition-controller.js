/**
 * Cognition controller.
 *
 * Owns the complete observer-side cognition map lifecycle: graph projection,
 * force layout, 2D/3D rendering, interaction, inspector and summary.
 */
import { el } from '../shared/dom.js';
import { augmentLearnedGraph } from './learning-graph.js';
import { cartographicGraph } from './cartographic-view.js';
import { buildCognition3DScene, orbitCamera, zoomCamera } from './cognition-3d.js';
import { inspectorMetric } from './components.js';
import { GRAPH_PHYSICS, PAL } from './config.js';
import { topologyComponentStats } from './derived.js';
import {
  buildLayoutAffinities,
  deriveFunctionalSectors,
  describeFunctionalSector,
  sectorBridges,
} from './functional-sectors.js';
import { enrichGraphModel } from './graph-model.js';
import { filterGraphForView, graphSubgraphIds } from './graph-selection.js';
import {
  compactSelfLabel,
  observerContextForNode,
  sensorySemantic,
} from './semantics.js';
import { graph, mindHistory, snap, tel } from './state.js';
import {
  classRatio,
  clamp01,
  finiteNumber,
  hashStr,
  pct,
  shortId,
} from './util.js';

export function createCognitionController({
  getActiveTab = () => 'overview',
  onSwitchTab = () => {},
} = {}) {
  let rafId = null;
  let windowMouseMove = null;
  let windowMouseUp = null;

  function selectCognitiveNode(nodeId) {
    graph.selectedNodeId = nodeId || null;
    onSwitchTab('cognition');
    renderCognitionInspector();
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
  }
  
  function buildGraphModel() {
    const source = graph.replaySnapshot ?? snap;
    const topology = source.topology;
    const cognition = source.cognition;
  
    if (!topology?.nodes?.length) {
      const beliefs = (snap.beliefs ?? []).slice(0, 8);
      const senses  = (snap.senses ?? []).slice(0, 4);
      const nodes = [
        ...senses.map(s => ({
          id: s.id,
          label: s.name ?? s.id,
          kind: 'sense',
          color: PAL.cyan,
          baseRadius: 6,
          activationLevel: s.active ? 0.8 : 0.1,
        })),
        ...beliefs.map(b => ({
          id: b.id,
          label: b.title ?? b.id,
          kind: 'concept',
          color: PAL.violet,
          baseRadius: 7,
          activationLevel: clamp01(b.certainty ?? 0.3),
        })),
      ];
      const edges = [];
      senses.forEach((s, si) => {
        beliefs.slice(si * 2, si * 2 + 2).forEach(b => {
          edges.push({ sourceId: s.id, targetId: b.id, kind: 'excitatory' });
        });
      });
      return enrichGraphModel(nodes, edges);
    }
  
    const errors   = (source.observerAnalysis?.predictionErrors ?? cognition?.predictionErrors) ?? {};
    const readouts = cognition?.readouts ?? {};
    const actClass = (source.observerAnalysis?.activationClasses ?? cognition?.activationClasses) ?? {};
    const stranded = cognition?.strandedConcepts ?? [];
  
    const learned = augmentLearnedGraph(
      topology,
      source.sensorimotor ?? snap.sensorimotor,
      source.observerSemantics ?? snap.observerSemantics,
      source.prospectiveAgency ?? null,
    );
    const cartography = cartographicGraph(
      learned.nodes,
      learned.edges,
      graph.selectedNodeId,
      graph.viewMode,
    );
    graph.hiddenMotor = cartography.hidden;
    const completeTopology = { nodes: cartography.nodes, edges: cartography.edges };
  
    const colorMap = {
      sense: PAL.cyan,
      readout: PAL.mint,
      state: '#4ecdc4',
      predictor: PAL.amber,
      gate: '#e09f3e',
      concept: PAL.violet,
      motor_primitive: '#ff8fd8',
      actuator: '#8fe3ff',
    };
    const baseRadiusMap = {
      sense: 5.2,
      readout: 8.5,
      state: 6.5,
      predictor: 7.2,
      gate: 6.8,
      concept: 6.4,
      motor_primitive: 8.4,
      actuator: 6.8,
    };
  
    const rawNodes = completeTopology.nodes.map(n => {
      const kind = n.kind ?? 'concept';
      const activationLevel = classRatio(actClass[n.id] ?? 0, 15);
      const readoutRaw = readouts[n.id];
      const readoutMagnitude = readoutRaw != null
        ? Math.min(1, Math.abs(finiteNumber(readoutRaw, 0)))
        : 0;
  
      const semantic = sensorySemantic(source.observerSemantics ?? snap.observerSemantics, n.id);
      return {
        id: n.id,
        label: n.id,
        observerLabel: n.observerLabel ?? semantic?.observerSummary ?? null,
        kind,
        color: colorMap[kind] ?? PAL.violet,
        baseRadius: baseRadiusMap[kind] ?? 6.4,
        activationLevel: n.replayActive || n.prospectiveSelected
          ? 1
          : activationLevel,
        readoutMagnitude,
        errorCls: errors[n.id] ?? null,
        readoutVal: readoutRaw != null ? finiteNumber(readoutRaw, 0).toFixed(3) : null,
        isStranded: stranded.includes(n.id),
        learnedLayer: n.learnedLayer ?? null,
        cognitivePrimitive: Boolean(n.cognitive),
        replayActive: Boolean(n.replayActive),
        prospectiveSelected: Boolean(n.prospectiveSelected),
        controllability: finiteNumber(n.controllability, 0),
        directionalConsistency: finiteNumber(n.directionalConsistency, 0),
        samples: finiteNumber(n.samples, 0),
        effectVariance: finiteNumber(n.effectVariance, 0),
        effectStrength: finiteNumber(n.effectStrength, 0),
        activations: finiteNumber(n.activations, 0),
        causalRelationCount: finiteNumber(n.causalRelationCount, 0),
        actuatorIds: n.actuatorIds ?? [],
        collapsedMotorDegree: finiteNumber(n.collapsedMotorDegree, 0),
        primitiveId: n.primitiveId ?? null,
        activeRepertoire: Boolean(n.activeRepertoire),
        effectorId: n.effectorId ?? null,
      };
    });
  
    const nodeSet = new Set(rawNodes.map(n => n.id));
    const edges = (completeTopology.edges ?? [])
      .filter(e => nodeSet.has(e.sourceId) && nodeSet.has(e.targetId))
      .map(e => ({
        sourceId: e.sourceId,
        targetId: e.targetId,
        kind: e.kind ?? 'excitatory',
        weight: finiteNumber(e.weight, 0),
        plasticity: clamp01(e.plasticity),
        delayTicks: finiteNumber(e.delayTicks, 0),
        support: finiteNumber(e.support, 0),
        ageTicks: finiteNumber(e.ageTicks, 0),
        stableTicks: finiteNumber(e.stableTicks, 0),
        lastUseTick: finiteNumber(e.lastUseTick, 0),
        learnedLayer: e.learnedLayer ?? null,
        correlation: finiteNumber(e.correlation, 0),
        samples: finiteNumber(e.samples, 0),
      }));
  
    const filtered = filterGraphForView(rawNodes, edges, graph.viewMode);
    const enriched = enrichGraphModel(filtered.nodes, filtered.edges);
  
    const affinities = buildLayoutAffinities(enriched.nodes, enriched.edges);
    const sectors = deriveFunctionalSectors(enriched.nodes, affinities);
    const sectorNodes = new Map();
    for (const node of enriched.nodes) {
      node.community = sectors.get(node.id) ?? 'isolated';
      if (node.community === 'isolated') continue;
      if (!sectorNodes.has(node.community)) sectorNodes.set(node.community, []);
      sectorNodes.get(node.community).push(node);
    }
    enriched.communities = sectors;
    enriched.layoutAffinities = affinities;
    enriched.sectorDescriptions = new Map(
      [...sectorNodes.entries()].map(([sectorId, members]) => [
        sectorId,
        describeFunctionalSector(members),
      ])
    );
    enriched.sectorBridges = sectorBridges(enriched.edges, sectors);
    return enriched;
  }
  
  function jaccardOverlap(a, b) {
    if (!a?.size || !b?.size) return 0;
    let intersection = 0;
    const smaller = a.size <= b.size ? a : b;
    const larger = smaller === a ? b : a;
    for (const item of smaller) if (larger.has(item)) intersection += 1;
    return intersection / (a.size + b.size - intersection);
  }
  
  function reconcileSectorLabels(communities, nodes) {
    const current = new Map();
    for (const node of nodes) {
      if (!node.community || node.community === 'isolated') continue;
      if (!current.has(node.community)) current.set(node.community, new Set());
      current.get(node.community).add(node.id);
    }
  
    const assigned = new Map();
    const usedPrevious = new Set();
    const ordered = [...current.entries()].sort((a,b) => b[1].size-a[1].size);
  
    for (const [communityId, members] of ordered) {
      let bestLabel = null;
      let bestOverlap = 0;
      for (const [label, previousMembers] of graph.sectorMemory.entries()) {
        if (usedPrevious.has(label)) continue;
        const overlap = jaccardOverlap(members, previousMembers);
        if (overlap > bestOverlap) {
          bestOverlap = overlap;
          bestLabel = label;
        }
      }
      if (!bestLabel || bestOverlap < 0.45) {
        bestLabel = `S-${String(graph.nextSectorId++).padStart(3,'0')}`;
      }
      usedPrevious.add(bestLabel);
      assigned.set(communityId, bestLabel);
    }
  
    graph.sectorLabels = assigned;
    graph.sectorMemory = new Map(
      [...assigned.entries()].map(([communityId,label]) => [label, new Set(current.get(communityId) ?? [])])
    );
  }
  
  function initGraphPhysics(width, height) {
    const {
      nodes: rawNodes,
      edges: rawEdges,
      adjacency,
      communities,
      components = [],
      layoutAffinities = [],
      sectorDescriptions = new Map(),
      sectorBridges: bridges = [],
    } = buildGraphModel();
    const cx = width / 2, cy = height / 2;
    const nodeMap = new Map();
  
    graph.communities = new Map();
    graph.components = components;
    graph.layoutAffinities = layoutAffinities;
    graph.sectorDescriptions = sectorDescriptions;
    graph.bridgeEdges = new Set();
    for (const bridge of bridges) {
      const ranked = [...bridge.edges].sort((a,b) =>
        finiteNumber(b.support,0) - finiteNumber(a.support,0) ||
        Math.abs(finiteNumber(b.correlation,0)) - Math.abs(finiteNumber(a.correlation,0))
      ).slice(0, 2);
      for (const edge of ranked) {
        graph.bridgeEdges.add(`${edge.sourceId}|${edge.targetId}|${edge.kind}`);
      }
    }
    for (const raw of rawNodes) {
      if (!raw.community || raw.community === 'isolated') continue;
      if (!graph.communities.has(raw.community)) {
        graph.communities.set(raw.community, []);
      }
      graph.communities.get(raw.community).push(raw.id);
    }
    if (graph.focusedSectorId && !graph.communities.has(graph.focusedSectorId)) {
      graph.focusedSectorId = null;
    }
    if (graph.replaySnapshot) {
      graph.sectorLabels = new Map(
        [...graph.communities.keys()].map(communityId => [
          communityId,
          `R-${String(hashStr(String(communityId)) % 997).padStart(3,'0')}`,
        ])
      );
    } else {
      reconcileSectorLabels(graph.communities, rawNodes);
    }
  
    const activeSectorLabels = new Set();
    for (const communityId of graph.communities.keys()) {
      const label = graph.sectorLabels.get(communityId);
      if (!label) continue;
      activeSectorLabels.add(label);
      if (!graph.sectorAnchors.has(label)) {
        const ordinal = Math.max(1, parseInt(label.replace(/\D/g, ''), 10) || (hashStr(label) % 97) + 1);
        const angle = ordinal * 2.399963229728653;
        const ring = ordinal % 3;
        const rx = Math.min(width * (0.20 + ring * 0.035), 320);
        const ry = Math.min(height * (0.18 + ring * 0.03), 230);
        graph.sectorAnchors.set(label, {
          x: cx + Math.cos(angle) * rx,
          y: cy + Math.sin(angle) * ry,
        });
      }
    }
  
    graph.nodes = rawNodes.map((raw, i) => {
      let node = graph.cachedPositions.get(raw.id);
      if (!node) {
        const seed = hashStr(raw.id);
        let x;
        let y;
  
        if (raw.isolated) {
          // Objective unintegrated pool: disconnected nodes occupy a peripheral
          // band instead of participating in the same force field as cognition.
          const cols = Math.max(8, Math.floor(width / 34));
          const isolatedIndex = rawNodes.slice(0, i + 1).filter(item => item.isolated).length - 1;
          const col = isolatedIndex % cols;
          const row = Math.floor(isolatedIndex / cols);
          x = 22 + col * ((width - 44) / Math.max(1, cols - 1));
          y = height - 28 - row * 20;
        } else {
          const sectorLabel = graph.sectorLabels.get(raw.community);
          const anchor = sectorLabel ? graph.sectorAnchors.get(sectorLabel) : null;
          const localAngle = ((seed % 360) / 180) * Math.PI;
          const localRadius = 18 + (seed % 7) * 9;
          x = (anchor?.x ?? cx) + Math.cos(localAngle) * localRadius;
          y = (anchor?.y ?? cy) + Math.sin(localAngle) * localRadius;
        }
  
        node = {
          ...raw,
          x, y,
          vx: 0,
          vy: 0,
          pinned: false,
        };
        graph.cachedPositions.set(raw.id, node);
      } else {
        Object.assign(node, raw);
      }
      node.neighbors = adjacency.get(raw.id) ?? new Set();
      const sectorLabel = graph.sectorLabels.get(raw.community);
      node.sectorLabel = sectorLabel ?? null;
      node.sectorAnchor = sectorLabel ? (graph.sectorAnchors.get(sectorLabel) ?? null) : null;
      nodeMap.set(node.id, node);
      return node;
    });
  
    graph.edges = rawEdges
      .map(e => ({
        ...e,
        source: nodeMap.get(e.sourceId),
        target: nodeMap.get(e.targetId),
      }))
      .filter(e => e.source && e.target);
  
    graph.layoutAffinities = layoutAffinities
      .map(link => ({
        ...link,
        source: nodeMap.get(link.sourceId),
        target: nodeMap.get(link.targetId),
      }))
      .filter(link => link.source && link.target);
  
    graph.alpha = 1.0;
    renderCognitionInspector();
  }
  
  function stepGraphPhysics(width, height) {
    const { nodes, edges } = graph;
    const n = nodes.length;
    if (!n) return;
    const cx = width / 2, cy = height / 2;
    const alpha = graph.alpha;
  
    const communityCenters = new Map();
    for (const node of nodes) {
      if (!node.community || node.community === 'isolated') continue;
      const state = communityCenters.get(node.community) ?? { x: 0, y: 0, n: 0 };
      state.x += node.x;
      state.y += node.y;
      state.n += 1;
      communityCenters.set(node.community, state);
    }
    for (const state of communityCenters.values()) {
      state.x /= Math.max(1, state.n);
      state.y /= Math.max(1, state.n);
    }
  
    // Relationship-aware repulsion/attraction.
    for (let i = 0; i < n; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < n; j++) {
        const b = nodes[j];
        const dx = b.x - a.x, dy = b.y - a.y;
        const distSq = dx * dx + dy * dy + 144;
        if (distSq > 490000) continue;
        const dist = Math.sqrt(distSq);
  
        const directlyRelated = a.neighbors?.has(b.id) || b.neighbors?.has(a.id);
        let shared = 0;
        if (!directlyRelated && a.neighbors?.size && b.neighbors?.size) {
          const smaller = a.neighbors.size < b.neighbors.size ? a.neighbors : b.neighbors;
          const larger  = smaller === a.neighbors ? b.neighbors : a.neighbors;
          for (const id of smaller) {
            if (larger.has(id)) shared += 1;
            if (shared >= 3) break;
          }
        }
  
        const sameCommunity =
          a.community &&
          b.community &&
          a.community !== 'isolated' &&
          a.community === b.community;
  
        // Unrelated nodes repel more strongly, making visual sectors emerge.
        const repulsionScale = directlyRelated ? 0.25 : sameCommunity ? 0.62 : 1.28;
        const force = ((GRAPH_PHYSICS.repulsion * repulsionScale) / distSq) * alpha;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
        if (!b.pinned) { b.vx += fx; b.vy += fy; }
  
        // Two nodes sharing downstream/upstream partners get a weak secondary
        // attraction. It uses graph structure only; no semantic clustering.
        if (!directlyRelated && shared > 0) {
          const desired = 95 + 18 / shared;
          const pull = (dist - desired) * 0.0065 * Math.min(3, shared) * alpha;
          const pfx = (dx / dist) * pull, pfy = (dy / dist) * pull;
          if (!a.pinned) { a.vx += pfx; a.vy += pfy; }
          if (!b.pinned) { b.vx -= pfx; b.vy -= pfy; }
        }
      }
    }
  
    // Direct graph edges are the strongest attractive force.
    for (const edge of edges) {
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const dist = Math.hypot(dx, dy) || 1;
      const touchesReadout = edge.source.kind === 'readout' || edge.target.kind === 'readout';
      const relationStrength = (
        edge.kind === 'gating' ? 1.25 :
        edge.kind === 'predictive' ? 1.18 :
        edge.kind === 'inhibitory' ? 1.05 : 1.0
      ) * (touchesReadout ? 0.58 : 1.0);
      const desired = touchesReadout ? 112 :
        edge.kind === 'predictive' ? 76 :
        edge.kind === 'gating' ? 72 : 88;
      const disp = dist - desired;
      const force = disp * GRAPH_PHYSICS.springK * relationStrength * alpha;
      const fx = (dx / dist) * force, fy = (dy / dist) * force;
      if (!edge.source.pinned) { edge.source.vx += fx; edge.source.vy += fy; }
      if (!edge.target.pinned) { edge.target.vx -= fx; edge.target.vy -= fy; }
    }
  
    // Observer-only affinity links affect spatial organisation without being
    // rendered as organism-owned edges. This lets related motor primitives form
    // stable local regions without inventing CognitiveGraph connections.
    for (const link of graph.layoutAffinities ?? []) {
      const dx = link.target.x - link.source.x;
      const dy = link.target.y - link.source.y;
      const dist = Math.hypot(dx, dy) || 1;
      const desired = link.basis === 'motor-similarity' ? 62 : 78;
      const strength = finiteNumber(link.strength, 1);
      const force = (dist - desired) * 0.012 * strength * alpha;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (!link.source.pinned) { link.source.vx += fx; link.source.vy += fy; }
      if (!link.target.pinned) { link.target.vx -= fx; link.target.vy -= fy; }
    }
  
    // Each stable sector has a persistent spatial anchor. Local graph relations
    // organise nodes inside the region; the anchor prevents sectors swapping
    // places every time topology changes.
    for (const node of nodes) {
      if (node.pinned || node.isolated) continue;
      const center = node.community ? communityCenters.get(node.community) : null;
      if (center) {
        const cohesion = 0.012 * alpha;
        node.vx += (center.x - node.x) * cohesion;
        node.vy += (center.y - node.y) * cohesion;
      }
      if (node.sectorAnchor) {
        const anchorPull = 0.024 * alpha;
        node.vx += (node.sectorAnchor.x - node.x) * anchorPull;
        node.vy += (node.sectorAnchor.y - node.y) * anchorPull;
      }
  
      // Very weak global gravity keeps the overall "brain" compact.
      node.vx += (cx - node.x) * (GRAPH_PHYSICS.centerGravity * 0.28) * alpha;
      node.vy += (cy - node.y) * (GRAPH_PHYSICS.centerGravity * 0.28) * alpha;
  
      const radial = Math.hypot(node.x - cx, node.y - cy);
      const maxRadius = Math.min(width, height) * 0.43;
      if (radial > maxRadius) {
        const excess = radial - maxRadius;
        node.vx += ((cx - node.x) / radial) * excess * 0.018 * alpha;
        node.vy += ((cy - node.y) / radial) * excess * 0.018 * alpha;
      }
  
      node.vx *= GRAPH_PHYSICS.damping;
      node.vy *= GRAPH_PHYSICS.damping;
      node.x += node.vx;
      node.y += node.vy;
    }
  
    graph.alpha = Math.max(GRAPH_PHYSICS.alphaMin, graph.alpha * GRAPH_PHYSICS.alphaDecay);
  }
  
  function cognitionEdgeColor(edge, focused = false) {
    const alpha = focused ? 0.96 : 0.48;
    if (edge.kind === 'inhibitory') return `rgba(255,127,131,${alpha})`;
    if (edge.kind === 'predictive') return `rgba(255,189,84,${alpha})`;
    if (edge.kind === 'gating') return `rgba(224,159,62,${alpha})`;
    if (edge.kind === 'invokes') return `rgba(255,143,216,${alpha})`;
    if (edge.kind === 'motor_component') return `rgba(143,227,255,${alpha})`;
    if (edge.kind === 'causal_effect') return `rgba(113,233,186,${alpha})`;
    return `rgba(80,217,255,${alpha})`;
  }
  
  function drawGraphFrame3D(canvas) {
    updateCognitionSummary();
    const ctx = canvas.getContext('2d');
    const { width, height } = canvas;
    const { nodes, edges, hoveredNode, fmriEnabled } = graph;
    ctx.clearRect(0, 0, width, height);
    if (!nodes.length) return;
  
    const scene = buildCognition3DScene(
      nodes,
      edges,
      graph.camera3d,
      width,
      height,
    );
    const sectorFocus = focusedSectorContext();
    graph.projected3d = sectorFocus
      ? new Map([...scene.byId.entries()].filter(([id]) => sectorFocus.visible.has(id)))
      : scene.byId;
  
    const now = performance.now();
    const focusId = hoveredNode?.id ?? graph.selectedNodeId;
    const activeTopology = currentRenderedTopology();
    const connectedIds = focusId
      ? graphSubgraphIds(activeTopology, focusId, graph.pathDepth)
      : null;
  
    // Global anatomy envelope: observer-side spatial reference only.
    for (const [index, ring] of (scene.brainHull ?? []).entries()) {
      if (!ring?.length) continue;
      ctx.beginPath();
      ring.forEach((point, i) => {
        if (i === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
      });
      ctx.strokeStyle = index === 0
        ? 'rgba(80,217,255,.10)'
        : 'rgba(167,119,255,.075)';
      ctx.lineWidth = index === 0 ? 1.1 : 0.8;
      ctx.setLineDash(index === 0 ? [8, 10] : [3, 12]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  
    // Functional regions become translucent volumes. The volume is an
    // observer-side projection of the same emergent sectors used in 2D.
    const sectorItems = [...scene.sectors.values()]
      .sort((a,b) => b.depth - a.depth);
    for (const sector of sectorItems) {
      if (sector.points.length < 2) continue;
      if (sectorFocus && sector.id !== sectorFocus.sectorId) continue;
      const sectorLabel = sector.stableLabel ?? graph.sectorLabels.get(sector.id) ?? 'S-???';
      const description = graph.sectorDescriptions.get(sector.id);
      const palette = [PAL.violet, PAL.cyan, PAL.amber, PAL.mint, '#4ecdc4', '#e09f3e'];
      const color = palette[hashStr(String(sector.id)) % palette.length];
  
      // True volumetric sector cue: three projected great circles around the
      // same 3D center. Their shape changes with camera orbit.
      for (const [index, ring] of sector.wireframes.entries()) {
        if (!ring?.length) continue;
        ctx.beginPath();
        ring.forEach((point, i) => {
          if (i === 0) ctx.moveTo(point.x, point.y);
          else ctx.lineTo(point.x, point.y);
        });
        ctx.strokeStyle = `${color}${index === 0 ? '2e' : index === 1 ? '22' : '18'}`;
        ctx.lineWidth = index === 0 ? 1.1 : 0.8;
        ctx.setLineDash(index === 0 ? [5, 7] : [2, 8]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
  
      const labelOffset = Math.max(20, sector.radius * sector.scale * 0.72);
  
      ctx.font = '600 10px -apple-system, sans-serif';
      ctx.fillStyle = `${color}d0`;
      ctx.textAlign = 'center';
      ctx.fillText(
        `${sectorLabel} · ${description?.interpretation ?? 'emergent sector'}`,
        sector.x,
        sector.y - labelOffset - 12,
      );
    }
  
    // Sparse long-range tract system. Internal connectivity remains implicit
    // until a node is focused, exactly like the 2D cartography.
    const visibleEdges = [];
    for (const edge of edges) {
      const a = scene.byId.get(edge.source.id);
      const b = scene.byId.get(edge.target.id);
      if (!a || !b) continue;
      const isConn = Boolean(
        focusId &&
        connectedIds?.has(edge.source.id) &&
        connectedIds?.has(edge.target.id)
      );
      const sameSector = (
        edge.source.community &&
        edge.source.community !== 'isolated' &&
        edge.source.community === edge.target.community
      );
      const bridgeKey = `${edge.source.id}|${edge.target.id}|${edge.kind}`;
      if (focusId) {
        if (!isConn) continue;
      } else if (sectorFocus) {
        const sourceLocal = sectorFocus.local.has(edge.source.id);
        const targetLocal = sectorFocus.local.has(edge.target.id);
        if (!(sourceLocal || targetLocal)) continue;
      } else if (sameSector || !graph.bridgeEdges.has(bridgeKey)) {
        continue;
      }
      visibleEdges.push({
        edge,
        a,
        b,
        depth: (a.depth + b.depth) / 2,
        focused: isConn,
      });
    }
    visibleEdges.sort((a,b) => b.depth - a.depth);
  
    for (const item of visibleEdges) {
      const { edge, a, b, focused } = item;
      ctx.strokeStyle = cognitionEdgeColor(edge, focused);
      ctx.globalAlpha = focused ? 0.95 : 0.58;
      ctx.lineWidth = focused ? 2.3 : 1.0;
      ctx.setLineDash(edge.kind === 'causal_effect' ? [6,4] : []);
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const lift = Math.max(10, Math.min(54, Math.hypot(dx, dy) * 0.12));
      const curveSign = hashStr(`${edge.source.id}|${edge.target.id}`) % 2 ? 1 : -1;
      const mx = (a.x + b.x) / 2 - dy * 0.10 * curveSign;
      const my = (a.y + b.y) / 2 + dx * 0.10 * curveSign - lift;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.quadraticCurveTo(mx, my, b.x, b.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }
  
    // Painter's algorithm: far nodes first, near nodes last.
    for (const projected of scene.projected) {
      const node = projected.node;
      if (sectorFocus && !sectorFocus.visible.has(node.id)) continue;
      const isHovered = hoveredNode?.id === node.id;
      const isSelected = graph.selectedNodeId === node.id;
      const isConn = connectedIds?.has(node.id);
      const dimmed = Boolean(focusId && !isConn);
      const breath = (fmriEnabled && node.activationLevel > 0)
        ? Math.sin(now * 0.003 + hashStr(node.id)) * node.activationLevel * 1.6
        : 0;
      const radius = projected.radius * (isHovered || isSelected ? 1.28 : 1) + breath;
  
      ctx.beginPath();
      ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? '#ffffff' : node.color;
      const depthFog = Math.max(0.32, Math.min(1, 1 - projected.depth / 1500));
      ctx.globalAlpha = dimmed
        ? 0.08
        : Math.max(0.22, Math.min(1, projected.scale * 0.78 * depthFog));
      ctx.fill();
      ctx.globalAlpha = 1;
  
      if (isSelected) {
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(projected.x, projected.y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
  
      if (fmriEnabled && node.activationLevel > 0 && !isSelected) {
        ctx.strokeStyle = node.color;
        ctx.globalAlpha = 0.25 + Math.min(0.55, node.activationLevel * 0.55);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(projected.x, projected.y, radius + 2.5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
  
      if (node.replayActive || node.prospectiveSelected) {
        ctx.strokeStyle = node.replayActive ? PAL.mint : PAL.amber;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(projected.x, projected.y, radius + 7, 0, Math.PI * 2);
        ctx.stroke();
      }
  
      if (isHovered || isSelected || isConn) {
        const label = node.observerLabel ?? compactSelfLabel(node.label ?? node.id, 12, 6);
        ctx.font = isSelected ? '600 10px -apple-system, sans-serif' : '9px -apple-system, sans-serif';
        ctx.fillStyle = isSelected ? '#fff' : 'rgba(200,216,228,.82)';
        ctx.textAlign = 'center';
        ctx.fillText(label, projected.x, projected.y + radius + 12);
      }
    }
  
    ctx.font = '9px -apple-system, sans-serif';
    ctx.fillStyle = 'rgba(98,120,136,.72)';
    ctx.textAlign = 'left';
    ctx.fillText(
      sectorFocus
        ? '3D sector focus · internal anatomy + real external bridges'
        : '3D anatomy · orbit to reveal depth · select a region node for local pathways',
      16,
      height - 16,
    );
  }
  
  function drawGraphFrame(canvas) {
    if (graph.dimension === '3d') {
      drawGraphFrame3D(canvas);
      return;
    }
    updateCognitionSummary();
    const ctx = canvas.getContext('2d');
    const { width, height } = canvas;
    const { nodes, edges, scale, panX, panY, hoveredNode, fmriEnabled } = graph;
    ctx.clearRect(0, 0, width, height);
    if (!nodes.length) return;
  
    ctx.save();
    ctx.translate(panX, panY);
    ctx.scale(scale, scale);
  
    const now = performance.now();
    const sectorFocus = focusedSectorContext();
  
    const isolatedCount = nodes.filter(node => node.isolated).length;
    if (isolatedCount && graph.viewMode === 'full') {
      ctx.font = '9px -apple-system, sans-serif';
      ctx.fillStyle = 'rgba(98,120,136,.72)';
      ctx.textAlign = 'left';
      ctx.fillText(`UNINTEGRATED · ${isolatedCount}`, 18, height / scale - 14);
    }
  
    // Draw relationship sectors behind the graph. Sectors are computed from the
    // current layout of topology-derived local communities; they are not organism
    // concepts and therefore carry no semantic labels.
    const communityStats = new Map();
    for (const node of nodes) {
      if (!node.community || node.community === 'isolated') continue;
      const s = communityStats.get(node.community) ?? { x: 0, y: 0, n: 0, nodes: [] };
      s.x += node.x; s.y += node.y; s.n += 1; s.nodes.push(node);
      communityStats.set(node.community, s);
    }
    for (const [communityId, s] of communityStats.entries()) {
      if (s.n < 3) continue;
      if (sectorFocus && communityId !== sectorFocus.sectorId) continue;
      s.x /= s.n; s.y /= s.n;
      let radius = 0;
      for (const node of s.nodes) {
        radius = Math.max(radius, Math.hypot(node.x - s.x, node.y - s.y) + node.radius);
      }
      radius = Math.max(38, Math.min(180, radius + 18));
      const palette = [PAL.violet, PAL.cyan, PAL.amber, PAL.mint, '#4ecdc4', '#e09f3e'];
      const color = palette[hashStr(String(communityId)) % palette.length];
      ctx.beginPath();
      ctx.arc(s.x, s.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `${color}0b`;
      ctx.strokeStyle = `${color}20`;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 7]);
      ctx.fill();
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.setLineDash([]);
  
      // Neutral observer label. It identifies a structural sector without
      // pretending that the organism has assigned it a semantic category.
      const sectorLabel = graph.sectorLabels.get(communityId) ?? 'S-???';
      const sectorDescription = graph.sectorDescriptions.get(communityId);
      ctx.font = '600 10px -apple-system, sans-serif';
      ctx.fillStyle = `${color}cc`;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(
        `${sectorLabel} · ${sectorDescription?.interpretation ?? 'emergent sector'}`,
        s.x + radius * 0.50,
        s.y - radius * 0.62,
      );
      ctx.font = '8px -apple-system, sans-serif';
      ctx.fillStyle = 'rgba(175,199,220,.48)';
      ctx.fillText(
        `${s.n} nodes · observer interpretation`,
        s.x + radius * 0.50,
        s.y - radius * 0.62 + 12,
      );
    }
  
    const focusId = hoveredNode?.id ?? graph.selectedNodeId;
    const activeTopology = currentRenderedTopology();
    const connectedIds = focusId ? graphSubgraphIds(activeTopology, focusId, graph.pathDepth) : null;
  
    // Edges: global view shows only a sparse inter-sector backbone.
    // Internal relations are encoded spatially and revealed on inspection.
    for (const edge of edges) {
      const isConn = Boolean(focusId && connectedIds?.has(edge.source.id) && connectedIds?.has(edge.target.id));
      const sameSector = (
        edge.source.community &&
        edge.source.community !== 'isolated' &&
        edge.source.community === edge.target.community
      );
      const bridgeKey = `${edge.source.id}|${edge.target.id}|${edge.kind}`;
      if (focusId) {
        if (!isConn) continue;
      } else if (sectorFocus) {
        const sourceLocal = sectorFocus.local.has(edge.source.id);
        const targetLocal = sectorFocus.local.has(edge.target.id);
        if (!(sourceLocal || targetLocal)) continue;
      } else if (sameSector || !graph.bridgeEdges.has(bridgeKey)) {
        continue;
      }
      const dimmed = false;
      let color;
      if (edge.kind === 'inhibitory')  color = `rgba(255,127,131,${isConn ? .95 : dimmed ? .04 : .35})`;
      else if (edge.kind === 'predictive') color = `rgba(255,189,84,${isConn ? .95 : dimmed ? .04 : .40})`;
      else if (edge.kind === 'gating') color = `rgba(224,159,62,${isConn ? .95 : dimmed ? .04 : .38})`;
      else if (edge.kind === 'invokes') color = `rgba(255,143,216,${isConn ? .98 : dimmed ? .05 : .68})`;
      else if (edge.kind === 'motor_component') color = `rgba(143,227,255,${isConn ? .98 : dimmed ? .05 : .58})`;
      else if (edge.kind === 'causal_effect') color = `rgba(113,233,186,${isConn ? .98 : dimmed ? .05 : .62})`;
      else                             color = `rgba(80,217,255,${isConn ? .95 : dimmed ? .04 : .28})`;
      ctx.beginPath();
      ctx.moveTo(edge.source.x, edge.source.y);
      ctx.lineTo(edge.target.x, edge.target.y);
      const supportScale = Math.min(1, Math.log1p(Math.max(0, edge.support ?? 0)) / 7);
      const liveTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
      const idleTicks = Math.max(0, liveTick - finiteNumber(edge.lastUseTick, liveTick));
      const recency = Math.exp(-idleTicks / 512);
      ctx.strokeStyle = color;
      ctx.globalAlpha = dimmed ? 0.18 : Math.max(0.18, 0.35 + recency * 0.65);
      ctx.lineWidth   = isConn ? 2.8 : 0.8 + supportScale * 2.4;
      ctx.setLineDash(edge.kind === 'inhibitory' ? [4, 4] : edge.kind === 'gating' ? [2, 3] : edge.kind === 'causal_effect' ? [6, 3] : []);
      ctx.stroke();
      ctx.setLineDash([]);
      // Arrowhead
      if (!dimmed) {
        const dx = edge.target.x - edge.source.x, dy = edge.target.y - edge.source.y;
        const dist = Math.hypot(dx, dy);
        if (dist > 14) {
          const angle = Math.atan2(dy, dx);
          const tr = (edge.target.radius ?? 6) + 3;
          const tx = edge.target.x - Math.cos(angle) * tr;
          const ty = edge.target.y - Math.sin(angle) * tr;
          const al = isConn ? 6 : 4;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.moveTo(tx, ty);
          ctx.lineTo(tx - al * Math.cos(angle - Math.PI / 6), ty - al * Math.sin(angle - Math.PI / 6));
          ctx.lineTo(tx - al * Math.cos(angle + Math.PI / 6), ty - al * Math.sin(angle + Math.PI / 6));
          ctx.closePath();
          ctx.fill();
        }
      }
    }
  
    // Nodes
    for (const node of nodes) {
      if (sectorFocus && !sectorFocus.visible.has(node.id)) continue;
      const isHovered = hoveredNode && hoveredNode.id === node.id;
      const isSelected = graph.selectedNodeId === node.id;
      const isConn = connectedIds && connectedIds.has(node.id);
      const dimmed = focusId && !isConn;
      const breath = (fmriEnabled && node.activationLevel > 0)
        ? Math.sin(now * 0.003 + hashStr(node.id)) * (node.activationLevel * 2.0)
        : 0;
      const r = ((isHovered || isSelected) ? node.radius * 1.35 : node.radius) + breath;
  
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? '#fff' : node.color;
      ctx.shadowColor = node.color;
      ctx.shadowBlur  = isSelected ? 20 : isConn ? 14 : (fmriEnabled && node.activationLevel > 0 ? 4 + node.activationLevel * 12 : 3);
      const graphTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
      const nodeIdleTicks = node.lastUseTick > 0 ? Math.max(0, graphTick - node.lastUseTick) : 2048;
      const nodeRecency = Math.exp(-nodeIdleTicks / 768);
      // Size is structural importance, glow is current activity, opacity is
      // recency of structural use. These dimensions deliberately stay separate.
      ctx.globalAlpha = dimmed
        ? 0.12
        : Math.min(1, 0.28 + nodeRecency * 0.52 + (isSelected || isHovered ? 0.2 : 0));
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.shadowBlur  = 0;
  
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
  
      // Error ring
      if (node.errorCls && ['medium', 'high', 'extreme'].includes(node.errorCls)) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 3.5, 0, Math.PI * 2);
        ctx.strokeStyle = PAL.coral;
        ctx.lineWidth = 1.4;
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
  
      // Readout label
      if (node.kind === 'readout' && node.readoutVal) {
        ctx.font = '10px monospace';
        ctx.fillStyle = PAL.mint;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.readoutVal, node.x, node.y);
      }
  
      // Node names are detail, not the global map. Sector labels carry the
      // overview; individual labels appear on focus, activity, or deep zoom.
      if (!dimmed && (
        isHovered ||
        isSelected ||
        isConn ||
        node.replayActive ||
        node.prospectiveSelected ||
        (scale >= 1.65 && node.visualValue > 0.55)
      )) {
        ctx.font = '10px -apple-system, sans-serif';
        ctx.fillStyle = isConn ? '#fff' : 'rgba(175,199,220,.7)';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'alphabetic';
        const observerLabel = node.observerLabel;
        const primary = observerLabel ?? node.label;
        const lbl = primary.length > 22 ? primary.slice(0, 18) + '…' : primary;
        ctx.fillText(lbl, node.x, node.y + r + 10);
        if ((isHovered || isSelected) && observerLabel) {
          ctx.font = '8px -apple-system, sans-serif';
          ctx.fillStyle = 'rgba(175,199,220,.55)';
          ctx.fillText(compactSelfLabel(node.label), node.x, node.y + r + 20);
        }
      }
    }
  
    ctx.restore();
  }
  
  function cognitionAnimLoop() {
    if (getActiveTab() !== 'cognition') {
      graph.isRunning = false;
      rafId = null;
      return;
    }
    const canvas = document.getElementById('mind-cognition-canvas');
    if (!canvas) { graph.isRunning = false; rafId = null; return; }
  
    // Resize canvas to wrapper
    const wrap = canvas.parentElement;
    if (wrap) {
      const rect = wrap.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        if (canvas.width !== Math.floor(rect.width) || canvas.height !== Math.floor(rect.height)) {
          canvas.width  = Math.floor(rect.width);
          canvas.height = Math.floor(rect.height);
          graph.alpha  = Math.max(graph.alpha, 0.5);
        }
      }
    }
  
    stepGraphPhysics(canvas.width, canvas.height);
    drawGraphFrame(canvas);
  
    const keepRunning = graph.alpha > GRAPH_PHYSICS.alphaMin || graph.isRunning;
    if (keepRunning) {
      rafId = requestAnimationFrame(cognitionAnimLoop);
    } else {
      rafId = null;
    }
  }
  
  function startCognitionGraph() {
    const canvas = document.getElementById('mind-cognition-canvas');
    if (!canvas) return;
    const wrap = canvas.parentElement;
    if (wrap) {
      const rect = wrap.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        canvas.width = Math.floor(rect.width);
        canvas.height = Math.floor(rect.height);
      }
    }
    if (!canvas.dataset.listenersInstalled) {
      installGraphListeners(canvas);
      canvas.dataset.listenersInstalled = 'true';
    }
    initGraphPhysics(canvas.width || 900, canvas.height || 600);
    graph.isRunning = true;
    if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
  
    // Button bindings
    const fmriBtn  = document.getElementById('mind-fmri-btn');
    const zoomIn   = document.getElementById('mind-zoom-in');
    const zoomOut  = document.getElementById('mind-zoom-out');
    const resetBtn = document.getElementById('mind-graph-reset');
  
    if (fmriBtn && !fmriBtn.dataset.bound) {
      fmriBtn.dataset.bound = 'true';
      fmriBtn.addEventListener('click', () => {
        graph.fmriEnabled = !graph.fmriEnabled;
        fmriBtn.classList.toggle('active', graph.fmriEnabled);
      });
    }
    if (zoomIn && !zoomIn.dataset.bound) {
      zoomIn.dataset.bound = 'true';
      zoomIn.addEventListener('click', () => {
        if (graph.dimension === '3d') {
          graph.camera3d = zoomCamera(graph.camera3d, -1);
        } else {
          const cx = canvas.width / 2, cy = canvas.height / 2;
          const ns = Math.min(5, graph.scale * 1.25);
          graph.panX = cx - (cx - graph.panX) * (ns / graph.scale);
          graph.panY = cy - (cy - graph.panY) * (ns / graph.scale);
          graph.scale = ns;
        }
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      });
    }
    if (zoomOut && !zoomOut.dataset.bound) {
      zoomOut.dataset.bound = 'true';
      zoomOut.addEventListener('click', () => {
        if (graph.dimension === '3d') {
          graph.camera3d = zoomCamera(graph.camera3d, 1);
        } else {
          const cx = canvas.width / 2, cy = canvas.height / 2;
          const ns = Math.max(0.2, graph.scale * 0.8);
          graph.panX = cx - (cx - graph.panX) * (ns / graph.scale);
          graph.panY = cy - (cy - graph.panY) * (ns / graph.scale);
          graph.scale = ns;
        }
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      });
    }
    if (resetBtn && !resetBtn.dataset.bound) {
      resetBtn.dataset.bound = 'true';
      resetBtn.addEventListener('click', () => {
        graph.scale = 1; graph.panX = 0; graph.panY = 0;
        graph.camera3d = { yaw: -0.55, pitch: 0.34, distance: 900 };
        graph.focusedSectorId = null;
        graph.selectedNodeId = null;
        graph.cachedPositions.clear();
        graph.alpha = 1.0;
        renderCognitionInspector();
      });
    }
  }
  
  function installGraphListeners(canvas) {
    let isPanning = false, isDragging = false, draggedNode = null;
    let pressedNode = null;
    let panStartX = 0, panStartY = 0, dragDist = 0;
    let orbitLastX = 0, orbitLastY = 0;
  
    function canvasCoords(event) {
      const rect = canvas.getBoundingClientRect();
      const sx = rect.width > 0 ? canvas.width / rect.width : 1;
      const sy = rect.height > 0 ? canvas.height / rect.height : 1;
      return { x: (event.clientX - rect.left) * sx, y: (event.clientY - rect.top) * sy };
    }
    function findNode(mx, my) {
      if (graph.dimension === '3d') {
        const projected = [...(graph.projected3d?.values?.() ?? [])];
        projected.sort((a,b) => a.depth - b.depth);
        for (let i = projected.length - 1; i >= 0; i--) {
          const item = projected[i];
          if (Math.hypot(item.x - mx, item.y - my) <= item.radius + 7) return item.node;
        }
        return null;
      }
      const wx = (mx - graph.panX) / graph.scale;
      const wy = (my - graph.panY) / graph.scale;
      for (let i = graph.nodes.length - 1; i >= 0; i--) {
        const n = graph.nodes[i];
        if (Math.hypot(n.x - wx, n.y - wy) <= n.radius + 6) return n;
      }
      return null;
    }
  
    canvas.addEventListener('wheel', ev => {
      ev.preventDefault();
      if (graph.dimension === '3d') {
        graph.camera3d = zoomCamera(graph.camera3d, ev.deltaY);
      } else {
        const factor = ev.deltaY < 0 ? 1.12 : 0.89;
        const ns = Math.min(5, Math.max(0.2, graph.scale * factor));
        const { x, y } = canvasCoords(ev);
        graph.panX = x - (x - graph.panX) * (ns / graph.scale);
        graph.panY = y - (y - graph.panY) * (ns / graph.scale);
        graph.scale = ns;
      }
      graph.alpha = Math.max(graph.alpha, 0.1);
      if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
    }, { passive: false });
  
    canvas.addEventListener('mousedown', ev => {
      if (ev.button !== 0) return;
      const { x, y } = canvasCoords(ev);
      const node = findNode(x, y);
      dragDist = 0;
      pressedNode = node;
      if (graph.dimension === '3d') {
        if (!node) {
          isPanning = true;
          orbitLastX = x;
          orbitLastY = y;
          canvas.style.cursor = 'grabbing';
        }
        return;
      }
      if (node) { isDragging = true; draggedNode = node; node.pinned = true; node.vx = node.vy = 0; }
      else { isPanning = true; panStartX = x - graph.panX; panStartY = y - graph.panY; canvas.style.cursor = 'grabbing'; }
    });
  
    // Window listeners outlive the canvas, so keep explicit references and
    // remove them during unmount/remount. This prevents listener accumulation.
    if (windowMouseMove) window.removeEventListener('mousemove', windowMouseMove);
    if (windowMouseUp) window.removeEventListener('mouseup', windowMouseUp);
  
    windowMouseMove = ev => {
      const { x, y } = canvasCoords(ev);
      if (graph.dimension === '3d') {
        if (isPanning) {
          const dx = x - orbitLastX;
          const dy = y - orbitLastY;
          dragDist += Math.abs(dx) + Math.abs(dy);
          graph.camera3d = orbitCamera(graph.camera3d, dx, dy);
          orbitLastX = x;
          orbitLastY = y;
          graph.alpha = Math.max(graph.alpha, 0.08);
          if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
        } else {
          graph.hoveredNode = findNode(x, y);
          canvas.style.cursor = graph.hoveredNode ? 'pointer' : 'grab';
          if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
        }
        return;
      }
      if (isDragging && draggedNode) {
        dragDist += Math.abs(ev.movementX) + Math.abs(ev.movementY);
        draggedNode.x = (x - graph.panX) / graph.scale;
        draggedNode.y = (y - graph.panY) / graph.scale;
        draggedNode.vx = draggedNode.vy = 0;
        graph.alpha = Math.max(graph.alpha, 0.4);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      } else if (isPanning) {
        graph.panX = x - panStartX;
        graph.panY = y - panStartY;
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      } else {
        graph.hoveredNode = findNode(x, y);
        canvas.style.cursor = graph.hoveredNode ? 'pointer' : 'grab';
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      }
    };
  
    windowMouseUp = () => {
      const clicked = pressedNode && dragDist < 5 ? pressedNode : null;
      if (draggedNode) { draggedNode.pinned = false; draggedNode = null; }
      if (clicked) {
        graph.selectedNodeId = graph.selectedNodeId === clicked.id ? null : clicked.id;
        const graphCanvas = document.getElementById('mind-cognition-canvas');
        if (graphCanvas) initGraphPhysics(graphCanvas.width || 900, graphCanvas.height || 600);
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.08);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      } else if (!pressedNode && dragDist < 5) {
        graph.selectedNodeId = null;
        renderCognitionInspector();
      }
      pressedNode = null;
      isDragging = false; isPanning = false;
      canvas.style.cursor = 'grab';
    };
  
    window.addEventListener('mousemove', windowMouseMove);
    window.addEventListener('mouseup', windowMouseUp);
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Regime Compass (adapted from observatory/render/regime-compass.js)
  // ─────────────────────────────────────────────────────────────────────────────
  
  // ─────────────────────────────────────────────────────────────────────────────
  // Snapshot ingestion (simplified projection from instance stream)
  // ─────────────────────────────────────────────────────────────────────────────
  
  function focusedSectorContext() {
    const sectorId = graph.focusedSectorId;
    if (!sectorId) return null;
    const local = new Set(
      graph.nodes
        .filter(node => node.community === sectorId)
        .map(node => node.id)
    );
    if (!local.size) return null;
  
    const bridges = new Set();
    for (const edge of graph.edges) {
      const sourceLocal = local.has(edge.source.id);
      const targetLocal = local.has(edge.target.id);
      if (sourceLocal === targetLocal) continue;
      bridges.add(sourceLocal ? edge.target.id : edge.source.id);
    }
    return {
      sectorId,
      local,
      bridges,
      visible: new Set([...local, ...bridges]),
    };
  }
  
  function currentRenderedTopology() {
    return {
      nodes: graph.nodes.map(node => ({ id: node.id, kind: node.kind })),
      edges: graph.edges.map(edge => ({
        sourceId: edge.source.id,
        targetId: edge.target.id,
        kind: edge.kind,
        support: edge.support,
        weight: edge.weight,
        plasticity: edge.plasticity,
        ageTicks: edge.ageTicks,
        stableTicks: edge.stableTicks,
        lastUseTick: edge.lastUseTick,
        correlation: edge.correlation,
        samples: edge.samples,
        learnedLayer: edge.learnedLayer,
      })),
    };
  }
  
  function cognitionNodeFacts(nodeId) {
    const topology = currentRenderedTopology();
    const edges = topology.edges ?? [];
    const inbound = edges.filter(edge => edge.targetId === nodeId);
    const outbound = edges.filter(edge => edge.sourceId === nodeId);
    const localIds = graphSubgraphIds(topology, nodeId, graph.pathDepth) ?? new Set([nodeId]);
    const reachesMotor = [...localIds].some(id =>
      String(id).startsWith('readout_motor:') ||
      String(id).startsWith('readout_primitive:') ||
      String(id).startsWith('motor_primitive:') ||
      String(id).startsWith('actuator.')
    );
    return { inbound, outbound, localIds, reachesMotor };
  }
  
  function renderCognitionInspector() {
    const panel = document.getElementById('mind-cognition-inspector-body');
    if (!panel) return;
    panel.innerHTML = '';
  
    const selected = graph.nodes.find(node => node.id === graph.selectedNodeId) ?? null;
    if (selected) {
      const title = el('div', '');
      title.style.cssText = 'font-size:12px;font-weight:650;color:var(--text);overflow-wrap:anywhere;margin-bottom:3px;';
      title.textContent = selected.label ?? selected.id;
      const subtitle = el('div', '');
      subtitle.style.cssText = 'font-size:9px;color:var(--muted);margin-bottom:10px;';
      subtitle.textContent = `${selected.kind} · selected node`;
      panel.append(title, subtitle);
  
      const facts = cognitionNodeFacts(selected.id);
      const observerContext = observerContextForNode(
        graph.replaySnapshot?.topology ?? snap.topology,
        graph.replaySnapshot?.observerSemantics ?? snap.observerSemantics,
        selected.id,
        2,
      );
      const motorSemantic = selected.learnedLayer === 'motor' && selected.observerLabel
        ? {
            summary: selected.observerLabel,
            kind: selected.kind === 'actuator' ? 'exact-source' : 'composition',
            distance: 0,
          }
        : null;
      const displayedSemantic = motorSemantic ?? observerContext;
      inspectorMetric(panel, 'Self label', selected.id, PAL.violet);
      inspectorMetric(
        panel,
        displayedSemantic.kind === 'exact-source'
          ? 'Observer truth'
          : displayedSemantic.kind === 'composition'
            ? 'Observer composition'
            : 'Observer context',
        displayedSemantic.summary ?? 'unresolved',
        displayedSemantic.summary ? PAL.cyan : PAL.muted,
      );
      inspectorMetric(
        panel,
        'Semantic relation',
        displayedSemantic.kind === 'exact-source'
          ? 'exact source mapping'
          : displayedSemantic.kind === 'composition'
            ? 'physical composition only'
            : displayedSemantic.kind === 'sensory-context'
              ? `linked within ${displayedSemantic.distance} hops`
              : 'unresolved',
      );
      inspectorMetric(panel, 'Kind', selected.kind);
      if (selected.kind === 'motor_primitive') {
        inspectorMetric(panel, 'Cognitive reuse', selected.cognitivePrimitive ? 'eligible' : 'not yet');
        inspectorMetric(panel, 'Samples', selected.samples);
        inspectorMetric(panel, 'Controllability', selected.controllability.toFixed(4), PAL.mint);
        inspectorMetric(panel, 'Directional consistency', pct(selected.directionalConsistency));
        inspectorMetric(panel, 'Effect variance', selected.effectVariance.toFixed(4));
        inspectorMetric(panel, 'Actuators', selected.actuatorIds.length);
        inspectorMetric(panel, 'Replay', selected.replayActive ? 'active now' : 'inactive', selected.replayActive ? PAL.mint : PAL.muted);
      }
      if (selected.kind === 'actuator') {
        inspectorMetric(panel, 'Observer effector', selected.observerLabel ?? 'unresolved', PAL.cyan);
        inspectorMetric(panel, 'Motor repertoire', selected.activeRepertoire ? 'active' : 'not promoted');
        inspectorMetric(panel, 'Effect strength', selected.effectStrength.toFixed(3), PAL.mint);
        inspectorMetric(panel, 'Effect relations', selected.causalRelationCount);
        inspectorMetric(panel, 'Activations observed', selected.activations);
      }
      inspectorMetric(panel, 'Degree', selected.neighbors?.size ?? 0);
      inspectorMetric(panel, 'Activity', pct(selected.activationLevel ?? 0), PAL.cyan);
      inspectorMetric(panel, 'Structural importance', pct(selected.structuralImportance ?? selected.visualValue ?? 0));
      inspectorMetric(panel, 'Component', selected.isolated ? 'unintegrated' : `#${(selected.componentRank ?? 0) + 1} · ${selected.componentSize ?? 1} nodes`);
      inspectorMetric(panel, 'Sector', selected.community && selected.community !== 'isolated'
        ? (graph.sectorLabels.get(selected.community) ?? 'unresolved')
        : 'none');
      inspectorMetric(panel, 'Inbound / outbound', `${facts.inbound.length} / ${facts.outbound.length}`);
      inspectorMetric(panel, `Within ${graph.pathDepth} hops`, facts.localIds.size);
      inspectorMetric(
        panel,
        'Motor path nearby',
        facts.reachesMotor ? 'yes' : 'no',
        facts.reachesMotor ? PAL.mint : PAL.muted,
      );
      if (selected.errorCls) inspectorMetric(panel, 'Prediction error', selected.errorCls, PAL.coral);
      if (selected.readoutVal != null) inspectorMetric(panel, 'Readout', selected.readoutVal, PAL.mint);
  
      const relTitle = el('div', '');
      relTitle.style.cssText = 'margin:13px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      relTitle.textContent = 'Direct relations';
      panel.appendChild(relTitle);
  
      const direct = [
        ...facts.inbound.map(edge => ({ dir: '←', other: edge.sourceId, edge })),
        ...facts.outbound.map(edge => ({ dir: '→', other: edge.targetId, edge })),
      ]
        .sort((a,b) => finiteNumber(b.edge.support,0) - finiteNumber(a.edge.support,0))
        .slice(0, 12);
  
      if (!direct.length) {
        const empty = el('div', '');
        empty.style.cssText = 'font-size:9px;color:var(--muted);';
        empty.textContent = 'No direct graph relations.';
        panel.appendChild(empty);
      } else {
        for (const relation of direct) {
          const row = el('button', '');
          row.type = 'button';
          row.style.cssText = `
            width:100%;display:block;text-align:left;padding:5px 6px;margin:3px 0;
            border:1px solid rgba(98,120,136,.16);border-radius:5px;
            background:rgba(80,217,255,.025);color:var(--muted);
            font-size:8px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
          `;
          row.textContent = `${relation.dir} ${shortId(relation.other, 9, 5)} · ${relation.edge.kind ?? 'edge'} · sup ${finiteNumber(relation.edge.support,0)}`;
          row.title =
            `${relation.other}\nkind ${relation.edge.kind ?? 'edge'} · weight ${finiteNumber(relation.edge.weight,0).toFixed(3)} · plasticity ${finiteNumber(relation.edge.plasticity,0).toFixed(3)}\nsupport ${finiteNumber(relation.edge.support,0)} · age ${finiteNumber(relation.edge.ageTicks,0)} · stable ${finiteNumber(relation.edge.stableTicks,0)} · last use t${finiteNumber(relation.edge.lastUseTick,0)}`;
          row.addEventListener('click', () => selectCognitiveNode(relation.other));
          panel.appendChild(row);
        }
      }
  
      const clear = el('button', 'mind-ctrl-btn');
      clear.type = 'button';
      clear.style.cssText = 'margin-top:12px;width:100%;';
      clear.textContent = 'Clear selection';
      clear.addEventListener('click', () => {
        graph.selectedNodeId = null;
        const canvas = document.getElementById('mind-cognition-canvas');
        if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.08);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      });
      panel.appendChild(clear);
      return;
    }
  
    const sectorFocus = focusedSectorContext();
    if (sectorFocus) {
      const label = graph.sectorLabels.get(sectorFocus.sectorId) ?? 'S-???';
      const description = graph.sectorDescriptions.get(sectorFocus.sectorId);
      const members = graph.nodes.filter(node => sectorFocus.local.has(node.id));
      const bridgeEdges = graph.edges.filter(edge => {
        const sourceLocal = sectorFocus.local.has(edge.source.id);
        const targetLocal = sectorFocus.local.has(edge.target.id);
        return sourceLocal !== targetLocal;
      });
      const kinds = {};
      for (const node of members) kinds[node.kind] = (kinds[node.kind] ?? 0) + 1;
      const activity = members.length
        ? members.reduce((sum, node) => sum + finiteNumber(node.activationLevel, 0), 0) / members.length
        : 0;
  
      const title = el('div', '');
      title.style.cssText = 'font-size:12px;font-weight:650;color:var(--text);margin-bottom:3px;';
      title.textContent = `${label} · ${description?.interpretation ?? 'emergent sector'}`;
      const subtitle = el('div', '');
      subtitle.style.cssText = 'font-size:9px;line-height:1.45;color:var(--muted);margin-bottom:10px;';
      subtitle.textContent = 'Observer-side sector focus. Membership is derived from graph relations and is not fed back to Symbiont.';
      panel.append(title, subtitle);
  
      inspectorMetric(panel, 'Nodes', members.length);
      inspectorMetric(panel, 'Mean activity', pct(activity), PAL.cyan);
      inspectorMetric(panel, 'External bridge endpoints', sectorFocus.bridges.size);
      inspectorMetric(panel, 'Cross-sector relations', bridgeEdges.length);
      inspectorMetric(
        panel,
        'Composition',
        Object.entries(kinds)
          .sort((a,b) => b[1] - a[1])
          .map(([kind, count]) => `${count} ${kind}`)
          .join(' · ') || '—',
      );
  
      const bridgeTitle = el('div', '');
      bridgeTitle.style.cssText = 'margin:13px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      bridgeTitle.textContent = 'Bridges to other sectors';
      panel.appendChild(bridgeTitle);
  
      const bridgeGroups = new Map();
      for (const edge of bridgeEdges) {
        const outside = sectorFocus.local.has(edge.source.id) ? edge.target : edge.source;
        const outsideSector = outside.community && outside.community !== 'isolated'
          ? (graph.sectorLabels.get(outside.community) ?? 'unresolved')
          : 'unintegrated';
        const item = bridgeGroups.get(outsideSector) ?? { count: 0, nodes: new Set() };
        item.count += 1;
        item.nodes.add(outside.id);
        bridgeGroups.set(outsideSector, item);
      }
  
      if (!bridgeGroups.size) {
        const empty = el('div', '');
        empty.style.cssText = 'font-size:9px;color:var(--muted);';
        empty.textContent = 'No external bridges in the current view.';
        panel.appendChild(empty);
      } else {
        for (const [target, item] of [...bridgeGroups.entries()].sort((a,b) => b[1].count - a[1].count)) {
          const row = el('div', '');
          row.style.cssText = 'padding:5px 0;border-top:1px solid rgba(98,120,136,.12);font-size:8px;color:var(--muted);';
          row.innerHTML = `<strong style="color:var(--text)">${target}</strong> · ${item.count} relations · ${item.nodes.size} endpoints`;
          panel.appendChild(row);
        }
      }
  
      const back = el('button', 'mind-ctrl-btn');
      back.type = 'button';
      back.style.cssText = 'margin-top:12px;width:100%;';
      back.textContent = 'Back to all sectors';
      back.addEventListener('click', () => {
        graph.focusedSectorId = null;
        graph.selectedNodeId = null;
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.12);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      });
      panel.appendChild(back);
      return;
    }
  
    const title = el('div', '');
    title.style.cssText = 'font-size:12px;font-weight:650;color:var(--text);margin-bottom:3px;';
    title.textContent = 'Structural sectors';
    const subtitle = el('div', '');
    subtitle.style.cssText = 'font-size:9px;line-height:1.45;color:var(--muted);margin-bottom:10px;';
    subtitle.textContent =
      'Observer layout derived only from graph relations. Sectors are not concepts invented for the Symbiont.';
    panel.append(title, subtitle);
  
    const componentSizes = (graph.components ?? []).map(component => component.length);
    if (componentSizes.length) {
      const objective = el('div','');
      objective.style.cssText='padding:8px 0 10px;border-top:1px solid rgba(98,120,136,.16);font-size:8px;line-height:1.45;color:var(--muted);';
      const isolates = componentSizes.filter(size => size === 1).length;
      objective.innerHTML =
        `<strong style="color:var(--text)">Connected components</strong><br>` +
        `${componentSizes.length} total · main ${componentSizes[0] ?? 0} nodes · ${isolates} isolates`;
      panel.appendChild(objective);
    }
  
    const sectors = [...graph.communities.entries()]
      .map(([id, ids]) => {
        const sectorNodes = ids.map(nodeId => graph.nodes.find(node => node.id === nodeId)).filter(Boolean);
        const kinds = {};
        for (const node of sectorNodes) kinds[node.kind] = (kinds[node.kind] ?? 0) + 1;
        const activity = sectorNodes.length
          ? sectorNodes.reduce((sum, node) => sum + finiteNumber(node.activationLevel, 0), 0) / sectorNodes.length
          : 0;
        return { id, ids, sectorNodes, kinds, activity };
      })
      .sort((a, b) => b.ids.length - a.ids.length);
  
    if (!sectors.length) {
      const empty = el('div', '');
      empty.style.cssText = 'font-size:9px;color:var(--muted);';
      empty.textContent = 'No multi-node sectors in the current view.';
      panel.appendChild(empty);
    }
  
    sectors.slice(0, 10).forEach((sector) => {
      const card = el('button', '');
      card.type = 'button';
      card.dataset.sectorId = sector.id;
      card.style.cssText = [
        'display:block;width:100%;text-align:left;padding:8px 0',
        'border:0;border-top:1px solid rgba(98,120,136,.16)',
        'background:transparent;color:inherit;cursor:pointer',
      ].join(';');
      const head = el('div', '');
      head.style.cssText = 'display:flex;justify-content:space-between;gap:8px;font-size:9px;';
      const name = el('strong', '');
      const description = graph.sectorDescriptions.get(sector.id);
      name.textContent = `${graph.sectorLabels.get(sector.id) ?? 'S-???'} · ${description?.interpretation ?? 'emergent sector'}`;
      const count = el('span', '');
      count.style.color = 'var(--muted)';
      count.textContent = `${sector.ids.length} nodes`;
      head.append(name, count);
      const composition = el('div', '');
      composition.style.cssText = 'font-size:8px;color:var(--muted);margin-top:3px;line-height:1.35;';
      composition.textContent = Object.entries(sector.kinds)
        .sort((a,b) => b[1] - a[1])
        .map(([kind, n]) => `${n} ${kind}`)
        .join(' · ');
      const activity = el('div', '');
      activity.style.cssText = 'font-size:8px;color:var(--muted);margin-top:3px;';
      activity.textContent = `mean activity ${pct(sector.activity)} · observer interpretation only`;
      card.append(head, composition, activity);
      card.addEventListener('click', () => {
        graph.focusedSectorId = sector.id;
        graph.selectedNodeId = null;
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.12);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      });
      panel.appendChild(card);
    });
  
    const hint = el('div', '');
    hint.style.cssText = 'margin-top:12px;padding:8px;border:1px solid rgba(80,217,255,.14);border-radius:6px;font-size:8px;line-height:1.45;color:var(--muted);';
    hint.textContent = 'Click a sector to focus its local anatomy and real bridges. Click a node for exact relations.';
    panel.appendChild(hint);
  }
  
  function updateCognitionSummary() {
    const panel = document.getElementById('mind-cognition-summary');
    if (!panel) return;
    const source = graph.replaySnapshot ?? snap;
    const topology = source.topology ?? { nodes: [], edges: [] };
    const learned = augmentLearnedGraph(
      topology,
      source.sensorimotor ?? snap.sensorimotor,
      source.observerSemantics ?? snap.observerSemantics,
      source.prospectiveAgency ?? null,
    );
    const nodes = learned.nodes;
    const topologyEdges = learned.edges;
    const current = {
      concepts: nodes.filter(node => node.kind === 'concept').length,
      predictors: nodes.filter(node => node.kind === 'predictor').length,
      edges: topologyEdges.length,
      motorEdges: topologyEdges.filter(edge =>
        String(edge.targetId ?? '').startsWith('readout_motor:') ||
        String(edge.targetId ?? '').startsWith('readout_primitive:')
      ).length,
      primitives: learned.counts.primitives,
      cognitivePrimitives: learned.counts.cognitivePrimitives,
      actuators: learned.counts.actuators,
      causalEffects: learned.counts.causalEffects,
      cognitiveMotorLinks: learned.counts.cognitiveMotorLinks,
    };
    const nowTick = finiteNumber(tel.tick, 0);
    const baseline = [...mindHistory].reverse().find(point => nowTick - point.tick >= 256)
      ?? mindHistory[0]
      ?? { tick: nowTick, concepts: current.concepts, predictors: current.predictors, edges: current.edges };
    const sign = value => value > 0 ? `+${value}` : String(value);
    const components = topologyComponentStats({ nodes, edges: topologyEdges });
    const replayLabel = graph.replayTick != null ? ` · replay t${graph.replayTick}` : ' · LIVE';
    const projectionLabel = ` · ${graph.dimension.toUpperCase()}`;
    const sectorFocusLabel = graph.focusedSectorId
      ? ` · focus ${graph.sectorLabels.get(graph.focusedSectorId) ?? 'sector'}`
      : '';
    panel.innerHTML =
      `<strong style="color:var(--text)">Complete learned structure${replayLabel}${projectionLabel}${sectorFocusLabel}</strong><br>` +
      `${current.concepts} concepts · ${current.predictors} predictors · ${current.primitives} motor primitives (${current.cognitivePrimitives} reusable) · ${current.actuators} learned actuators<br>` +
      `<span style="color:var(--muted)">${current.edges} learned relations · ${current.causalEffects} actuator→percept causal effects · ${current.cognitiveMotorLinks} readout→motor links</span><br>` +
      `<span style="color:var(--muted)">map: ${graph.hiddenMotor.actuators} actuators + ${graph.hiddenMotor.motorEdges} low-level motor edges collapsed${graph.viewMode === 'connected' ? ' · connected motor capabilities preserved while substrate stays collapsed' : ' · select a primitive to expand'}</span><br>` +
      `<span style="color:var(--muted)">components ${components.count} · main ${components.main} · secondary ${components.secondary} · unintegrated ${components.isolates}</span><br>` +
      `<span style="color:var(--muted)">Δ since t${baseline.tick}: ${sign(current.concepts-baseline.concepts)} C · ${sign(current.predictors-baseline.predictors)} P · view ${graph.viewMode}</span><br>` +
      `<span style="color:${current.cognitiveMotorLinks > 0 ? 'var(--mint)' : 'var(--muted)'}">${current.cognitiveMotorLinks > 0 ? 'cognition→motor linkage present' : 'motor learning exists outside cognitive control'} · motor origin ${tel.motorOrigin ?? '—'}</span>`;
  }

  function setDimension(dimension) {
    graph.dimension = dimension;
    graph.alpha = Math.max(graph.alpha, 0.12);
    if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
  }

  function setViewMode(mode) {
    graph.viewMode = mode;
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
    renderCognitionInspector();
  }

  function returnLive() {
    graph.replaySnapshot = null;
    graph.replayTick = null;
    updateCognitionSummary();
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
  }

  function resize() {
    const canvas = document.getElementById('mind-cognition-canvas');
    if (!canvas?.parentElement) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    canvas.width = Math.floor(rect.width);
    canvas.height = Math.floor(rect.height);
    if (getActiveTab() === 'cognition') {
      initGraphPhysics(canvas.width, canvas.height);
    }
  }

  function stop() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    graph.isRunning = false;
    if (windowMouseMove) {
      window.removeEventListener('mousemove', windowMouseMove);
      windowMouseMove = null;
    }
    if (windowMouseUp) {
      window.removeEventListener('mouseup', windowMouseUp);
      windowMouseUp = null;
    }
  }

  return {
    init: initGraphPhysics,
    renderInspector: renderCognitionInspector,
    resize,
    returnLive,
    selectNode: selectCognitiveNode,
    setDimension,
    setViewMode,
    start: startCognitionGraph,
    stop,
    updateSummary: updateCognitionSummary,
  };
}
