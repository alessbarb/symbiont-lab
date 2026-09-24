/**
 * Cognition controller.
 *
 * Owns the complete observer-side cognition map lifecycle: graph projection,
 * force layout, 2D/3D rendering, interaction, inspector and summary.
 */
import { el } from '../shared/dom.js';
import { augmentLearnedGraph } from './learning-graph.js';
import { cartographicGraph } from './cartographic-view.js';
import {
  ATLAS_MODES,
  atlasEdgeScore,
  atlasModeScore,
  atlasRegions,
  atlasSignals,
  cognitivePath,
  learningFrontier,
} from './cognitive-atlas.js';
import {
  buildCognition3DScene,
  ensure3DState,
  orbitCamera,
  relaxCognition3D,
  zoomCamera,
} from './cognition-3d.js';
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
import { graph, historySnapshots, mindHistory, observerUsage, snap, tel } from './state.js';
import {
  classRatio,
  clamp01,
  finiteNumber,
  hashStr,
  pct,
  shortId,
} from './util.js';
import {
  atlasSnapshotDiff,
  cognitiveStructures,
  deriveCognitiveEpisodes,
  observedCognitiveFlow,
  reconcileRegionLineage,
} from './cognitive-temporal.js';
import {
  atlasDetailLevel,
  atlasRegionLinks,
  atlasVisibleNodeIds,
  learningFrontierClusters,
  reconcileFrontierEvolution,
} from './cognitive-lod.js';
import { cognitiveSituation } from './cognitive-observatory.js';
import {
  prioritizedLabelIds,
  recordObserverUsage,
  summarizeDiff,
} from './cognitive-refinement.js';
import {
  blendRegionShape,
  boundaryPointToward,
  boundaryTension,
  densityHotspots,
  functionalCenter,
  organicRegionShape,
  polygonContains,
  protoSubregions,
  traceRegionPath,
} from './cognitive-regions.js';

