import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";

const CLUSTER_COLORS = [
  palette.cyan,
  palette.mint,
  palette.violet,
  palette.amber,
  palette.coral,
  "#7bb7ff",
  "#b8e986",
  "#d79cff",
];

// Physics constants
const REPULSION = 14000;
const SPRING_LENGTH = 110;
const SPRING_K = 0.045;
const CENTER_GRAVITY = 0.0035;
const DAMPING = 0.86;
const ALPHA_MIN = 0.001;

// Simulation & Interaction state
let cachedNodes = new Map();
let currentNodes = [];
let currentLinks = [];
let alpha = 1.0;
let animFrameId = null;
let trafficPhase = 0;
let trafficEnabled = true;
let showNiches = false;
let isDragging = false;
let draggedNode = null;
let hoveredNode = null;
let hoveredLink = null;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panX = 0;
let panY = 0;
let zoomScale = 1.0;
let lastPopulationKey = "";

function populationMembers() {
  return state.fleetConnected ? state.fleetPopulation : state.population;
}

function reheat(val = 0.8) {
  alpha = Math.max(alpha, val);
  if (!animFrameId) {
    animFrameId = requestAnimationFrame(animationLoop);
  }
}

// ---------------------------------------------------------------------------
// 1. Mini SVG renderer (for #population-mini in sidebar)
// ---------------------------------------------------------------------------
function renderMiniSvg(targetEl) {
  targetEl.replaceChildren();
  const population = populationMembers();
  const sx = 0.34;
  const sy = 0.22;

  const relationships = state.fleetConnected ? state.fleetRelationships : state.relationships;
  relationships.filter(link => link.type === state.populationMode).forEach(link => {
    const item = population.find(m => m.id === link.source);
    const other = population.find(m => m.id === link.target);
    if (!item || !other) return;
    targetEl.append(svg("line", {
      x1: item.x * sx,
      y1: item.y * sy,
      x2: other.x * sx,
      y2: other.y * sy,
      opacity: String(0.25 + link.strength * 0.65),
      class: `population-edge${link.type === "dissent" ? " dissent" : ""}`,
    }));
  });

  population.forEach(item => {
    const magnitude = state.populationMode === "knowledge" ? Math.min(1, item.knowledge / 45) : state.populationMode === "dissent" ? Math.min(1, item.contested / 5) : item.pressure;
    const modeColor = state.populationMode === "activity" ? palette.amber : state.populationMode === "dissent" ? palette.coral : CLUSTER_COLORS[item.cluster % CLUSTER_COLORS.length];
    const selectedClass = state.organismA?.id === item.id ? " selected-a" : state.organismB?.id === item.id ? " selected-b" : "";
    const node = svg("circle", {
      cx: item.x * sx,
      cy: item.y * sy,
      r: 4 + magnitude * 4,
      fill: `${modeColor}33`,
      stroke: modeColor,
      color: modeColor,
      opacity: item.liveness === "stale" ? "0.42" : "1",
      class: `population-node${selectedClass}`,
    });
    targetEl.append(node);
  });
}

// ---------------------------------------------------------------------------
// 2. Physics & Force Simulation Model
// ---------------------------------------------------------------------------
function updatePhysicsModel(width, height) {
  const population = populationMembers();
  const relationships = state.fleetConnected ? state.fleetRelationships : state.relationships;
  const key = `${population.length}-${relationships.length}-${state.fleetConnected}`;

  if (key !== lastPopulationKey) {
    lastPopulationKey = key;
    reheat(0.9);
  }

  const cx = width / 2;
  const cy = height / 2;
  const nodeMap = new Map();

  currentNodes = population.map((raw, index) => {
    let node = cachedNodes.get(raw.id);
    if (!node) {
      const angle = index * (Math.PI * 2 / Math.max(population.length, 1));
      const radius = 120 + (index % 4) * 35;
      node = {
        ...raw,
        x: raw.x || (cx + Math.cos(angle) * radius),
        y: raw.y || (cy + Math.sin(angle) * radius),
        vx: 0,
        vy: 0,
        pinned: false,
      };
      cachedNodes.set(raw.id, node);
    } else {
      Object.assign(node, raw);
    }
    nodeMap.set(node.id, node);
    return node;
  });

  currentLinks = relationships
    .map(r => ({
      ...r,
      sourceNode: nodeMap.get(r.source),
      targetNode: nodeMap.get(r.target),
    }))
    .filter(l => l.sourceNode && l.targetNode);
}

