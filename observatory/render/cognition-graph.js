import { state } from "../state/store.js";
import { renderInspector } from "./inspector.js";

let animFrameId = null;
let isSimulating = false;
let alpha = 1.0;
const ALPHA_MIN = 0.001;
const ALPHA_DECAY = 0.985;

// Physics parameters
const REPULSION = 7500;
const SPRING_K = 0.045;
const SPRING_LENGTH = 80;
const CENTER_GRAVITY = 0.015;
const DAMPING = 0.86;

// View transform (pan & zoom)
let scale = 1.0;
let panX = 0;
let panY = 0;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;

// Dragging & Hover state
let isDragging = false;
let draggedNode = null;
let hoveredNode = null;
let dragDist = 0;

// Graph model cache
let cachedNodes = new Map();
let currentNodes = [];
let currentEdges = [];
let lastTopologyRevision = null;
let lastDisplayId = null;
let fmriEnabled = true;

function hashStr(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function makeDemoGraph() {
  const nodes = [];
  const edges = [];
  const nodeMap = new Map();

  // Senses
  (state.senses ?? []).forEach((sense, idx) => {
    const node = {
      id: sense.id,
      label: sense.name,
      kind: "sense",
      active: sense.active,
      quality: sense.quality,
      dev: {
        tier: sense.active ? (idx === 1 ? "probing" : "active") : "dormant",
        utility: sense.quality ? sense.quality * 0.35 : 0.05,
        samples: Math.floor((sense.quality || 0.3) * 350) + 40,
        availability: sense.quality || 0.5,
      },
      topRelation: idx === 0 ? {
        senseA: sense.id,
        senseB: "storage_pressure",
        synchronous: 0.86,
        aToB: 0.74,
        samples: 48,
      } : (idx === 1 ? {
        senseA: sense.id,
        senseB: "system_load",
        synchronous: -0.62,
        aToB: -0.58,
        samples: 36,
      } : null),
      inboundCount: 0,
      outboundCount: 2,
    };
    nodes.push(node);
    nodeMap.set(node.id, node);
  });

  // Concepts from beliefs
  (state.beliefs ?? []).slice(0, 16).forEach((belief, i) => {
    const errClasses = ["zero", "trace", "low", "medium", "high"];
    const node = {
      id: belief.id,
      label: belief.title,
      kind: "concept",
      dissent: belief.dissent,
      evidence: belief.evidence,
      certainty: belief.certainty,
      errorCls: belief.dissent ? "high" : errClasses[i % 4],
      inboundCount: (i % 3) + 2,
      outboundCount: 1,
    };
    nodes.push(node);
    nodeMap.set(node.id, node);
  });

  // Readouts
  const readouts = [
    { id: "readout_motor", label: "Motor activity", kind: "readout", readoutVal: "0.45", inboundCount: 3, outboundCount: 0 },
    { id: "readout_attention", label: "Attention focus", kind: "readout", readoutVal: "0.78", inboundCount: 4, outboundCount: 0 },
    { id: "readout_homeostasis", label: "Homeostasis", kind: "readout", readoutVal: "0.91", inboundCount: 4, outboundCount: 0 },
  ];
  readouts.forEach(r => {
    nodes.push(r);
    nodeMap.set(r.id, r);
  });

  // Edges: link senses to concepts
  nodes.filter(n => n.kind === "sense").forEach((sense, idx) => {
    const targetConcepts = nodes.filter(n => n.kind === "concept").slice(idx * 2, idx * 2 + 3);
    targetConcepts.forEach((c, cIdx) => {
      edges.push({
        sourceId: sense.id,
        targetId: c.id,
        kind: cIdx % 3 === 1 ? "inhibitory" : "excitatory",
      });
    });
  });

  // Edges: interconnect concepts
  const concepts = nodes.filter(n => n.kind === "concept");
  concepts.forEach((c, i) => {
    const next = concepts[(i + 3) % concepts.length];
    if (next && next.id !== c.id) {
      edges.push({
        sourceId: c.id,
        targetId: next.id,
        kind: i % 4 === 0 ? "modulatory" : (i % 3 === 0 ? "inhibitory" : "excitatory"),
      });
    }
  });

  // Edges: link concepts to readouts
  readouts.forEach((ro, roIdx) => {
    const sources = concepts.slice(roIdx * 4, roIdx * 4 + 4);
    sources.forEach(src => {
      edges.push({
        sourceId: src.id,
        targetId: ro.id,
        kind: "excitatory",
      });
    });
  });

  nodes.forEach(n => {
    const inE = edges.filter(e => e.targetId === n.id);
    n.inboundKinds = inE.map(e => e.kind);
  });

  return { nodes, edges };
}

function extractGraphData() {
  const hasTopology = Boolean(state.topology && Array.isArray(state.topology.nodes) && state.topology.nodes.length > 0);
  if (hasTopology) {
    const errors = state.cognition?.predictionErrors ?? {};
    const readouts = state.cognition?.readouts ?? {};
    const rawEdges = state.topology.edges ?? [];
    const devRecords = state.sensoryDevelopment ?? [];
    const relRecords = state.sensoryRelations ?? [];

    const nodes = state.topology.nodes.map(n => {
      const dev = devRecords.find(d => d.name === n.id);
      const rels = relRecords.filter(r => r.senseA === n.id || r.senseB === n.id);
      const inEdges = rawEdges.filter(e => e.targetId === n.id);
      const inCount = inEdges.length;
      const outCount = rawEdges.filter(e => e.sourceId === n.id).length;

      return {
        id: n.id,
        label: n.id,
        kind: n.kind ?? "concept",
        errorCls: errors[n.id] ?? null,
        readoutVal: readouts[n.id] != null ? Number(readouts[n.id]).toFixed(2) : null,
        dev: dev || null,
        relations: rels,
        topRelation: rels[0] || null,
        inboundCount: inCount,
        inboundKinds: inEdges.map(e => e.kind ?? "excitatory"),
        outboundCount: outCount,
      };
    });
    const edges = rawEdges.map(e => ({
      sourceId: e.sourceId,
      targetId: e.targetId,
      kind: e.kind ?? "excitatory",
    }));
    return { nodes, edges };
  }

  if (state.source === "demo") {
    return makeDemoGraph();
  }

  return { nodes: [], edges: [] };
}

function updateGraphModel(width, height) {
  const { nodes: rawNodes, edges: rawEdges } = extractGraphData();
  const currentRevision = state.topology?.topologyRevision ?? 0;
  const currentDisplay = state.displayId ?? state.instanceId ?? "demo";

  if (currentRevision !== lastTopologyRevision || currentDisplay !== lastDisplayId) {
    lastTopologyRevision = currentRevision;
    lastDisplayId = currentDisplay;
    reheat(0.8);
  }

  const cx = width / 2;
  const cy = height / 2;
  const nodeMap = new Map();

  currentNodes = rawNodes.map((raw, index) => {
    let node = cachedNodes.get(raw.id);
    if (!node) {
      const angle = (index * 2.399) + Math.random() * 0.5;
      const radius = 60 + (index % 7) * 35;
      node = {
        ...raw,
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        pinned: false,
      };
      cachedNodes.set(raw.id, node);
    } else {
      Object.assign(node, raw);
    }

    // Assign radius and color by kind and learned dynamics
    if (node.kind === "sense") {
      const util = node.dev ? node.dev.utility : (node.quality ? node.quality * 0.4 : 0.2);
      const tier = node.dev ? node.dev.tier : (node.active ? "active" : "dormant");
      node.radius = 5.5 + Math.min(13, util * 28);
      if (tier === "active") {
        node.color = "#50d9ff";
      } else if (tier === "probing") {
        node.color = "#ffbd54";
      } else {
        node.color = "#48627b";
      }
    } else if (node.kind === "readout") {
      node.radius = 10.0;
      node.color = "#71e9ba";
    } else if (node.kind === "motor") {
      node.radius = 8.5;
      node.color = "#ffbd54";
    } else {
      // Concept
      const inCount = node.inboundCount ?? 1;
      node.radius = 5.5 + Math.min(7.5, inCount * 1.2);
      node.color = "#a777ff";
    }

    nodeMap.set(node.id, node);
    return node;
  });

  currentEdges = rawEdges
    .map(e => ({
      source: nodeMap.get(e.sourceId),
      target: nodeMap.get(e.targetId),
      kind: e.kind,
    }))
    .filter(e => e.source && e.target);
}

function stepPhysics(width, height) {
  const n = currentNodes.length;
  if (n === 0) return;
  const cx = width / 2;
  const cy = height / 2;

  // 1. Repulsion (pairwise)
  for (let i = 0; i < n; i++) {
    const na = currentNodes[i];
    for (let j = i + 1; j < n; j++) {
      const nb = currentNodes[j];
      const dx = nb.x - na.x;
      const dy = nb.y - na.y;
      const distSq = dx * dx + dy * dy + 100;
      if (distSq > 360000) continue;
      const dist = Math.sqrt(distSq);
      const force = (REPULSION / distSq) * alpha;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (!na.pinned) { na.vx -= fx; na.vy -= fy; }
      if (!nb.pinned) { nb.vx += fx; nb.vy += fy; }
    }
  }

  // 2. Springs along edges
  for (let i = 0; i < currentEdges.length; i++) {
    const edge = currentEdges[i];
    const na = edge.source;
    const nb = edge.target;
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.hypot(dx, dy) || 1;
    const displacement = dist - SPRING_LENGTH;
    const force = displacement * SPRING_K * alpha;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    if (!na.pinned) { na.vx += fx; na.vy += fy; }
    if (!nb.pinned) { nb.vx -= fx; nb.vy -= fy; }
  }

  // 3. Gravity to center & velocity integration
  for (let i = 0; i < n; i++) {
    const node = currentNodes[i];
    if (node.pinned) continue;
    const dx = cx - node.x;
    const dy = cy - node.y;
    node.vx += dx * CENTER_GRAVITY * alpha;
    node.vy += dy * CENTER_GRAVITY * alpha;

    node.vx *= DAMPING;
    node.vy *= DAMPING;

    node.x += node.vx;
    node.y += node.vy;
  }

  // 4. Alpha decay
  alpha = Math.max(ALPHA_MIN, alpha * ALPHA_DECAY);
}

function reheat(heat = 0.5) {
  alpha = Math.max(alpha, heat);
  if (!isSimulating) {
    startAnimationLoop();
  }
}

function shortenLabel(id) {
  if (!id) return "";
  const clean = id.replace(/^(signal\.|sense\.|node\.)/, "");
  if (clean.length > 14) {
    return clean.slice(0, 6) + "…" + clean.slice(-4);
  }
  return clean;
}

function renderCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  if (currentNodes.length === 0) {
    return;
  }

  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(scale, scale);

  // Connected set when hovered or selected
  let connectedIds = null;
  const activeFocusId = hoveredNode?.id || state.selectedNodeId;
  if (activeFocusId) {
    connectedIds = new Set([activeFocusId]);
    currentEdges.forEach(e => {
      if (e.source.id === activeFocusId) connectedIds.add(e.target.id);
      if (e.target.id === activeFocusId) connectedIds.add(e.source.id);
    });
  }

  // 1. Draw Edges
  for (let i = 0; i < currentEdges.length; i++) {
    const edge = currentEdges[i];
    const isConn = activeFocusId && (edge.source.id === activeFocusId || edge.target.id === activeFocusId);
    const dimmed = activeFocusId && !isConn;

    let strokeColor;
    if (edge.kind === "inhibitory") {
      strokeColor = isConn ? "rgba(255, 127, 131, 0.95)" : (dimmed ? "rgba(255, 127, 131, 0.04)" : "rgba(255, 127, 131, 0.38)");
    } else if (edge.kind === "modulatory" || edge.kind === "predictive") {
      strokeColor = isConn ? "rgba(255, 189, 84, 0.95)" : (dimmed ? "rgba(255, 189, 84, 0.04)" : "rgba(255, 189, 84, 0.38)");
    } else {
      strokeColor = isConn ? "rgba(80, 217, 255, 0.95)" : (dimmed ? "rgba(80, 217, 255, 0.04)" : "rgba(80, 217, 255, 0.32)");
    }

    ctx.beginPath();
    ctx.moveTo(edge.source.x, edge.source.y);
    ctx.lineTo(edge.target.x, edge.target.y);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = isConn ? 2.6 : (dimmed ? 0.5 : 1.2);

    if (edge.kind === "inhibitory" || edge.kind === "modulatory") {
      ctx.setLineDash([3, 3]);
    } else {
      ctx.setLineDash([]);
    }

    if (isConn) {
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 8;
    } else {
      ctx.shadowBlur = 0;
    }

    ctx.stroke();

    // Directional arrowhead (from source to target)
    if (!dimmed && (isConn || scale >= 0.7)) {
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const dist = Math.hypot(dx, dy);
      if (dist > 16) {
        const angle = Math.atan2(dy, dx);
        const targetR = (edge.target.radius || 6) + 3;
        const tipX = edge.target.x - Math.cos(angle) * targetR;
        const tipY = edge.target.y - Math.sin(angle) * targetR;
        const arrowLen = isConn ? 6.5 : 4.5;
        ctx.fillStyle = strokeColor;
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(tipX - arrowLen * Math.cos(angle - Math.PI / 6), tipY - arrowLen * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(tipX - arrowLen * Math.cos(angle + Math.PI / 6), tipY - arrowLen * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fill();
      }
    }
  }
  ctx.setLineDash([]);
  ctx.shadowBlur = 0;

  // fMRI Synaptic Pulses along edges
  if (fmriEnabled) {
    const now = performance.now();
    for (let i = 0; i < currentEdges.length; i++) {
      const edge = currentEdges[i];
      const isConn = activeFocusId && (edge.source.id === activeFocusId || edge.target.id === activeFocusId);
      const dimmed = activeFocusId && !isConn;
      if (dimmed) continue;

      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 18) continue;

      const ux = dx / dist;
      const uy = dy / dist;
      const seed = hashStr(edge.source.id + "->" + edge.target.id);
      const speed = edge.kind === "inhibitory" ? 0.0007 : 0.0012;
      const pulsePhase = ((now * speed + (seed % 100) * 0.01) % 1.0);

      const startR = edge.source.radius || 6;
      const endR = edge.target.radius || 6;
      const usableDist = Math.max(1, dist - startR - endR);
      const currentDist = startR + usableDist * pulsePhase;

      const px = edge.source.x + ux * currentDist;
      const py = edge.source.y + uy * currentDist;

      let pulseColor = "rgba(160, 240, 255, 0.95)";
      let pulseRadius = isConn ? 3.4 : 2.5;
      if (edge.kind === "inhibitory") {
        pulseColor = "rgba(255, 140, 145, 0.95)";
        pulseRadius = isConn ? 3.0 : 2.2;
      } else if (edge.kind === "modulatory" || edge.kind === "predictive") {
        pulseColor = "rgba(255, 205, 110, 0.95)";
      }

      ctx.beginPath();
      ctx.arc(px, py, pulseRadius, 0, Math.PI * 2);
      ctx.fillStyle = pulseColor;
      ctx.shadowColor = pulseColor;
      ctx.shadowBlur = isConn ? 10 : 6;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  // 2. Draw Nodes
  for (let i = 0; i < currentNodes.length; i++) {
    const node = currentNodes[i];
    const isHovered = hoveredNode && hoveredNode.id === node.id;
    const isSelected = state.selectedNodeId && state.selectedNodeId === node.id;
    const isConn = connectedIds && connectedIds.has(node.id);
    const dimmed = activeFocusId && !isConn;

    const r = isHovered ? node.radius * 1.35 : node.radius;

    // Outer glow & base circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);

    if (isHovered) {
      ctx.fillStyle = "#ffffff";
      ctx.shadowColor = node.color;
      ctx.shadowBlur = 18;
    } else if (dimmed) {
      ctx.fillStyle = node.color;
      ctx.globalAlpha = 0.18;
      ctx.shadowBlur = 0;
    } else {
      ctx.fillStyle = node.color;
      ctx.shadowColor = node.color;
      ctx.shadowBlur = isConn ? 12 : 6;
      ctx.globalAlpha = 0.95;
    }

    ctx.fill();
    ctx.globalAlpha = 1.0;
    ctx.shadowBlur = 0;

    // Selection halo if selected
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 5, 0, Math.PI * 2);
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2.2;
      ctx.shadowColor = node.color;
      ctx.shadowBlur = 12;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Error ring if applicable
    if (node.errorCls && ["medium", "high", "extreme"].includes(node.errorCls)) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 3.5, 0, Math.PI * 2);
      ctx.strokeStyle = "#ff7f83";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([2, 2]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // fMRI Shockwave for prediction surprise / Huber error
    if (fmriEnabled && node.errorCls && ["medium", "high", "extreme"].includes(node.errorCls)) {
      const now = performance.now();
      const seed = hashStr(node.id);
      const shockProgress = ((now * 0.0011 + (seed % 50) * 0.02) % 1.0);
      const shockRadius = node.radius + shockProgress * 26;
      const shockAlpha = (1.0 - shockProgress) * (node.errorCls === "extreme" ? 0.85 : 0.6);

      ctx.beginPath();
      ctx.arc(node.x, node.y, shockRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 127, 131, ${shockAlpha.toFixed(2)})`;
      ctx.lineWidth = 1.4;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // fMRI Attention & Metabolic Breathing Halo
    if (fmriEnabled && (node.kind === "sense" && (node.dev?.tier === "active" || node.active))) {
      const now = performance.now();
      const seed = hashStr(node.id);
      const breath = Math.sin(now * 0.0024 + (seed % 10)) * 0.5 + 0.5;
      const haloRadius = node.radius + 3.5 + breath * 5.5;
      const haloAlpha = 0.15 + breath * 0.25;

      ctx.beginPath();
      ctx.arc(node.x, node.y, haloRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(80, 217, 255, ${haloAlpha.toFixed(2)})`;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }

    // Readout ring
    if (node.kind === "readout") {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 3, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(113, 233, 186, 0.7)";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
  }

  // 3. Draw Labels (Obsidian style)
  ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  for (let i = 0; i < currentNodes.length; i++) {
    const node = currentNodes[i];
    const isHovered = hoveredNode && hoveredNode.id === node.id;
    const isConn = connectedIds && connectedIds.has(node.id);
    const dimmed = activeFocusId && !isConn;

    if (dimmed) continue;

    // Hover tooltip pill
    if (isHovered) {
      const dev = node.dev;
      const title = shortenLabel(node.label || node.id);
      const lines = [
        `${title}  ·  ${node.kind.toUpperCase()}`
      ];

      if (node.kind === "sense") {
        const tier = (dev?.tier || (node.active ? "active" : "dormant")).toUpperCase();
        const util = ((dev?.utility ?? (node.quality ? node.quality * 0.4 : 0)) * 100).toFixed(1);
        const samples = dev?.samples ?? (node.quality ? Math.floor(node.quality * 300) : 0);
        lines.push(`Tier: ${tier} | Util: ${util}% | ${samples} obs`);
        if (node.topRelation) {
          const r = node.topRelation;
          if (r.aToB != null) {
            lines.push(`⚡ Anticipates ${shortenLabel(r.senseB)} (a→b: ${r.aToB.toFixed(2)})`);
          } else if (r.synchronous != null) {
            lines.push(`🔗 Correlates with ${shortenLabel(r.senseA === node.id ? r.senseB : r.senseA)} (r: ${r.synchronous.toFixed(2)})`);
          }
        }
      } else if (node.kind === "concept") {
        const inCount = node.inboundCount ?? 0;
        const outCount = node.outboundCount ?? 0;
        const err = (node.errorCls || "trace").toUpperCase();
        let archetype = "Integrador Multimodal";
        if (node.inboundKinds && node.inboundKinds.length > 0) {
          const hasExc = node.inboundKinds.includes("excitatory");
          const hasInh = node.inboundKinds.includes("inhibitory");
          const hasMod = node.inboundKinds.includes("modulatory") || node.inboundKinds.includes("predictive");
          if (hasExc && hasInh) archetype = "Detector Diferencial";
          else if (hasMod) archetype = "Compuerta Moduladora";
          else if (inCount === 1) archetype = "Transductor Directo";
        }
        lines.push(`Rol: ${archetype} | Error: ${err}`);
        lines.push(`Entradas: ${inCount} señales | Proyecciones: ${outCount}`);
      } else if (node.kind === "readout") {
        const val = node.readoutVal != null ? node.readoutVal : "0.00";
        lines.push(`Value: ${val} | Inbound: ${node.inboundCount ?? 0} concepts`);
      }

      ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      let maxW = 0;
      lines.forEach(l => {
        const w = ctx.measureText(l).width;
        if (w > maxW) maxW = w;
      });

      const padX = 10;
      const lineH = 15;
      const pillW = maxW + padX * 2;
      const pillH = lines.length * lineH + 10;
      const pillX = node.x - pillW / 2;
      const pillY = node.y - node.radius - pillH - 8;

      ctx.fillStyle = "rgba(6, 20, 34, 0.94)";
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(pillX, pillY, pillW, pillH, 6);
      ctx.fill();
      ctx.stroke();

      lines.forEach((l, idx) => {
        if (idx === 0) {
          ctx.fillStyle = "#ffffff";
          ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        } else if (idx === 1) {
          ctx.fillStyle = "rgba(175, 199, 220, 0.9)";
          ctx.font = '10.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        } else {
          ctx.fillStyle = "#ffbd54";
          ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        }
        ctx.fillText(l, node.x, pillY + 12 + idx * lineH);
      });
    } else if (isConn || scale >= 1.15 || node.kind === "readout" || node.kind === "sense") {
      const display = shortenLabel(node.label || node.id);
      ctx.fillStyle = isConn ? "#ffffff" : "rgba(175, 199, 220, 0.75)";
      ctx.fillText(display, node.x, node.y + node.radius + 10);
    }
  }

  ctx.restore();
}

function animationLoop() {
  const canvas = document.querySelector("#cognition-graph-canvas");
  if (!canvas || state.view !== "individual" || state.organismView !== "cognition") {
    isSimulating = false;
    animFrameId = null;
    return;
  }

  const width = canvas.width;
  const height = canvas.height;

  stepPhysics(width, height);
  renderCanvas(canvas);

  const shouldContinue = (alpha > ALPHA_MIN || isDragging || isPanning) || (fmriEnabled && state.playing);
  if (shouldContinue) {
    animFrameId = requestAnimationFrame(animationLoop);
  } else {
    isSimulating = false;
    animFrameId = null;
  }
}

function startAnimationLoop() {
  if (isSimulating) return;
  isSimulating = true;
  animFrameId = requestAnimationFrame(animationLoop);
}

function initCanvasSize(canvas) {
  const wrap = canvas.parentElement;
  if (!wrap) return;
  const rect = wrap.getBoundingClientRect();
  const width = Math.max(300, Math.floor(rect.width));
  const height = Math.max(300, Math.floor(rect.height));

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
    if (panX === 0 && panY === 0) {
      panX = 0;
      panY = 0;
    }
    reheat(0.5);
  }
}

function findNodeAt(mouseX, mouseY) {
  const worldX = (mouseX - panX) / scale;
  const worldY = (mouseY - panY) / scale;
  for (let i = currentNodes.length - 1; i >= 0; i--) {
    const node = currentNodes[i];
    const dist = Math.hypot(node.x - worldX, node.y - worldY);
    if (dist <= node.radius + 6) {
      return node;
    }
  }
  return null;
}

let listenersInstalled = false;

function installCanvasListeners(canvas) {
  if (listenersInstalled) return;
  listenersInstalled = true;

  canvas.addEventListener("wheel", event => {
    event.preventDefault();
    const factor = event.deltaY < 0 ? 1.12 : 0.89;
    const newScale = Math.min(5.0, Math.max(0.2, scale * factor));
    const mouseX = event.offsetX;
    const mouseY = event.offsetY;
    panX = mouseX - (mouseX - panX) * (newScale / scale);
    panY = mouseY - (mouseY - panY) * (newScale / scale);
    scale = newScale;
    reheat(0.1);
  }, { passive: false });

  canvas.addEventListener("mousedown", event => {
    if (event.button !== 0) return;
    const mouseX = event.offsetX;
    const mouseY = event.offsetY;
    const node = findNodeAt(mouseX, mouseY);
    dragDist = 0;

    if (node) {
      isDragging = true;
      draggedNode = node;
      node.pinned = true;
      node.vx = 0;
      node.vy = 0;
      reheat(0.6);
    } else {
      isPanning = true;
      panStartX = mouseX - panX;
      panStartY = mouseY - panY;
      canvas.style.cursor = "grabbing";
    }
  });

  window.addEventListener("mousemove", event => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    if (isDragging && draggedNode) {
      dragDist += Math.abs(event.movementX) + Math.abs(event.movementY);
      draggedNode.x = (mouseX - panX) / scale;
      draggedNode.y = (mouseY - panY) / scale;
      draggedNode.vx = 0;
      draggedNode.vy = 0;
      reheat(0.4);
      return;
    }

    if (isPanning) {
      panX = mouseX - panStartX;
      panY = mouseY - panStartY;
      reheat(0.1);
      return;
    }

    // Hover detection
    if (mouseX >= 0 && mouseX <= rect.width && mouseY >= 0 && mouseY <= rect.height) {
      const node = findNodeAt(mouseX, mouseY);
      if (node !== hoveredNode) {
        hoveredNode = node;
        canvas.style.cursor = hoveredNode ? "pointer" : "grab";
        reheat(0.05);
      }
    } else if (hoveredNode) {
      hoveredNode = null;
      reheat(0.05);
    }
  });

  window.addEventListener("mouseup", () => {
    if (isDragging && draggedNode) {
      draggedNode.pinned = false;
      // Click selection if minimal drag
      if (dragDist < 6) {
        state.selectedNodeId = draggedNode.id;
        state.selected = (state.beliefs ?? []).find(b => b.id === draggedNode.id || b.title === draggedNode.label) ?? null;
        const matchingSense = (state.senses ?? []).find(s => s.id === draggedNode.id);
        state.selectedSignalId = matchingSense?.knowledgeSignalId ?? null;

        document.querySelector(".inspector")?.classList.add("open");
        const deepInspector = document.querySelector("#deep-inspector");
        if (deepInspector) deepInspector.hidden = false;
        document.querySelector('.inspector-tab[data-tab="current"]')?.click();

        renderInspector();
        reheat(0.15);
      }
      draggedNode = null;
    }
    isDragging = false;
    isPanning = false;
    canvas.style.cursor = hoveredNode ? "pointer" : "grab";
  });

  // Controls
  document.querySelector("#graph-fmri-toggle")?.addEventListener("click", event => {
    fmriEnabled = !fmriEnabled;
    event.currentTarget.classList.toggle("active", fmriEnabled);
    reheat(0.15);
  });

  document.querySelector("#graph-zoom-in")?.addEventListener("click", () => {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const newScale = Math.min(5.0, scale * 1.25);
    panX = cx - (cx - panX) * (newScale / scale);
    panY = cy - (cy - panY) * (newScale / scale);
    scale = newScale;
    reheat(0.1);
  });

  document.querySelector("#graph-zoom-out")?.addEventListener("click", () => {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const newScale = Math.max(0.2, scale * 0.8);
    panX = cx - (cx - panX) * (newScale / scale);
    panY = cy - (cy - panY) * (newScale / scale);
    scale = newScale;
    reheat(0.1);
  });

  document.querySelector("#graph-reset")?.addEventListener("click", () => {
    scale = 1.0;
    panX = 0;
    panY = 0;
    reheat(0.6);
  });

  window.addEventListener("resize", () => {
    if (state.organismView === "cognition") {
      initCanvasSize(canvas);
    }
  });
}

function renderCognitionGraph() {
  const canvas = document.querySelector("#cognition-graph-canvas");
  const emptyEl = document.querySelector("#cognition-graph-empty");
  if (!canvas) return;

  initCanvasSize(canvas);
  installCanvasListeners(canvas);
  updateGraphModel(canvas.width, canvas.height);

  const hasContent = currentNodes.length > 0;
  if (emptyEl) {
    emptyEl.classList.toggle("hidden", hasContent);
  }

  reheat(0.6);
}

export { renderCognitionGraph };
