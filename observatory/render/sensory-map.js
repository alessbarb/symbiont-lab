import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";

const NS = "http://www.w3.org/2000/svg";

function shortId(value, head = 14, tail = 7) {
  if (typeof value !== "string") return "—";
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

function sourceLabel(signalId) {
  const sense = (state.senses ?? []).find(item => item.knowledgeSignalId === signalId);
  if (sense) return sense.name;
  return shortId(signalId, 15, 6);
}

function relationSignalId(value) {
  if (typeof value !== "string") return null;
  if (value.startsWith("signal.")) return value;
  const sense = (state.senses ?? []).find(item => item.id === value || item.name === value);
  return sense?.knowledgeSignalId ?? null;
}

function sensorRank(sensor) {
  return (sensor.selectionCredit ?? 0) * 4 + (sensor.utility ?? 0) * 3 + (sensor.confidence ?? 0);
}

function currentFilter() {
  return typeof state.sensoryModalityFilter === "string" ? state.sensoryModalityFilter : "all";
}

function filteredSensors() {
  const sensors = [...(state.sensoryPhenotype?.sensors ?? [])];
  const filter = currentFilter();
  return sensors
    .filter(sensor => filter === "all" || sensor.modalityId === filter)
    .sort((a, b) => sensorRank(b) - sensorRank(a) || a.sensorId.localeCompare(b.sensorId));
}

function sensorSignals(sensors) {
  const known = new Set();
  (state.signalKnowledge ?? []).forEach(item => {
    if (typeof item.signalId === "string") known.add(item.signalId);
  });
  (state.senses ?? []).forEach(item => {
    if (typeof item.knowledgeSignalId === "string") known.add(item.knowledgeSignalId);
  });
  sensors.forEach(sensor => (sensor.signalIds ?? []).forEach(id => known.add(id)));
  return [...known].sort();
}

function modalitySummary(container) {
  container.replaceChildren();
  const phenotype = state.sensoryPhenotype;
  if (!phenotype?.modalities?.length) {
    const empty = document.createElement("span");
    empty.className = "sensory-map-note";
    empty.textContent = "No sensory phenotype exported.";
    container.append(empty);
    return;
  }
  phenotype.modalities.forEach(modality => {
    const card = document.createElement("div");
    card.className = "sensory-modality-card";
    const title = document.createElement("strong");
    title.textContent = modality.modalityId;
    const stats = document.createElement("small");
    const primitives = modality.allowedTransductions?.length
      ? modality.allowedTransductions.join(" · ")
      : "legacy capability";
    stats.textContent = `${modality.sensorCount} sensors · max ${modality.maxInputs} input(s) · temporal ${modality.temporalCapacity}`;
    const ops = document.createElement("em");
    ops.textContent = primitives;
    card.append(title, stats, ops);
    container.append(card);
  });
}

function installFilter(select, modalities) {
  const wanted = currentFilter();
  const values = ["all", ...modalities.map(item => item.modalityId)];
  const signature = values.join("|");
  if (select.dataset.signature !== signature) {
    select.replaceChildren();
    values.forEach(value => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value === "all" ? "All substrate classes" : value;
      select.append(option);
    });
    select.dataset.signature = signature;
  }
  select.value = values.includes(wanted) ? wanted : "all";
}

function renderEmpty(canvas, detail) {
  canvas.replaceChildren();
  canvas.setAttribute("viewBox", "0 0 900 620");
  const title = svg("text", { x: "450", y: "280", "text-anchor": "middle", class: "sensory-map-empty-title" });
  title.textContent = "No organism-owned sensors are exported yet";
  const copy = svg("text", { x: "450", y: "310", "text-anchor": "middle", class: "sensory-map-empty-copy" });
  copy.textContent = "World signals can exist before a sensory phenotype develops.";
  canvas.append(title, copy);
  detail.textContent = "Select a live organism with sensory phenotype telemetry.";
}

function rectNode(x, y, width, height, className, title, subtitle) {
  const group = svg("g", { class: className });
  group.append(svg("rect", { x, y, width, height, rx: "8" }));
  const t = svg("text", { x: x + 12, y: y + 17, class: "sensory-map-node-title" });
  t.textContent = title;
  group.append(t);
  if (subtitle) {
    const s = svg("text", { x: x + 12, y: y + 31, class: "sensory-map-node-subtitle" });
    s.textContent = subtitle;
    group.append(s);
  }
  return group;
}

