const NS = "http://www.w3.org/2000/svg";

const palette = { cyan: "#50d9ff", violet: "#a777ff", amber: "#ffbd54", coral: "#ff7f83", mint: "#71e9ba" };
let senses = [
  { id: "system_load", name: "System load", icon: "CPU", quality: .92, active: true },
  { id: "storage_pressure", name: "Storage pressure", icon: "IO", quality: .84, active: true },
  { id: "memory_pressure", name: "Memory pressure", icon: "MEM", quality: .68, active: true },
  { id: "thermal_state", name: "Thermal state", icon: "°C", quality: .48, active: false },
  { id: "power_state", name: "Power state", icon: "PWR", quality: .72, active: true },
];

let beliefs = Array.from({ length: 25 }, (_, index) => {
  const angle = index * 2.399;
  const radius = 48 + (index % 5) * 42;
  return {
    id: `belief-${index}`,
    x: 450 + Math.cos(angle) * radius,
    y: 362 + Math.sin(angle) * radius * .82,
    r: 5 + (index % 4) * 2.5,
    certainty: .42 + ((index * 17) % 50) / 100,
    revisions: 1 + (index % 7),
    evidence: 4 + (index * 3) % 19,
    title: ["Workload rhythm", "Storage recovery", "Resource coupling", "Quiet-state memory", "Shared context"][index % 5],
    dissent: index % 6 === 0,
  };
});

let population = Array.from({ length: 18 }, (_, i) => {
  const cluster = i % 3;
  const centers = [[280, 230], [610, 250], [470, 500]];
  const a = i * 2.17;
  const d = 28 + (i % 5) * 18;
  return { id: `S-${String(i + 1).padStart(2, "0")}`, cluster, x: centers[cluster][0] + Math.cos(a) * d, y: centers[cluster][1] + Math.sin(a) * d, pressure: .2 + (i % 6) * .12 };
});

const state = { view: "individual", mode: "live", playing: true, tick: 18, selected: beliefs[12] };

function svg(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function sparkline(index) {
  const el = svg("svg", { viewBox: "0 0 52 22", class: "spark" });
  const points = Array.from({ length: 14 }, (_, i) => `${i * 4},${11 + Math.sin(i * 1.8 + index) * (4 + (i % 3))}`).join(" ");
  el.append(svg("polyline", { points, fill: "none", stroke: senses[index].active ? palette.cyan : "#52708f", "stroke-width": "1.3" }));
  return el;
}

function renderSenses() {
  const list = document.querySelector("#senses");
  list.replaceChildren();
  senses.forEach((sense, index) => {
    const row = document.createElement("div");
    row.className = `sense-row${index === 0 ? " selected" : ""}`;
    const icon = document.createElement("div"); icon.className = "sense-icon"; icon.textContent = sense.icon;
    const copy = document.createElement("div"); copy.className = "sense-copy";
    const name = document.createElement("strong"); name.textContent = sense.name;
    const status = document.createElement("small"); status.textContent = `${sense.active ? "Active" : "Unavailable"} · ${(sense.quality * 100).toFixed(0)}%`;
    const quality = document.createElement("div"); quality.className = "quality";
    const fill = document.createElement("i"); fill.style.width = `${sense.quality * 100}%`; quality.append(fill);
    copy.append(name, status, quality); row.append(icon, copy);
    row.append(sparkline(index));
    row.addEventListener("click", () => {
      document.querySelectorAll(".sense-row").forEach(el => el.classList.remove("selected"));
      row.classList.add("selected");
      state.selected = beliefs[(index * 5 + state.tick) % beliefs.length];
      renderInspector();
      renderOrganism();
      document.querySelector(".inspector").classList.add("open");
    });
    list.append(row);
  });
}

function renderOrganism() {
  const canvas = document.querySelector("#organism-canvas");
  canvas.replaceChildren();
  const defs = svg("defs");
  const radial = svg("radialGradient", { id: "cell-fill" });
  radial.append(svg("stop", { offset: "0", "stop-color": "#17274e", "stop-opacity": ".46" }), svg("stop", { offset: ".75", "stop-color": "#0a2632", "stop-opacity": ".16" }), svg("stop", { offset: "1", "stop-color": "#71e9ba", "stop-opacity": ".08" }));
  defs.append(radial); canvas.append(defs);
  const group = svg("g", { class: "organism-group" });

  senses.forEach((sense, i) => {
    const y = 205 + i * 80;
    group.append(svg("path", { d: `M 75 ${y} C 170 ${y}, 180 ${315 + (i - 2) * 35}, 235 ${330 + (i - 2) * 23}`, class: "sensor-path", opacity: sense.active ? ".85" : ".25" }));
    const pulse = svg("circle", { cx: 112 + ((state.tick * 13 + i * 27) % 100), cy: y, r: 3.5, class: "sensor-pulse", opacity: sense.active ? "1" : "0" });
    group.append(pulse);
  });

  const cellPath = "M450 110 C570 102 674 177 696 290 C731 403 668 536 557 588 C448 650 298 599 229 494 C157 390 182 238 286 165 C330 132 390 112 450 110 Z";
  group.append(svg("path", { d: cellPath, fill: "url(#cell-fill)", class: "membrane" }));
  group.append(svg("path", { d: cellPath, class: "membrane-inner" }));

  beliefs.forEach((belief, index) => {
    const neighbor = beliefs[(index + 4) % beliefs.length];
    group.append(svg("line", { x1: belief.x, y1: belief.y, x2: neighbor.x, y2: neighbor.y, class: "belief-edge" }));
  });
  const focus = beliefs[(state.tick + 7) % beliefs.length];
  group.append(svg("path", { d: `M ${focus.x} ${focus.y} Q 470 365 555 430`, class: "dissent-path", opacity: focus.dissent ? "1" : ".35" }));
  group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 30, class: "attention-ring" }));
  group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 16, class: "attention-ring" }));

  beliefs.forEach(belief => {
    const node = svg("circle", { cx: belief.x, cy: belief.y, r: belief.r, class: `belief-node${state.selected.id === belief.id ? " selected" : ""}`, opacity: belief.certainty });
    node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderOrganism(); document.querySelector(".inspector").classList.add("open"); });
    group.append(node);
  });
  canvas.append(group);
}

