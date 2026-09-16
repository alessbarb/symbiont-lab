import { state } from "../state/store.js";
import { palette } from "./svg.js";

// Canonical host regime basins in 2D normalized space
const REGIMES = [
  {
    id: "quiescence",
    name: "Quiescencia Nocturna",
    icon: "🌙",
    x: -160,
    y: 130,
    color: "#50d9ff",
    radius: 95,
    description: "Carga basal mínima. Señales estables y predecibles, baja tasa de eventos en el host.",
  },
  {
    id: "sustained_compute",
    name: "Carga Sostenida / Trabajo Regular",
    icon: "⚙️",
    x: 170,
    y: 110,
    color: "#71e9ba",
    radius: 100,
    description: "Actividad sensorial intensa pero altamente sincronizada y anticipada por la red cognitiva.",
  },
  {
    id: "burst_io",
    name: "Transición Concurrente / Ráfagas E/S",
    icon: "⚡",
    x: -40,
    y: -50,
    color: "#ffbd54",
    radius: 90,
    description: "Conmutación rápida de contexto, ráfagas aperiódicas y correlaciones temporales transitorias.",
  },
  {
    id: "desync_stress",
    name: "Desincronización / Estrés Ambiental",
    icon: "🚨",
    x: 180,
    y: -170,
    color: "#ff7f83",
    radius: 95,
    description: "Contradicción elevada de modelos previos. Fuerte desincronización y alta sorpresa acumulada.",
  },
];

let trail = [];
let animFrameId = null;
let showContours = true;
let showTrail = true;
let sonarPhase = 0;
let lastCoord = null;
let currentVelocity = 0;
let mousePos = null;

function shorten(id) {
  if (!id) return "";
  return id.replace(/^(signal\.|sense\.|node\.)/, "");
}

function computeHostCoordinates() {
  // X: Metabolic & Causal Dynamic Flux [-280, 280]
  const dev = state.sensoryDevelopment ?? [];
  const senses = state.senses ?? [];
  const activeSenses = dev.length > 0 ? dev.filter(d => d.tier === "active") : senses.filter(s => s.active);
  const totalSenses = Math.max(1, dev.length || senses.length || 8);
  const activeRatio = activeSenses.length / totalSenses;

  let meanUtil = 0.3;
  if (dev.length > 0) {
    meanUtil = dev.reduce((acc, d) => acc + (d.utility || 0), 0) / dev.length;
  } else if (senses.length > 0) {
    meanUtil = senses.reduce((acc, s) => acc + (s.quality || 0.3), 0) / senses.length;
  }

  const readouts = state.cognition?.readouts ?? {};
  const roValues = Object.values(readouts);
  const meanReadout = roValues.length > 0 ? roValues.reduce((a, b) => a + Math.abs(b), 0) / roValues.length : 0.4;

  const fluxNorm = (activeRatio * 0.4 + meanUtil * 0.35 + meanReadout * 0.25); // 0.0 to 1.0
  const targetX = (fluxNorm - 0.48) * 520;

  // Y: Predictive Tension & Surprise [-240, 240] (inverted: top is high surprise/negative Y in canvas)
  const errors = state.cognition?.predictionErrors ?? {};
  const errMap = { zero: 0.05, trace: 0.15, low: 0.35, medium: 0.65, high: 0.85, extreme: 1.0 };
  const errValues = Object.values(errors);
  const meanErr = errValues.length > 0 ? errValues.reduce((a, c) => a + (errMap[c] ?? 0.2), 0) / errValues.length : 0.2;

  const beliefs = state.beliefs ?? [];
  const dissentCount = beliefs.filter(b => b.dissent).length;
  const dissentRatio = beliefs.length > 0 ? dissentCount / beliefs.length : 0;

  const safetyFails = state.cognition?.safetyState?.consecutiveFailures ?? 0;
  const safetyPenalty = Math.min(1.0, safetyFails * 0.25);

  const surpriseNorm = (meanErr * 0.55 + dissentRatio * 0.3 + safetyPenalty * 0.15); // 0.0 to 1.0
  // Canvas Y: 0 is center, top is negative Y (high surprise), bottom is positive Y (calm)
  const targetY = (0.50 - surpriseNorm) * 440;

  return { x: targetX, y: targetY, fluxNorm, surpriseNorm };
}