function stepPhysics(width, height) {
  const n = currentNodes.length;
  if (n === 0) return;
  const cx = width / 2;
  const cy = height / 2;

  // 1. Pairwise Repulsion (Coulomb)
  for (let i = 0; i < n; i++) {
    const na = currentNodes[i];
    for (let j = i + 1; j < n; j++) {
      const nb = currentNodes[j];
      const dx = nb.x - na.x;
      const dy = nb.y - na.y;
      const distSq = dx * dx + dy * dy + 100;
      if (distSq > 400000) continue;
      const dist = Math.sqrt(distSq);
      const force = (REPULSION / distSq) * alpha;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (!na.pinned) { na.vx -= fx; na.vy -= fy; }
      if (!nb.pinned) { nb.vx += fx; nb.vy += fy; }
    }
  }

  // 2. Spring Forces along Social Links
  for (let i = 0; i < currentLinks.length; i++) {
    const link = currentLinks[i];
    const na = link.sourceNode;
    const nb = link.targetNode;
    const dx = nb.x - na.x;
    const dy = nb.y - na.y;
    const dist = Math.hypot(dx, dy) || 1;

    // Social valence modulates spring rest length:
    // Positive/cooperative links pull closer; conflicts push further apart
    const isConflict = link.valence === "negative" || link.type === "dissent" || (link.conflicts && link.conflicts > 0);
    const targetLength = isConflict ? SPRING_LENGTH * 1.5 : SPRING_LENGTH * 0.85;
    const displacement = dist - targetLength;
    const springK = isConflict ? SPRING_K * 0.5 : SPRING_K * (0.8 + (link.strength || 0.5) * 0.4);

    const force = displacement * springK * alpha;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    if (!na.pinned) { na.vx += fx; na.vy += fy; }
    if (!nb.pinned) { nb.vx += fx; nb.vy += fy; }
  }

  // 3. Cluster Center Gravity & Centering
  // Calculate centroids of clusters
  const clusterCentroids = new Map();
  for (let i = 0; i < n; i++) {
    const node = currentNodes[i];
    const c = node.cluster ?? 0;
    if (!clusterCentroids.has(c)) {
      clusterCentroids.set(c, { sumX: 0, sumY: 0, count: 0 });
    }
    const agg = clusterCentroids.get(c);
    agg.sumX += node.x;
    agg.sumY += node.y;
    agg.count += 1;
  }

  for (let i = 0; i < n; i++) {
    const node = currentNodes[i];
    if (node.pinned) continue;

    // Gentle global pull to center
    const gdx = cx - node.x;
    const gdy = cy - node.y;
    node.vx += gdx * CENTER_GRAVITY * alpha;
    node.vy += gdy * CENTER_GRAVITY * alpha;

    // Cluster cohesion
    const c = node.cluster ?? 0;
    const agg = clusterCentroids.get(c);
    if (agg && agg.count > 1) {
      const ccx = agg.sumX / agg.count;
      const ccy = agg.sumY / agg.count;
      node.vx += (ccx - node.x) * 0.008 * alpha;
      node.vy += (ccy - node.y) * 0.008 * alpha;
    }

    node.vx *= DAMPING;
    node.vy *= DAMPING;

    node.x += node.vx;
    node.y += node.vy;

    // Boundary containment
    node.x = Math.max(50, Math.min(width - 50, node.x));
    node.y = Math.max(50, Math.min(height - 50, node.y));
  }

  alpha = Math.max(0, alpha - 0.0035);
}