function renderPopulation(target = "#population-canvas", mini = false) {
  const canvas = document.querySelector(target); canvas.replaceChildren();
  const sx = mini ? .34 : 1, sy = mini ? .22 : 1;
  const colors = [palette.cyan, palette.mint, palette.violet, palette.amber, palette.coral, "#7bb7ff", "#b8e986", "#d79cff"];
  population.forEach((item, i) => {
    const other = population[(i + 4) % population.length];
    canvas.append(svg("line", { x1: item.x * sx, y1: item.y * sy, x2: other.x * sx, y2: other.y * sy, class: `population-edge${i % 7 === 0 ? " dissent" : ""}` }));
  });
  population.forEach((item, i) => {
    const node = svg("circle", { cx: item.x * sx, cy: item.y * sy, r: (mini ? 4 : 7 + item.pressure * 5), fill: `${colors[item.cluster]}33`, stroke: colors[item.cluster], color: colors[item.cluster], class: "population-node" });
    if (!mini) node.addEventListener("click", () => { document.querySelector("#organism-name").textContent = `Organism ${item.id}`; switchView("individual"); });
    canvas.append(node);
    if (!mini && i % 3 === 0) { const label = svg("text", { x: item.x + 12, y: item.y + 4, class: "population-label" }); label.textContent = item.id; canvas.append(label); }
  });
}

function renderInspector() {
  const b = state.selected;
  document.querySelector("#inspector-title").textContent = b.title;
  document.querySelector("#inspector-kind").textContent = b.dissent ? "Contested belief" : "Revisable belief";
  document.querySelector("#inspector-content").innerHTML = `
    <div class="metric"><div class="metric-head"><span>Certainty</span><strong>${b.certainty.toFixed(2)}</strong></div><div class="meter"><i style="width:${b.certainty * 100}%"></i></div></div>
    <div class="metric"><div class="metric-head"><span>Evidence</span><strong>${b.evidence} observations</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Revisions</span><strong>${b.revisions}</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Dissent</span><strong>${b.dissent ? "Preserved" : "None recent"}</strong></div><div class="meter"><i style="width:${b.dissent ? 64 : 10}%;background:${b.dissent ? palette.coral : palette.mint}"></i></div></div>
    <p class="inspector-summary">This belief emerged from repeated platform-neutral percepts. It is ${b.dissent ? "being held open because recent evidence conflicts with its prior baseline" : "currently consistent with the organism’s recent context"}. No host identity or raw reading is displayed.</p>
    <h3 class="evidence-title">Why it matters now</h3>
    <ul class="evidence-list"><li>Observed in the current context</li><li>${b.evidence} bounded evidence points retained</li><li>Attention allocation remains read-only</li><li>${b.dissent ? "Contradictory evidence remains visible" : "No recent contradictory evidence"}</li></ul>`;
}

function renderTimeline() {
  const track = document.querySelector("#event-track"); track.replaceChildren();
  for (let i = 3; i < 60; i += 5) {
    const dot = document.createElement("i"); dot.className = "event-dot"; dot.style.left = `${(i / 59) * 100}%`; dot.style.background = [palette.cyan, palette.violet, palette.coral, palette.mint][i % 4]; track.append(dot);
  }
  document.querySelector("#scrubber").value = state.tick;
  document.querySelector("#position").textContent = `${state.tick + 1} / 60`;
  document.querySelector("#timestamp").textContent = `10:${String(24 + Math.floor(state.tick / 2)).padStart(2, "0")}:${String((state.tick * 7) % 60).padStart(2, "0")}`;
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".toggle").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  document.querySelector("#organism-canvas").classList.toggle("hidden", view !== "individual");
  document.querySelector("#population-canvas").classList.toggle("hidden", view !== "population");
  document.querySelector("#organism-state").textContent = view === "individual" ? "Active · Exploring" : "18 organisms · 3 ecologies";
  if (view === "population") renderPopulation(); else renderOrganism();
}

