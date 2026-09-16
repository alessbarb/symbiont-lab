import { state } from "../state/store.js";
import { updateUiState } from "../state/transition.js";

const MAX_LIVE_SAMPLES = 500;
const MAX_TOPOLOGY_REVISIONS = 32;
let historyView = "events";
let trendWindow = 100;

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function sampleFromProjection(projection) {
  const cognition = projection?.cognition ?? {};
  return {
    tick: projection?.tick ?? null,
    acclimation: finiteOrNull(projection?.details?.acclimation),
    activeSenses: finiteOrNull(projection?.sampling?.active),
    probingSenses: finiteOrNull(projection?.sampling?.probing),
    dormantSenses: finiteOrNull(projection?.sampling?.dormant),
    attentionConcentration: finiteOrNull(projection?.attention?.concentration),
    attentionEntropy: finiteOrNull(projection?.attention?.entropy),
    physiology: projection?.physiology?.state ?? null,
    contestedBeliefs: Array.isArray(projection?.beliefs) ? projection.beliefs.filter(item => item.dissent).length : null,
    structuralPressure: finiteOrNull(cognition.structuralPressure ?? cognition.structural_pressure),
    relationChurn: finiteOrNull(cognition.relationChurn ?? cognition.relation_churn),
  };
}

function sampleFromRaw(snapshot) {
  const organism = snapshot?.organism ?? {};
  const cognition = organism.cognition ?? {};
  const percepts = Array.isArray(organism.percepts) ? organism.percepts : [];
  const beliefs = Array.isArray(organism.beliefs) ? organism.beliefs : [];
  return {
    tick: Number.isInteger(snapshot?.tick) ? snapshot.tick : null,
    acclimation: finiteOrNull(organism.acclimation),
    activeSenses: finiteOrNull(organism.sampling?.active) ?? percepts.filter(item => item?.available === true).length,
    probingSenses: finiteOrNull(organism.sampling?.probing),
    dormantSenses: finiteOrNull(organism.sampling?.dormant),
    attentionConcentration: finiteOrNull(organism.attention?.concentration),
    attentionEntropy: finiteOrNull(organism.attention?.entropy),
    physiology: typeof organism.physiology?.state === "string" ? organism.physiology.state : null,
    contestedBeliefs: beliefs.filter(item => item?.contested === true).length,
    structuralPressure: finiteOrNull(cognition.structural_pressure),
    relationChurn: finiteOrNull(cognition.relation_churn),
  };
}

function recordTrendSample(projection) {
  if (!projection || !Number.isInteger(projection.tick)) return;
  const samples = [...(state.liveTrendSamples ?? []), sampleFromProjection(projection)].slice(-MAX_LIVE_SAMPLES);
  updateUiState({ liveTrendSamples: samples });
}

function edgeKey(edge) {
  return `${edge.sourceId}|${edge.targetId}|${edge.kind}`;
}

function recordTopologyRevision(topology) {
  if (!topology || !Number.isInteger(topology.topologyRevision)) return;
  const history = state.topologyHistory ?? [];
  if (history.at(-1)?.revision === topology.topologyRevision) return;
  const entry = {
    revision: topology.topologyRevision,
    nodes: (topology.nodes ?? []).map(node => `${node.kind}:${node.id}`),
    edges: (topology.edges ?? []).map(edgeKey),
  };
  updateUiState({ topologyHistory: [...history, entry].slice(-MAX_TOPOLOGY_REVISIONS) });
}

function allTrendSamples() {
  return state.replay.length ? state.replay.map(sampleFromRaw) : (state.liveTrendSamples ?? []);
}

function visibleTrendSamples() {
  const samples = allTrendSamples();
  if (trendWindow === "all") return samples;
  return samples.slice(-trendWindow);
}

function createHistorySubnav(panel) {
  const nav = document.createElement("div");
  nav.id = "history-subviews";
  nav.className = "event-filters";
  [["events", "Events"], ["trends", "Trends"], ["topology", "Topology diff"]].forEach(([id, label]) => {
    const button = document.createElement("button");
    button.dataset.historyView = id;
    button.textContent = label;
    button.addEventListener("click", () => { historyView = id; renderHistoryExplorer(); });
    nav.append(button);
  });
  const events = document.createElement("div");
  events.id = "history-events-view";
  ["event-filters", "history-list", "event-detail"].forEach(id => {
    const element = document.querySelector(`#${id}`);
    if (element) events.append(element);
  });
  const trends = document.createElement("section"); trends.id = "history-trends-view"; trends.hidden = true;
  const topology = document.createElement("section"); topology.id = "history-topology-view"; topology.hidden = true;
  panel.prepend(nav);
  panel.append(events, trends, topology);
}