function renderDetail(detail, sensor) {
  detail.replaceChildren();
  if (!sensor) {
    detail.textContent = "Select a receptor to inspect its world bindings and downstream path.";
    return;
  }
  const heading = document.createElement("strong");
  heading.textContent = sensor.sensorId;
  const line = document.createElement("span");
  line.textContent = `${sensor.sampleGeometry || "scalar"} → ${sensor.transduction || "identity"} → ${sensor.downstreamName || "SENSE"}`;
  const metrics = document.createElement("span");
  metrics.textContent = `utility ${sensor.utility.toFixed(3)} · selection ${sensor.selectionCredit.toFixed(3)} · confidence ${sensor.confidence.toFixed(3)} · cost ${sensor.cost.toFixed(3)}`;
  const sources = document.createElement("span");
  sources.textContent = sensor.signalIds?.length
    ? `world: ${sensor.signalIds.map(id => sourceLabel(id)).join(" + ")}`
    : "world: source lineage not exported";
  detail.append(heading, line, metrics, sources);
}

function renderSensoryMap() {
  const wrap = document.querySelector("#sensory-map-wrap");
  const canvas = document.querySelector("#sensory-world-canvas");
  const detail = document.querySelector("#sensory-map-detail");
  const modalityCards = document.querySelector("#sensory-modality-cards");
  const filter = document.querySelector("#sensory-modality-filter");
  if (!wrap || !canvas || !detail || !modalityCards || !filter) return;

  const phenotype = state.sensoryPhenotype;
  const modalities = phenotype?.modalities ?? [];
  installFilter(filter, modalities);
  modalitySummary(modalityCards);

  if (!phenotype?.sensors?.length) {
    renderEmpty(canvas, detail);
    return;
  }

  const sensors = filteredSensors();
  const signals = sensorSignals(sensors);
  const cognitionNames = [...new Set(sensors.map(sensor => sensor.downstreamName).filter(Boolean))].sort();

  const row = 48;
  const top = 125;
  const sourceY = new Map(signals.map((id, index) => [id, top + index * row]));
  const sensorY = new Map(sensors.map((item, index) => [item.sensorId, top + index * row]));
  const cognitionY = new Map(cognitionNames.map((name, index) => [name, top + index * row]));
  const height = Math.max(620, top + Math.max(signals.length, sensors.length, cognitionNames.length, 1) * row + 90);
  canvas.setAttribute("viewBox", `0 0 900 ${height}`);
  canvas.replaceChildren();

  const headings = [
    [95, "WORLD / SIGNALS", "environment-owned"],
    [450, "RECEPTORS", "organism-owned"],
    [790, "COGNITION", "downstream"],
  ];
  headings.forEach(([x, title, sub]) => {
    const h = svg("text", { x, y: "66", "text-anchor": "middle", class: "sensory-map-column-title" });
    h.textContent = title;
    const s = svg("text", { x, y: "84", "text-anchor": "middle", class: "sensory-map-column-subtitle" });
    s.textContent = sub;
    canvas.append(h, s);
  });

  // World/world relations are discovered source structure, not receptor structure.
  (state.sensoryRelations ?? []).forEach(relation => {
    const left = relationSignalId(relation.senseA);
    const right = relationSignalId(relation.senseB);
    if (!left || !right || !sourceY.has(left) || !sourceY.has(right) || left === right) return;
    const y1 = sourceY.get(left) + 18;
    const y2 = sourceY.get(right) + 18;
    const strength = Math.max(
      Math.abs(Number(relation.synchronous) || 0),
      Math.abs(Number(relation.aToB) || 0),
      Math.abs(Number(relation.bToA) || 0),
    );
    canvas.append(svg("path", {
      d: `M 20 ${y1 + 16} C 2 ${y1 + 24}, 2 ${y2 - 8}, 20 ${y2}`,
      class: "sensory-world-relation",
      "stroke-opacity": String(Math.max(0.18, Math.min(0.75, strength))),
    }));
  });

  // World -> receptor -> cognition links render before nodes.
  sensors.forEach(sensor => {
    const sy = sensorY.get(sensor.sensorId) + 18;
    (sensor.signalIds ?? []).forEach(signalId => {
      if (!sourceY.has(signalId)) return;
      const y = sourceY.get(signalId) + 18;
      canvas.append(svg("path", {
        d: `M 185 ${y} C 275 ${y}, 305 ${sy}, 360 ${sy}`,
        class: "sensory-world-link",
      }));
    });
    if (sensor.downstreamName && cognitionY.has(sensor.downstreamName)) {
      const cy = cognitionY.get(sensor.downstreamName) + 18;
      canvas.append(svg("path", {
        d: `M 540 ${sy} C 625 ${sy}, 650 ${cy}, 700 ${cy}`,
        class: sensor.selectionCredit > 0 ? "sensory-cognition-link selected-credit" : "sensory-cognition-link",
      }));
    }
    (sensor.parentSensorIds ?? []).forEach(parentId => {
      if (!sensorY.has(parentId)) return;
      const py = sensorY.get(parentId) + 18;
      canvas.append(svg("path", {
        d: `M 450 ${py + 18} C 420 ${py + 30}, 420 ${sy - 12}, 450 ${sy}`,
        class: "sensory-lineage-link",
      }));
    });
  });

  signals.forEach(signalId => {
    const y = sourceY.get(signalId);
    const sense = (state.senses ?? []).find(item => item.knowledgeSignalId === signalId);
    const subtitle = sense ? `${sense.active ? "available" : "unavailable"} · q ${sense.quality.toFixed(2)}` : shortId(signalId, 13, 5);
    const node = rectNode(12, y, 173, 37, "sensory-world-node", sourceLabel(signalId), subtitle);
    canvas.append(node);
  });

  sensors.forEach(sensor => {
    const y = sensorY.get(sensor.sensorId);
    const selected = state.selectedSensorySensorId === sensor.sensorId;
    const node = rectNode(
      360, y, 180, 37,
      `sensory-receptor-node ${selected ? "selected" : ""} maturity-${sensor.maturity}`,
      shortId(sensor.sensorId, 18, 6),
      `${sensor.transduction || "identity"} · ${sensor.modalityId}`
    );
    node.setAttribute("role", "button");
    node.setAttribute("tabindex", "0");
    node.style.cursor = "pointer";
    const choose = () => {
      state.selectedSensorySensorId = sensor.sensorId;
      state.selectedSignalId = sensor.signalIds?.[0] ?? null;
      state.selectedNodeId = sensor.downstreamName || sensor.sensorId;
      renderSensoryMap();
    };
    node.addEventListener("click", choose);
    node.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        choose();
      }
    });
    canvas.append(node);

    const utilityWidth = Math.max(0, Math.min(1, sensor.utility)) * 154;
    canvas.append(svg("rect", { x: 373, y: y + 31, width: utilityWidth, height: "2", class: "sensory-utility-bar" }));
    if (sensor.selectionCredit > 0) {
      canvas.append(svg("circle", { cx: "526", cy: y + 9, r: "4", fill: palette.mint, class: "sensory-credit-dot" }));
    }
  });

  cognitionNames.forEach(name => {
    const y = cognitionY.get(name);
    const belief = (state.beliefs ?? []).find(item => item.id === name || item.title === name);
    const subtitle = belief ? `belief certainty ${belief.certainty.toFixed(2)}` : "SENSE / downstream";
    canvas.append(rectNode(700, y, 188, 37, "sensory-cognition-node", shortId(name, 20, 8), subtitle));
  });

  const selected = sensors.find(sensor => sensor.sensorId === state.selectedSensorySensorId)
    ?? sensors[0]
    ?? null;
  if (selected && !state.selectedSensorySensorId) state.selectedSensorySensorId = selected.sensorId;
  renderDetail(detail, selected);

  const cluster = svg("text", { x: "450", y: height - 30, "text-anchor": "middle", class: "sensory-map-footer" });
  cluster.textContent = "Current modality classes are predeclared substrate metadata · derived modalities: not yet available (M07)";
  canvas.append(cluster);
}

const filter = document.querySelector("#sensory-modality-filter");
if (filter && filter.dataset.bound !== "1") {
  filter.dataset.bound = "1";
  filter.addEventListener("change", event => {
    state.sensoryModalityFilter = event.target.value;
    state.selectedSensorySensorId = null;
    renderSensoryMap();
  });
}

export { renderSensoryMap };