function updateTrail(coord) {
  const currentTick = state.tick ?? 0;
  if (lastCoord) {
    const dx = coord.x - lastCoord.x;
    const dy = coord.y - lastCoord.y;
    currentVelocity = Math.hypot(dx, dy);
  }

  // Only push if new tick or distance moved
  if (trail.length === 0 || trail[trail.length - 1].tick !== currentTick) {
    trail.push({ x: coord.x, y: coord.y, tick: currentTick });
    if (trail.length > 28) {
      trail.shift();
    }
  } else {
    // Smooth in place
    const head = trail[trail.length - 1];
    head.x += (coord.x - head.x) * 0.25;
    head.y += (coord.y - head.y) * 0.25;
  }
  lastCoord = coord;
}

function evaluateRegimes(pos) {
  let minD = Infinity;
  let nearest = REGIMES[0];

  REGIMES.forEach(r => {
    const d = Math.hypot(pos.x - r.x, pos.y - r.y);
    if (d < minD) {
      minD = d;
      nearest = r;
    }
  });

  const affinity = Math.max(0, Math.min(100, Math.round((1 - minD / (nearest.radius * 1.8)) * 100)));
  const isUnexplored = minD > nearest.radius * 1.35;
  const noveltyPct = isUnexplored
    ? Math.min(100, Math.round(55 + ((minD - nearest.radius * 1.35) / 140) * 45))
    : Math.max(0, Math.round((minD / (nearest.radius * 1.35)) * 50));

  return { nearest, minDistance: minD, affinity, isUnexplored, noveltyPct };
}

function updateCompassHUD(analysis, coord) {
  const titleEl = document.querySelector("#compass-regime-title");
  const subEl = document.querySelector("#compass-regime-sub");
  const badgeEl = document.querySelector("#compass-novelty-badge");
  const valEl = document.querySelector("#compass-novelty-val");
  const barEl = document.querySelector("#compass-novelty-bar");
  const driftEl = document.querySelector("#compass-drift-val");
  const alertEl = document.querySelector("#compass-unexplored-alert");
  const expEl = document.querySelector("#compass-explanation");

  if (!titleEl || !subEl || !badgeEl || !valEl || !barEl || !driftEl || !alertEl || !expEl) return;

  const { nearest, affinity, isUnexplored, noveltyPct } = analysis;

  if (isUnexplored) {
    titleEl.textContent = "Territorio Inexplorado";
    subEl.textContent = `Afinidad atractor más cercano: ${affinity}% (${nearest.name})`;
    badgeEl.textContent = "INÉDITO";
    badgeEl.className = "compass-badge alert";
    barEl.style.background = palette.coral;
    alertEl.classList.remove("hidden");
  } else {
    titleEl.textContent = nearest.name;
    subEl.textContent = `Atractor activo · Afinidad ${affinity}%`;
    const isMedium = noveltyPct > 35;
    badgeEl.textContent = isMedium ? "DERIVA MODERADA" : "FAMILIAR";
    badgeEl.className = isMedium ? "compass-badge moderate" : "compass-badge familiar";
    barEl.style.background = isMedium ? palette.amber : palette.mint;
    alertEl.classList.add("hidden");
  }

  valEl.textContent = `${noveltyPct}%`;
  barEl.style.width = `${Math.max(4, noveltyPct)}%`;
  driftEl.textContent = `${currentVelocity.toFixed(1)} px/tick`;

  // Dynamic driver explanation
  const dev = state.sensoryDevelopment ?? [];
  const topDev = [...dev].sort((a, b) => (b.utility || 0) - (a.utility || 0))[0];
  const driverName = topDev ? shorten(topDev.name) : "canales sensoriales primarios";

  if (isUnexplored) {
    expEl.textContent = `Alerta de Régimen Inédito: El vector de estado del host se sitúa fuera de los atractores aprendidos. La red incrementa la presión estructural de plasticidad (impulsado por la varianza en ${driverName}).`;
  } else {
    expEl.textContent = `${nearest.description} El organismo asigna eficientemente el presupuesto atencional con ${driverName} como ancla principal.`;
  }
}

