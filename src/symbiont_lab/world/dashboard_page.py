"""Scientific Observatory dashboard page.

Strictly read-only interface providing real-time visualization of the persistent
Symbiont World:
- Persistent SVG DOM (no flicker / innerHTML reset)
- Biome geography and selectable overlays (Region, Resources, Hazards, Fields, Population)
- Independent organism glyphs with vitality rings (integrity, reserve, vital state)
- Four epistemological perspectives in the Inspector: Reality, Phenotype, Perception, Self
- Native Canvas historical timelines (population, vitality, stress)
- Causal Event Journal feed with mechanical vs contributing provenance
(docs/design/symbiont-world-v3.md §16-35)
"""
from __future__ import annotations

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Symbiont World — Scientific Observatory</title>
<style>
:root {
  color-scheme: dark;
  --bg: #090d13;
  --surface: #101620;
  --panel: #161e2a;
  --panel-hover: #1c2635;
  --border: #222d3d;
  --border-focus: #3b82f6;
  --text: #e2e8f0;
  --text-muted: #8b9bb4;
  --accent: #10b981;
  --accent-cyan: #06b6d4;
  --accent-amber: #f59e0b;
  --accent-rose: #f43f5e;
  --accent-purple: #a855f7;
  --hex-stroke: #1e293b;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  overflow-x: hidden;
}

header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.brand {
  display: flex;
  flex-direction: column;
}
.brand h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #fff;
}
.brand .sub {
  color: var(--text-muted);
  font-size: 11px;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
}
.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}
.badge.stopped .badge-dot { background: var(--accent-amber); }
.badge.bad .badge-dot { background: var(--accent-rose); }

.controls-bar {
  display: flex;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.ctrl-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.ctrl-btn:hover {
  background: var(--panel-hover);
  color: #fff;
}
.ctrl-btn.active {
  background: var(--border-focus);
  color: #fff;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  height: calc(100vh - 65px);
}
@media (max-width: 1080px) {
  .layout {
    grid-template-columns: 1fr;
    height: auto;
  }
}

.main-view {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.map-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  position: relative;
}
.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
.svg-container {
  width: 100%;
  max-height: 520px;
  display: flex;
  justify-content: center;
  align-items: center;
}
svg#grid {
  width: 100%;
  height: auto;
  max-height: 500px;
  display: block;
}

/* Hex styling */
.hex-base {
  stroke: var(--hex-stroke);
  stroke-width: 0.8;
  cursor: pointer;
  transition: fill 0.35s ease, stroke 0.2s;
}
.hex-base:hover {
  stroke: #94a3b8;
  stroke-width: 1.5;
}
.hex-selected {
  stroke: #60a5fa !important;
  stroke-width: 2.2 !important;
}

/* Organism Glyphs */
.org-glyph {
  cursor: pointer;
  transition: transform 0.4s ease;
}
.org-outer-ring {
  fill: none;
  stroke-width: 2.2;
  transition: stroke 0.3s, stroke-dashoffset 0.3s;
}
.org-inner-core {
  transition: r 0.3s, fill 0.3s;
}
.org-pulse {
  animation: pulse-ring 1.2s infinite ease-out;
}
@keyframes pulse-ring {
  0% { r: 6px; opacity: 0.8; stroke-width: 2px; }
  100% { r: 16px; opacity: 0; stroke-width: 0.5px; }
}

.org-label {
  fill: #fff;
  font-family: var(--font-mono);
  font-size: 8px;
  text-anchor: middle;
  pointer-events: none;
  font-weight: 700;
}

.map-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 11px;
}
.legend-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-muted);
}
.swatch {
  width: 9px;
  height: 9px;
  border-radius: 2px;
}

/* Charts section */
.charts-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
}
.chart-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
}
canvas#timelineCanvas {
  width: 100%;
  height: 120px;
  display: block;
}

/* Sidebar HUD */
.sidebar {
  background: var(--surface);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.inspector-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
}
.tab-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 10px 4px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}
.tab-btn:hover {
  color: #fff;
}
.tab-btn.active {
  color: #60a5fa;
  border-bottom-color: #60a5fa;
  background: var(--surface);
}

.inspector-body {
  padding: 14px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.epistemic-banner {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 11px;
  color: #93c5fd;
  line-height: 1.35;
}

.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.info-table tr {
  border-bottom: 1px solid var(--border);
}
.info-table tr:last-child {
  border-bottom: none;
}
.info-table td {
  padding: 6px 0;
}
.info-table .lbl {
  color: var(--text-muted);
  width: 44%;
}
.info-table .val {
  font-family: var(--font-mono);
  font-weight: 500;
  text-align: right;
}

.bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}
.bar-track {
  width: 70px;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
}