function ensureHistoryExplorer() {
  const panel = document.querySelector("#history-panel");
  if (!panel) return null;
  if (!document.querySelector("#history-subviews")) createHistorySubnav(panel);
  return panel;
}

function metricCard(label, key, samples, formatter = value => Number(value).toFixed(2)) {
  const section = document.createElement("section");
  section.className = "profile-section";
  const heading = document.createElement("h3"); heading.textContent = label;
  const values = samples.map(sample => sample[key]);
  const finite = values.filter(Number.isFinite);
  if (!finite.length) {
    const empty = document.createElement("p"); empty.textContent = "Not published in this window.";
    section.append(heading, empty); return section;
  }
  const min = Math.min(...finite); const max = Math.max(...finite); const span = Math.max(max - min, Number.EPSILON);
  const latest = [...values].reverse().find(Number.isFinite);
  const meta = document.createElement("p"); meta.textContent = `Latest ${formatter(latest)} · range ${formatter(min)}–${formatter(max)} · ${finite.length}/${samples.length} observations`;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 520 84"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", `${label} over the selected time window`); svg.style.width = "100%"; svg.style.height = "84px";
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  let d = ""; let contiguous = false;
  values.forEach((value, index) => {
    if (!Number.isFinite(value)) { contiguous = false; return; }
    const x = values.length <= 1 ? 0 : (index / (values.length - 1)) * 520;
    const y = 76 - ((value - min) / span) * 68;
    d += `${contiguous ? " L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
    contiguous = true;
  });
  path.setAttribute("d", d); path.setAttribute("fill", "none"); path.setAttribute("stroke", "currentColor"); path.setAttribute("stroke-width", "1.5"); path.setAttribute("vector-effect", "non-scaling-stroke");
  svg.append(path); section.append(heading, meta, svg); return section;
}

function renderReplayComparison(container, samples) {
  if (!state.replay.length || !Number.isInteger(state.compareA) || !Number.isInteger(state.compareB)) return;
  const a = samples[state.compareA]; const b = samples[state.compareB];
  if (!a || !b) return;
  const section = document.createElement("section"); section.className = "profile-section";
  const heading = document.createElement("h3"); heading.textContent = `A/B snapshot comparison · t${a.tick ?? "?"} → t${b.tick ?? "?"}`;
  const list = document.createElement("ul"); list.className = "detail-list";
  [["Acclimation", a.acclimation, b.acclimation], ["Active senses", a.activeSenses, b.activeSenses], ["Attention concentration", a.attentionConcentration, b.attentionConcentration], ["Contested beliefs", a.contestedBeliefs, b.contestedBeliefs], ["Structural pressure", a.structuralPressure, b.structuralPressure], ["Relation churn", a.relationChurn, b.relationChurn]].forEach(([label, before, after]) => {
    const item = document.createElement("li"); const name = document.createElement("b"); const value = document.createElement("span");
    name.textContent = label; value.textContent = `${Number.isFinite(before) ? Number(before).toFixed(3) : "not published"} → ${Number.isFinite(after) ? Number(after).toFixed(3) : "not published"}`; item.append(name, value); list.append(item);
  });
  const note = document.createElement("p"); note.textContent = "Descriptive difference only — Observatory does not infer improvement, fitness or causality.";
  section.append(heading, list, note); container.append(section);
}

function renderTrends() {
  const container = document.querySelector("#history-trends-view"); if (!container) return;
  container.replaceChildren();
  const controls = document.createElement("div"); controls.className = "event-filters";
  const label = document.createElement("label"); label.textContent = "Window"; label.setAttribute("for", "trend-window");
  const select = document.createElement("select"); select.id = "trend-window";
  [[30, "30"], [100, "100"], [500, "500"], ["all", "All"]].forEach(([]) => { const option = document.createElement("option"); option.value = String(value); option.textContent = text; option.selected = String(trendWindow) === String(value); select.append(option); });
  select.addEventListener("change", () => { trendWindow = select.value === "all" ? "all" : Number(select.value); renderTrends(); });
  controls.append(label, select); container.append(controls);
  const samples = visibleTrendSamples();
  const source = document.createElement("p"); source.className = "comparison-note"; source.textContent = state.replay.length ? `${samples.length} replay snapshots in the selected window.` : `${samples.length} browser-local live samples retained; maximum ${MAX_LIVE_SAMPLES}.`;
  container.append(source);
  if (!samples.length) { const empty = document.createElement("p"); empty.className = "history-empty"; empty.textContent = "No longitudinal samples are available yet."; container.append(empty); return; }
  container.append(
    metricCard("Acclimation", "acclimation", samples, value => `${Math.round(value * 100)}%`),
    metricCard("Active senses", "activeSenses", samples, value => String(Math.round(value))),
    metricCard("Attention concentration", "attentionConcentration", samples, value => `${Math.round(value * 100)}%`),
    metricCard("Contested beliefs", "contestedBeliefs", samples, value => String(Math.round(value))),
    metricCard("Structural pressure", "structuralPressure", samples, value => `${Math.round(value * 100)}%`),
    metricCard("Relation churn", "relationChurn", samples, value => `${Math.round(value * 100)}%`),
  );
  const physiology = samples.map(sample => sample.physiology).filter(Boolean);
  const physiologySection = document.createElement("section"); physiologySection.className = "profile-section";
  const physiologyHeading = document.createElement("h3"); physiologyHeading.textContent = "Physiology states";
  const physiologyText = document.createElement("p");
  const counts = physiology.reduce((out, value) => { out[value] = (out[value] ?? 0) + 1; return out; }, {});
  physiologyText.textContent = physiology.length ? Object.entries(counts).map(([name, count]) => `${name}: ${count}`).join(" · ") : "Not published in this window.";
  physiologySection.append(physiologyHeading, physiologyText); container.append(physiologySection);
  renderReplayComparison(container, allTrendSamples());
}

function setDifference(a, b) { return [...a].filter(value => !b.has(value)); }

function renderTopologyDiff() {
  const container = document.querySelector("#history-topology-view"); if (!container) return;
  container.replaceChildren();
  const history = state.topologyHistory ?? [];
  if (history.length < 2) {
    const empty = document.createElement("p"); empty.className = "history-empty";
    empty.textContent = state.replay.length ? "Topology revision history is not embedded in this replay." : "Two live topology revisions are required before a structural diff can be shown.";
    container.append(empty); return;
  }
  const before = history.at(-2); const after = history.at(-1);
  const beforeNodes = new Set(before.nodes); const afterNodes = new Set(after.nodes); const beforeEdges = new Set(before.edges); const afterEdges = new Set(after.edges);
  const addedNodes = setDifference(afterNodes, beforeNodes); const removedNodes = setDifference(beforeNodes, afterNodes); const addedEdges = setDifference(afterEdges, beforeEdges); const removedEdges = setDifference(beforeEdges, afterEdges);
  const heading = document.createElement("h3"); heading.textContent = `Topology r${before.revision} → r${after.revision}`;
  const summary = document.createElement("p"); summary.textContent = `Nodes +${addedNodes.length}/−${removedNodes.length} ÷ edges +${addedEdges.length}/−${removedEdges.length}`;
  container.append(heading, summary);
  [["Nodes added", addedNodes], ["Nodes removed", removedNodes], ["Edges added", addedEdges], ["Edges removed", removedEdges]].forEach(([label, values]) => {
    const section = document.createElement("section"); section.className = "profile-section"; const title = document.createElement("h3"); title.textContent = label; const list = document.createElement("ul"); list.className = "detail-list";
    (values.length ? values.slice(0, 12) : ["No changes"]).forEach(value => { const item = document.createElement("li"); const text = document.createElement("span"); text.textContent = value; item.append(text); list.append(item); });
    if (values.length > 12) { const note = document.createElement("p"); note.textContent = `${values.length - 12} additional changes omitted from this compact view.`; section.append(title, list, note); } else section.append(title, list);
    container.append(section);
  });
  const note = document.createElement("p"); note.className = "comparison-note"; note.textContent = "Structural difference only — no fitness, health or causal interpretation is inferred."; container.append(note);
}

function renderHistoryExplorer() {
  if (!ensureHistoryExplorer()) return;
  document.querySelectorAll("[data-history-view]").forEach(button => button.classList.toggle("active", button.dataset.historyView === historyView));
  const events = document.querySelector("#history-events-view"); const trends = document.querySelector("#history-trends-view"); const topology = document.querySelector("#history-topology-view");
  if (events) events.hidden = historyView !== "events";
  if (trends) trends.hidden = historyView !== "trends";
  if (topology) topology.hidden = historyView !== "topology";
  if (historyView === "trends") renderTrends();
  if (historyView === "topology") renderTopologyDiff();
}

export { recordTrendSample, recordTopologyRevision, renderHistoryExplorer };