function renderCompassFrame(ctx, width, height) {
  ctx.clearRect(0, 0, width, height);

  const cx = width / 2;
  const cy = height / 2;

  // 1. Polar Radar Background & Grid Lines
  ctx.save();
  ctx.translate(cx, cy);

  // Concentric radar circles
  const rings = [70, 140, 220, 300];
  rings.forEach((r, idx) => {
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.strokeStyle = idx === rings.length - 1 ? "rgba(80, 217, 255, 0.15)" : "rgba(80, 217, 255, 0.06)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 6]);
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // Crosshair Axes
  ctx.strokeStyle = "rgba(100, 160, 210, 0.18)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-340, 0);
  ctx.lineTo(340, 0);
  ctx.moveTo(0, -260);
  ctx.lineTo(0, 260);
  ctx.stroke();

  // Axis Labels
  ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = "rgba(148, 184, 215, 0.65)";
  ctx.textAlign = "center";
  ctx.fillText("▲ TENSIÓN PREDICTIVA & SORPRESA", 0, -270);
  ctx.fillText("ESTABILIDAD & REGULARIDAD ▼", 0, 275);
  ctx.textAlign = "left";
  ctx.fillText("ACTIVIDAD DINÁMICA DEL HOST ►", 200, -8);
  ctx.textAlign = "right";
  ctx.fillText("◄ QUIESCENCIA BASAL", -200, -8);

  // 2. Topographic Basins (Isoclines)
  if (showContours) {
    REGIMES.forEach(r => {
      const grad = ctx.createRadialGradient(r.x, r.y, 10, r.x, r.y, r.radius * 1.3);
      grad.addColorStop(0, `${r.color}22`);
      grad.addColorStop(0.5, `${r.color}0d`);
      grad.addColorStop(1, "transparent");

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(r.x, r.y, r.radius * 1.3, 0, Math.PI * 2);
      ctx.fill();

      // Concentric isoclines
      [0.4, 0.75, 1.15].forEach((scale, i) => {
        ctx.beginPath();
        ctx.arc(r.x, r.y, r.radius * scale, 0, Math.PI * 2);
        ctx.strokeStyle = `${r.color}${i === 1 ? "44" : "22"}`;
        ctx.lineWidth = 1;
        ctx.setLineDash(i === 2 ? [3, 4] : []);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Regime Centroid Anchor & Icon
      ctx.beginPath();
      ctx.arc(r.x, r.y, 8, 0, Math.PI * 2);
      ctx.fillStyle = r.color;
      ctx.fill();

      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(r.icon, r.x, r.y - 14);

      ctx.font = 'bold 10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = "#ffffff";
      ctx.fillText(r.name, r.x, r.y + 22);
    });
  }

  // 3. Compute Coordinates & Trajectory Trail
  const coord = computeHostCoordinates();
  updateTrail(coord);
  const analysis = evaluateRegimes(coord);
  updateCompassHUD(analysis, coord);

  // Draw Trajectory Trail
  if (showTrail && trail.length > 1) {
    ctx.lineWidth = 2.2;
    for (let i = 1; i < trail.length; i++) {
      const p0 = trail[i - 1];
      const p1 = trail[i];
      const alpha = (i / trail.length) * 0.85;

      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.strokeStyle = analysis.isUnexplored ? `rgba(255, 127, 131, ${alpha})` : `rgba(80, 217, 255, ${alpha})`;
      ctx.stroke();
    }
  }

  // 4. Current State Particle & Sonar Shockwave
  const px = coord.x;
  const py = coord.y;
  const pointColor = analysis.isUnexplored ? palette.coral : (analysis.noveltyPct > 35 ? palette.amber : palette.mint);

  // Sonar wave when in unexplored territory or during state playback
  sonarPhase += 0.04;
  if (sonarPhase > 1) sonarPhase -= 1;

  if (analysis.isUnexplored) {
    const waveRadius = 16 + sonarPhase * 70;
    const waveAlpha = (1 - sonarPhase) * 0.7;
    ctx.beginPath();
    ctx.arc(px, py, waveRadius, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(255, 127, 131, ${waveAlpha})`;
    ctx.lineWidth = 1.8;
    ctx.stroke();
  }

  // Ethereal particle halo
  const haloR = 12 + Math.sin(sonarPhase * Math.PI * 2) * 3;
  ctx.beginPath();
  ctx.arc(px, py, haloR, 0, Math.PI * 2);
  ctx.fillStyle = `${pointColor}33`;
  ctx.fill();

  // Core particle dot
  ctx.beginPath();
  ctx.arc(px, py, 6.5, 0, Math.PI * 2);
  ctx.fillStyle = pointColor;
  ctx.shadowColor = pointColor;
  ctx.shadowBlur = 10;
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // Heading Velocity Arrow
  if (currentVelocity > 1) {
    const angle = Math.atan2(coord.y - (lastCoord?.y ?? coord.y), coord.x - (lastCoord?.x ?? coord.x));
    const arrowLen = Math.min(32, 10 + currentVelocity * 2.5);
    const ax = px + Math.cos(angle) * arrowLen;
    const ay = py + Math.sin(angle) * arrowLen;

    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(ax, ay);
    ctx.strokeStyle = pointColor;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // Label current host state
  ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.fillText("HOST STATE", px + 14, py - 6);

  ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillStyle = "rgba(175, 199, 220, 0.9)";
  ctx.fillText(`Novedad: ${analysis.noveltyPct}%`, px + 14, py + 8);

  // Crosshair hover coordinates if user moves mouse
  if (mousePos) {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.moveTo(mousePos.x, -260);
    ctx.lineTo(mousePos.x, 260);
    ctx.moveTo(-340, mousePos.y);
    ctx.lineTo(340, mousePos.y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Check if hovering an attractor regime
    const hoveredRegime = REGIMES.find(r => Math.hypot(r.x - mousePos.x, r.y - mousePos.y) <= r.radius);
    if (hoveredRegime) {
      ctx.beginPath();
      ctx.arc(hoveredRegime.x, hoveredRegime.y, hoveredRegime.radius + 6, 0, Math.PI * 2);
      ctx.strokeStyle = hoveredRegime.color;
      ctx.lineWidth = 2.0;
      ctx.stroke();

      const title = `${hoveredRegime.icon} ${hoveredRegime.name}`;
      const desc = hoveredRegime.description;
      ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      const w1 = ctx.measureText(title).width;
      ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      const w2 = ctx.measureText(desc).width;
      const pillW = Math.max(w1, w2) + 20;
      const pillH = 38;
      const pillX = mousePos.x + 12;
      const pillY = mousePos.y - 20;

      ctx.fillStyle = "rgba(5, 18, 32, 0.94)";
      ctx.strokeStyle = hoveredRegime.color;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      if (typeof ctx.roundRect === "function") {
        ctx.roundRect(pillX, pillY, pillW, pillH, 6);
      } else {
        ctx.rect(pillX, pillY, pillW, pillH);
      }
      ctx.fill();
      ctx.stroke();

      ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "left";
      ctx.fillText(title, pillX + 10, pillY + 15);

      ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillStyle = "rgba(175, 199, 220, 0.85)";
      ctx.fillText(desc, pillX + 10, pillY + 30);
    }
  }

  ctx.restore();
}

function animationLoop() {
  if (state.view !== "individual" || state.organismView !== "regimes") {
    isSimulating = false;
    animFrameId = null;
    return;
  }

  const canvas = document.querySelector("#regime-compass-canvas");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    renderCompassFrame(ctx, canvas.width, canvas.height);
  }

  animFrameId = requestAnimationFrame(animationLoop);
}

function installCompassControls() {
  const canvas = document.querySelector("#regime-compass-canvas");
  if (!canvas) return;

  canvas.addEventListener("mousemove", e => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = rect.width > 0 ? canvas.width / rect.width : 1;
    const scaleY = rect.height > 0 ? canvas.height / rect.height : 1;
    const canvasX = (e.clientX - rect.left) * scaleX;
    const canvasY = (e.clientY - rect.top) * scaleY;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    mousePos = {
      x: canvasX - cx,
      y: canvasY - cy,
    };
  });

  canvas.addEventListener("mouseleave", () => {
    mousePos = null;
  });

  const contourBtn = document.querySelector("#compass-contour-toggle");
  if (contourBtn && !contourBtn.dataset.bound) {
    contourBtn.dataset.bound = "true";
    contourBtn.addEventListener("click", () => {
      showContours = !showContours;
      contourBtn.classList.toggle("active", showContours);
    });
  }

  const trailBtn = document.querySelector("#compass-trail-toggle");
  if (trailBtn && !trailBtn.dataset.bound) {
    trailBtn.dataset.bound = "true";
    trailBtn.addEventListener("click", () => {
      showTrail = !showTrail;
      trailBtn.classList.toggle("active", showTrail);
      if (!showTrail) trail = [];
    });
  }

  const resetBtn = document.querySelector("#compass-reset");
  if (resetBtn && !resetBtn.dataset.bound) {
    resetBtn.dataset.bound = "true";
    resetBtn.addEventListener("click", () => {
      trail = [];
      showContours = true;
      showTrail = true;
      contourBtn?.classList.add("active");
      trailBtn?.classList.add("active");
    });
  }
}

function renderRegimeCompass() {
  const wrap = document.querySelector("#regime-compass-wrap");
  const canvas = document.querySelector("#regime-compass-canvas");
  if (!wrap || !canvas || state.view !== "individual" || state.organismView !== "regimes") {
    if (animFrameId) {
      cancelAnimationFrame(animFrameId);
      animFrameId = null;
    }
    return;
  }

  installCompassControls();

  if (!animFrameId) {
    animFrameId = requestAnimationFrame(animationLoop);
  }
}

export { renderRegimeCompass, REGIMES, computeHostCoordinates, evaluateRegimes };