/* Event feed */
.event-card {
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 260px;
}
.event-card-header {
  padding: 10px 14px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--panel);
  display: flex;
  justify-content: space-between;
}
.event-feed {
  padding: 8px 14px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.event-item {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 11px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.event-row1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.event-badge {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}
.ev-HAZARD_EXPOSURE { background: rgba(245, 158, 11, 0.18); color: #fcd34d; }
.ev-PHYSIOLOGICAL_DAMAGE { background: rgba(244, 63, 94, 0.18); color: #fda4af; }
.ev-REPAIR { background: rgba(16, 185, 129, 0.18); color: #6ee7b7; }
.ev-RESOURCE_ACQUIRED { background: rgba(6, 182, 212, 0.18); color: #67e8f9; }
.ev-DEATH { background: rgba(153, 27, 27, 0.35); color: #fca5a5; }
.ev-GENERIC { background: rgba(100, 116, 139, 0.2); color: #cbd5e1; }

.event-causal {
  font-size: 10px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
.event-causal .parent {
  color: #60a5fa;
}

details.raw-section {
  padding: 8px 14px;
  border-top: 1px solid var(--border);
}
details.raw-section summary {
  cursor: pointer;
  font-size: 11px;
  color: var(--text-muted);
}
details.raw-section pre {
  margin: 6px 0 0;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px;
  font-size: 10px;
  max-height: 140px;
  overflow: auto;
}
</style>
</head>
<body>

<header>
  <div class="brand">
    <h1>Symbiont World — Scientific Observatory</h1>
    <div class="sub">Read-only apparatus · Ground truth decoupled from organism cognition</div>
  </div>

  <div class="top-bar">
    <div class="controls-bar" id="overlayControls">
      <button class="ctrl-btn active" data-overlay="region">Region</button>
      <button class="ctrl-btn" data-overlay="resources">Resources</button>
      <button class="ctrl-btn" data-overlay="hazards">Hazards</button>
      <button class="ctrl-btn" data-overlay="fields">Fields</button>
      <button class="ctrl-btn" data-overlay="population">Population</button>
    </div>

    <div id="statusBadge" class="badge">
      <span class="badge-dot"></span>
      <span id="statusText">Connecting…</span>
    </div>
  </div>
</header>

<div class="layout">
  <!-- Left/Center Column -->
  <div class="main-view">
    <div class="map-card">
      <div class="map-header">
        <span id="worldInfo">World: ...</span>
        <span id="selectionInfo">Select cell or organism to inspect</span>
      </div>

      <div class="svg-container">
        <svg id="grid" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
          <g id="hexLayer"></g>
          <g id="selectionLayer"></g>
          <g id="organismLayer"></g>
        </svg>
      </div>

      <div class="map-footer">
        <div class="legend-group" id="legendContainer"></div>
        <div id="fieldsSummary" style="color:var(--text-muted)"></div>
      </div>
    </div>

    <div class="charts-card">
      <div class="chart-header">
        <span>Timeline Telemetry (Alive, Integrity, Reserve)</span>
        <span id="timelineStats" style="font-family:var(--font-mono);font-size:11px;">0 ticks recorded</span>
      </div>
      <canvas id="timelineCanvas" width="900" height="120"></canvas>
    </div>
  </div>

  <!-- Right Sidebar: Epistemological Inspector & Causal Journal -->
  <div class="sidebar">
    <div class="inspector-tabs" id="inspectorTabs">
      <button class="tab-btn" data-tab="reality">[ Reality ]</button>
      <button class="tab-btn active" data-tab="phenotype">[ Phenotype ]</button>
      <button class="tab-btn" data-tab="perception">[ Perception ]</button>
      <button class="tab-btn" data-tab="self">[ Self ]</button>
    </div>

    <div class="inspector-body" id="inspectorContent">
      <div class="epistemic-banner" id="tabNotice">
        Select an organism or terrain cell on the map to inspect telemetry across epistemological perspectives.
      </div>
      <div id="inspectorDetails">
        <p style="color:var(--text-muted);font-size:12px;margin:12px 0;">No active selection. Click any cell or organism glyph on the grid.</p>
      </div>
    </div>

    <div class="event-card">
      <div class="event-card-header">
        <span>Causal Event Stream (Committed)</span>
        <span id="eventCount">0 events</span>
      </div>
      <div class="event-feed" id="eventFeed">
        <div style="color:var(--text-muted);font-size:11px;padding:8px 0;">Awaiting journal events…</div>
      </div>
    </div>

    <details class="raw-section">
      <summary>Raw World State View</summary>
      <pre id="rawView">Loading…</pre>
    </details>
  </div>
</div>

<script>
const SVG_NS = "http://www.w3.org/2000/svg";
const HEX_SIZE = 32;

// Regional palette
const REGION_PALETTE = {
  "north": "#1e3a5f",
  "south": "#2d3748",
  "rich biome": "#164e63",
  "arid": "#451a03",
  "temperate": "#14532d",
  "cold": "#1e293b",
};
const FALLBACK_COLORS = ["#1e3a5f", "#14532d", "#312e81", "#3b0764", "#4a044e", "#1e293b"];

// App State
let worldData = null;
let activeOverlay = "region";
let activeTab = "phenotype";
let selectedCoord = null;
let selectedOrgId = null;

// Persistent SVG Nodes (Section 30)
const cellNodes = new Map();
const orgNodes = new Map();
let selectionPolygon = null;
let initializedGrid = false;

function axialToPixel(q, r) {
  const x = HEX_SIZE * Math.sqrt(3) * (q + r / 2);
  const y = HEX_SIZE * 1.5 * r;
  return [x, y];
}

function hexPoints(cx, cy, radius = HEX_SIZE) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push((cx + radius * Math.cos(angle)).toFixed(2) + "," + (cy + radius * Math.sin(angle)).toFixed(2));
  }
  return pts.join(" ");
}

function getRegionColor(region) {
  if (!region) return "#151e2b";
  if (REGION_PALETTE[region]) return REGION_PALETTE[region];
  let hash = 0;
  for (let i = 0; i < region.length; i++) hash = (hash * 31 + region.charCodeAt(i)) >>> 0;
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length];
}

function initSvgGrid(data) {
  const svg = document.getElementById("grid");
  const hexLayer = document.getElementById("hexLayer");
  const selLayer = document.getElementById("selectionLayer");
  const orgLayer = document.getElementById("organismLayer");

  hexLayer.innerHTML = "";
  selLayer.innerHTML = "";
  orgLayer.innerHTML = "";
  cellNodes.clear();
  orgNodes.clear();

  const width = data.width || 8;
  const height = data.height || 8;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let q = 0; q < width; q++) {
    for (let r = 0; r < height; r++) {
      const [x, y] = axialToPixel(q, r);
      minX = Math.min(minX, x - HEX_SIZE);
      maxX = Math.max(maxX, x + HEX_SIZE);
      minY = Math.min(minY, y - HEX_SIZE);
      maxY = Math.max(maxY, y + HEX_SIZE);
    }
  }

  const pad = 18;
  svg.setAttribute("viewBox", `${minX - pad} ${minY - pad} ${maxX - minX + pad * 2} ${maxY - minY + pad * 2}`);

  // Base hex grid
  for (let q = 0; q < width; q++) {
    for (let r = 0; r < height; r++) {
      const key = `${q},${r}`;
      const [cx, cy] = axialToPixel(q, r);

      const poly = document.createElementNS(SVG_NS, "polygon");
      poly.setAttribute("points", hexPoints(cx, cy));
      poly.setAttribute("class", "hex-base");
      poly.setAttribute("data-key", key);

      const title = document.createElementNS(SVG_NS, "title");
      poly.appendChild(title);

      poly.addEventListener("click", () => {
        selectCell(key);
      });

      hexLayer.appendChild(poly);
      cellNodes.set(key, { poly, title, cx, cy });
    }
  }

  // Selection highlight outline
  selectionPolygon = document.createElementNS(SVG_NS, "polygon");
  selectionPolygon.setAttribute("class", "hex-selected");
  selectionPolygon.setAttribute("fill", "none");
  selectionPolygon.setAttribute("points", "");
  selectionPolygon.style.display = "none";
  selLayer.appendChild(selectionPolygon);

  initializedGrid = true;
}

function updateMap(data) {
  if (!initializedGrid || cellNodes.size === 0) {
    initSvgGrid(data);
  }

  // Update base cells according to active overlay
  for (const [key, node] of cellNodes.entries()) {
    const cell = data.cells ? data.cells[key] : null;
    const region = cell ? cell.region : "unknown";
    const baseColor = getRegionColor(region);

    let fillColor = baseColor;
    let strokeColor = "var(--hex-stroke)";
    let tooltip = `Cell (${key}) - Region: ${region}`;

    if (cell) {
      if (activeOverlay === "region") {
        fillColor = baseColor;
      } else if (activeOverlay === "resources") {
        let totalRes = 0;
        let totalCap = 0;
        if (cell.resources && cell.resource_capacities) {
          for (const [rk, val] of Object.entries(cell.resources)) {
            const cap = cell.resource_capacities[rk];
            if (cap == null) continue;
            totalRes += val;
            totalCap += cap;
          }
        }
        const ratio = totalCap > 0 ? Math.min(1.0, totalRes / totalCap) : 0.0;
        fillColor = `rgba(16, 185, 129, ${0.12 + ratio * 0.75})`;
        tooltip += `\nResources: ${totalRes.toFixed(2)} / ${totalCap.toFixed(2)}`;
      } else if (activeOverlay === "hazards") {
        let maxExposure = 0;
        if (cell.hazards) {
          for (const val of Object.values(cell.hazards)) {
            maxExposure = Math.max(maxExposure, val);
          }
        }
        const hazardIntensity = Math.min(1.0, maxExposure * 2.0);
        fillColor = hazardIntensity > 0
          ? `rgba(244, 63, 94, ${0.15 + hazardIntensity * 0.75})`
          : baseColor;
        tooltip += `\nMax Hazard Exposure: ${maxExposure.toFixed(4)}`;
      } else if (activeOverlay === "fields") {
        fillColor = baseColor;
        strokeColor = "#38bdf8";
        tooltip += `\nAmbient Fields Active`;
      } else if (activeOverlay === "population") {
        const isOcc = !!cell.occupant;
        fillColor = isOcc ? "#1e3a8a" : "#0d131a";
        tooltip += isOcc ? `\nOccupant: ${cell.occupant}` : `\nUnoccupied`;
      }

      if (cell.resources) {
        for (const [k, v] of Object.entries(cell.resources)) {
          tooltip += `\n  res [${k}]: ${v.toFixed(2)}`;
        }
      }
      if (cell.hazards) {
        for (const [k, v] of Object.entries(cell.hazards)) {
          tooltip += `\n  hazard [${k}]: ${v.toFixed(3)}`;
        }
      }
    }

    node.poly.setAttribute("fill", fillColor);
    node.poly.setAttribute("stroke", strokeColor);
    node.title.textContent = tooltip;
  }

  // Update selection polygon
  if (selectedCoord && cellNodes.has(selectedCoord)) {
    const node = cellNodes.get(selectedCoord);
    selectionPolygon.setAttribute("points", hexPoints(node.cx, node.cy, HEX_SIZE + 1.5));
    selectionPolygon.style.display = "block";
  } else {
    selectionPolygon.style.display = "none";
  }

  // Update organism glyphs (Section 19, 20, 21)
  const orgLayer = document.getElementById("organismLayer");
  const activeIds = new Set();

  if (data.organisms) {
    for (const org of data.organisms) {
      activeIds.add(org.id);
      const coordKey = `${org.q},${org.r}`;
      const cellNode = cellNodes.get(coordKey);
      if (!cellNode) continue;

      let orgGroup = orgNodes.get(org.id);
      if (!orgGroup) {
        // Create new organism glyph group
        const g = document.createElementNS(SVG_NS, "g");
        g.setAttribute("class", "org-glyph");

        // Action / damage pulse
        const pulse = document.createElementNS(SVG_NS, "circle");
        pulse.setAttribute("r", "10");
        pulse.setAttribute("fill", "none");
        pulse.setAttribute("stroke", "#f43f5e");
        pulse.setAttribute("class", "org-pulse");
        pulse.style.display = "none";
        g.appendChild(pulse);

        // Outer health/integrity ring
        const outer = document.createElementNS(SVG_NS, "circle");
        outer.setAttribute("r", "13");
        outer.setAttribute("class", "org-outer-ring");
        g.appendChild(outer);

        // Inner metabolic reserve core
        const core = document.createElementNS(SVG_NS, "circle");
        core.setAttribute("class", "org-inner-core");
        g.appendChild(core);

        // ID label
        const lbl = document.createElementNS(SVG_NS, "text");
        lbl.setAttribute("class", "org-label");
        lbl.setAttribute("y", "3");
        g.appendChild(lbl);

        g.addEventListener("click", (e) => {
          e.stopPropagation();
          selectOrganism(org.id, coordKey);
        });

        orgLayer.appendChild(g);
        orgGroup = { g, outer, core, pulse, lbl };
        orgNodes.set(org.id, orgGroup);
      }

      // Position
      orgGroup.g.setAttribute("transform", `translate(${cellNode.cx}, ${cellNode.cy})`);

      // Integrity ring color
      const integ = org.integrity;
      let ringColor = "#64748b"; // unknown
      if (integ != null) {
        ringColor = "#10b981";
        if (integ < 0.4) ringColor = "#f43f5e";
        else if (integ < 0.75) ringColor = "#f59e0b";
      }
      orgGroup.outer.setAttribute("stroke", ringColor);

      // Vital state dash pattern
      if (org.vital_state === "stressed") {
        orgGroup.outer.setAttribute("stroke-dasharray", "4,2");
      } else if (org.vital_state === "dormant") {
        orgGroup.outer.setAttribute("stroke-dasharray", "2,2");
      } else {
        orgGroup.outer.removeAttribute("stroke-dasharray");
      }

      // Metabolic reserve core
      const reserve = org.metabolic_reserve;
      const coreRadius = reserve != null ? Math.max(3, 9 * reserve) : 3;
      orgGroup.core.setAttribute("r", coreRadius.toFixed(1));
      orgGroup.core.setAttribute("fill", reserve != null && org.alive ? "#38bdf8" : "#475569");

      // Action / Damage pulse
      if (org.recent_damage && org.recent_damage > 0) {
        orgGroup.pulse.style.display = "block";
        orgGroup.pulse.setAttribute("stroke", "#f43f5e");
      } else if (org.last_action && org.last_action.includes("intake")) {
        orgGroup.pulse.style.display = "block";
        orgGroup.pulse.setAttribute("stroke", "#10b981");
      } else {
        orgGroup.pulse.style.display = "none";
      }

      // Label
      const shortId = org.id.replace(/^founder-/, "#").substring(0, 5);
      orgGroup.lbl.textContent = shortId;
    }
  }

  // Remove dead/unoccupied organisms no longer reported
  for (const [id, orgGroup] of orgNodes.entries()) {
    if (!activeIds.has(id)) {
      orgLayer.removeChild(orgGroup.g);
      orgNodes.delete(id);
    }
  }

  // Update Legend & Header
  document.getElementById("worldInfo").textContent =
    `World: ${data.world_id || "Genesis"} · Grid: ${data.width || 8}x${data.height || 8} · Organisms: ${data.alive_count || 0}`;

  updateLegend(data);
}

function updateLegend(data) {
  const legend = document.getElementById("legendContainer");
  const regions = new Set();
  if (data.cells) {
    for (const c of Object.values(data.cells)) {
      if (c.region) regions.add(c.region);
    }
  }

  let html = "";
  for (const r of regions) {
    const col = getRegionColor(r);
    html += `<span class="legend-item"><span class="swatch" style="background:${col}"></span>${r}</span>`;
  }
  html += `<span class="legend-item" style="margin-left:8px;"><span class="swatch" style="background:#10b981"></span>Integrity</span>`;
  html += `<span class="legend-item"><span class="swatch" style="background:#38bdf8"></span>Reserve</span>`;
  legend.innerHTML = html;

  const fieldsDiv = document.getElementById("fieldsSummary");
  if (data.fields && Object.keys(data.fields).length > 0) {
    const fieldPairs = Object.entries(data.fields).map(([k, v]) => `${k}=${v.toFixed(2)}`);
    fieldsDiv.textContent = `Fields: ${fieldPairs.join("  ")}`;
  } else {
    fieldsDiv.textContent = "";
  }
}

function selectCell(coordKey) {
  selectedCoord = coordKey;
  // If occupied, select organism automatically
  selectedOrgId = null;
  if (worldData && worldData.organisms) {
    const found = worldData.organisms.find(o => `${o.q},${o.r}` === coordKey);
    if (found) selectedOrgId = found.id;
  }
  updateInspector();
  if (worldData) updateMap(worldData);
}

function selectOrganism(orgId, coordKey) {
  selectedOrgId = orgId;
  selectedCoord = coordKey;
  updateInspector();
  if (worldData) updateMap(worldData);
}

function updateInspector() {
  const details = document.getElementById("inspectorDetails");
  const notice = document.getElementById("tabNotice");
  const selInfo = document.getElementById("selectionInfo");

  if (!selectedCoord) {
    selInfo.textContent = "Select cell or organism to inspect";
    details.innerHTML = `<p style="color:var(--text-muted);font-size:12px;margin:12px 0;">No active selection. Click any cell or organism glyph on the grid.</p>`;
    return;
  }

  selInfo.textContent = `Inspecting Cell (${selectedCoord})` + (selectedOrgId ? ` · Organism: ${selectedOrgId}` : "");

  const cell = (worldData && worldData.cells) ? worldData.cells[selectedCoord] : null;
  const org = (worldData && worldData.organisms && selectedOrgId)
    ? worldData.organisms.find(o => o.id === selectedOrgId)
    : null;

  // Epistemological tabs explanation (Section 24, 25)
  if (activeTab === "reality") {
    notice.innerHTML = `<strong>REALITY (Ground Truth):</strong> Objective facts of the physical habitat. Bounded laws, real resource stores, local exposure, ambient fields. Never visible to organism cognition.`;
    details.innerHTML = renderRealityTab(cell, org);
  } else if (activeTab === "phenotype") {
    notice.innerHTML = `<strong>PHENOTYPE:</strong> Actual physiological state and biological behavior of the organism. Measured directly by evaluator apparatus.`;
    details.innerHTML = renderPhenotypeTab(org, cell);
  } else if (activeTab === "perception") {
    notice.innerHTML = `<strong>PERCEPTION:</strong> Signals effectively received through local sensory reading providers. Bounded, noisy, subjective transductions.`;
    details.innerHTML = renderPerceptionTab(org);
  } else if (activeTab === "self") {
    notice.innerHTML = `<strong>SELF (Internal Representation):</strong> Private model, hypothesis generation, concepts, prediction confidence, and self-model structure.`;
    details.innerHTML = renderSelfTab(org);
  }
}

function renderRealityTab(cell, org) {
  if (!cell) return `<p style="color:var(--text-muted)">Cell not materialized.</p>`;
  let resRows = "";
  if (cell.resources) {
    for (const [k, v] of Object.entries(cell.resources)) {
      const cap = cell.resource_capacities ? cell.resource_capacities[k] : null;
      const pct = cap != null && cap > 0 ? Math.min(100, Math.round((v / cap) * 100)) : 0;
      resRows += `<tr>
        <td class="lbl">${k}</td>
        <td class="val">
          <div class="bar-wrap">
            <span>${v.toFixed(3)}${cap != null ? ` / ${cap.toFixed(1)}` : " / not available"}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
          </div>
        </td>
      </tr>`;
    }
  }

  let hazRows = "";
  if (cell.hazards) {
    for (const [k, v] of Object.entries(cell.hazards)) {
      hazRows += `<tr>
        <td class="lbl">${k}</td>
        <td class="val" style="color:${v > 0.1 ? '#f43f5e' : 'inherit'}">${v.toFixed(4)}</td>
      </tr>`;
    }
  }

  return `
    <table class="info-table">
      <tr><td class="lbl">Coordinates (q, r)</td><td class="val">${cell.q}, ${cell.r}</td></tr>
      <tr><td class="lbl">Biome Region</td><td class="val">${cell.region != null ? cell.region : "(none)"}</td></tr>
      <tr><td class="lbl">Local Density</td><td class="val">${(cell.density || 0.0).toFixed(3)}</td></tr>
      <tr><td class="lbl">Occupant</td><td class="val">${cell.occupant || "(empty)"}</td></tr>
    </table>
    <div style="font-weight:600;font-size:11px;color:var(--text-muted);margin:10px 0 4px;">Local Resources</div>
    <table class="info-table">${resRows || '<tr><td colspan="2" style="color:var(--text-muted)">No resources present</td></tr>'}</table>
    <div style="font-weight:600;font-size:11px;color:var(--text-muted);margin:10px 0 4px;">Real Hazard Exposure</div>
    <table class="info-table">${hazRows || '<tr><td colspan="2" style="color:var(--text-muted)">No hazard active</td></tr>'}</table>
  `;
}

function renderPhenotypeTab(org, cell) {
  if (!org) {
    return `<p style="color:var(--text-muted);font-size:12px;">This cell has no live occupant. Select an organism glyph to inspect phenotype.</p>`;
  }
  const integ = org.integrity;
  const integPct = integ != null ? Math.round(integ * 100) : 0;
  const res = org.metabolic_reserve;
  const resPct = res != null ? Math.round(res * 100) : 0;

  return `
    <table class="info-table">
      <tr><td class="lbl">Organism ID</td><td class="val">${org.id}</td></tr>
      <tr><td class="lbl">Vital State</td><td class="val" style="color:#60a5fa">${org.vital_state != null ? org.vital_state : "not available"}</td></tr>
      <tr><td class="lbl">Alive</td><td class="val">${org.alive ? "Yes" : "No"}</td></tr>
      <tr><td class="lbl">Generation</td><td class="val">${org.generation != null ? org.generation : "not available"}</td></tr>
      <tr><td class="lbl">Age (ticks)</td><td class="val">${org.age != null ? org.age : "not available"}</td></tr>
      <tr>
        <td class="lbl">Integrity</td>
        <td class="val">
          <div class="bar-wrap">
            <span>${integ != null ? integ.toFixed(3) : "not available"}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${integPct}%;background:${integ != null && integ < 0.4 ? '#f43f5e' : '#10b981'}"></div></div>
          </div>
        </td>
      </tr>
      <tr>
        <td class="lbl">Metabolic Reserve</td>
        <td class="val">
          <div class="bar-wrap">
            <span>${res != null ? res.toFixed(3) : "not available"}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${resPct}%;background:#38bdf8"></div></div>
          </div>
        </td>
      </tr>
      <tr><td class="lbl">Metabolic Pressure</td><td class="val">${org.metabolic_pressure != null ? org.metabolic_pressure : "not available"}</td></tr>
      <tr><td class="lbl">Last Action</td><td class="val" style="color:#fcd34d">${org.last_action || "none"}</td></tr>
      <tr><td class="lbl">Recent Damage</td><td class="val" style="color:${org.recent_damage > 0 ? '#f43f5e' : 'inherit'}">${org.recent_damage != null ? org.recent_damage.toFixed(3) : "not available"}</td></tr>
    </table>
  `;
}

function renderPerceptionTab(org) {
  if (!org) {
    return `<p style="color:var(--text-muted);font-size:12px;">No organism selected. Select an organism to view perceived sensory signals.</p>`;
  }
  if (!org.perception || Object.keys(org.perception).length === 0) {
    return `<p style="color:var(--text-muted);font-size:12px;">No sensory readings registered in current tick.</p>`;
  }
  let rows = "";
  for (const [sig, val] of Object.entries(org.perception)) {
    rows += `<tr>
      <td class="lbl">${sig}</td>
      <td class="val">${typeof val === "number" ? val.toFixed(4) : val}</td>
    </tr>`;
  }
  return `
    <div style="font-weight:600;font-size:11px;color:var(--text-muted);margin-bottom:8px;">Transduced Input Signals</div>
    <table class="info-table">${rows}</table>
  `;
}

function renderSelfTab(org) {
  if (!org) {
    return `<p style="color:var(--text-muted);font-size:12px;">No organism selected. Select an organism to view private cognitive representations.</p>`;
  }
  const cog = org.cognition || {};
  const conf = cog.prediction_confidence;
  const confPct = conf != null ? Math.round(conf * 100) : 0;
  const bridgeState = cog.private_model_bridge_active === true
    ? "active"
    : (cog.private_model_bridge_active === false ? "not attached" : "not available");
  const interoceptionState = cog.interoception_mode != null
    ? cog.interoception_mode
    : "not available";

  return `
    <table class="info-table">
      <tr><td class="lbl">Acquired Concepts</td><td class="val">${cog.concept_count != null ? cog.concept_count : "not available"}</td></tr>
      <tr>
        <td class="lbl">Prediction Confidence</td>
        <td class="val">
          <div class="bar-wrap">
            <span>${conf != null ? conf.toFixed(3) : "not available"}</span>
            <div class="bar-track"><div class="bar-fill" style="width:${confPct}%;background:#a855f7"></div></div>
          </div>
        </td>
      </tr>
      <tr><td class="lbl">Private Model Bridge</td><td class="val">${bridgeState}</td></tr>
      <tr><td class="lbl">Interoception Surface</td><td class="val">${interoceptionState}</td></tr>
    </table>
    <div style="margin-top:12px;font-size:11px;color:var(--text-muted);line-height:1.4;">
      <em>The organism perceives opaque signals and builds its own concepts without knowledge of human labels or evaluator ground truth.</em>
    </div>
  `;
}

// Native Canvas Timeline Charts (Section 27, 28)
function renderTimeline(history) {
  const canvas = document.getElementById("timelineCanvas");
  if (!canvas || !history || !history.ticks || history.ticks.length < 2) return;

  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const ticks = history.ticks;
  const alive = history.alive || [];
  const integrity = history.mean_integrity || [];
  const reserve = history.mean_reserve || [];
  const n = ticks.length;

  document.getElementById("timelineStats").textContent = `${n} ticks (${ticks[0]} → ${ticks[n - 1]})`;

  // Draw grid
  ctx.strokeStyle = "rgba(34, 45, 61, 0.8)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let y = 20; y < h; y += 30) {
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
  }
  ctx.stroke();

  // Helper to plot series
  function plotSeries(series, maxVal, color, lineWidth = 2) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * (w - 20) + 10;
      const val = series[i] != null ? series[i] : 0;
      const y = h - 12 - (val / (maxVal || 1)) * (h - 24);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // Alive count (scaled to max alive observed)
  const maxAlive = Math.max(8, ...alive);
  plotSeries(alive, maxAlive, "#60a5fa", 2);

  // Mean integrity (0.0 to 1.0)
  plotSeries(integrity, 1.0, "#10b981", 1.5);

  // Mean reserve (0.0 to 1.0)
  plotSeries(reserve, 1.0, "#38bdf8", 1.5);

  // Legend on canvas
  ctx.font = "10px ui-monospace, monospace";
  ctx.fillStyle = "#60a5fa";
  ctx.fillText(`Alive (${alive[n - 1] != null ? alive[n - 1] : 0})`, 10, 14);
  ctx.fillStyle = "#10b981";
  ctx.fillText(`Integrity (${(integrity[n - 1] != null ? integrity[n - 1] : 0).toFixed(2)})`, 100, 14);
  ctx.fillStyle = "#38bdf8";
  ctx.fillText(`Reserve (${(reserve[n - 1] != null ? reserve[n - 1] : 0).toFixed(2)})`, 200, 14);
}

// Causal Event Feed (Section 29)
function updateEventFeed(events) {
  const feed = document.getElementById("eventFeed");
  const countSpan = document.getElementById("eventCount");
  if (!events || events.length === 0) {
    feed.innerHTML = `<div style="color:var(--text-muted);font-size:11px;padding:8px 0;">No committed events in journal.</div>`;
    countSpan.textContent = "0 events";
    return;
  }

  countSpan.textContent = `${events.length} events`;
  const recent = events.slice(-30).reverse();

  let html = "";
  for (const ev of recent) {
    const badgeCls = "ev-" + (ev.kind || "GENERIC");
    let provenance = "";
    if (ev.causal_parent_ids && ev.causal_parent_ids.length > 0) {
      provenance += ` ➔ causal parent: <span class="parent">${ev.causal_parent_ids.join(", ")}</span>`;
    }
    if (ev.contributing_event_ids && ev.contributing_event_ids.length > 0) {
      provenance += ` (contributing: ${ev.contributing_event_ids.join(", ")})`;
    }

    html += `
      <div class="event-item">
        <div class="event-row1">
          <span class="event-badge ${badgeCls}">${ev.kind}</span>
          <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-muted)">t=${ev.tick}</span>
        </div>
        <div style="font-size:11px;color:#cbd5e1;">Actor: <strong>${ev.actor || "world"}</strong> at (${ev.position || "ambient"})</div>
        ${provenance ? `<div class="event-causal">${provenance}</div>` : ""}
      </div>
    `;
  }
  feed.innerHTML = html;
}

// Wire Overlay Buttons
document.querySelectorAll("#overlayControls button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#overlayControls button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeOverlay = btn.dataset.overlay;
    if (worldData) updateMap(worldData);
  });
});

// Wire Inspector Tabs
document.querySelectorAll("#inspectorTabs button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#inspectorTabs button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeTab = btn.dataset.tab;
    updateInspector();
  });
});

// Polling loop (read-only GET /api/state)
async function poll() {
  try {
    const res = await fetch("/api/state");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    worldData = data;

    // Update status badge
    const badge = document.getElementById("statusBadge");
    const statusText = document.getElementById("statusText");
    if (data.error) {
      badge.className = "badge bad";
      statusText.textContent = `Error: ${data.error}`;
    } else {
      badge.className = data.running ? "badge" : "badge stopped";
      statusText.textContent = `${data.running ? "Running" : "Stopped"} · Tick ${data.tick} · ${data.alive_count} Alive`;
    }

    // Map & telemetry
    updateMap(data);
    updateInspector();
    if (data.history) renderTimeline(data.history);
    if (data.events) updateEventFeed(data.events);

    // Raw text view
    if (data.text) document.getElementById("rawView").textContent = data.text;
  } catch (err) {
    const badge = document.getElementById("statusBadge");
    badge.className = "badge bad";
    document.getElementById("statusText").textContent = "Disconnected";
  }
  setTimeout(poll, 700);
}

// Start polling
poll();
</script>
</body>
</html>
'''