export function createCognitionController({
  getActiveTab = () => 'overview',
  onSwitchTab = () => {},
} = {}) {
  let rafId = null;
  let windowMouseMove = null;
  let windowMouseUp = null;

  function selectCognitiveNode(nodeId) {
    graph.selectedNodeId = nodeId || null;
    if (graph.selectedNodeId) recordObserverUsage(observerUsage, 'selection');
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
    };
    const baseRadiusMap = {
      sense: 5.2,
      readout: 8.5,
      state: 6.5,
      predictor: 7.2,
      gate: 6.8,
      concept: 6.4,
      motor_primitive: 8.4,
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

    const atlasTick = finiteNumber(source.tick ?? graph.replayTick ?? tel.tick, 0);
    graph.atlasSignals = atlasSignals(enriched.nodes, enriched.edges, atlasTick);
    for (const node of enriched.nodes) {
      node.atlasScore = atlasModeScore(node, graph.atlasSignals, graph.atlasMode);
      node.atlasSignals = graph.atlasSignals.get(node.id) ?? null;
    }
    graph.learningFrontier = learningFrontier(enriched.nodes, graph.atlasSignals, 10);
    const nextFrontierClusters = learningFrontierClusters(
      enriched.nodes,
      enriched.edges,
      graph.atlasSignals,
      0.30,
    );
    graph.learningFrontierClusters = reconcileFrontierEvolution(
      nextFrontierClusters,
      graph.previousFrontierClusters,
    );
    graph.previousFrontierClusters = graph.learningFrontierClusters.map(cluster => ({
      ...cluster,
      nodeIds: [...cluster.nodeIds],
      boundaryIds: [...cluster.boundaryIds],
      communities: [...cluster.communities],
    }));
    graph.regionLinks = atlasRegionLinks(enriched.nodes, enriched.edges);
    graph.atlasPath = cognitivePath(
      graph.selectedNodeId,
      enriched.nodes,
      enriched.edges,
      12,
    );

    graph.cognitiveStructures = cognitiveStructures(enriched.nodes, enriched.edges);
    graph.observedFlow = observedCognitiveFlow(
      enriched.nodes,
      enriched.edges,
      atlasTick,
      48,
    );
    graph.cognitiveEpisodes = deriveCognitiveEpisodes(historySnapshots, mindHistory, 160);

    if (graph.diffBaselineSnapshot) {
      graph.atlasDiff = atlasSnapshotDiff(
        {
          ...graph.diffBaselineSnapshot,
          tick: graph.diffBaselineTick,
        },
        {
          ...source,
          tick: atlasTick,
        },
      );
    } else {
      graph.atlasDiff = null;
    }

    if (graph.atlasMode === 'diff') {
      const changedNodes = new Set(graph.atlasDiff?.addedNodes ?? []);
      for (const item of graph.atlasDiff?.predictionErrorChanges ?? []) {
        changedNodes.add(item.id);
      }
      for (const item of graph.atlasDiff?.changedEdges ?? []) {
        const [sourceId, targetId] = item.key.split('|');
        changedNodes.add(sourceId);
        changedNodes.add(targetId);
      }
      for (const key of graph.atlasDiff?.addedEdges ?? []) {
        const [sourceId, targetId] = key.split('|');
        changedNodes.add(sourceId);
        changedNodes.add(targetId);
      }
      for (const node of enriched.nodes) {
        const diffScore = changedNodes.has(node.id) ? 1 : 0.08;
        const signal = graph.atlasSignals.get(node.id);
        if (signal) signal.diff = diffScore;
        node.atlasScore = diffScore;
      }
    }
    return enriched;
  }
  
  function reconcileSectorLabels(communities, nodes, tick) {
    const current = new Map();
    for (const node of nodes) {
      if (!node.community || node.community === 'isolated') continue;
      if (!current.has(node.community)) current.set(node.community, new Set());
      current.get(node.community).add(node.id);
    }

    const reconciled = reconcileRegionLineage(
      current,
      graph.regionLineage,
      tick,
      graph.nextSectorId,
    );
    graph.sectorLabels = reconciled.labels;
    graph.regionLineage = reconciled.lineage;
    graph.regionEvents = reconciled.events;
    for (const event of reconciled.events) {
      const key = JSON.stringify(event);
      if (graph.regionEventHistory.some(item => item._key === key)) continue;
      graph.regionEventHistory.push({ ...event, _key: key });
    }
    while (graph.regionEventHistory.length > 256) graph.regionEventHistory.shift();
    graph.nextSectorId = reconciled.nextOrdinal;
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
    const labelTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
    if (graph.replaySnapshot) {
      graph.sectorLabels = new Map(
        [...graph.communities.keys()].map(communityId => [
          communityId,
          `R-${String(hashStr(String(communityId)) % 997).padStart(3,'0')}`,
        ])
      );
      graph.regionEvents = [];
    } else {
      reconcileSectorLabels(graph.communities, rawNodes, labelTick);
    }

    graph.atlasRegions = atlasRegions(
      rawNodes,
      rawEdges,
      graph.sectorLabels,
      sectorDescriptions,
      graph.atlasSignals,
    );
    graph.cognitiveSituation = cognitiveSituation({
      nodes: rawNodes,
      edges: rawEdges,
      regions: graph.atlasRegions,
      signals: graph.atlasSignals,
      flow: graph.observedFlow,
      frontierClusters: graph.learningFrontierClusters,
      structures: graph.cognitiveStructures,
      tick: finiteNumber(graph.replayTick ?? tel.tick, 0),
      motorOrigin: tel.motorOrigin ?? 'none',
    });
  
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

    ensure3DState(
      graph.nodes,
      graph.edges,
      graph.world3d,
      graph.velocity3d,
    );
  
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

  function atlasModeMeta() {
    return ATLAS_MODES.find(mode => mode.id === graph.atlasMode) ?? ATLAS_MODES[0];
  }

  function atlasPathSets() {
    const nodeIds = new Set(graph.atlasPath?.nodeIds ?? []);
    const edgeKeys = new Set((graph.atlasPath?.edges ?? []).map(edge =>
      `${edge.sourceId}|${edge.targetId}|${edge.kind ?? 'edge'}`
    ));
    return { nodeIds, edgeKeys };
  }

  function atlasEdgeKey(edge) {
    return `${edge.source?.id ?? edge.sourceId}|${edge.target?.id ?? edge.targetId}|${edge.kind ?? 'edge'}`;
  }

  function currentAtlasEdgeScore(edge, tick) {
    if (graph.atlasMode !== 'diff') {
      return atlasEdgeScore(edge, graph.atlasMode, tick);
    }
    const key = atlasEdgeKey(edge);
    if ((graph.atlasDiff?.addedEdges ?? []).includes(key)) return 1;
    if ((graph.atlasDiff?.changedEdges ?? []).some(item => item.key === key)) return 0.82;
    return 0.04;
  }

  function atlasRegionScore(region) {
    return clamp01(finiteNumber(region?.[graph.atlasMode], 0));
  }

  function currentLabelIds(nodes, atlasPath) {
    return prioritizedLabelIds(nodes, {
      selectedNodeId: graph.selectedNodeId,
      hoveredNodeId: graph.hoveredNode?.id ?? null,
      focusedSectorId: graph.focusedSectorId,
      pathNodeIds: atlasPath?.nodeIds ?? new Set(),
      hubIds: new Set((graph.cognitiveStructures?.hubs ?? []).map(item => item.id)),
      atlasMode: graph.atlasMode,
      detailLevel: graph.detailLevel,
    });
  }

  function flowTraceSets() {
    const nodeIds = new Set();
    const edgeKeys = new Set();
    if (!graph.flowTraceEnabled) return { nodeIds, edgeKeys };
    for (const path of graph.observedFlow?.paths ?? []) {
      for (const id of path.nodeIds ?? []) nodeIds.add(id);
      for (const edge of path.edges ?? []) edgeKeys.add(atlasEdgeKey(edge));
    }
    return { nodeIds, edgeKeys };
  }

  function fit2DView(canvas) {
    if (!graph.autoFramePending || graph.manualViewOverride || !graph.nodes.length) return;
    const candidates = graph.focusedSectorId
      ? graph.nodes.filter(node => node.community === graph.focusedSectorId)
      : graph.nodes.filter(node => !node.isolated);
    const nodes = candidates.length ? candidates : graph.nodes;
    const xs = nodes.map(node => node.x);
    const ys = nodes.map(node => node.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const spanX = Math.max(120, maxX - minX + 120);
    const spanY = Math.max(120, maxY - minY + 120);
    const scale = Math.min(2.2, Math.max(0.38,
      Math.min((canvas.width * 0.76) / spanX, (canvas.height * 0.76) / spanY)
    ));
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    graph.scale = scale;
    graph.panX = canvas.width / 2 - cx * scale;
    graph.panY = canvas.height / 2 - cy * scale;
    graph.autoFramePending = false;
  }

  function structureRole(nodeId) {
    const structures = graph.cognitiveStructures ?? { hubs: [], bottlenecks: [], loops: [] };
    return {
      hub: structures.hubs.some(item => item.id === nodeId),
      bottleneck: structures.bottlenecks.some(item => item.id === nodeId),
      loopCount: structures.loops.filter(loop => loop.includes(nodeId)).length,
    };
  }

  function drawStructureRoleMarker(ctx, x, y, radius, nodeId, alpha = 1) {
    if (!['structure','anatomy'].includes(graph.atlasMode)) return;
    const role = structureRole(nodeId);
    if (!role.hub && !role.bottleneck && !role.loopCount) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.arc(x, y, radius + 5, 0, Math.PI * 2);
    ctx.strokeStyle = role.hub
      ? 'rgba(255,189,84,.78)'
      : role.bottleneck
        ? 'rgba(113,233,186,.72)'
        : 'rgba(200,216,228,.55)';
    ctx.lineWidth = role.hub ? 1.6 : 1.1;
    ctx.setLineDash(role.bottleneck ? [3, 3] : role.loopCount ? [1, 3] : []);
    ctx.stroke();
    ctx.setLineDash([]);
    if (role.loopCount > 1) {
      ctx.beginPath();
      ctx.arc(x, y, radius + 8, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(200,216,228,.34)';
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }
    ctx.restore();
  }

  function currentDetailLevel() {
    graph.detailLevel = atlasDetailLevel({
      dimension: graph.dimension,
      scale: graph.scale,
      cameraDistance: graph.camera3d?.distance ?? 900,
      focusedRegion: Boolean(graph.focusedSectorId),
      previousLevel: graph.detailLevel,
    });
    return graph.detailLevel;
  }

  function regionInternalEdgeCount(regionId) {
    return graph.edges.filter(edge =>
      edge.source?.community === regionId &&
      edge.target?.community === regionId
    ).length;
  }

  function rememberCenterTrail(store, regionId, point, tick) {
    const trail = store.get(regionId) ?? [];
    const previous = trail[trail.length - 1];
    if (!previous || Math.hypot(previous.x - point.x, previous.y - point.y) > 2 || tick - previous.tick >= 16) {
      trail.push({ x: point.x, y: point.y, tick });
      while (trail.length > 24) trail.shift();
      store.set(regionId, trail);
    }
    return trail;
  }

  function regionGeometry(region, points, dimension, tick) {
    const previousStore = dimension === '3d'
      ? graph.regionShapeHistory3d
      : graph.regionShapeHistory2d;
    const trailStore = dimension === '3d'
      ? graph.regionCenterTrails3d
      : graph.regionCenterTrails2d;
    const raw = organicRegionShape(points, {
      padding: dimension === '3d' ? 12 : 18,
      bins: Math.max(14, Math.min(26, points.length + 8)),
      smoothPasses: 2,
      sampleCount: 44,
    });
    const previous = previousStore.get(region.id);
    const shape = blendRegionShape(previous, raw, graph.replaySnapshot ? 1 : 0.24);
    previousStore.set(region.id, shape);
    const center = functionalCenter(points, graph.atlasMode);
    const trail = rememberCenterTrail(trailStore, region.id, center, tick);
    const internalEdges = regionInternalEdgeCount(region.id);
    return {
      ...shape,
      functionalCenter: center,
      trail,
      tension: boundaryTension(region, internalEdges),
      hotspots: densityHotspots(points, {
        maxHotspots: 4,
        bandwidth: dimension === '3d' ? 34 : 52,
      }),
    };
  }

  function drawRegionDensity(ctx, shape, color) {
    if (!['activity','learning','prediction','dynamics'].includes(graph.atlasMode)) return;
    if (!shape?.hotspots?.length || !traceRegionPath(ctx, shape)) return;
    ctx.save();
    ctx.clip();
    const maxDensity = Math.max(...shape.hotspots.map(item => item.density), 1);
    for (const hotspot of shape.hotspots) {
      const strength = Math.min(1, hotspot.density / maxDensity);
      const radius = Math.max(24, shape.radius * (0.18 + strength * 0.20));
      const gradient = ctx.createRadialGradient(
        hotspot.x, hotspot.y, 0,
        hotspot.x, hotspot.y, radius,
      );
      gradient.addColorStop(0, `${color}${Math.round((0.05 + strength * 0.10) * 255).toString(16).padStart(2,'0')}`);
      gradient.addColorStop(1, `${color}00`);
      ctx.fillStyle = gradient;
      ctx.fillRect(hotspot.x - radius, hotspot.y - radius, radius * 2, radius * 2);
    }
    ctx.restore();
  }

  function drawFunctionalCenter(ctx, shape, color) {
    if (!['structure','anatomy','dynamics'].includes(graph.atlasMode)) return;
    const center = shape.functionalCenter;
    if (!center) return;
    ctx.save();
    const trail = shape.trail ?? [];
    if (trail.length > 1) {
      ctx.beginPath();
      ctx.moveTo(trail[0].x, trail[0].y);
      for (let i = 1; i < trail.length; i++) ctx.lineTo(trail[i].x, trail[i].y);
      ctx.strokeStyle = `${color}36`;
      ctx.lineWidth = 0.8;
      ctx.setLineDash([2,4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.beginPath();
    ctx.arc(center.x, center.y, 2.6, 0, Math.PI * 2);
    ctx.fillStyle = `${color}cc`;
    ctx.fill();
    ctx.restore();
  }

  function drawProtoSubregions(ctx, region, points, shape, color) {
    if (graph.atlasMode !== 'anatomy' || graph.detailLevel === 'regions') return;
    const memberIds = new Set(region.nodeIds);
    const regionNodes = graph.nodes.filter(node => memberIds.has(node.id));
    const components = protoSubregions(regionNodes, graph.edges, { minimumSize: 3 });
    graph.protoSubregions.set(region.id, components);
    if (!components.length) return;
    const pointById = new Map(points.map(point => [point.id, point]));
    ctx.save();
    if (traceRegionPath(ctx, shape)) ctx.clip();
    for (const component of components.slice(0, 4)) {
      const subPoints = component.map(id => pointById.get(id)).filter(Boolean);
      if (subPoints.length < 3) continue;
      const subShape = organicRegionShape(subPoints, {
        padding: 8,
        bins: Math.max(10, subPoints.length + 4),
        smoothPasses: 2,
        sampleCount: 32,
      });
      if (!traceRegionPath(ctx, subShape)) continue;
      ctx.fillStyle = `${color}0b`;
      ctx.strokeStyle = `${color}4c`;
      ctx.lineWidth = 0.8;
      ctx.setLineDash([2,5]);
      ctx.fill();
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();
  }

  function visibleIdsForDetail(nodes, atlasPath) {
    const structures = graph.cognitiveStructures ?? { hubs: [], bottlenecks: [] };
    return atlasVisibleNodeIds(nodes, graph.detailLevel, {
      selectedNodeId: graph.selectedNodeId,
      pathNodeIds: [...(atlasPath?.nodeIds ?? [])],
      hubIds: (structures.hubs ?? []).map(item => item.id),
      bottleneckIds: (structures.bottlenecks ?? []).map(item => item.id),
    });
  }

  function drawRegionMass(ctx, region, points, dimension, tick, color) {
    if (points.length < 2) return null;
    const shape = regionGeometry(region, points, dimension, tick);
    const score = atlasRegionScore(region);
    const active = graph.focusedSectorId === region.id;
    const anatomy = graph.atlasMode === 'anatomy';
    const dynamics = graph.atlasMode === 'dynamics';
    const fillAlpha = anatomy
      ? 0.018 + score * 0.030
      : dynamics
        ? 0.020 + score * 0.050
        : 0.028 + score * 0.075;
    const strokeAlpha = anatomy
      ? 0.32 + score * 0.44
      : 0.14 + score * 0.38;
    const tension = shape.tension ?? 0;

    ctx.save();
    if (traceRegionPath(ctx, shape)) {
      ctx.fillStyle = `${color}${Math.round(fillAlpha * 255).toString(16).padStart(2,'0')}`;
      ctx.strokeStyle = active
        ? 'rgba(220,232,240,.88)'
        : `${color}${Math.round(strokeAlpha * 255).toString(16).padStart(2,'0')}`;
      ctx.lineWidth = active ? 2.2 : 0.9 + score * 1.3 + (1 - tension) * 0.45;
      // High bridge tension = more permeable/discontinuous frontier.
      ctx.setLineDash(
        active ? [] :
        tension > 0.66 ? [2, 6] :
        tension > 0.34 ? [5, 6] :
        [9, 5]
      );
      ctx.fill();
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();

    drawRegionDensity(ctx, shape, color);
    drawProtoSubregions(ctx, region, points, shape, color);
    drawFunctionalCenter(ctx, shape, color);
    return shape;
  }

  function drawAtlasRegionLinks(ctx, geometry, tick) {
    if (graph.detailLevel === 'nodes' || graph.focusedSectorId) return;
    for (const link of graph.regionLinks ?? []) {
      const a = geometry.get(link.a);
      const b = geometry.get(link.b);
      if (!a || !b) continue;
      const start = boundaryPointToward(a, b.center ?? b);
      const end = boundaryPointToward(b, a.center ?? a);
      const idle = link.lastUseTick > 0
        ? Math.max(0, tick - link.lastUseTick)
        : 4096;
      const recency = Math.exp(-idle / 768);
      const strength = Math.min(1, Math.log1p(link.count) / 3.2);
      const supportStrength = Math.min(1, Math.log1p(link.support ?? 0) / 7);
      const directionTotal = Math.max(1, (link.forward ?? 0) + (link.reverse ?? 0));
      const directionBias = ((link.forward ?? 0) - (link.reverse ?? 0)) / directionTotal;
      const anatomy = graph.atlasMode === 'anatomy';
      const dynamics = graph.atlasMode === 'dynamics' || graph.atlasMode === 'activity';
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.strokeStyle = dynamics
        ? `rgba(80,217,255,${0.16 + recency * 0.66})`
        : anatomy
          ? `rgba(200,216,228,${0.16 + strength * 0.54})`
          : `rgba(140,166,188,${0.10 + strength * 0.38})`;
      ctx.lineWidth = 1 + strength * 3.1 + supportStrength * 1.2;
      ctx.setLineDash(graph.detailLevel === 'regions' || anatomy ? [] : [4, 5]);
      ctx.stroke();
      ctx.setLineDash([]);

      if (Math.abs(directionBias) >= 0.28 && (anatomy || dynamics)) {
        const forward = directionBias > 0;
        const from = forward ? start : end;
        const to = forward ? end : start;
        const t = 0.62;
        const x = from.x + (to.x - from.x) * t;
        const y = from.y + (to.y - from.y) * t;
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const size = 4 + strength * 3;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(
          x - Math.cos(angle - Math.PI / 6) * size,
          y - Math.sin(angle - Math.PI / 6) * size,
        );
        ctx.lineTo(
          x - Math.cos(angle + Math.PI / 6) * size,
          y - Math.sin(angle + Math.PI / 6) * size,
        );
        ctx.closePath();
        ctx.fillStyle = dynamics
          ? 'rgba(80,217,255,.68)'
          : 'rgba(200,216,228,.58)';
        ctx.fill();
      }
      ctx.restore();
    }
  }

  function drawLearningFrontierZones(ctx, pointsById) {
    if (!['learning','dynamics'].includes(graph.atlasMode)) return;
    for (const [clusterIndex, cluster] of (graph.learningFrontierClusters ?? []).entries()) {
      const points = cluster.nodeIds.map(id => pointsById.get(id)).filter(Boolean);
      if (!points.length) continue;
      const x = points.reduce((sum, item) => sum + item.x, 0) / points.length;
      const y = points.reduce((sum, item) => sum + item.y, 0) / points.length;
      let radius = 18;
      for (const point of points) {
        radius = Math.max(
          radius,
          Math.hypot(point.x - x, point.y - y) + finiteNumber(point.radius, 5) + 8,
        );
      }
      radius = Math.min(150, radius);
      ctx.save();
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,189,84,${0.025 + cluster.meanScore * 0.06})`;
      ctx.strokeStyle = `rgba(255,189,84,${0.24 + cluster.maxScore * 0.52})`;
      ctx.lineWidth = 1 + cluster.maxScore * 1.5;
      ctx.setLineDash([3, 5]);
      ctx.fill();
      ctx.stroke();
      ctx.setLineDash([]);
      if (clusterIndex < 3) {
        ctx.font = '600 8px -apple-system, sans-serif';
        ctx.fillStyle = 'rgba(255,205,120,.76)';
        ctx.textAlign = 'left';
        ctx.fillText(
          `learning frontier · ${cluster.nodeIds.length} nodes · ${Math.round(cluster.maxScore * 100)}%`,
          x - radius * 0.62,
          y + radius + 11,
        );
      }
      ctx.restore();
    }
  }

  function drawAtlasRegions3D(ctx, scene, sectorFocus) {
    graph.atlasRegionHitAreas3d = [];
    graph.atlasRegionGeometry3d.clear();
    const tick = finiteNumber(graph.replayTick ?? tel.tick, 0);
    const palette = [PAL.violet, PAL.cyan, PAL.amber, PAL.mint, '#4ecdc4', '#e09f3e'];

    for (const region of graph.atlasRegions ?? []) {
      if (sectorFocus && region.id !== sectorFocus.sectorId) continue;
      const projected = region.nodeIds
        .map(id => scene.byId.get(id))
        .filter(Boolean)
        .map(item => ({
          id: item.node.id,
          x: item.x,
          y: item.y,
          radius: item.radius,
          atlasScore: item.node.atlasScore,
          signals: item.node.atlasSignals,
        }));
      if (projected.length < 2) continue;

      const color = palette[hashStr(String(region.id)) % palette.length];
      const shape = drawRegionMass(ctx, region, projected, '3d', tick, color);
      if (!shape) continue;

      graph.atlasRegionHitAreas3d.push({ id: region.id, polygon: shape.polygon, radius: shape.radius });
      graph.atlasRegionGeometry3d.set(region.id, shape);

      const labelX = shape.center.x - shape.radius * 0.52;
      const labelY = shape.center.y - shape.radius - 10;
      ctx.textAlign = 'left';
      ctx.font = '600 10px -apple-system, sans-serif';
      ctx.fillStyle = `${color}e6`;
      ctx.fillText(`${region.label} · ${region.interpretation}`, labelX, labelY);
      ctx.font = '8px -apple-system, sans-serif';
      ctx.fillStyle = 'rgba(140,166,188,.72)';
      ctx.fillText(
        `${region.total} nodes · ${atlasModeMeta().label.toLowerCase()} ${Math.round(atlasRegionScore(region) * 100)}% · boundary tension ${Math.round((shape.tension ?? 0) * 100)}%`,
        labelX,
        labelY + 12,
      );
    }
  }

  function drawGraphFrame3D(canvas) {
    currentDetailLevel();
    updateCognitionSummary();
    const ctx = canvas.getContext('2d');
    const { width, height } = canvas;
    const { nodes, edges, hoveredNode, fmriEnabled } = graph;
    ctx.clearRect(0, 0, width, height);
    if (!nodes.length) return;

    let scene = buildCognition3DScene(
      nodes,
      edges,
      graph.camera3d,
      width,
      height,
      graph.world3d,
      graph.threeDMode,
    );
    if (graph.autoFramePending && !graph.manualViewOverride && scene.metrics?.occupiedRadius > 0) {
      const distance = Math.min(1500, Math.max(420, scene.metrics.occupiedRadius * 3.0 + 220));
      graph.camera3d = { ...graph.camera3d, distance };
      graph.autoFramePending = false;
      scene = buildCognition3DScene(
        nodes,
        edges,
        graph.camera3d,
        width,
        height,
        graph.world3d,
        graph.threeDMode,
      );
    }
    const sectorFocus = focusedSectorContext();

    const now = performance.now();
    const focusId = hoveredNode?.id ?? graph.selectedNodeId;
    const activeTopology = currentRenderedTopology();
    const connectedIds = focusId
      ? graphSubgraphIds(activeTopology, focusId, graph.pathDepth)
      : null;
    const atlasPath = atlasPathSets();
    const labelIds = currentLabelIds(nodes, atlasPath);
    const flowTrace = flowTraceSets();
    const detailLevel = currentDetailLevel();
    const visibleIds = visibleIdsForDetail(nodes, atlasPath);
    graph.detailVisibleIds = visibleIds;
    graph.projected3d = new Map(
      [...scene.byId.entries()].filter(([id]) =>
        sectorFocus ? sectorFocus.visible.has(id) : visibleIds.has(id)
      )
    );
    const atlasTick = finiteNumber(graph.replayTick ?? tel.tick, 0);

    drawAtlasRegions3D(ctx, scene, sectorFocus);
    drawAtlasRegionLinks(ctx, graph.atlasRegionGeometry3d, atlasTick);
    drawLearningFrontierZones(ctx, scene.byId);

    // Objective connected-component labels remain secondary context in
    // Structure mode. Atlas regions are the primary observer-level anatomy.
    if (!sectorFocus && graph.atlasMode === 'structure' && graph.detailLevel !== 'regions') {
      for (const component of scene.components ?? []) {
        if (component.count < 2) continue;
        ctx.font = '8px -apple-system, sans-serif';
        ctx.fillStyle = component.rank === 0
          ? 'rgba(200,216,228,.42)'
          : 'rgba(98,120,136,.36)';
        ctx.textAlign = 'center';
        ctx.fillText(
          `component #${component.rank + 1} · ${component.count}`,
          component.x,
          component.y - 12,
        );
      }
    }

    // Real graph edges. Geometry is straight because curvature would add a
    // second observer-invented spatial dimension unrelated to evidence.
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
      const edgeKey = atlasEdgeKey(edge);
      const pathEdge = atlasPath.edgeKeys.has(edgeKey);
      const flowEdge = flowTrace.edgeKeys.has(edgeKey);
      if (graph.flowTraceEnabled && !flowEdge && !pathEdge) continue;
      const endpointsVisible =
        visibleIds.has(edge.source.id) && visibleIds.has(edge.target.id);
      if (!sectorFocus && detailLevel === 'regions' && !focusId && !pathEdge) continue;
      if (!sectorFocus && detailLevel === 'meso' && !endpointsVisible && !pathEdge && !isConn) continue;
      if (focusId && !isConn && !pathEdge) continue;
      if (sectorFocus) {
        const sourceLocal = sectorFocus.local.has(edge.source.id);
        const targetLocal = sectorFocus.local.has(edge.target.id);
        if (!(sourceLocal || targetLocal)) continue;
      }

      visibleEdges.push({
        edge,
        a,
        b,
        depth: (a.depth + b.depth) / 2,
        focused: isConn || pathEdge,
      });
    }
    visibleEdges.sort((a,b) => b.depth - a.depth);

    for (const item of visibleEdges) {
      const { edge, a, b, focused } = item;
      const support = Math.max(0, finiteNumber(edge.support, 0));
      const stable = Math.max(0, finiteNumber(edge.stableTicks, 0));
      const liveTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
      const idle = Math.max(0, liveTick - finiteNumber(edge.lastUseTick, liveTick));
      const recency = Math.exp(-idle / 512);
      const evidenceWidth = 0.65 + Math.min(2.4, Math.log1p(support) * 0.34 + Math.log1p(stable) * 0.08);

      const modeScore = currentAtlasEdgeScore(edge, liveTick);
      ctx.strokeStyle = cognitionEdgeColor(edge, focused);
      ctx.globalAlpha = focused
        ? 0.98
        : Math.max(0.06, 0.08 + modeScore * 0.72 + recency * 0.20);
      ctx.lineWidth = focused
        ? Math.max(2.6, evidenceWidth)
        : Math.max(0.55, evidenceWidth * (0.45 + modeScore * 0.85));
      ctx.setLineDash(edge.kind === 'causal_effect' ? [5,4] : []);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.setLineDash([]);

      // Recent-use pulse: direction is source -> target. This is a visual
      // encoding of last_use_tick, not simulated neural activity.
      if (idle <= 48) {
        const phase = ((now * 0.00045) + ((liveTick - idle) % 17) / 17) % 1;
        const px = a.x + (b.x - a.x) * phase;
        const py = a.y + (b.y - a.y) * phase;
        ctx.beginPath();
        ctx.arc(px, py, focused ? 2.4 : 1.7, 0, Math.PI * 2);
        ctx.fillStyle = cognitionEdgeColor(edge, true);
        ctx.globalAlpha = 0.85;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    // Painter's algorithm: far nodes first, near nodes last.
    for (const projected of scene.projected) {
      const node = projected.node;
      if (sectorFocus && !sectorFocus.visible.has(node.id)) continue;
      const pathNode = atlasPath.nodeIds.has(node.id);
      const isSelected = graph.selectedNodeId === node.id;
      const isHovered = hoveredNode?.id === node.id;
      if (!sectorFocus && !visibleIds.has(node.id) && !pathNode && !isSelected && !isHovered) continue;
      const isConn = connectedIds?.has(node.id);
      const dimmed = Boolean(
        (focusId && !isConn) ||
        (graph.flowTraceEnabled && !flowTrace.nodeIds.has(node.id))
      );

      const graphTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
      const nodeIdleTicks = node.lastUseTick > 0
        ? Math.max(0, graphTick - node.lastUseTick)
        : 2048;
      const nodeRecency = Math.exp(-nodeIdleTicks / 768);
      const activityGlow = fmriEnabled
        ? Math.max(0, finiteNumber(node.activationLevel, 0))
        : 0;

      const radius = projected.radius * (isHovered || isSelected ? 1.28 : 1);
      ctx.beginPath();
      if (node.kind === 'motor_primitive') {
        ctx.moveTo(projected.x, projected.y - radius);
        ctx.lineTo(projected.x + radius, projected.y);
        ctx.lineTo(projected.x, projected.y + radius);
        ctx.lineTo(projected.x - radius, projected.y);
        ctx.closePath();
      } else if (node.kind === 'actuator') {
        ctx.rect(projected.x - radius * 0.8, projected.y - radius * 0.8, radius * 1.6, radius * 1.6);
      } else {
        ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
      }
      const modeScore = clamp01(finiteNumber(node.atlasScore, 0));
      ctx.fillStyle = isHovered ? '#ffffff' : node.color;
      const depthFog = Math.max(0.34, Math.min(1, 1 - projected.depth / 1800));
      ctx.globalAlpha = dimmed
        ? 0.05
        : pathNode
          ? 0.98
          : Math.min(1, (0.16 + modeScore * 0.62 + nodeRecency * 0.12 + activityGlow * 0.10) * depthFog);
      ctx.shadowColor = node.color;
      ctx.shadowBlur = isSelected ? 18 : pathNode ? 11 : activityGlow * 9;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
      drawStructureRoleMarker(ctx, projected.x, projected.y, radius, node.id, depthFog);

      if (node.kind === 'readout') {
        ctx.strokeStyle = PAL.mint;
        ctx.globalAlpha = dimmed ? 0.08 : 0.72;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.arc(projected.x, projected.y, radius + 2.5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      if (node.errorCls) {
        const errorLevel = classRatio(node.errorCls, 15);
        if (errorLevel > 0) {
          ctx.strokeStyle = PAL.coral;
          ctx.globalAlpha = 0.18 + errorLevel * 0.55;
          ctx.lineWidth = 1 + errorLevel * 1.5;
          ctx.beginPath();
          ctx.arc(projected.x, projected.y, radius + 3 + errorLevel * 4, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      if (isSelected) {
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(projected.x, projected.y, radius + 5, 0, Math.PI * 2);
        ctx.stroke();
      }

      if (node.replayActive || node.prospectiveSelected) {
        ctx.strokeStyle = node.replayActive ? PAL.mint : PAL.amber;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(projected.x, projected.y, radius + 8, 0, Math.PI * 2);
        ctx.stroke();
      }

      if (isHovered || isSelected || labelIds.has(node.id)) {
        const label = node.observerLabel ?? compactSelfLabel(node.label ?? node.id, 12, 6);
        ctx.font = isSelected ? '600 10px -apple-system, sans-serif' : '9px -apple-system, sans-serif';
        ctx.fillStyle = isSelected ? '#fff' : 'rgba(200,216,228,.82)';
        ctx.textAlign = 'center';
        ctx.fillText(label, projected.x, projected.y + radius + 12);
      }
    }

    const note = document.getElementById('mind-cognition-3d-note');
    if (note) {
      if (graph.dimension === '3d') {
        const physicalized = graph.threeDMode === 'physicalized';
        note.textContent = physicalized
          ? `PHYSICALIZED 3D · ${atlasModeMeta().label.toUpperCase()} · ${graph.detailLevel.toUpperCase()} · observer experiment · wiring ${scene.metrics.wiringLength.toFixed(0)} · radius ${scene.metrics.occupiedRadius.toFixed(0)} · density ${(scene.metrics.packingDensity*100).toFixed(1)}% · ◇ primitive · ○ readout · no anatomical coordinates`
          : `RELATIONAL 3D · ${atlasModeMeta().label.toUpperCase()} · ${graph.detailLevel.toUpperCase()} · XYZ from graph evidence only · wiring ${scene.metrics.wiringLength.toFixed(0)} · ◇ primitive · ○ readout · no anatomical coordinates`;
      } else {
        note.textContent = '2D observer cartography';
      }
    }

  }

  function drawGraphFrame(canvas) {
    if (graph.dimension === '3d') {
      drawGraphFrame3D(canvas);
      return;
    }
    currentDetailLevel();
    updateCognitionSummary();
    const ctx = canvas.getContext('2d');
    const { width, height } = canvas;
    const { nodes, edges, scale, panX, panY, hoveredNode, fmriEnabled } = graph;
    ctx.clearRect(0, 0, width, height);
    if (!nodes.length) return;
    fit2DView(canvas);
  
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
  
    // Observer-derived organic territories behind the graph.
    graph.atlasRegionHitAreas2d = [];
    graph.atlasRegionGeometry2d.clear();
    const communityStats = new Map();
    for (const node of nodes) {
      if (!node.community || node.community === 'isolated') continue;
      const s = communityStats.get(node.community) ?? { n: 0, nodes: [] };
      s.n += 1;
      s.nodes.push(node);
      communityStats.set(node.community, s);
    }
    const regionTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
    const palette = [PAL.violet, PAL.cyan, PAL.amber, PAL.mint, '#4ecdc4', '#e09f3e'];

    for (const [communityId, s] of communityStats.entries()) {
      if (s.n < 2) continue;
      if (sectorFocus && communityId !== sectorFocus.sectorId) continue;
      const atlasRegion = (graph.atlasRegions ?? []).find(region => region.id === communityId);
      if (!atlasRegion) continue;
      const points = s.nodes.map(node => ({
        id: node.id,
        x: node.x,
        y: node.y,
        radius: node.radius,
        atlasScore: node.atlasScore,
        signals: node.atlasSignals,
      }));
      const color = palette[hashStr(String(communityId)) % palette.length];
      const shape = drawRegionMass(ctx, atlasRegion, points, '2d', regionTick, color);
      if (!shape) continue;

      graph.atlasRegionHitAreas2d.push({ id: communityId, polygon: shape.polygon, radius: shape.radius });
      graph.atlasRegionGeometry2d.set(communityId, shape);

      const sectorLabel = graph.sectorLabels.get(communityId) ?? 'S-???';
      const sectorDescription = graph.sectorDescriptions.get(communityId);
      const labelX = shape.center.x - shape.radius * 0.55;
      const labelY = shape.center.y - shape.radius - 10;
      ctx.font = '600 10px -apple-system, sans-serif';
      ctx.fillStyle = `${color}e6`;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(
        `${sectorLabel} · ${sectorDescription?.interpretation ?? 'emergent region'}`,
        labelX,
        labelY,
      );
      ctx.font = '8px -apple-system, sans-serif';
      ctx.fillStyle = 'rgba(175,199,220,.62)';
      ctx.fillText(
        `${s.n} nodes · ${atlasModeMeta().label.toLowerCase()} ${Math.round(atlasRegionScore(atlasRegion) * 100)}% · boundary tension ${Math.round((shape.tension ?? 0) * 100)}%`,
        labelX,
        labelY + 12,
      );
    }

    const focusId = hoveredNode?.id ?? graph.selectedNodeId;
    const activeTopology = currentRenderedTopology();
    const connectedIds = focusId ? graphSubgraphIds(activeTopology, focusId, graph.pathDepth) : null;
    const atlasPath = atlasPathSets();
    const labelIds = currentLabelIds(nodes, atlasPath);
    const flowTrace = flowTraceSets();
    const detailLevel = currentDetailLevel();
    const visibleIds = visibleIdsForDetail(nodes, atlasPath);
    graph.detailVisibleIds = visibleIds;
    const atlasTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
    drawAtlasRegionLinks(ctx, graph.atlasRegionGeometry2d, atlasTick);
    const pointMap = new Map(nodes.map(node => [
      node.id,
      { x: node.x, y: node.y, radius: node.radius },
    ]));
    drawLearningFrontierZones(ctx, pointMap);
  
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
      const liveTick = atlasTick;
      const modeScore = currentAtlasEdgeScore(edge, liveTick);
      const edgeKey = atlasEdgeKey(edge);
      const pathEdge = atlasPath.edgeKeys.has(edgeKey);
      const flowEdge = flowTrace.edgeKeys.has(edgeKey);
      if (graph.flowTraceEnabled && !flowEdge && !pathEdge) continue;
      const endpointsVisible =
        visibleIds.has(edge.source.id) && visibleIds.has(edge.target.id);
      if (!sectorFocus && detailLevel === 'regions' && !focusId && !pathEdge) continue;
      if (!sectorFocus && detailLevel === 'meso' && !endpointsVisible && !pathEdge && !isConn) continue;
      if (focusId) {
        if (!isConn && !pathEdge) continue;
      } else if (sectorFocus) {
        const sourceLocal = sectorFocus.local.has(edge.source.id);
        const targetLocal = sectorFocus.local.has(edge.target.id);
        if (!(sourceLocal || targetLocal)) continue;
      } else if (graph.atlasMode === 'structure') {
        if (sameSector && modeScore < 0.58) continue;
        if (!sameSector && !graph.bridgeEdges.has(bridgeKey) && modeScore < 0.46) continue;
      } else if (modeScore < 0.16) {
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
      const idleTicks = Math.max(0, liveTick - finiteNumber(edge.lastUseTick, liveTick));
      const recency = Math.exp(-idleTicks / 512);
      ctx.strokeStyle = color;
      ctx.globalAlpha = pathEdge
        ? 0.98
        : dimmed
          ? 0.12
          : Math.max(0.08, 0.10 + modeScore * 0.72 + recency * 0.18);
      ctx.lineWidth = pathEdge
        ? 3.1
        : isConn
          ? 2.8
          : 0.55 + supportScale * 1.6 + modeScore * 1.2;
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
      const pathNode = atlasPath.nodeIds.has(node.id);
      const isHovered = hoveredNode && hoveredNode.id === node.id;
      const isSelected = graph.selectedNodeId === node.id;
      if (!sectorFocus && !visibleIds.has(node.id) && !pathNode && !isSelected && !isHovered) continue;
      const isConn = connectedIds && connectedIds.has(node.id);
      const dimmed = Boolean(
        (focusId && !isConn) ||
        (graph.flowTraceEnabled && !flowTrace.nodeIds.has(node.id))
      );
      const breath = (fmriEnabled && node.activationLevel > 0)
        ? Math.sin(now * 0.003 + hashStr(node.id)) * (node.activationLevel * 2.0)
        : 0;
      const modeScore = clamp01(finiteNumber(node.atlasScore, 0));
      const r = ((isHovered || isSelected)
        ? node.radius * 1.35
        : node.radius * (0.82 + modeScore * 0.28)) + breath;
  
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? '#fff' : node.color;
      ctx.shadowColor = node.color;
      ctx.shadowBlur = isSelected
        ? 20
        : pathNode
          ? 12
          : isConn
            ? 10
            : (fmriEnabled && node.activationLevel > 0 ? 3 + node.activationLevel * 8 : 2);
      const graphTick = finiteNumber(graph.replayTick ?? tel.tick, 0);
      const nodeIdleTicks = node.lastUseTick > 0 ? Math.max(0, graphTick - node.lastUseTick) : 2048;
      const nodeRecency = Math.exp(-nodeIdleTicks / 768);
      ctx.globalAlpha = dimmed
        ? 0.08
        : pathNode
          ? 1
          : Math.min(1, 0.18 + modeScore * 0.70 + nodeRecency * 0.12 + (isSelected || isHovered ? 0.15 : 0));
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.shadowBlur  = 0;
      drawStructureRoleMarker(ctx, node.x, node.y, r, node.id);
  
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
        labelIds.has(node.id) ||
        node.replayActive ||
        node.prospectiveSelected
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
  
    if (graph.dimension === '3d') {
      relaxCognition3D(
        graph.nodes,
        graph.edges,
        graph.world3d,
        graph.velocity3d,
        graph.threeDMode,
        graph.alpha > 0.08 ? 2 : 1,
      );
      graph.alpha = Math.max(GRAPH_PHYSICS.alphaMin, graph.alpha * 0.988);
    } else {
      stepGraphPhysics(canvas.width, canvas.height);
    }
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
    const flowBtn  = document.getElementById('mind-flow-trace-btn');
    const fmriBtn  = document.getElementById('mind-fmri-btn');
    const zoomIn   = document.getElementById('mind-zoom-in');
    const zoomOut  = document.getElementById('mind-zoom-out');
    const resetBtn = document.getElementById('mind-graph-reset');
    const timelineInput = document.getElementById('mind-atlas-timeline');
    const timelineDiff = document.getElementById('mind-atlas-diff-btn');
    const timelineLive = document.getElementById('mind-atlas-timeline-live');

    updateTimelineControls();

    if (timelineInput && !timelineInput.dataset.bound) {
      timelineInput.dataset.bound = 'true';
      timelineInput.addEventListener('input', () => replayHistoryIndex(timelineInput.value));
    }
    if (timelineDiff && !timelineDiff.dataset.bound) {
      timelineDiff.dataset.bound = 'true';
      timelineDiff.addEventListener('click', toggleDiffBaseline);
    }
    if (timelineLive && !timelineLive.dataset.bound) {
      timelineLive.dataset.bound = 'true';
      timelineLive.addEventListener('click', returnLive);
    }
  
    if (flowBtn && !flowBtn.dataset.bound) {
      flowBtn.dataset.bound = 'true';
      flowBtn.addEventListener('click', () => {
        graph.flowTraceEnabled = !graph.flowTraceEnabled;
        flowBtn.classList.toggle('active', graph.flowTraceEnabled);
        recordObserverUsage(observerUsage, 'flow-trace');
        graph.alpha = Math.max(graph.alpha, 0.12);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      });
    }
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
        graph.manualViewOverride = true;
        graph.autoFramePending = false;
        if (graph.dimension === '3d') {
          invalidateProjectedRegionHistory3D();
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
        graph.manualViewOverride = true;
        graph.autoFramePending = false;
        if (graph.dimension === '3d') {
          invalidateProjectedRegionHistory3D();
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
        invalidateProjectedRegionHistory3D();
        graph.autoFramePending = true;
        graph.manualViewOverride = false;
        graph.focusedSectorId = null;
        graph.selectedNodeId = null;
        graph.cachedPositions.clear();
        graph.world3d.clear();
        graph.velocity3d.clear();
        ensure3DState(graph.nodes, graph.edges, graph.world3d, graph.velocity3d);
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
        if (graph.detailVisibleIds && !graph.detailVisibleIds.has(n.id)) continue;
        if (Math.hypot(n.x - wx, n.y - wy) <= n.radius + 6) return n;
      }
      return null;
    }

    function findRegion(mx, my) {
      const areas = graph.dimension === '3d'
        ? (graph.atlasRegionHitAreas3d ?? [])
        : (graph.atlasRegionHitAreas2d ?? []);
      const point = graph.dimension === '3d'
        ? { x: mx, y: my }
        : {
            x: (mx - graph.panX) / graph.scale,
            y: (my - graph.panY) / graph.scale,
          };
      let best = null;
      for (const area of areas) {
        if (!polygonContains(area.polygon ?? [], point.x, point.y)) continue;
        if (!best || area.radius < best.radius) best = area;
      }
      return best;
    }
  
    canvas.addEventListener('wheel', ev => {
      ev.preventDefault();
      graph.manualViewOverride = true;
      graph.autoFramePending = false;
      if (graph.dimension === '3d') {
        invalidateProjectedRegionHistory3D();
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
          invalidateProjectedRegionHistory3D();
          graph.manualViewOverride = true;
          graph.autoFramePending = false;
          isPanning = true;
          orbitLastX = x;
          orbitLastY = y;
          canvas.style.cursor = 'grabbing';
        }
        return;
      }
      if (node) { isDragging = true; draggedNode = node; node.pinned = true; node.vx = node.vy = 0; }
      else { graph.manualViewOverride = true; graph.autoFramePending = false; isPanning = true; panStartX = x - graph.panX; panStartY = y - graph.panY; canvas.style.cursor = 'grabbing'; }
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
          invalidateProjectedRegionHistory3D();
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
  
    windowMouseUp = ev => {
      const clicked = pressedNode && dragDist < 5 ? pressedNode : null;
      const coords = canvasCoords(ev);
      const clickedRegion = !clicked && dragDist < 5
        ? findRegion(coords.x, coords.y)
        : null;
      if (draggedNode) { draggedNode.pinned = false; draggedNode = null; }
      if (clicked) {
        graph.selectedNodeId = graph.selectedNodeId === clicked.id ? null : clicked.id;
        if (graph.selectedNodeId) recordObserverUsage(observerUsage, 'selection');
        const graphCanvas = document.getElementById('mind-cognition-canvas');
        if (graphCanvas) initGraphPhysics(graphCanvas.width || 900, graphCanvas.height || 600);
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.08);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      } else if (clickedRegion) {
        recordObserverUsage(observerUsage, 'region-focus');
        graph.focusedSectorId = graph.focusedSectorId === clickedRegion.id
          ? null
          : clickedRegion.id;
        graph.selectedNodeId = null;
        graph.autoFramePending = true;
        graph.manualViewOverride = false;
        renderCognitionInspector();
        graph.alpha = Math.max(graph.alpha, 0.12);
        if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
      } else if (!pressedNode && dragDist < 5) {
        graph.selectedNodeId = null;
        graph.focusedSectorId = null;
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
  
  function inspectorGroup(parent, title, open = true) {
    const group = document.createElement('details');
    group.open = open;
    group.style.cssText = 'margin:9px 0;border-top:1px solid rgba(98,120,136,.14);padding-top:4px;';
    const summary = document.createElement('summary');
    summary.textContent = title;
    summary.style.cssText = 'cursor:pointer;font-size:9px;font-weight:650;color:var(--text);padding:4px 0;';
    group.appendChild(summary);
    parent.appendChild(group);
    return group;
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
      const identityGroup = inspectorGroup(panel, 'Identity', true);
      const topologyGroup = inspectorGroup(panel, 'Topology', true);
      const dynamicsGroup = inspectorGroup(panel, 'Dynamics', false);
      const roleGroup = inspectorGroup(panel, 'Role', true);
      const relationsGroup = inspectorGroup(panel, 'Relations & pathway', true);
  
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
      inspectorMetric(identityGroup, 'Self label', selected.id, PAL.violet);
      inspectorMetric(
        identityGroup,
        displayedSemantic.kind === 'exact-source'
          ? 'Observer truth'
          : displayedSemantic.kind === 'composition'
            ? 'Observer composition'
            : 'Observer context',
        displayedSemantic.summary ?? 'unresolved',
        displayedSemantic.summary ? PAL.cyan : PAL.muted,
      );
      inspectorMetric(
        identityGroup,
        'Semantic relation',
        displayedSemantic.kind === 'exact-source'
          ? 'exact source mapping'
          : displayedSemantic.kind === 'composition'
            ? 'physical composition only'
            : displayedSemantic.kind === 'sensory-context'
              ? `linked within ${displayedSemantic.distance} hops`
              : 'unresolved',
      );
      inspectorMetric(identityGroup, 'Kind', selected.kind);
      if (selected.kind === 'motor_primitive') {
        inspectorMetric(roleGroup, 'Cognitive reuse', selected.cognitivePrimitive ? 'eligible' : 'not yet');
        inspectorMetric(roleGroup, 'Samples', selected.samples);
        inspectorMetric(roleGroup, 'Controllability', selected.controllability.toFixed(4), PAL.mint);
        inspectorMetric(roleGroup, 'Directional consistency', pct(selected.directionalConsistency));
        inspectorMetric(roleGroup, 'Effect variance', selected.effectVariance.toFixed(4));
        inspectorMetric(roleGroup, 'Actuators', selected.actuatorIds.length);
        inspectorMetric(roleGroup, 'Replay', selected.replayActive ? 'active now' : 'inactive', selected.replayActive ? PAL.mint : PAL.muted);
      }
      if (selected.kind === 'actuator') {
        inspectorMetric(roleGroup, 'Observer effector', selected.observerLabel ?? 'unresolved', PAL.cyan);
        inspectorMetric(roleGroup, 'Motor repertoire', selected.activeRepertoire ? 'active' : 'not promoted');
        inspectorMetric(roleGroup, 'Effect strength', selected.effectStrength.toFixed(3), PAL.mint);
        inspectorMetric(roleGroup, 'Effect relations', selected.causalRelationCount);
        inspectorMetric(roleGroup, 'Activations observed', selected.activations);
      }
      inspectorMetric(topologyGroup, 'Degree', selected.neighbors?.size ?? 0);
      inspectorMetric(dynamicsGroup, 'Activity', pct(selected.activationLevel ?? 0), PAL.cyan);
      inspectorMetric(topologyGroup, 'Structural importance', pct(selected.structuralImportance ?? selected.visualValue ?? 0));
      inspectorMetric(topologyGroup, 'Component', selected.isolated ? 'unintegrated' : `#${(selected.componentRank ?? 0) + 1} · ${selected.componentSize ?? 1} nodes`);
      inspectorMetric(topologyGroup, 'Sector', selected.community && selected.community !== 'isolated'
        ? (graph.sectorLabels.get(selected.community) ?? 'unresolved')
        : 'none');
      inspectorMetric(topologyGroup, 'Inbound / outbound', `${facts.inbound.length} / ${facts.outbound.length}`);
      inspectorMetric(topologyGroup, `Within ${graph.pathDepth} hops`, facts.localIds.size);
      inspectorMetric(
        roleGroup,
        'Motor path nearby',
        facts.reachesMotor ? 'yes' : 'no',
        facts.reachesMotor ? PAL.mint : PAL.muted,
      );
      const structureRoles = [];
      if ((graph.cognitiveStructures?.hubs ?? []).some(item => item.id === selected.id)) {
        structureRoles.push('hub');
      }
      if ((graph.cognitiveStructures?.bottlenecks ?? []).some(item => item.id === selected.id)) {
        structureRoles.push('bottleneck');
      }
      const loopCount = (graph.cognitiveStructures?.loops ?? [])
        .filter(loop => loop.includes(selected.id))
        .length;
      if (loopCount) structureRoles.push(`${loopCount} recurrent loop${loopCount === 1 ? '' : 's'}`);
      const flowCount = (graph.observedFlow?.paths ?? [])
        .filter(path => path.nodeIds.includes(selected.id))
        .length;
      inspectorMetric(
        roleGroup,
        'Higher-order role',
        structureRoles.length ? structureRoles.join(' · ') : 'none detected',
        structureRoles.length ? PAL.amber : PAL.muted,
      );
      inspectorMetric(
        roleGroup,
        'Recent flow paths',
        flowCount,
        flowCount ? PAL.cyan : PAL.muted,
      );
      if (selected.errorCls) inspectorMetric(dynamicsGroup, 'Prediction error', selected.errorCls, PAL.coral);
      if (selected.readoutVal != null) inspectorMetric(dynamicsGroup, 'Readout', selected.readoutVal, PAL.mint);
  
      const relTitle = el('div', '');
      relTitle.style.cssText = 'margin:13px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      relTitle.textContent = 'Direct relations';
      relationsGroup.appendChild(relTitle);
  
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
        relationsGroup.appendChild(empty);
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
          relationsGroup.appendChild(row);
        }
      }
  
      if (graph.atlasPath?.nodeIds?.length > 1) {
        const pathTitle = el('div', '');
        pathTitle.style.cssText = 'margin:13px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
        pathTitle.textContent = 'Cognitive pathway';
        relationsGroup.appendChild(pathTitle);

        const pathCopy = el('div', '');
        pathCopy.style.cssText = 'font-size:8px;line-height:1.5;color:var(--muted);margin-bottom:6px;';
        pathCopy.textContent = graph.atlasPath.nodeIds
          .map(id => {
            const node = graph.nodes.find(item => item.id === id);
            return node ? `${node.kind}: ${shortId(node.id, 9, 5)}` : shortId(id, 9, 5);
          })
          .join(' → ');
        relationsGroup.appendChild(pathCopy);

        for (const id of graph.atlasPath.nodeIds) {
          const node = graph.nodes.find(item => item.id === id);
          if (!node) continue;
          const row = el('button', '');
          row.type = 'button';
          row.style.cssText = 'display:block;width:100%;text-align:left;margin:3px 0;padding:5px 6px;border:1px solid rgba(80,217,255,.16);border-radius:5px;background:rgba(80,217,255,.025);color:var(--muted);font-size:8px;cursor:pointer;';
          row.textContent = `${node.kind} · ${node.observerLabel ?? shortId(node.id, 10, 5)}`;
          row.addEventListener('click', () => selectCognitiveNode(node.id));
          relationsGroup.appendChild(row);
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
      subtitle.textContent = 'Observer-side region focus. Shape and membership are derived from graph relations and are not fed back to Symbiont.';
      panel.append(title, subtitle);
  
      inspectorMetric(panel, 'Nodes', members.length);
      inspectorMetric(panel, 'Mean activity', pct(activity), PAL.cyan);
      const lineageLabel = graph.sectorLabels.get(sectorFocus.sectorId) ?? null;
      const lineage = lineageLabel ? graph.regionLineage.get(lineageLabel) : null;
      if (!graph.replaySnapshot && lineage) {
        inspectorMetric(panel, 'Region since', `t${lineage.firstTick}`);
        inspectorMetric(panel, 'Lineage observations', lineage.observations);
      }
      const regionShape = graph.dimension === '3d'
        ? graph.atlasRegionGeometry3d.get(sectorFocus.sectorId)
        : graph.atlasRegionGeometry2d.get(sectorFocus.sectorId);
      const proto = graph.protoSubregions.get(sectorFocus.sectorId) ?? [];
      if (regionShape) {
        inspectorMetric(panel, 'Boundary tension', pct(regionShape.tension ?? 0), (regionShape.tension ?? 0) > 0.6 ? PAL.amber : PAL.muted);
        inspectorMetric(panel, 'Proto-subregions', proto.length, proto.length ? PAL.violet : PAL.muted);
        inspectorMetric(panel, 'Cartographic functional center', `${regionShape.functionalCenter?.x?.toFixed?.(0) ?? '—'}, ${regionShape.functionalCenter?.y?.toFixed?.(0) ?? '—'}`);
        const trail = regionShape.trail ?? [];
        const displacement = trail.length > 1
          ? Math.hypot(
              trail[trail.length - 1].x - trail[0].x,
              trail[trail.length - 1].y - trail[0].y,
            )
          : 0;
        inspectorMetric(panel, 'Center displacement (observer layout)', displacement.toFixed(1));
      }
      inspectorMetric(panel, 'External bridge endpoints', sectorFocus.bridges.size);
      inspectorMetric(panel, 'Cross-region relations', bridgeEdges.length);
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
      bridgeTitle.textContent = 'Corridors to other regions';
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
      back.textContent = 'Back to all regions';
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
    title.textContent = 'Cognitive Atlas';
    const subtitle = el('div', '');
    subtitle.style.cssText = 'font-size:9px;line-height:1.45;color:var(--muted);margin-bottom:10px;';
    subtitle.textContent = `${atlasModeMeta().label} · ${atlasModeMeta().description}. Regions are observer-derived from graph relations and never fed back to Symbiont.`;
    panel.append(title, subtitle);

    const situation = graph.cognitiveSituation;
    if (situation) {
      const situationTitle = el('div', '');
      situationTitle.style.cssText = 'margin:4px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      situationTitle.textContent = 'Current observed process';
      panel.appendChild(situationTitle);

      const stageWrap = el('div', '');
      stageWrap.style.cssText = 'display:grid;gap:4px;margin-bottom:8px;';
      for (const stage of situation.stages ?? []) {
        const ratio = stage.total ? Math.min(1, stage.active / stage.total) : 0;
        const row = el('div', '');
        row.style.cssText = 'display:grid;grid-template-columns:78px 1fr 42px;gap:6px;align-items:center;font-size:8px;color:var(--muted);';
        row.innerHTML =
          `<span>${stage.label}</span>` +
          `<span style="height:3px;background:rgba(98,120,136,.18);border-radius:2px;overflow:hidden"><i style="display:block;height:100%;width:${Math.round(ratio*100)}%;background:var(--cyan)"></i></span>` +
          `<span style="text-align:right">${stage.active}/${stage.total}</span>`;
        stageWrap.appendChild(row);
      }
      panel.appendChild(stageWrap);

      inspectorMetric(panel, 'Active regions', situation.activeRegionCount, PAL.cyan);
      inspectorMetric(panel, 'Prediction pressure', pct(situation.prediction.pressure), situation.prediction.pressure > 0.5 ? PAL.amber : PAL.muted);
      inspectorMetric(panel, 'Learning zones', situation.learning.zones, situation.learning.zones ? PAL.amber : PAL.muted);
      inspectorMetric(panel, 'Recent relation coverage', pct(situation.flow.relationCoverage), PAL.cyan);
      inspectorMetric(panel, 'Observed motor paths', situation.flow.motorPaths, situation.flow.motorPaths ? PAL.mint : PAL.muted);
      inspectorMetric(panel, 'Motor origin', situation.motorOrigin ?? 'none');

      const evidenceNote = el('div', '');
      evidenceNote.style.cssText = 'margin:8px 0 10px;padding:7px;border:1px solid rgba(98,120,136,.14);border-radius:6px;font-size:8px;line-height:1.4;color:var(--muted);';
      evidenceNote.textContent =
        'Observer evidence only · no inferred intent · no feedback to Symbiont.';
      panel.appendChild(evidenceNote);
    }
  
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
        const atlasRegion = (graph.atlasRegions ?? []).find(region => region.id === id) ?? null;
        return { id, ids, sectorNodes, kinds, activity, atlasRegion };
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
      const regionScore = atlasRegionScore(sector.atlasRegion);
      activity.textContent = `${atlasModeMeta().label.toLowerCase()} ${pct(regionScore)} · activity ${pct(sector.activity)} · ${sector.atlasRegion?.bridges ?? 0} bridges`;
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
  
    const structures = graph.cognitiveStructures ?? { hubs: [], bottlenecks: [], loops: [] };
    const structuresTitle = el('div', '');
    structuresTitle.style.cssText = 'margin:14px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
    structuresTitle.textContent = 'Higher-order structures';
    panel.appendChild(structuresTitle);

    const structureSummary = el('div', '');
    structureSummary.style.cssText = 'font-size:8px;line-height:1.5;color:var(--muted);';
    structureSummary.innerHTML =
      `<strong style="color:var(--text)">${structures.hubs.length}</strong> hubs · ` +
      `<strong style="color:var(--text)">${structures.bottlenecks.length}</strong> bottlenecks · ` +
      `<strong style="color:var(--text)">${structures.loops.length}</strong> recurrent loops`;
    panel.appendChild(structureSummary);

    for (const item of structures.hubs.slice(0, 3)) {
      const row = el('button', '');
      row.type = 'button';
      row.style.cssText = 'display:flex;width:100%;justify-content:space-between;padding:4px 0;border:0;background:transparent;color:var(--muted);font-size:8px;cursor:pointer;text-align:left;';
      row.innerHTML = `<span>hub · <strong style="color:var(--text)">${shortId(item.id, 10, 5)}</strong></span><span>degree ${item.degree}</span>`;
      row.addEventListener('click', () => selectCognitiveNode(item.id));
      panel.appendChild(row);
    }

    const flow = graph.observedFlow ?? { paths: [], recentEdgeCount: 0, windowTicks: 48 };
    const flowTitle = el('div', '');
    flowTitle.style.cssText = 'margin:14px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
    flowTitle.textContent = 'Observed cognitive flow';
    panel.appendChild(flowTitle);
    const flowSummary = el('div', '');
    flowSummary.style.cssText = 'font-size:8px;line-height:1.45;color:var(--muted);';
    flowSummary.textContent =
      `${flow.recentEdgeCount} relations used within ${flow.windowTicks} ticks · ${flow.paths.length} observed paths`;
    panel.appendChild(flowSummary);
    for (const path of flow.paths.slice(0, 3)) {
      const row = el('div', '');
      row.style.cssText = 'padding:4px 0;border-top:1px solid rgba(98,120,136,.10);font-size:8px;color:var(--muted);line-height:1.35;';
      row.textContent = path.nodeIds
        .slice(0, 6)
        .map(id => shortId(id, 7, 4))
        .join(' → ') + (path.nodeIds.length > 6 ? ' → …' : '');
      panel.appendChild(row);
    }

    if ((graph.cognitiveEpisodes ?? []).length) {
      const episodeTitle = el('div', '');
      episodeTitle.style.cssText = 'margin:14px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      episodeTitle.textContent = 'Recent Cognitive Episodes';
      panel.appendChild(episodeTitle);
      for (const episode of graph.cognitiveEpisodes.slice(-3).reverse()) {
        const row = el('div', '');
        row.style.cssText = 'padding:5px 0;border-top:1px solid rgba(98,120,136,.10);font-size:8px;color:var(--muted);line-height:1.4;';
        const totals = episode.totals ?? {};
        const context = episode.context ?? {};
        row.innerHTML =
          `<strong style="color:var(--text)">t${episode.startTick}–t${episode.endTick}</strong> · ` +
          `${episode.events.length} windows<br>` +
          `+${totals.addedNodes ?? 0}/-${totals.removedNodes ?? 0} nodes · ` +
          `+${totals.addedEdges ?? 0}/-${totals.removedEdges ?? 0} relations` +
          (context.motorOrigins?.length ? `<br>motor: ${context.motorOrigins.join(' → ')}` : '');
        panel.appendChild(row);
      }
    }

    if (graph.atlasDiff) {
      const diff = graph.atlasDiff;
      const diffTitle = el('div', '');
      diffTitle.style.cssText = 'margin:14px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      diffTitle.textContent = `Diff from t${graph.diffBaselineTick ?? '—'}`;
      panel.appendChild(diffTitle);
      const diffSummary = el('div', '');
      diffSummary.style.cssText = 'font-size:8px;line-height:1.45;color:var(--muted);';
      const diffInsight = summarizeDiff(diff, graph.nodes, graph.atlasRegions);
      diffSummary.innerHTML =
        `+${diff.addedNodes.length} nodes · -${diff.removedNodes.length} nodes · +${diff.addedEdges.length} relations · -${diff.removedEdges.length} relations · ${diff.changedEdges.length} changed` +
        (diffInsight?.topRegion ? `<br>top changed region: <strong style="color:var(--text)">${diffInsight.topRegion.label ?? diffInsight.topRegion.id}</strong>` : '') +
        (diffInsight?.topNode ? `<br>most changed node: <strong style="color:var(--text)">${shortId(diffInsight.topNode.id, 10, 5)}</strong>` : '') +
        `<br>largest delta type: <strong style="color:var(--text)">${diffInsight?.largestDeltaType ?? 'none'}</strong>` +
        `<br>cognition→motor linkage changed: <strong style="color:var(--text)">${diffInsight?.motorLinkageChanged ? 'yes' : 'no'}</strong>`;
      panel.appendChild(diffSummary);
    }

    if ((graph.regionEventHistory ?? []).length) {
      const regionTitle = el('div', '');
      regionTitle.style.cssText = 'margin:14px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      regionTitle.textContent = 'Region lineage';
      panel.appendChild(regionTitle);
      for (const event of graph.regionEventHistory.slice(-5).reverse()) {
        const row = el('div', '');
        row.style.cssText = 'padding:4px 0;border-top:1px solid rgba(98,120,136,.10);font-size:8px;color:var(--muted);';
        const detail =
          event.type === 'region-split' ? ` → ${(event.into ?? []).join(', ')}` :
          event.type === 'region-merged' ? ` ← ${(event.from ?? []).join(', ')}` :
          '';
        row.textContent = `t${event.tick} · ${event.label} · ${event.type.replace('region-', '')}${detail}`;
        panel.appendChild(row);
      }
    }

    if ((graph.learningFrontierClusters ?? []).length) {
      const frontierTitle = el('div', '');
      frontierTitle.style.cssText = 'margin:14px 0 6px;font-size:9px;font-weight:650;color:var(--text);';
      frontierTitle.textContent = 'Learning frontier zones';
      panel.appendChild(frontierTitle);
      for (const cluster of graph.learningFrontierClusters.slice(0, 5)) {
        const block = el('div', '');
        block.style.cssText = 'padding:6px 0;border-top:1px solid rgba(98,120,136,.12);font-size:8px;line-height:1.4;color:var(--muted);';
        block.innerHTML =
          `<strong style="color:var(--text)">${cluster.nodeIds.length} learning nodes</strong> · ` +
          `peak ${Math.round(cluster.maxScore * 100)}% · mean ${Math.round(cluster.meanScore * 100)}%<br>` +
          `${cluster.boundaryIds.length} boundary contacts · ${cluster.communities.length} regions · ` +
          `${cluster.observations ?? 1} observations<br>` +
          `+${cluster.enteredIds?.length ?? 0} entered · -${cluster.exitedIds?.length ?? 0} exited · continuity ${Math.round((cluster.previousOverlap ?? 0) * 100)}%`;
        panel.appendChild(block);
        for (const id of cluster.nodeIds.slice(0, 3)) {
          const node = graph.nodes.find(item => item.id === id);
          if (!node) continue;
          const row = el('button', '');
          row.type = 'button';
          row.style.cssText = 'display:block;width:100%;text-align:left;padding:3px 5px;margin-top:2px;border:0;background:rgba(255,189,84,.025);color:var(--muted);font-size:8px;cursor:pointer;';
          row.textContent = `${node.kind} · ${node.observerLabel ?? shortId(node.id, 10, 5)}`;
          row.addEventListener('click', () => selectCognitiveNode(node.id));
          panel.appendChild(row);
        }
      }
    }

    const usage = el('div', '');
    usage.style.cssText = 'margin-top:12px;padding-top:8px;border-top:1px solid rgba(98,120,136,.12);font-size:8px;line-height:1.45;color:var(--muted);';
    const topMode = Object.entries(observerUsage.modeChanges ?? {})
      .sort((a,b) => b[1] - a[1])[0];
    usage.textContent =
      `observer use · selections ${observerUsage.selections} · regions ${observerUsage.regionFocuses} · timeline ${observerUsage.timelineScrubs} · diff ${observerUsage.diffUses} · traces ${observerUsage.flowTraces}` +
      (topMode ? ` · top mode ${topMode[0]}` : '');
    panel.appendChild(usage);

    const hint = el('div', '');
    hint.style.cssText = 'margin-top:12px;padding:8px;border:1px solid rgba(80,217,255,.14);border-radius:6px;font-size:8px;line-height:1.45;color:var(--muted);';
    hint.textContent = 'Region → local graph → node → exact evidence. Select a node to reveal a real cognitive pathway when one exists.';
    panel.appendChild(hint);
  }
  
  function syncAtlasModeButtons() {
    document.querySelectorAll('[data-atlas-mode]').forEach(button => {
      button.classList.toggle('active', button.dataset.atlasMode === graph.atlasMode);
    });
  }

  function updateTimelineControls() {
    const input = document.getElementById('mind-atlas-timeline');
    const label = document.getElementById('mind-atlas-timeline-label');
    const diffBtn = document.getElementById('mind-atlas-diff-btn');
    const liveBtn = document.getElementById('mind-atlas-timeline-live');
    if (!input || !label) return;

    const count = historySnapshots.length;
    input.min = '0';
    input.max = String(Math.max(0, count - 1));
    input.disabled = count < 2;

    if (graph.replaySnapshot) {
      if (graph.timelineIndex == null && graph.replayTick != null) {
        const replayIndex = historySnapshots.findIndex(item => item.tick === graph.replayTick);
        if (replayIndex >= 0) graph.timelineIndex = replayIndex;
      }
      input.value = String(Math.max(0, Math.min(count - 1, graph.timelineIndex ?? 0)));
      label.textContent = `timeline · t${graph.replayTick ?? '—'}`;
    } else {
      input.value = String(Math.max(0, count - 1));
      label.textContent = `timeline · LIVE${count ? ` · ${count} captures` : ''}`;
    }

    if (diffBtn) {
      diffBtn.classList.toggle('active', Boolean(graph.diffBaselineSnapshot));
      diffBtn.title = graph.diffBaselineSnapshot
        ? `Diff baseline t${graph.diffBaselineTick} · click to clear`
        : 'Compare against previous captured snapshot';
    }
    if (liveBtn) liveBtn.classList.toggle('active', !graph.replaySnapshot);
  }

  function replayHistoryIndex(index) {
    if (!historySnapshots.length) return;
    recordObserverUsage(observerUsage, 'timeline');
    const bounded = Math.max(0, Math.min(historySnapshots.length - 1, Number(index) || 0));
    const item = historySnapshots[bounded];
    if (!item?.snapshot?.topology) return;
    graph.timelineIndex = bounded;
    graph.replaySnapshot = item.snapshot;
    graph.replayTick = item.tick;
    graph.cachedPositions.clear();
    graph.world3d.clear();
    graph.velocity3d.clear();
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
    updateTimelineControls();
    updateCognitionSummary();
    renderCognitionInspector();
  }

  function toggleDiffBaseline() {
    recordObserverUsage(observerUsage, 'diff');
    if (graph.diffBaselineSnapshot) {
      graph.diffBaselineSnapshot = null;
      graph.diffBaselineTick = null;
      graph.atlasDiff = null;
      if (graph.atlasMode === 'diff') graph.atlasMode = 'structure';
      syncAtlasModeButtons();
    } else if (historySnapshots.length >= 2) {
      const currentIndex = graph.timelineIndex != null
        ? graph.timelineIndex
        : historySnapshots.length;
      const baselineIndex = currentIndex - 1;
      if (baselineIndex < 0 || baselineIndex >= historySnapshots.length) return;
      const baseline = historySnapshots[baselineIndex];
      graph.diffBaselineSnapshot = baseline?.snapshot ?? null;
      graph.diffBaselineTick = baseline?.tick ?? null;
      if (graph.diffBaselineSnapshot) graph.atlasMode = 'diff';
      syncAtlasModeButtons();
    }
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
    updateTimelineControls();
    updateCognitionSummary();
    renderCognitionInspector();
  }

  function updateCognitionSummary() {
    updateTimelineControls();
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
        String(edge.sourceId ?? '').startsWith('readout_motor:') ||
        String(edge.sourceId ?? '').startsWith('readout_primitive:')
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
      `<strong style="color:var(--text)">Cognitive Observatory · Atlas${replayLabel}${projectionLabel}${sectorFocusLabel}</strong><br>` +
      `${current.concepts} concepts · ${current.predictors} predictors · ${current.primitives} motor primitives (${current.cognitivePrimitives} reusable)<br>` +
      `<span style="color:var(--muted)">${current.edges} learned relations · ${current.cognitiveMotorLinks} readout→motor links</span><br>` +
      `<span style="color:var(--muted)">mode ${atlasModeMeta().label} · detail ${graph.detailLevel} · ${(graph.atlasRegions ?? []).length} emergent regions · physical actuators hidden</span><br>` +
      `<span style="color:var(--muted)">components ${components.count} · main ${components.main} · secondary ${components.secondary} · unintegrated ${components.isolates}</span><br>` +
      `<span style="color:var(--muted)">higher-order ${graph.cognitiveStructures?.hubs?.length ?? 0} hubs · ${graph.cognitiveStructures?.bottlenecks?.length ?? 0} bottlenecks · ${graph.cognitiveStructures?.loops?.length ?? 0} loops · flow ${graph.observedFlow?.recentEdgeCount ?? 0} recent relations</span><br>` +
      `<span style="color:var(--muted)">temporal ${graph.cognitiveEpisodes?.length ?? 0} episodes · ${graph.regionEventHistory?.length ?? 0} region events${graph.diffBaselineTick != null ? ` · diff baseline t${graph.diffBaselineTick}` : ''}</span><br>` +
      `<span style="color:var(--muted)">Δ since t${baseline.tick}: ${sign(current.concepts-baseline.concepts)} C · ${sign(current.predictors-baseline.predictors)} P · frontier ${(graph.learningFrontierClusters ?? []).length} zones / ${(graph.learningFrontier ?? []).length} nodes</span><br>` +
      `<span style="color:${current.cognitiveMotorLinks > 0 ? 'var(--mint)' : 'var(--muted)'}">${current.cognitiveMotorLinks > 0 ? 'cognition→motor linkage present' : 'motor learning exists outside cognitive control'} · motor origin ${tel.motorOrigin ?? '—'}</span>`;
  }

  function invalidateProjectedRegionHistory3D() {
    graph.regionShapeHistory3d.clear();
    graph.regionCenterTrails3d.clear();
  }

  function setDimension(dimension) {
    graph.dimension = dimension;
    recordObserverUsage(observerUsage, 'dimension', dimension);
    graph.autoFramePending = true;
    graph.manualViewOverride = false;
    if (dimension === '3d') {
      invalidateProjectedRegionHistory3D();
      ensure3DState(graph.nodes, graph.edges, graph.world3d, graph.velocity3d);
    }
    const note = document.getElementById('mind-cognition-3d-note');
    if (note && dimension !== '3d') note.textContent = '2D observer cartography';
    graph.alpha = Math.max(graph.alpha, 0.18);
    if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
  }

  function set3DMode(mode) {
    if (!['relational','physicalized'].includes(mode)) return;
    graph.threeDMode = mode;
    invalidateProjectedRegionHistory3D();
    graph.alpha = Math.max(graph.alpha, 0.35);
    if (graph.dimension !== '3d') graph.dimension = '3d';
    if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
  }

  function setViewMode(mode) {
    graph.viewMode = mode;
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
    renderCognitionInspector();
  }

  function setAtlasMode(mode) {
    if (!ATLAS_MODES.some(item => item.id === mode)) return;
    if (mode === 'diff' && !graph.diffBaselineSnapshot) {
      if (historySnapshots.length < 2) {
        syncAtlasModeButtons();
        return;
      }
      const currentIndex = graph.timelineIndex != null
        ? graph.timelineIndex
        : historySnapshots.length;
      const baselineIndex = currentIndex - 1;
      if (baselineIndex < 0 || baselineIndex >= historySnapshots.length) {
        syncAtlasModeButtons();
        return;
      }
      graph.diffBaselineSnapshot = historySnapshots[baselineIndex]?.snapshot ?? null;
      graph.diffBaselineTick = historySnapshots[baselineIndex]?.tick ?? null;
    }
    graph.atlasMode = mode;
    recordObserverUsage(observerUsage, 'mode', mode);
    graph.viewMode = 'full';
    syncAtlasModeButtons();
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
    updateTimelineControls();
    updateCognitionSummary();
    renderCognitionInspector();
    graph.alpha = Math.max(graph.alpha, 0.22);
    if (!rafId) rafId = requestAnimationFrame(cognitionAnimLoop);
  }

  function returnLive() {
    graph.replaySnapshot = null;
    graph.replayTick = null;
    graph.timelineIndex = null;
    updateTimelineControls();
    updateCognitionSummary();
    const canvas = document.getElementById('mind-cognition-canvas');
    if (canvas) initGraphPhysics(canvas.width || 900, canvas.height || 600);
    renderCognitionInspector();
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
    set3DMode,
    setViewMode,
    setAtlasMode,
    start: startCognitionGraph,
    stop,
    updateSummary: updateCognitionSummary,
  };
}