function advance(delta = 1) {
  state.tick = (state.tick + delta + 60) % 60;
  state.selected = beliefs[(state.tick + 12) % beliefs.length];
  renderTimeline(); renderInspector(); if (state.view === "individual") renderOrganism();
}

function boundedSnapshot(snapshot) {
  if (!snapshot || snapshot.schema_version !== 1 || !Number.isInteger(snapshot.tick)) return null;
  const organism = snapshot.organism ?? {};
  const incomingSenses = Array.isArray(organism.percepts) ? organism.percepts.slice(0, 32) : [];
  const incomingBeliefs = Array.isArray(organism.beliefs) ? organism.beliefs.slice(0, 128) : [];
  const incomingMembers = Array.isArray(snapshot.population?.members) ? snapshot.population.members.slice(0, 500) : [];
  return {
    tick: Math.max(0, snapshot.tick),
    displayId: typeof organism.display_id === "string" ? organism.display_id.slice(0, 48) : null,
    organismState: ["observing", "exploring", "reflecting", "resting", "unknown"].includes(organism.state) ? organism.state : "unknown",
    senses: incomingSenses.filter(item => item && typeof item.id === "string" && typeof item.label === "string").map((item, index) => ({
      id: item.id.slice(0, 64), name: item.label.slice(0, 80), icon: `S${index + 1}`,
      quality: Math.min(1, Math.max(0, Number(item.quality) || 0)), active: item.available === true,
    })),
    beliefs: incomingBeliefs.filter(item => item && typeof item.id === "string" && typeof item.label === "string").map((item, index) => {
      const angle = index * 2.399, radius = 48 + (index % 5) * 42;
      return {
        id: item.id.slice(0, 64), title: item.label.slice(0, 120),
        x: 450 + Math.cos(angle) * radius, y: 362 + Math.sin(angle) * radius * .82,
        r: 5 + (index % 4) * 2.5, certainty: Math.min(1, Math.max(0, Number(item.certainty) || 0)),
        evidence: Math.max(0, Number.parseInt(item.evidence_count, 10) || 0),
        revisions: Math.max(0, Number.parseInt(item.revision_count, 10) || 0), dissent: item.contested === true,
      };
    }),
    population: incomingMembers.filter(item => item && typeof item.display_id === "string").map((item, index) => {
      const cluster = Math.min(7, Math.max(0, Number.parseInt(item.ecology, 10) || 0));
      const centers = [[280, 230], [610, 250], [470, 500], [300, 470], [640, 480], [440, 190], [210, 360], [690, 360]];
      const angle = index * 2.17, distance = 28 + (index % 5) * 18;
      return { id: item.display_id.slice(0, 48), cluster, x: centers[cluster][0] + Math.cos(angle) * distance, y: centers[cluster][1] + Math.sin(angle) * distance, pressure: Math.min(1, Math.max(0, Number(item.activity) || 0)) };
    }),
  };
}

function ingestSnapshot(snapshot) {
  const projection = boundedSnapshot(snapshot);
  if (!projection) return;
  state.tick = projection.tick % 60;
  if (projection.senses.length) senses = projection.senses;
  if (projection.beliefs.length) beliefs = projection.beliefs;
  if (projection.population.length) population = projection.population;
  if (!beliefs.some(item => item.id === state.selected?.id)) state.selected = beliefs[0];
  if (projection.displayId) document.querySelector("#organism-name").textContent = `Organism ${projection.displayId}`;
  document.querySelector("#organism-state").textContent = projection.organismState[0].toUpperCase() + projection.organismState.slice(1);
  document.querySelector(".connection small").textContent = "snapshot stream";
  renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline();
}

document.querySelectorAll(".toggle").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));
document.querySelectorAll(".mode").forEach(button => button.addEventListener("click", () => {
  state.mode = button.dataset.mode; document.querySelectorAll(".mode").forEach(b => b.classList.toggle("active", b === button));
}));
document.querySelector("#open-population").addEventListener("click", () => switchView("population"));
document.querySelector("#scrubber").addEventListener("input", event => { state.tick = Number(event.target.value); state.mode = "replay"; document.querySelectorAll(".mode").forEach(b => b.classList.toggle("active", b.dataset.mode === "replay")); advance(0); });
document.querySelector("#previous").addEventListener("click", () => advance(-1));
document.querySelector("#next").addEventListener("click", () => advance(1));
document.querySelector("#play").addEventListener("click", event => { state.playing = !state.playing; event.currentTarget.classList.toggle("paused", !state.playing); event.currentTarget.setAttribute("aria-label", state.playing ? "Pause playback" : "Resume playback"); });

window.addEventListener("message", event => {
  if (event.data?.type !== "symbiont-observatory-snapshot") return;
  if (event.origin !== window.location.origin) return;
  ingestSnapshot(event.data.snapshot);
});

renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline();
setInterval(() => { if (state.playing && state.mode === "live") advance(1); }, 1800);