// ---------------------------------------------------------------------------
// 3. Canvas 2D Live Rendering & Traffic Particles
// ---------------------------------------------------------------------------
function renderCanvasFrame(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);

  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(zoomScale, zoomScale);

  // 1. Draw Organic Ecological Cluster Hulls
  const clusters = [...new Set(currentNodes.map(item => item.cluster ?? 0))];
  clusters.forEach(cluster => {
    const members = currentNodes.filter(item => item.cluster === cluster);
    if (members.length === 0) return;

    const cx = members.reduce((sum, item) => sum + item.x, 0) / members.length;
    const cy = members.reduce((sum, item) => sum + item.y, 0) / members.length;
    let maxDist = 70;
    members.forEach(m => {
      const d = Math.hypot(m.x - cx, m.y - cy);
      if (d > maxDist) maxDist = d;
    });

    const rx = maxDist + 35;
    const ry = maxDist * 0.85 + 30;
    const col = CLUSTER_COLORS[cluster % CLUSTER_COLORS.length];

    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    ctx.fillStyle = `${col}09`;
    ctx.fill();
    ctx.strokeStyle = `${col}33`;
    ctx.lineWidth = 1.2;
    ctx.setLineDash([6, 8]);
    ctx.stroke();
    ctx.restore();

    // Cluster tag
    ctx.font = 'bold 9.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = `${col}99`;
    ctx.textAlign = "center";
    ctx.fillText(`ECOLOGY ${cluster + 1}`, cx, cy - ry + 14);
  });

  // 1.5 Draw Habitat Resource Niches & Foraging Conduits
  const resources = Array.isArray(state.socialResourceEvidence) ? state.socialResourceEvidence : [];
  if (showNiches && resources.length > 0) {
    resources.forEach((res, resIdx) => {
      const defaultCenters = [[280, 210], [620, 230], [470, 520]];
      const rx = res.x ?? defaultCenters[resIdx % defaultCenters.length][0];
      const ry = res.y ?? defaultCenters[resIdx % defaultCenters.length][1];
      const isContested = res.consecutive_denied > 0 || res.availability < 0.7;
      const resCol = isContested ? palette.coral : (res.availability >= 0.85 ? palette.mint : palette.amber);

      // Radial well gradient
      const wellGrad = ctx.createRadialGradient(rx, ry, 6, rx, ry, 65);
      wellGrad.addColorStop(0, `${resCol}22`);
      wellGrad.addColorStop(0.5, `${resCol}0d`);
      wellGrad.addColorStop(1, "transparent");

      ctx.beginPath();
      ctx.arc(rx, ry, 65, 0, Math.PI * 2);
      ctx.fillStyle = wellGrad;
      ctx.fill();

      // Equipotential ring
      ctx.beginPath();
      ctx.arc(rx, ry, 45, 0, Math.PI * 2);
      ctx.strokeStyle = `${resCol}33`;
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Feeder foraging beams connecting nearest cluster members
      const targetNodes = currentNodes.filter(n => (n.cluster ?? 0) === (resIdx % 3));
      targetNodes.forEach(tn => {
        ctx.beginPath();
        ctx.moveTo(rx, ry);
        ctx.lineTo(tn.x, tn.y);
        ctx.strokeStyle = isContested ? "rgba(255, 127, 131, 0.16)" : "rgba(113, 233, 186, 0.16)";
        ctx.lineWidth = 1.0;
        ctx.stroke();

        // Ingestion particles moving from resource well to node
        if (trafficEnabled) {
          const pProg = (trafficPhase * 1.5 + (tn.id.charCodeAt(tn.id.length - 1) % 5) * 0.2) % 1.0;
          const ipx = rx + (tn.x - rx) * pProg;
          const ipy = ry + (tn.y - ry) * pProg;
          ctx.beginPath();
          ctx.arc(ipx, ipy, 2.2, 0, Math.PI * 2);
          ctx.fillStyle = resCol;
          ctx.fill();
        }
      });

      // Center resource crystal (rotated square)
      ctx.save();
      ctx.translate(rx, ry);
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = resCol;
      ctx.fillRect(-6, -6, 12, 12);
      ctx.restore();

      // Resource token label
      const cleanToken = res.token.replace(/^res_/, "");
      ctx.font = 'bold 9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.fillText(cleanToken, rx, ry - 14);

      ctx.font = '8.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = resCol;
      const statusText = isContested ? `⚠️ ${res.consecutive_denied} denegados` : `${Math.round(res.availability * 100)}% disp`;
      ctx.fillText(statusText, rx, ry + 16);
    });
  }

  // 2. Draw Social Links
  const activeFocusId = hoveredNode?.id || state.organismA?.id || state.organismB?.id;
  const connectedIds = activeFocusId
    ? new Set(
        currentLinks
          .filter(l => l.sourceNode.id === activeFocusId || l.targetNode.id === activeFocusId)
          .flatMap(l => [l.sourceNode.id, l.targetNode.id])
      )
    : null;

  currentLinks.forEach(link => {
    const na = link.sourceNode;
    const nb = link.targetNode;
    const matchesMode = link.type === state.populationMode || state.populationMode === "ecology";
    const isConn = !activeFocusId || (connectedIds && connectedIds.has(na.id) && connectedIds.has(nb.id));
    const isConflict = link.valence === "negative" || link.type === "dissent" || (link.conflicts && link.conflicts > 0);

    const baseColor = isConflict
      ? palette.coral
      : link.type === "activity"
      ? palette.amber
      : link.type === "knowledge"
      ? palette.cyan
      : palette.mint;

    const baseAlpha = matchesMode ? (isConn ? 0.75 : 0.12) : (isConn ? 0.25 : 0.05);
    const strokeW = 1.0 + (link.strength || 0.4) * 2.2;

    ctx.beginPath();
    ctx.moveTo(na.x, na.y);
    ctx.lineTo(nb.x, nb.y);
    ctx.strokeStyle = isConflict
      ? `rgba(255, 127, 131, ${baseAlpha})`
      : `rgba(80, 217, 255, ${baseAlpha})`;
    ctx.lineWidth = strokeW;
    if (isConflict) {
      ctx.setLineDash([3, 4]);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // 3. Dynamic Traffic Photons along Edges
    if (trafficEnabled && matchesMode && isConn) {
      const numPhotons = isConflict ? 1 : 2;
      const dist = Math.hypot(nb.x - na.x, nb.y - na.y) || 1;

      for (let p = 0; p < numPhotons; p++) {
        const offset = p / numPhotons;
        const progress = (trafficPhase * (1.2 + (link.strength || 0.5)) + offset) % 1.0;
        const px = na.x + (nb.x - na.x) * progress;
        const py = na.y + (nb.y - na.y) * progress;

        const pRadius = isConflict ? 2.5 : 3.0;
        const pColor = isConflict ? palette.coral : (link.type === "activity" ? palette.amber : palette.mint);

        ctx.beginPath();
        ctx.arc(px, py, pRadius, 0, Math.PI * 2);
        ctx.fillStyle = pColor;
        ctx.shadowColor = pColor;
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }
  });

  // 4. Draw Nodes (Organisms)
  currentNodes.forEach((node, i) => {
    const isConn = !activeFocusId || (connectedIds && connectedIds.has(node.id));
    const isHovered = hoveredNode && hoveredNode.id === node.id;
    const isSelectedA = state.organismA && state.organismA.id === node.id;
    const isSelectedB = state.organismB && state.organismB.id === node.id;

    const clusterCol = CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length];
    const modeColor = state.populationMode === "activity"
      ? palette.amber
      : state.populationMode === "dissent"
      ? palette.coral
      : clusterCol;

    const magnitude = state.populationMode === "knowledge"
      ? Math.min(1, (node.knowledge || 10) / 45)
      : state.populationMode === "dissent"
      ? Math.min(1, (node.contested || 0) / 5)
      : (node.pressure || 0.3);

    const baseR = 7.5 + magnitude * 7.5;
    const r = isHovered ? baseR * 1.25 : baseR;
    const nodeAlpha = isConn ? 1.0 : 0.22;

    // Selection ring
    if (isSelectedA || isSelectedB) {
      const ringCol = isSelectedA ? palette.cyan : palette.amber;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 5.5, 0, Math.PI * 2);
      ctx.strokeStyle = ringCol;
      ctx.lineWidth = 2.2;
      ctx.stroke();
    }

    // Node body
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(5, 18, 32, 0.92)`;
    ctx.fill();

    ctx.strokeStyle = modeColor;
    ctx.lineWidth = isHovered ? 2.8 : 1.8;
    ctx.globalAlpha = nodeAlpha;
    ctx.stroke();
    ctx.globalAlpha = 1.0;

    // Center nucleus
    ctx.beginPath();
    ctx.arc(node.x, node.y, Math.max(2, r * 0.42), 0, Math.PI * 2);
    ctx.fillStyle = modeColor;
    ctx.fill();

    // Harmonic Consensus / Counter-phase Dissent Halo
    const hasDissent = (node.contested || 0) > 0;
    if (trafficEnabled) {
      if (hasDissent) {
        // Counter-phase oscillation: shifted by PI with faster frequency and jitter
        const dissentPulse = Math.sin(trafficPhase * Math.PI * 6 + Math.PI);
        const dissentR = r + 4 + dissentPulse * 3;
        ctx.beginPath();
        ctx.arc(node.x, node.y, dissentR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 127, 131, ${0.4 + dissentPulse * 0.3})`;
        ctx.lineWidth = 1.6;
        ctx.setLineDash([2, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Expanding epistemic ripple when in dissent mode
        if (state.populationMode === "dissent") {
          const rippleProgress = (trafficPhase * 3) % 1.0;
          const rippleR = r + rippleProgress * 28;
          ctx.beginPath();
          ctx.arc(node.x, node.y, rippleR, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(255, 127, 131, ${(1 - rippleProgress) * 0.5})`;
          ctx.lineWidth = 1.2;
          ctx.stroke();
        }
      } else {
        // Synchronous consensus phase
        const consensusPulse = Math.sin(trafficPhase * Math.PI * 2.5);
        const consensusR = r + 3 + consensusPulse * 2;
        ctx.beginPath();
        ctx.arc(node.x, node.y, consensusR, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(113, 233, 186, ${0.25 + consensusPulse * 0.15})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
    }

    // Node label
    if (isHovered || isSelectedA || isSelectedB || (i < 30 && i % 2 === 0)) {
      ctx.font = 'bold 9.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = isHovered ? "#ffffff" : `rgba(200, 225, 245, ${nodeAlpha * 0.9})`;
      ctx.textAlign = "left";
      ctx.fillText(node.id, node.x + r + 5, node.y + 3);
    }
  });

  // 5. Hover Tooltip Pill
  if (hoveredNode) {
    const node = hoveredNode;
    const coopLinks = currentLinks.filter(l => (l.sourceNode.id === node.id || l.targetNode.id === node.id) && l.valence !== "negative");
    const conflictLinks = currentLinks.filter(l => (l.sourceNode.id === node.id || l.targetNode.id === node.id) && (l.valence === "negative" || l.type === "dissent" || l.conflicts > 0));

    const lines = [
      `${node.id}  ·  Ecology ${node.cluster + 1}`,
      `Actividad: ${(node.pressure * 100).toFixed(0)}% | Saber: ${node.knowledge || 0} | Disenso: ${node.contested || 0}`,
      `Vínculos: ${coopLinks.length} coop (🟢) · ${conflictLinks.length} conflicto (🔴)`,
    ];

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
    const pillY = node.y - 18 - pillH;

    ctx.fillStyle = "rgba(5, 18, 32, 0.94)";
    ctx.strokeStyle = CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length];
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.roundRect(pillX, pillY, pillW, pillH, 6);
    ctx.fill();
    ctx.stroke();

    lines.forEach((l, idx) => {
      ctx.font = idx === 0 ? 'bold 11px sans-serif' : '10.5px sans-serif';
      ctx.fillStyle = idx === 0 ? '#ffffff' : (idx === 1 ? 'rgba(175, 199, 220, 0.9)' : '#71e9ba');
      ctx.textAlign = "left";
      ctx.fillText(l, pillX + padX, pillY + 16 + idx * lineH);
    });
  }

  // 6. Epistemic Swarm Resonator HUD
  if (currentNodes.length > 0) {
    const dissentCount = currentNodes.filter(n => (n.contested || 0) > 0).length;
    const consensusCount = currentNodes.length - dissentCount;

    ctx.save();
    ctx.font = '10.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const hudText1 = `🌿 Coro Consenso: ${consensusCount}`;
    const hudText2 = `⚡ Focos Disenso: ${dissentCount}`;
    const hudSub = "La mayoría no define la verdad · Disenso preservado";

    const w1 = ctx.measureText(hudText1).width;
    const w2 = ctx.measureText(hudText2).width;
    const w3 = ctx.measureText(hudSub).width;
    const boxW = Math.max(w1 + w2 + 30, w3 + 24);
    const boxH = 46;
    const boxX = 24;
    const boxY = height - 68;

    ctx.fillStyle = "rgba(5, 18, 32, 0.88)";
    ctx.strokeStyle = dissentCount > 0 ? "rgba(255, 127, 131, 0.35)" : "rgba(113, 233, 186, 0.35)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxW, boxH, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = palette.mint;
    ctx.textAlign = "left";
    ctx.fillText(hudText1, boxX + 12, boxY + 18);

    ctx.fillStyle = dissentCount > 0 ? palette.coral : "rgba(148, 184, 215, 0.6)";
    ctx.fillText(hudText2, boxX + w1 + 26, boxY + 18);

    ctx.font = '9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = "rgba(148, 184, 215, 0.75)";
    ctx.fillText(hudSub, boxX + 12, boxY + 36);
    ctx.restore();
  }

  ctx.restore();
}

function animationLoop() {
  if (state.view !== "population") {
    animFrameId = null;
    return;
  }

  const canvas = document.querySelector("#population-canvas");
  if (!canvas || canvas.classList.contains("hidden")) {
    animFrameId = null;
    return;
  }

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  updatePhysicsModel(width, height);
  stepPhysics(width, height);

  trafficPhase = (trafficPhase + 0.008) % 1.0;
  renderCanvasFrame(ctx, width, height);

  const shouldContinue = alpha > ALPHA_MIN || isDragging || isPanning || trafficEnabled;
  if (shouldContinue) {
    animFrameId = requestAnimationFrame(animationLoop);
  } else {
    animFrameId = null;
  }
}

// ---------------------------------------------------------------------------
// 4. Interactive Listeners (Drag, Hover, Click, Zoom, Pan)
// ---------------------------------------------------------------------------
function installPopulationCanvasListeners(canvas) {
  if (canvas.dataset.listenersInstalled) return;
  canvas.dataset.listenersInstalled = "true";

  function toCanvas(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = rect.width > 0 ? canvas.width / rect.width : 1;
    const scaleY = rect.height > 0 ? canvas.height / rect.height : 1;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
      rect,
    };
  }

  function toWorld(clientX, clientY) {
    const { x: cx, y: cy } = toCanvas(clientX, clientY);
    return {
      x: (cx - panX) / zoomScale,
      y: (cy - panY) / zoomScale,
    };
  }

  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    const { x: mouseX, y: mouseY } = toCanvas(e.clientX, e.clientY);

    panX = mouseX - (mouseX - panX) * zoomFactor;
    panY = mouseY - (mouseY - panY) * zoomFactor;
    zoomScale = Math.max(0.4, Math.min(3.0, zoomScale * zoomFactor));
    reheat(0.1);
  }, { passive: false });

  canvas.addEventListener("mousedown", e => {
    const { x, y } = toWorld(e.clientX, e.clientY);
    let clicked = null;
    for (let i = currentNodes.length - 1; i >= 0; i--) {
      const node = currentNodes[i];
      if (Math.hypot(node.x - x, node.y - y) <= 18) {
        clicked = node;
        break;
      }
    }

    if (clicked && e.button === 0) {
      isDragging = true;
      draggedNode = clicked;
      draggedNode.pinned = true;
      reheat(0.8);
    } else {
      isPanning = true;
      const { x: mouseX, y: mouseY } = toCanvas(e.clientX, e.clientY);
      panStartX = mouseX - panX;
      panStartY = mouseY - panY;
      canvas.style.cursor = "grabbing";
    }
  });

  window.addEventListener("mousemove", e => {
    if (isDragging && draggedNode) {
      const { x, y } = toWorld(e.clientX, e.clientY);
      draggedNode.x = x;
      draggedNode.y = y;
      draggedNode.vx = 0;
      draggedNode.vy = 0;
      reheat(0.4);
      return;
    }

    if (isPanning) {
      const { x: mouseX, y: mouseY } = toCanvas(e.clientX, e.clientY);
      panX = mouseX - panStartX;
      panY = mouseY - panStartY;
      reheat(0.1);
      return;
    }

    const { rect } = toCanvas(e.clientX, e.clientY);
    const isInside = (
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom
    );

    if (!isInside) {
      if (hoveredNode) {
        hoveredNode = null;
        canvas.style.cursor = "grab";
        reheat(0.1);
      }
      return;
    }

    const { x, y } = toWorld(e.clientX, e.clientY);
    let found = null;
    for (let i = currentNodes.length - 1; i >= 0; i--) {
      const node = currentNodes[i];
      if (Math.hypot(node.x - x, node.y - y) <= 18) {
        found = node;
        break;
      }
    }

    if (found !== hoveredNode) {
      hoveredNode = found;
      canvas.style.cursor = hoveredNode ? "pointer" : "grab";
      reheat(0.15);
    }
  });

  canvas.addEventListener("mouseleave", () => {
    if (!isDragging && !isPanning && hoveredNode) {
      hoveredNode = null;
      canvas.style.cursor = "grab";
      reheat(0.1);
    }
  });

  function distToSegment(px, py, x1, y1, x2, y2) {
    const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
    if (l2 === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
  }

  window.addEventListener("mouseup", e => {
    if (isDragging && draggedNode) {
      const wasPinned = draggedNode;
      draggedNode.pinned = false;
      isDragging = false;
      draggedNode = null;
      reheat(0.3);

      const { x, y } = toWorld(e.clientX, e.clientY);
      if (Math.hypot(wasPinned.x - x, wasPinned.y - y) < 5) {
        selectPopulationMember(wasPinned);
      }
      return;
    }

    if (isPanning) {
      const { x: mouseX, y: mouseY } = toCanvas(e.clientX, e.clientY);
      const wasPanning = Math.hypot(mouseX - panStartX - panX, mouseY - panStartY - panY) > 4;
      isPanning = false;
      canvas.style.cursor = hoveredNode ? "pointer" : "grab";

      // If clicked on canvas without dragging or panning, check if clicked on a link
      if (!wasPanning) {
        const { x, y } = toWorld(e.clientX, e.clientY);
        let clickedLink = null;
        for (let i = currentLinks.length - 1; i >= 0; i--) {
          const link = currentLinks[i];
          const d = distToSegment(x, y, link.sourceNode.x, link.sourceNode.y, link.targetNode.x, link.targetNode.y);
          if (d <= 8) {
            clickedLink = link;
            break;
          }
        }
        if (clickedLink) {
          state.organismA = clickedLink.sourceNode;
          state.organismB = clickedLink.targetNode;
          renderPopulation();
          renderPopulationInspector();
        }
      }
    }
  });

  // Action buttons
  document.querySelector("#population-niches-toggle")?.addEventListener("click", e => {
    showNiches = !showNiches;
    e.currentTarget.classList.toggle("active", showNiches);
    reheat(0.3);
  });

  document.querySelector("#population-traffic-toggle")?.addEventListener("click", e => {
    trafficEnabled = !trafficEnabled;
    e.currentTarget.classList.toggle("active", trafficEnabled);
    reheat(0.2);
  });

  document.querySelector("#population-reset")?.addEventListener("click", () => {
    panX = 0;
    panY = 0;
    zoomScale = 1.0;
    cachedNodes.clear();
    reheat(1.0);
  });
}

// ---------------------------------------------------------------------------
// 5. Main entrypoint
// ---------------------------------------------------------------------------
function renderPopulation(target = "#population-canvas", mini = false) {
  const el = document.querySelector(target);
  if (!el) return;

  if (mini) {
    renderMiniSvg(el);
    return;
  }

  // Main interactive population canvas
  if (el.tagName.toLowerCase() === "canvas") {
    installPopulationCanvasListeners(el);
    reheat(0.7);
  } else {
    // Fallback if target is SVG
    renderMiniSvg(el);
  }
}

function selectPopulationMember(item) {
  if (!state.organismA || state.organismB) {
    state.organismA = item;
    state.organismB = null;
  } else if (state.organismA.id !== item.id) {
    state.organismB = item;
  }
  renderPopulation();
  renderPopulationInspector();
}

function renderPopulationInspector() {
  const selected = state.organismB ?? state.organismA;
  const subtitle = document.querySelector("#cluster-subtitle");
  const explanation = document.querySelector("#cluster-explanation");
  const comparison = document.querySelector("#organism-comparison");
  if (!subtitle || !explanation || !comparison) return;

  explanation.replaceChildren();
  comparison.replaceChildren();
  const population = populationMembers();

  if (population.length <= 1) {
    subtitle.textContent = "Single organism recorded";
    const p = document.createElement("p");
    p.textContent = "This recording only contains one organism, so ecology, knowledge, activity and dissent comparisons have nothing to relate it to yet. Load or record data with more than one organism to use this view.";
    explanation.append(p);
    const empty = document.createElement("p");
    empty.className = "comparison-empty";
    empty.textContent = "Comparison needs at least two organisms.";
    comparison.append(empty);
    return;
  }

  if (!selected) {
    subtitle.textContent = "Select an organism";
    const p = document.createElement("p");
    p.textContent = "Choose a node to explain its ecological cluster, then choose another to compare them.";
    explanation.append(p);
    const empty = document.createElement("p");
    empty.className = "comparison-empty";
    empty.textContent = "No organisms selected.";
    comparison.append(empty);
    return;
  }

  const members = population.filter(item => item.cluster === selected.cluster);
  subtitle.textContent = `Ecology ${selected.cluster + 1} · ${members.length} organisms`;

  const title = document.createElement("h3");
  title.textContent = `Ecology ${selected.cluster + 1}`;
  const body = document.createElement("p");
  body.textContent = "These organisms are close because their normalized environments are compatible. This grouping says nothing about which organism is more reliable or correct.";

  const facts = document.createElement("ul");
  facts.className = "cluster-facts";
  [
    `${members.length} organisms share this context`,
    `Average activity ${(members.reduce((s, x) => s + x.pressure, 0) / members.length * 100).toFixed(0)}%`,
    `${members.reduce((s, x) => s + x.contested, 0)} contested beliefs remain visible`,
  ].forEach(text => {
    const li = document.createElement("li");
    li.textContent = text;
    facts.append(li);
  });
  explanation.append(title, body, facts);

  if (!state.organismA || !state.organismB) {
    const empty = document.createElement("p");
    empty.className = "comparison-empty";
    empty.textContent = `${state.organismA.id} is selected as A. Choose a second organism to compare without collapsing their differences into one score.`;
    comparison.append(empty);
    return;
  }

  const names = document.createElement("div");
  names.className = "comparison-names";
  [state.organismA, state.organismB].forEach((item, index) => {
    const box = document.createElement("div");
    box.className = "comparison-name";
    const b = document.createElement("b");
    b.textContent = `${index ? "B" : "A"} · ${item.id}`;
    const small = document.createElement("small");
    small.textContent = `Ecology ${item.cluster + 1}`;
    box.append(b, small);
    names.append(box);
  });
  comparison.append(names);

  // Dyad Mutualism Dial Analysis
  const relationships = state.fleetConnected ? state.fleetRelationships : state.relationships;
  const directRels = (relationships || []).filter(
    r => (r.source === state.organismA.id && r.target === state.organismB.id) ||
         (r.source === state.organismB.id && r.target === state.organismA.id)
  );

  const totalSupport = directRels.reduce((acc, r) => acc + (r.support || (r.valence === "positive" ? 1.5 : 0.5)), 0);
  const totalHarm = directRels.reduce((acc, r) => acc + (r.harm || (r.valence === "negative" ? 1.5 : 0.0)), 0);
  const totalConflicts = directRels.reduce((acc, r) => acc + (r.conflicts || (r.type === "dissent" ? 1 : 0)), 0);
  const isReciprocal = directRels.some(r => r.reciprocal) || directRels.length >= 2;
  const meanReliability = directRels.length > 0 ? directRels.reduce((acc, r) => acc + (r.reliability || 0.8), 0) / directRels.length : 0.5;
  const meanFreshness = directRels.length > 0 ? directRels.reduce((acc, r) => acc + (r.freshness || 0.8), 0) / directRels.length : 0.5;
  const channel = directRels[0]?.channel || "default";

  let archetype = "Mutualismo Simbiótico";
  let badgeClass = "mutualism";
  let icon = "🌿";
  let description = "Intercambio simbiótico cooperativo con refuerzo mutuo en validaciones y coexistencia armónica.";

  if (directRels.length === 0) {
    archetype = "Nichos Paralelos";
    badgeClass = "neutral";
    icon = "🌐";
    description = `No se registran transacciones directas entre ${state.organismA.id} y ${state.organismB.id}. Coexisten en nichos paralelos sin dependencia mutua.`;
  } else if (totalHarm > totalSupport || totalConflicts > 0) {
    archetype = "Antagonismo / Conflicto";
    badgeClass = "conflict";
    icon = "⚔️";
    description = `Fricción y contradicción observada. Se registran ${totalConflicts} disputas o rechazos de validación entre ambos organismos.`;
  } else if (!isReciprocal || Math.abs(totalSupport - totalHarm) < 0.3) {
    archetype = "Comensalismo Asimétrico";
    badgeClass = "asymmetry";
    icon = "⚖️";
    description = "Flujo unidireccional de información o recursos sin perjuicio pero con asimetría en la reciprocidad de retorno.";
  }

  const reliabilityPct = Math.round(meanReliability * 100);
  const freshnessPct = Math.round(meanFreshness * 100);

  const dyadEl = document.createElement("div");
  dyadEl.className = "dyad-card";
  dyadEl.innerHTML = `
    <div class="dyad-head">
      <div class="dyad-title"><span>${icon}</span> <span>Dial de Mutualismo</span></div>
      <span class="dyad-archetype-badge ${badgeClass}">${archetype.toUpperCase()}</span>
    </div>
    <p class="dyad-desc">${description}</p>
    <div class="dyad-metrics">
      <div class="dyad-metric">
        <div class="dyad-metric-head"><span>Reciprocidad</span><strong>${isReciprocal ? "Bilateral" : "Unilateral"}</strong></div>
        <div class="meter"><i style="width:${isReciprocal ? 95 : 35}%;background:${isReciprocal ? palette.mint : palette.amber}"></i></div>
      </div>
      <div class="dyad-metric">
        <div class="dyad-metric-head"><span>Fiabilidad Evidencia</span><strong>${reliabilityPct}%</strong></div>
        <div class="meter"><i style="width:${reliabilityPct}%;background:${palette.cyan}"></i></div>
      </div>
    </div>
    <ul class="dyad-facts-list">
      <li>Canal de interacción: <span>${channel}</span></li>
      <li>Transacciones directas: <span>${directRels.length} enlaces observados</span></li>
      <li>Fricciones / Conflictos: <span style="color:${totalConflicts > 0 ? palette.coral : '#71e9ba'}">${totalConflicts} registros</span></li>
      <li>Frescura de la relación: <span>${freshnessPct}%</span></li>
    </ul>
  `;
  comparison.append(dyadEl);

  const table = document.createElement("table");
  [
    ["Ecology", `Context ${state.organismA.cluster + 1}`, `Context ${state.organismB.cluster + 1}`],
    ["Activity", `${(state.organismA.pressure * 100).toFixed(0)}%`, `${(state.organismB.pressure * 100).toFixed(0)}%`],
    ["Shared knowledge", state.organismA.knowledge, state.organismB.knowledge],
    ["Contested beliefs", state.organismA.contested, state.organismB.contested],
  ].forEach(row => {
    const tr = document.createElement("tr");
    row.forEach((value, index) => {
      const cell = document.createElement(index ? "td" : "th");
      cell.textContent = String(value);
      tr.append(cell);
    });
    table.append(tr);
  });
  comparison.append(table);
}

export { renderPopulation, selectPopulationMember, renderPopulationInspector };
