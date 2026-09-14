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
  return { id: `S-${String(i + 1).padStart(2, "0")}`, cluster, x: centers[cluster][0] + Math.cos(a) * d, y: centers[cluster][1] + Math.sin(a) * d, pressure: .2 + (i % 6) * .12, knowledge: 5 + (i * 7) % 38, contested: i % 5 };
});
let relationships = population.map((item, index) => ({ source: item.id, target: population[(index + 4) % population.length].id, type: ["ecology", "knowledge", "activity", "dissent"][index % 4], strength: .35 + (index % 6) * .1 }));

const demoEvents = Array.from({ length: 18 }, (_, index) => ({
  id: `event-${index}`, type: ["perception", "attention", "revision", "contradiction"][index % 4],
  label: ["A normalized input changed", "Attention moved to an uncertain pattern", "A belief incorporated new evidence", "Conflicting evidence remains open"][index % 4],
  explanation: "The organism kept this transition inspectable without assigning a threat label or taking an action.",
  beliefId: `belief-${(index * 3) % 25}`, delta: ((index % 7) - 3) / 10, tick: index * 3,
  chain: ["A bounded perception entered the current context.", "Memory supplied a comparable prior pattern.", "Attention was allocated according to uncertainty.", "The related belief remained revisable."],
}));

const state = { view: "individual", mode: "live", playing: true, tick: 18, realTick: null, selected: beliefs[12], replay: [], replayIndex: 0, source: "demo", events: demoEvents, liveEvents: [], eventFilter: "all", query: "", selectedEvent: demoEvents[6], compareA: null, compareB: null, populationMode: "ecology", organismA: null, organismB: null, displayId: null, organismState: "unknown", sensoryDevelopment: [], sensoryRelations: [], sampling: { active: 0, probing: 0, dormant: 0, unknown: 0, sampledThisTick: 0, discovered: 0 }, schemaVersion: 1, senseHistory: new Map() };
state.profile = "summary";
state.details = { narrative:"The organism is observing familiar host rhythms while keeping one uncertain pattern open for another look.", acclimation:.72, resourceBudget:{cpu:.22,memory:.31,storage:.14,ticksRemaining:82}, memory:["Quiet workload rhythm retained","Storage recovery pattern strengthened"], openQuestions:["Will the current load return to its familiar range?"], investigations:["Second look at resource coupling"], regimeChanges:["No confirmed regime change"] };

function svg(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function sparkline(sense) {
  const el = svg("svg", { viewBox: "0 0 52 22", class: "spark" });
  const hist = state.senseHistory.get(sense.id) || state.senseHistory.get(sense.name) || [];
  if (hist.length < 2) {
    el.append(svg("line", { x1: "0", y1: "11", x2: "52", y2: "11", stroke: "#253b52", "stroke-width": "1", "stroke-dasharray": "2 2" }));
    return el;
  }
  const maxVal = Math.max(...hist, 0.01);
  const minVal = Math.min(...hist, 0);
  const range = (maxVal - minVal) || 0.01;
  const stepX = 52 / (hist.length - 1);
  const points = hist.map((v, i) => `${(i * stepX).toFixed(1)},${(18 - ((v - minVal) / range) * 14).toFixed(1)}`).join(" ");
  el.append(svg("polyline", { points, fill: "none", stroke: sense.active ? palette.cyan : "#52708f", "stroke-width": "1.3" }));
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

    const dev = state.sensoryDevelopment.find(d => d.name === sense.id || d.name === sense.name);
    const status = document.createElement("small");
    const quality = document.createElement("div"); quality.className = "quality";
    const fill = document.createElement("i");

    if (dev) {
      status.textContent = `${dev.tier.toUpperCase()} · ${dev.samples} samples · util ${dev.utility.toFixed(3)} · avail ${Math.round(dev.availability * 100)}%`;
      fill.style.width = `${Math.min(100, Math.max(6, dev.utility * 2500))}%`;
      fill.style.background = dev.tier === "active" ? palette.cyan : (dev.tier === "probing" ? palette.amber : "#52708f");
    } else if (state.source !== "demo") {
      status.textContent = `${sense.active ? "ACTIVE" : "DORMANT"} · detail not exported`;
      fill.style.width = sense.active ? "25%" : "0%";
      fill.style.background = sense.active ? palette.cyan : "#52708f";
    } else {
      status.textContent = `${sense.active ? "Active" : "Unavailable"} · avail ${(sense.quality * 100).toFixed(0)}%`;
      fill.style.width = `${sense.quality * 100}%`;
    }
    quality.append(fill);
    copy.append(name, status, quality); row.append(icon, copy);
    row.append(sparkline(sense));
    row.addEventListener("click", () => {
      document.querySelectorAll(".sense-row").forEach(el => el.classList.remove("selected"));
      row.classList.add("selected");
      state.selected = beliefs.find(b => b.id.includes(sense.id) || b.title.includes(sense.name)) ?? (beliefs.length ? beliefs[index % beliefs.length] : null);
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

  const count = senses.length;
  const top = 140;
  const bottom = 580;
  const sensePositions = new Map();

  senses.forEach((sense, i) => {
    const y = count <= 1 ? (top + bottom) / 2 : top + i * (bottom - top) / (count - 1);
    sensePositions.set(sense.id, { x: 75, y });
    const membraneY = count <= 1 ? 330 : 250 + i * (160 / Math.max(count - 1, 1));
    group.append(svg("path", { d: `M 75 ${y} C 160 ${y}, 180 ${membraneY}, 235 ${membraneY}`, class: "sensor-path", opacity: sense.active ? ".85" : ".25" }));
    const perceivedThisTick = (state.source === "demo")
      ? sense.active
      : (Array.isArray(state.events) && state.events.some(e => e.type === "perception" && (e.id.includes(sense.id) || e.label.includes(sense.id) || (sense.name && e.label.includes(sense.name)))));
    if (perceivedThisTick) {
      const pulse = svg("circle", { cx: 155, cy: y, r: 3.5, class: "sensor-pulse", opacity: "1" });
      group.append(pulse);
    }
  });

  if (Array.isArray(state.sensoryRelations) && state.sensoryRelations.length) {
    state.sensoryRelations.forEach(rel => {
      const posA = sensePositions.get(rel.senseA);
      const posB = sensePositions.get(rel.senseB);
      if (!posA || !posB || rel.samples < 3) return;
      const syncVal = rel.synchronous !== null ? rel.synchronous : 0;
      const absSync = Math.abs(syncVal);
      const confidence = Math.min(1, rel.samples / 25);
      const stroke = syncVal >= 0 ? palette.mint : palette.coral;
      const dash = syncVal < 0 ? "3 3" : "none";
      const midY = (posA.y + posB.y) / 2;
      const arcOffset = 22 * (0.5 + 0.5 * absSync);
      const strokeWidth = (0.7 + absSync * 1.5).toFixed(1);
      const opacity = (0.2 + absSync * 0.6 * confidence).toFixed(2);
      group.append(svg("path", {
        d: `M ${posA.x} ${posA.y} Q ${posA.x - arcOffset} ${midY} ${posB.x} ${posB.y}`,
        fill: "none", stroke, "stroke-width": strokeWidth, "stroke-dasharray": dash, opacity,
      }));
    });
  }

  const cellPath = "M450 110 C570 102 674 177 696 290 C731 403 668 536 557 588 C448 650 298 599 229 494 C157 390 182 238 286 165 C330 132 390 112 450 110 Z";
  group.append(svg("path", { d: cellPath, fill: "url(#cell-fill)", class: "membrane" }));
  group.append(svg("path", { d: cellPath, class: "membrane-inner" }));

  beliefs.forEach((belief, index) => {
    const neighbor = beliefs[(index + 4) % beliefs.length];
    group.append(svg("line", { x1: belief.x, y1: belief.y, x2: neighbor.x, y2: neighbor.y, class: "belief-edge" }));
  });
  let focus = null;
  if (state.source === "demo") {
    focus = beliefs.length ? beliefs[(state.tick + 7) % beliefs.length] : null;
  } else if (Array.isArray(state.events) && state.events.length) {
    const attentionEvent = state.events.find(e => e.type === "attention");
    if (attentionEvent) {
      const targetId = attentionEvent.belief_id ?? attentionEvent.beliefId;
      if (targetId) {
        focus = beliefs.find(b => b.id === targetId || b.id.slice(0, 64) === targetId.slice(0, 64));
      }
      if (!focus && attentionEvent.label) {
        const match = attentionEvent.label.match(/(?:signal|belief|sense)[._a-zA-Z0-9]+/);
        if (match) {
          focus = beliefs.find(b => b.id.includes(match[0]) || b.title.includes(match[0]));
        }
      }
    }
  }
  if (focus) {
    group.append(svg("path", { d: `M ${focus.x} ${focus.y} Q 470 365 555 430`, class: "dissent-path", opacity: focus.dissent ? "1" : ".35" }));
    group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 30, class: "attention-ring" }));
    group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 16, class: "attention-ring" }));
  }

  beliefs.forEach(belief => {
    const node = svg("circle", { cx: belief.x, cy: belief.y, r: belief.r, class: `belief-node${state.selected?.id === belief.id ? " selected" : ""}`, opacity: belief.certainty });
    node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderOrganism(); document.querySelector(".inspector").classList.add("open"); });
    group.append(node);
  });
  canvas.append(group);
}

function renderPopulation(target = "#population-canvas", mini = false) {
  const canvas = document.querySelector(target); canvas.replaceChildren();
  const sx = mini ? .34 : 1, sy = mini ? .22 : 1;
  const colors = [palette.cyan, palette.mint, palette.violet, palette.amber, palette.coral, "#7bb7ff", "#b8e986", "#d79cff"];
  if (!mini) [...new Set(population.map(item => item.cluster))].forEach(cluster => {
    const members = population.filter(item => item.cluster === cluster); if (!members.length) return;
    const cx = members.reduce((sum,item)=>sum+item.x,0)/members.length, cy=members.reduce((sum,item)=>sum+item.y,0)/members.length;
    canvas.append(svg("ellipse", { cx, cy, rx:115, ry:92, fill:`${colors[cluster]}0c`, stroke:`${colors[cluster]}55`, class:"population-hull" }));
  });
  relationships.filter(link => mini || link.type === state.populationMode).forEach(link => {
    const item=population.find(member=>member.id===link.source), other=population.find(member=>member.id===link.target); if(!item||!other)return;
    canvas.append(svg("line", { x1:item.x*sx,y1:item.y*sy,x2:other.x*sx,y2:other.y*sy,opacity:String(.25+link.strength*.65),class:`population-edge${link.type === "dissent" ? " dissent" : ""}` }));
  });
  population.forEach((item, i) => {
    const magnitude = state.populationMode === "knowledge" ? Math.min(1,item.knowledge/45) : state.populationMode === "dissent" ? Math.min(1,item.contested/5) : item.pressure;
    const modeColor = state.populationMode === "activity" ? palette.amber : state.populationMode === "dissent" ? palette.coral : colors[item.cluster];
    const selectedClass = state.organismA?.id === item.id ? " selected-a" : state.organismB?.id === item.id ? " selected-b" : "";
    const node = svg("circle", { cx: item.x * sx, cy: item.y * sy, r: (mini ? 4 : 7 + magnitude * 7), fill: `${modeColor}33`, stroke: modeColor, color: modeColor, class: `population-node${selectedClass}` });
    if (!mini) node.addEventListener("click", () => selectPopulationMember(item));
    canvas.append(node);
    if (!mini && i < 40 && i % 3 === 0) { const label = svg("text", { x: item.x + 12, y: item.y + 4, class: "population-label" }); label.textContent = item.id; canvas.append(label); }
  });
}

function selectPopulationMember(item) {
  if (!state.organismA || state.organismB) { state.organismA = item; state.organismB = null; }
  else if (state.organismA.id !== item.id) state.organismB = item;
  renderPopulation(); renderPopulationInspector();
}

function renderPopulationInspector() {
  const selected = state.organismB ?? state.organismA; const subtitle=document.querySelector("#cluster-subtitle"), explanation=document.querySelector("#cluster-explanation"), comparison=document.querySelector("#organism-comparison");
  explanation.replaceChildren(); comparison.replaceChildren();
  if (population.length <= 1) { subtitle.textContent="Single organism recorded"; const p=document.createElement("p");p.textContent="This recording only contains one organism, so ecology, knowledge, activity and dissent comparisons have nothing to relate it to yet. Load or record data with more than one organism to use this view.";explanation.append(p); const empty=document.createElement("p");empty.className="comparison-empty";empty.textContent="Comparison needs at least two organisms.";comparison.append(empty);return; }
  if (!selected) { subtitle.textContent="Select an organism"; const p=document.createElement("p");p.textContent="Choose a node to explain its ecological cluster, then choose another to compare them.";explanation.append(p); const empty=document.createElement("p");empty.className="comparison-empty";empty.textContent="No organisms selected.";comparison.append(empty);return; }
  const members=population.filter(item=>item.cluster===selected.cluster); subtitle.textContent=`Ecology ${selected.cluster + 1} · ${members.length} organisms`;
  const title=document.createElement("h3");title.textContent=`Ecology ${selected.cluster + 1}`; const body=document.createElement("p");body.textContent=`These organisms are close because their normalized environments are compatible. This grouping says nothing about which organism is more reliable or correct.`;
  const facts=document.createElement("ul");facts.className="cluster-facts"; [`${members.length} organisms share this context`,`Average activity ${(members.reduce((s,x)=>s+x.pressure,0)/members.length*100).toFixed(0)}%`,`${members.reduce((s,x)=>s+x.contested,0)} contested beliefs remain visible`].forEach(text=>{const li=document.createElement("li");li.textContent=text;facts.append(li)}); explanation.append(title,body,facts);
  if (!state.organismA || !state.organismB) { const empty=document.createElement("p");empty.className="comparison-empty";empty.textContent=`${state.organismA.id} is selected as A. Choose a second organism to compare without collapsing their differences into one score.`;comparison.append(empty);return; }
  const names=document.createElement("div");names.className="comparison-names";[state.organismA,state.organismB].forEach((item,index)=>{const box=document.createElement("div");box.className="comparison-name";const b=document.createElement("b");b.textContent=`${index?"B":"A"} · ${item.id}`;const small=document.createElement("small");small.textContent=`Ecology ${item.cluster+1}`;box.append(b,small);names.append(box)});comparison.append(names);
  const table=document.createElement("table"); [["Ecology",`Context ${state.organismA.cluster+1}`,`Context ${state.organismB.cluster+1}`],["Activity",`${(state.organismA.pressure*100).toFixed(0)}%`,`${(state.organismB.pressure*100).toFixed(0)}%`],["Shared knowledge",state.organismA.knowledge,state.organismB.knowledge],["Contested beliefs",state.organismA.contested,state.organismB.contested]].forEach(row=>{const tr=document.createElement("tr");row.forEach((value,index)=>{const cell=document.createElement(index?"td":"th");cell.textContent=String(value);tr.append(cell)});table.append(tr)});comparison.append(table);
}

function makeProfileSection(title, value, description) { const section=document.createElement("section");section.className="profile-section";const h=document.createElement("h3");h.textContent=title;const strong=document.createElement("strong");strong.textContent=value;const p=document.createElement("p");p.textContent=description;section.append(h,strong,p);return section; }

function renderProfiles() {
  const summary=document.querySelector("#summary-content");summary.replaceChildren();
  summary.append(makeProfileSection("Lifecycle", document.querySelector("#organism-state").textContent, "Current phase of the continuous cognitive cycle."));
  summary.append(makeProfileSection("Acclimation", `${Math.round(state.details.acclimation*100)}%`, "How much recent context has been incorporated — not a health or risk score."));
  const budget=document.createElement("section");budget.className="profile-section";const bh=document.createElement("h3");bh.textContent="Resource budget";budget.append(bh);[["CPU","cpu"],["Memory","memory"],["Storage","storage"]].forEach(([label,key])=>{const row=document.createElement("div");row.className="budget-row";const name=document.createElement("span");name.textContent=label;const raw=state.details.resourceBudget[key];const meter=document.createElement("i");const value=document.createElement("b");if(raw===null||raw===undefined){meter.style.setProperty("--value","0%");meter.classList.add("unmeasured");value.textContent="Not measured";}else{meter.style.setProperty("--value",`${raw*100}%`);value.textContent=`${Math.round(raw*100)}%`;}row.append(name,meter,value);budget.append(row)});summary.append(budget,makeProfileSection("Narrative","What it is doing",state.details.narrative));
  const organism=document.querySelector("#organism-details");organism.replaceChildren();[["Memory",state.details.memory],["Open questions",state.details.openQuestions],["Investigations",state.details.investigations],["Regime changes",state.details.regimeChanges]].forEach(([title,items])=>{const section=document.createElement("section");section.className="profile-section";const h=document.createElement("h3");h.textContent=title;const list=document.createElement("ul");list.className="detail-list";(items.length?items:["Nothing currently exposed"]).forEach((text,index)=>{const li=document.createElement("li");const b=document.createElement("b");b.textContent=`${title.replace(/s$/,"")} ${index+1}`;const span=document.createElement("span");span.textContent=text;li.append(b,span);list.append(li)});section.append(h,list);organism.append(section)});
  const research=document.querySelector("#research-details");research.replaceChildren();const dl=document.createElement("dl");dl.className="research-grid";
  const researchEntries = [
    ["Schema", `v${state.schemaVersion}`],
    ["Source", state.source],
    ["Tick", state.realTick ?? state.tick],
    ["Percepts", senses.length],
    ["Beliefs", beliefs.length],
    ["Events", availableEvents().length],
    ["Population", population.length],
    ["Relationships", relationships.length],
    ["Ticks remaining", state.details.resourceBudget.ticksRemaining],
  ];
  if (state.source !== "demo") {
    researchEntries.push(
      ["Cognition", state.schemaVersion === 1 ? "native sensory development" : "structural graph"],
      ["Structural graph", state.schemaVersion === 1 ? "not configured" : "active"],
      ["Discovered", state.sampling.discovered],
      ["Active", state.sampling.active],
      ["Probing", state.sampling.probing],
      ["Dormant", state.sampling.dormant],
      ["Unknown", state.sampling.unknown],
      ["Sampled this tick", state.sampling.sampledThisTick],
      ["Development details exported", state.sensoryDevelopment.length],
      ["Strongest relations exported", state.sensoryRelations.length],
      ["Events retained locally", state.liveEvents.length],
    );
  }
  researchEntries.forEach(([label,value])=>{const div=document.createElement("div");const dt=document.createElement("dt");dt.textContent=label;const dd=document.createElement("dd");dd.textContent=String(value);div.append(dt,dd);dl.append(div)});research.append(dl);
}

function renderAccessibleTable() { const table=document.querySelector("#accessible-table");table.replaceChildren();const head=document.createElement("tr");["Type","Name","State","Value"].forEach(text=>{const th=document.createElement("th");th.textContent=text;head.append(th)});table.append(head);const rows=[...senses.map(item=>["Percept",item.name,item.active?"Available":"Unavailable",`${Math.round(item.quality*100)}%`]),...beliefs.map(item=>["Belief",item.title,item.dissent?"Contested":"Revisable",item.certainty.toFixed(2)])];rows.slice(0,160).forEach(values=>{const tr=document.createElement("tr");values.forEach(value=>{const td=document.createElement("td");td.textContent=String(value);tr.append(td)});table.append(tr)}); }

function renderInspector() {
  const b = state.selected;
  if (!b) {
    document.querySelector("#inspector-title").textContent = "No beliefs yet";
    document.querySelector("#inspector-kind").textContent = "";
    document.querySelector("#inspector-content").innerHTML = `<p class="inspector-summary">This organism has not formed any bounded beliefs yet.</p>`;
    return;
  }
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
  const scrubber = document.querySelector("#scrubber");
  const positionEl = document.querySelector("#position");
  const timestampEl = document.querySelector("#timestamp");
  const isLiveReal = state.mode === "live" && state.source !== "demo";

  if (isLiveReal) {
    scrubber.disabled = true;
    const currentTick = state.realTick ?? state.tick ?? 0;
    positionEl.textContent = `Live · tick ${currentTick}`;
    timestampEl.textContent = "Live stream";

    const windowStart = Math.max(0, currentTick - 59);
    const windowSpan = Math.max(1, currentTick - windowStart);

    const recentEvents = state.liveEvents.filter(e => e.tick >= windowStart && e.tick <= currentTick);
    recentEvents.forEach(event => {
      const dot = document.createElement("i");
      dot.className = "event-dot";
      const pct = ((event.tick - windowStart) / windowSpan) * 100;
      dot.style.left = `${pct.toFixed(1)}%`;
      dot.style.background = eventColor(event.type);
      dot.style.opacity = event.type === "perception" ? "0.4" : "0.9";
      track.append(dot);
    });
    scrubber.min = String(windowStart);
    scrubber.max = String(currentTick);
    scrubber.value = String(currentTick);
  } else {
    scrubber.disabled = false;
    for (let i = 3; i < 60; i += 5) {
      const dot = document.createElement("i"); dot.className = "event-dot"; dot.style.left = `${(i / 59) * 100}%`; dot.style.background = [palette.cyan, palette.violet, palette.coral, palette.mint][i % 4]; track.append(dot);
    }
    const total = state.replay.length || 60;
    const position = state.replay.length ? state.replayIndex : (state.realTick ?? state.tick);
    scrubber.max = String(Math.max(0, total - 1));
    scrubber.value = String(position);
    positionEl.textContent = `${position + 1} / ${total}`;
    timestampEl.textContent = `10:${String(24 + Math.floor(state.tick / 2)).padStart(2, "0")}:${String((state.tick * 7) % 60).padStart(2, "0")}`;
  }
}

function eventColor(type) { return ({ perception: palette.cyan, attention: palette.amber, revision: palette.violet, contradiction: palette.coral })[type] || palette.cyan; }

function availableEvents() {
  const source = state.replay.length
    ? state.replay.flatMap((snapshot, snapshotIndex) => (snapshot.organism?.events ?? []).map(event => ({
        id: String(event.id), type: event.type, label: event.label, explanation: event.explanation ?? "No additional explanation was included.",
        beliefId: event.belief_id ?? null, delta: Number(event.delta) || 0, tick: snapshot.tick, replayIndex: snapshotIndex,
        chain: Array.isArray(event.causal_chain) ? event.causal_chain : [],
      })))
    : (state.source !== "demo" ? state.liveEvents : demoEvents);
  const query = state.query.trim().toLowerCase();
  return source.filter(event => (state.eventFilter === "all" || event.type === state.eventFilter) && (!query || `${event.label} ${event.explanation}`.toLowerCase().includes(query)));
}

function comparisonFor(event) {
  if (!state.replay.length || state.compareA === null || state.compareB === null || !event?.beliefId) return null;
  const find = index => state.replay[index]?.organism?.beliefs?.find(item => item.id === event.beliefId);
  const earlier = find(Math.min(state.compareA, state.compareB)), now = find(Math.max(state.compareA, state.compareB));
  return earlier && now ? { earlier, now } : null;
}

function renderHistory() {
  const filters = document.querySelector("#event-filters"); filters.replaceChildren();
  ["all", "perception", "attention", "revision", "contradiction"].forEach(type => {
    const button = document.createElement("button"); button.className = `event-filter${state.eventFilter === type ? " active" : ""}`; button.textContent = type[0].toUpperCase() + type.slice(1);
    button.addEventListener("click", () => { state.eventFilter = type; renderHistory(); }); filters.append(button);
  });
  const list = document.querySelector("#history-list"); list.replaceChildren(); const events = availableEvents();
  if (!events.length) { const empty = document.createElement("p"); empty.className = "history-empty"; empty.textContent = "No cognitive events match this view."; list.append(empty); }
  if (!events.some(e => e.id === state.selectedEvent?.id)) {
    state.selectedEvent = events.length ? events[events.length - 1] : null;
  }
  events.slice().reverse().slice(0, 120).forEach(event => {
    const button = document.createElement("button"); button.className = `history-event${state.selectedEvent?.id === event.id ? " active" : ""}`;
    const color = document.createElement("i"); color.className = "event-color"; color.style.background = eventColor(event.type);
    const time = document.createElement("time"); time.textContent = `t${event.tick}`;
    const label = document.createElement("span"); label.textContent = event.label;
    const delta = document.createElement("em"); delta.textContent = `${event.delta >= 0 ? "+" : ""}${event.delta.toFixed(2)}`; delta.className = event.delta < 0 ? "negative" : "positive";
    button.append(color, time, label, delta); button.addEventListener("click", () => { state.selectedEvent = event; if (Number.isInteger(event.replayIndex)) { state.replayIndex = event.replayIndex; advance(0); } renderHistory(); }); list.append(button);
  });
  renderEventDetail();
}

function renderEventDetail() {
  const detail = document.querySelector("#event-detail"); detail.replaceChildren(); const event = state.selectedEvent;
  if (!event) return;
  const title = document.createElement("h3"); title.textContent = event.label; const explanation = document.createElement("p"); explanation.textContent = event.explanation;
  detail.append(title, explanation);
  if (event.chain.length) { const heading = document.createElement("h3"); heading.textContent = "Causal chain"; const chain = document.createElement("ol"); chain.className = "causal-chain"; event.chain.forEach(text => { const item = document.createElement("li"); item.textContent = text; chain.append(item); }); detail.append(heading, chain); }
  const comparison = comparisonFor(event);
  if (comparison) {
    const box = document.createElement("div"); box.className = "comparison";
    const head = document.createElement("div"); head.className = "comparison-head"; ["What changed", "Earlier", "", "Now"].forEach(text => { const span = document.createElement("span"); span.textContent = text; head.append(span); }); box.append(head);
    [["Certainty",comparison.earlier.certainty,comparison.now.certainty],["Evidence",comparison.earlier.evidence_count,comparison.now.evidence_count],["Revisions",comparison.earlier.revision_count,comparison.now.revision_count]].forEach(([label,a,b]) => { const row=document.createElement("div"); row.className="comparison-row"; [label,String(a),"→",String(b)].forEach(value=>{const cell=document.createElement("b");cell.textContent=value;row.append(cell)}); box.append(row); });
    const note=document.createElement("p"); note.className="comparison-note"; note.textContent="Difference between marked snapshots only — not a quality or risk judgment."; box.append(note); detail.append(box);
  }
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".toggle").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  document.querySelector("#organism-canvas").classList.toggle("hidden", view !== "individual");
  document.querySelector("#population-canvas").classList.toggle("hidden", view !== "population");
  document.querySelector("#population-tools").classList.toggle("hidden", view !== "population");
  document.querySelector("#individual-inspector").hidden = view === "population"; document.querySelector("#population-inspector").hidden = view !== "population";
  document.querySelector("#organism-state").textContent = view === "individual" ? "Active · Exploring" : "18 organisms · 3 ecologies";
  if (view === "population") { renderPopulation(); renderPopulationInspector(); } else renderOrganism();
  localStorage.setItem("symbiont-observatory-view", view);
}

function advance(delta = 1) {
  if (state.replay.length) {
    state.replayIndex = (state.replayIndex + delta + state.replay.length) % state.replay.length;
    ingestSnapshot(state.replay[state.replayIndex], false);
    return;
  }
  state.tick = (state.tick + delta + 60) % 60;
  state.selected = beliefs.length ? beliefs[(state.tick + 12) % beliefs.length] : null;
  renderTimeline(); renderInspector(); if (state.view === "individual") renderOrganism();
}

function boundedRatioOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(1, Math.max(0, number)) : null;
}

function normalizeSnapshot(raw) {
  if (!raw) return raw;
  if (raw.schema_version === 1) {
    return { ...raw, organism: { ...raw.organism, cognition: null } };
  }
  return raw; // v2 already carries organism.cognition
}

function boundedCognition(cognition) {
  if (!cognition || typeof cognition !== "object") return null;
  const readouts = {};
  Object.entries(cognition.readouts ?? {}).forEach(([id, value]) => { if (typeof id === "string" && Number.isFinite(Number(value))) readouts[id.slice(0, 128)] = Number(value); });
  const predictionErrors = {};
  Object.entries(cognition.prediction_errors ?? {}).forEach(([id, cls]) => { if (typeof id === "string" && typeof cls === "string") predictionErrors[id.slice(0, 128)] = cls; });
  const mutations = (Array.isArray(cognition.mutations) ? cognition.mutations : []).slice(0, 8).map(item => ({
    kind: typeof item?.kind === "string" ? item.kind : "unknown",
    nodeId: typeof item?.node_id === "string" ? item.node_id.slice(0, 128) : null,
    edgeId: typeof item?.edge_id === "string" ? item.edge_id.slice(0, 260) : null,
  }));
  const safety = cognition.safety_state ?? {};
  return {
    topologyRevision: Math.max(0, Number.parseInt(cognition.topology_revision, 10) || 0),
    readouts, predictionErrors, mutations,
    safetyState: { consecutiveFailures: Math.max(0, Number.parseInt(safety.consecutive_failures, 10) || 0), frozen: safety.frozen === true },
  };
}

function boundedSnapshot(snapshot) {
  if (!snapshot || ![1, 2].includes(snapshot.schema_version) || !Number.isInteger(snapshot.tick)) return null;
  const organism = snapshot.organism ?? {};
  const incomingSenses = Array.isArray(organism.percepts) ? organism.percepts.slice(0, 32) : [];
  const incomingBeliefs = Array.isArray(organism.beliefs) ? organism.beliefs.slice(0, 128) : [];
  const incomingMembers = Array.isArray(snapshot.population?.members) ? snapshot.population.members.slice(0, 500) : [];
  const incomingRelationships = Array.isArray(snapshot.population?.relationships) ? snapshot.population.relationships.slice(0, 1000) : [];
  const incomingEvents = Array.isArray(organism.events) ? organism.events.slice(0, 64) : [];
  const incomingSensoryDev = Array.isArray(organism.sensory_development) ? organism.sensory_development.slice(0, 64) : [];
  const incomingSensoryRel = Array.isArray(organism.sensory_relations) ? organism.sensory_relations.slice(0, 24) : [];
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
    details:{ narrative:typeof organism.narrative==="string"?organism.narrative.slice(0,600):state.details.narrative, acclimation:Math.min(1,Math.max(0,Number(organism.acclimation)||0)), resourceBudget:{cpu:boundedRatioOrNull(organism.resource_budget?.cpu),memory:boundedRatioOrNull(organism.resource_budget?.memory),storage:boundedRatioOrNull(organism.resource_budget?.storage),ticksRemaining:Math.max(0,Number.parseInt(organism.resource_budget?.ticks_remaining,10)||0)}, memory:(Array.isArray(organism.memory)?organism.memory:[]).slice(0,32),openQuestions:(Array.isArray(organism.open_questions)?organism.open_questions:[]).slice(0,16),investigations:(Array.isArray(organism.investigations)?organism.investigations:[]).slice(0,16),regimeChanges:(Array.isArray(organism.regime_changes)?organism.regime_changes:[]).slice(0,16)}, population: incomingMembers.filter(item => item && typeof item.display_id === "string").map((item, index) => {
      const cluster = Math.min(7, Math.max(0, Number.parseInt(item.ecology, 10) || 0));
      const centers = [[280, 230], [610, 250], [470, 500], [300, 470], [640, 480], [440, 190], [210, 360], [690, 360]];
      const angle = index * 2.17, distance = 28 + (index % 5) * 18;
      return { id: item.display_id.slice(0, 48), cluster, x: centers[cluster][0] + Math.cos(angle) * distance, y: centers[cluster][1] + Math.sin(angle) * distance, pressure: Math.min(1, Math.max(0, Number(item.activity) || 0)), knowledge:Math.max(0,Number.parseInt(item.knowledge_count,10)||0), contested:Math.max(0,Number.parseInt(item.contested_count,10)||0) };
    }), relationships: incomingRelationships.filter(link=>link&&typeof link.source==="string"&&typeof link.target==="string"), events: incomingEvents,
    cognition: boundedCognition(organism.cognition),
    sensoryDevelopment: incomingSensoryDev.filter(item => item && typeof item.name === "string").map(item => ({
      name: item.name.slice(0, 64),
      samples: Math.max(0, Number.parseInt(item.samples, 10) || 0),
      availability: Math.min(1, Math.max(0, Number(item.availability) || 0)),
      utility: Math.min(1, Math.max(0, Number(item.utility) || 0)),
      tier: ["active", "probing", "dormant"].includes(item.tier) ? item.tier : "dormant",
    })),
    sensoryRelations: incomingSensoryRel.filter(item => item && typeof item.sense_a === "string" && typeof item.sense_b === "string").map(item => ({
      senseA: item.sense_a.slice(0, 64),
      senseB: item.sense_b.slice(0, 64),
      synchronous: item.synchronous === null || item.synchronous === undefined ? null : Math.min(1, Math.max(-1, Number(item.synchronous) || 0)),
      aToB: item.a_to_b === null || item.a_to_b === undefined ? null : Math.min(1, Math.max(-1, Number(item.a_to_b) || 0)),
      bToA: item.b_to_a === null || item.b_to_a === undefined ? null : Math.min(1, Math.max(-1, Number(item.b_to_a) || 0)),
      samples: Math.max(0, Number.parseInt(item.samples, 10) || 0),
    })),
    sampling: {
      active: Math.max(0, Number.parseInt(organism.sampling?.active, 10) || 0),
      probing: Math.max(0, Number.parseInt(organism.sampling?.probing, 10) || 0),
      dormant: Math.max(0, Number.parseInt(organism.sampling?.dormant, 10) || 0),
      unknown: Math.max(0, Number.parseInt(organism.sampling?.unknown, 10) || 0),
      sampledThisTick: Math.max(0, Number.parseInt(organism.sampling?.sampled_this_tick, 10) || 0),
      discovered: Math.max(0, Number.parseInt(organism.sampling?.discovered, 10) || 0),
    },
    schemaVersion: snapshot.schema_version ?? 1,
  };
}

function ingestSnapshot(snapshot, announce = true) {
  const projection = boundedSnapshot(normalizeSnapshot(snapshot));
  if (!projection) return;
  state.tick = projection.tick;
  // The demo/replay animation position (0-59) and the organism's own real
  // tick number are different things — state.tick above only drives
  // decorative animation indexing. state.realTick is what "Tick" actually
  // means once real data has arrived, and it is never touched by the
  // demo/replay animation timer (roadmap safety finding A08).
  state.realTick = projection.tick;
  senses = projection.senses;
  beliefs = projection.beliefs;
  population = projection.population;
  relationships = projection.relationships;
  state.events = projection.events;
  if (Array.isArray(projection.events) && projection.events.length) {
    const seenEventKeys = new Set(state.liveEvents.map(e => `${e.tick}:${e.id}`));
    projection.events.forEach(event => {
      const key = `${projection.tick}:${event.id}`;
      if (!seenEventKeys.has(key)) {
        seenEventKeys.add(key);
        state.liveEvents.push({
          id: String(event.id),
          tick: projection.tick,
          type: event.type,
          label: event.label,
          explanation: event.explanation ?? "No additional explanation was included.",
          beliefId: event.belief_id ?? null,
          delta: Number(event.delta) || 0,
          chain: Array.isArray(event.causal_chain) ? event.causal_chain : [],
        });
      }
    });
    if (state.liveEvents.length > 2048) {
      state.liveEvents = state.liveEvents.slice(-2048);
    }
  }
  state.details = projection.details;
  state.sensoryDevelopment = projection.sensoryDevelopment;
  if (Array.isArray(projection.sensoryDevelopment) && projection.sensoryDevelopment.length) {
    projection.sensoryDevelopment.forEach(item => {
      let hist = state.senseHistory.get(item.name);
      if (!hist) { hist = []; state.senseHistory.set(item.name, hist); }
      hist.push(item.utility);
      if (hist.length > 14) hist.shift();
    });
  }
  state.sensoryRelations = projection.sensoryRelations;
  state.sampling = projection.sampling;
  state.schemaVersion = projection.schemaVersion;
  // Re-resolve by id against the freshly-ingested beliefs array rather than
  // keeping the previous snapshot's object — that object's certainty/evidence
  // are now stale even when its id still exists in the new collection
  // (roadmap safety finding B07).
  state.selected = beliefs.find(item => item.id === state.selected?.id) ?? beliefs[0] ?? null;
  if (projection.displayId) { state.displayId = projection.displayId; document.querySelector("#organism-name").textContent = `Organism ${projection.displayId}`; }
  state.organismState = projection.organismState;
  document.querySelector("#organism-state").textContent = projection.organismState[0].toUpperCase() + projection.organismState.slice(1);
  if (announce) document.querySelector(".connection small").textContent = "snapshot stream";
  renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderProfiles();
  renderCognitionState(projection.cognition);
}

function renderCognitionTopology(topology) {
  if (!topology) return;
  const subtitle = document.querySelector("#cognition-subtitle");
  const summary = document.querySelector("#cognition-topology-summary");
  if (!subtitle || !summary) return;
  subtitle.textContent = `Genome ${topology.genome_id ?? "?"} · revision ${topology.topology_revision ?? 0}`;
  summary.textContent = `${(topology.nodes ?? []).length} nodes, ${(topology.edges ?? []).length} edges`;
}

function renderCognitionState(cognition) {
  const readoutsEl = document.querySelector("#cognition-readouts");
  const errorsEl = document.querySelector("#cognition-prediction-errors");
  const mutationsEl = document.querySelector("#cognition-mutations");
  const safetyEl = document.querySelector("#cognition-safety-state");
  const subtitleEl = document.querySelector("#cognition-subtitle");
  const summaryEl = document.querySelector("#cognition-topology-summary");
  if (!readoutsEl || !errorsEl || !mutationsEl || !safetyEl || !subtitleEl) return;
  readoutsEl.replaceChildren();
  errorsEl.replaceChildren();
  mutationsEl.replaceChildren();
  if (!cognition) {
    if (state.schemaVersion === 1) {
      subtitleEl.textContent = "Structural cognition not configured";
      if (summaryEl) {
        summaryEl.textContent = "This resident is developing opaque senses autonomously. No owner-authored genome/cognitive graph was loaded.";
      }
    } else {
      subtitleEl.textContent = "No cognition data for this organism";
      if (summaryEl) {
        summaryEl.textContent = "";
      }
    }
    safetyEl.textContent = "";
    return;
  }
  Object.entries(cognition.readouts).forEach(([id, value]) => {
    const row = document.createElement("p"); row.textContent = `${id}: ${value}`; readoutsEl.append(row);
  });
  Object.entries(cognition.predictionErrors).forEach(([id, cls]) => {
    const row = document.createElement("p"); row.textContent = `${id}: ${cls}`; errorsEl.append(row);
  });
  cognition.mutations.forEach(mutation => {
    const row = document.createElement("p"); row.textContent = `${mutation.kind} ${mutation.nodeId ?? mutation.edgeId ?? ""}`; mutationsEl.append(row);
  });
  safetyEl.textContent = `Frozen: ${cognition.safetyState.frozen}, failures: ${cognition.safetyState.consecutiveFailures}`;
}

let currentInstanceSource = null;
let currentInstanceId = null;

function renderFleet(instances) {
  const list = document.querySelector("#fleet-list");
  if (!list) return;
  list.replaceChildren();
  const alive = instances.filter(i => i.liveness === "alive");
  instances.forEach(instance => {
    const row = document.createElement("button");
    row.className = `fleet-row fleet-${instance.liveness}${instance.instance_id === currentInstanceId ? " active" : ""}`;
    row.textContent = `${instance.display_id ?? instance.instance_id} (${instance.liveness})`;
    row.addEventListener("click", () => connectInstance(instance.instance_id));
    list.append(row);
  });
  if (!currentInstanceId && alive.length > 0 && !document.querySelector("#welcome").hidden) {
    connectInstance(alive[0].instance_id);
  }
}

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) {
    currentInstanceSource.close();
  }
  currentInstanceId = instanceId;
  const source = new EventSource(`/instance/${instanceId}/stream`);
  currentInstanceSource = source;
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.topology) { renderCognitionTopology(payload.topology); return; }
    if (payload.snapshot) { state.source = "local server"; document.querySelector("#welcome").hidden = true; document.querySelector(".connection strong").textContent = "Connected"; ingestSnapshot(payload.snapshot); }
  };
}

function connectFleet() {
  if (!("EventSource" in window)) return;
  const source = new EventSource("/fleet");
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    renderFleet(Array.isArray(payload.instances) ? payload.instances : []);
  };
  source.onerror = () => { /* passive: no local server running is a normal, silent state */ };
}

function showToast(message) {
  const toast = document.querySelector("#toast"); toast.textContent = message; toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2200);
}

function openReplayDialog() {
  document.querySelector("#welcome").hidden = true;
  document.querySelector("#replay-dialog").showModal();
}

function validateReplay(documentValue) {
  const snapshots = Array.isArray(documentValue) ? documentValue : documentValue?.snapshots;
  if (!Array.isArray(snapshots) || snapshots.length === 0) throw new Error("The replay must contain a non-empty snapshots array.");
  if (snapshots.length > 10000) throw new Error("The replay exceeds the 10,000 snapshot limit.");
  const firstInvalid = snapshots.findIndex(snapshot => !boundedSnapshot(snapshot));
  if (firstInvalid !== -1) throw new Error(`Snapshot ${firstInvalid + 1} does not match schema v1.`);
  return snapshots;
}

async function loadReplayFile(file) {
  const status = document.querySelector("#import-status"); const summary = document.querySelector("#replay-summary");
  summary.hidden = true; status.className = "import-status";
  try {
    if (!file || file.size > 5 * 1024 * 1024) throw new Error("Choose a JSON file no larger than 5 MB.");
    const parsed = JSON.parse(await file.text());
    state.replay = validateReplay(parsed); state.replayIndex = 0; state.mode = "replay"; state.source = "replay"; state.playing = false;
    document.querySelectorAll(".mode").forEach(button => button.classList.toggle("active", button.dataset.mode === "replay"));
    document.querySelector("#play").classList.add("paused"); document.querySelector("#play").setAttribute("aria-label", "Resume playback");
    ingestSnapshot(state.replay[0], false);
    document.querySelector(".connection strong").textContent = "Replay ready"; document.querySelector(".connection small").textContent = "local file";
    document.querySelector("#audit-transport").textContent = "Local replay";
    status.textContent = "✓ Replay ready"; status.classList.add("success");
    summary.hidden = false; summary.textContent = `${file.name} · ${state.replay.length} snapshots · ${(file.size / 1024).toFixed(1)} KB · kept in memory only`;
    window.setTimeout(() => document.querySelector("#replay-dialog").close(), 650); showToast(`Loaded ${state.replay.length} snapshots`);
  } catch (error) { status.textContent = error instanceof Error ? error.message : "The replay could not be opened."; status.classList.add("error"); }
}

function currentSnapshot() {
  const resourceBudget = { ticks_remaining: state.details.resourceBudget.ticksRemaining };
  ["cpu", "memory", "storage"].forEach(key => { if (typeof state.details.resourceBudget[key] === "number") resourceBudget[key] = state.details.resourceBudget[key]; });
  const events = state.events.slice(0, 64).map(event => {
    const beliefId = event.belief_id ?? event.beliefId ?? null;
    const chain = event.causal_chain ?? event.chain ?? [];
    const out = { id: String(event.id), type: event.type, label: event.label };
    if (event.explanation) out.explanation = event.explanation;
    if (beliefId) out.belief_id = beliefId;
    if (typeof event.delta === "number") out.delta = Math.max(-1, Math.min(1, event.delta));
    if (chain.length) out.causal_chain = chain.slice(0, 8);
    return out;
  });
  return {
    schema_version: 1,
    tick: state.realTick ?? state.tick,
    organism: {
      display_id: (state.displayId ?? "local-symbiont").slice(0, 48),
      state: state.organismState,
      narrative: state.details.narrative.slice(0, 600),
      acclimation: state.details.acclimation,
      resource_budget: resourceBudget,
      memory: state.details.memory.slice(0, 32),
      open_questions: state.details.openQuestions.slice(0, 16),
      investigations: state.details.investigations.slice(0, 16),
      regime_changes: state.details.regimeChanges.slice(0, 16),
      percepts: senses.slice(0, 32).map(item => ({ id: item.id, label: item.name, quality: item.quality, available: item.active })),
      beliefs: beliefs.slice(0, 128).map(item => ({ id: item.id, label: item.title, certainty: item.certainty, evidence_count: item.evidence, revision_count: item.revisions, contested: item.dissent })),
      events,
    },
    population: {
      members: population.slice(0, 500).map(item => ({ display_id: item.id, ecology: item.cluster, activity: item.pressure, knowledge_count: item.knowledge, contested_count: item.contested })),
      relationships: relationships.slice(0, 1000),
    },
  };
}

function exportReplay() {
  const snapshots = state.replay.length ? state.replay : [currentSnapshot()];
  const url = URL.createObjectURL(new Blob([JSON.stringify({ schema_version: 1, snapshots }, null, 2)], { type: "application/json" }));
  const link = document.createElement("a"); link.href = url; link.download = "symbiont-replay.json"; link.click(); URL.revokeObjectURL(url); showToast("Replay exported locally");
}

document.querySelectorAll(".toggle").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));
document.querySelectorAll(".mode").forEach(button => button.addEventListener("click", () => {
  if (button.dataset.mode === "live" && state.source === "replay") { showToast("Live input is not connected"); return; }
  state.mode = button.dataset.mode; document.querySelectorAll(".mode").forEach(b => b.classList.toggle("active", b === button));
}));
document.querySelector("#open-population").addEventListener("click", () => switchView("population"));
document.querySelector("#scrubber").addEventListener("input", event => { const value = Number(event.target.value); if (state.replay.length) state.replayIndex = value; else state.tick = value; state.mode = "replay"; document.querySelectorAll(".mode").forEach(b => b.classList.toggle("active", b.dataset.mode === "replay")); advance(0); });
document.querySelector("#previous").addEventListener("click", () => advance(-1));
document.querySelector("#next").addEventListener("click", () => advance(1));
document.querySelector("#play").addEventListener("click", event => { state.playing = !state.playing; event.currentTarget.classList.toggle("paused", !state.playing); event.currentTarget.setAttribute("aria-label", state.playing ? "Pause playback" : "Resume playback"); });

window.addEventListener("message", event => {
  if (event.data?.type !== "symbiont-observatory-snapshot") return;
  if (event.origin !== window.location.origin) return;
  state.source="same-origin message";document.querySelector(".connection strong").textContent="Connected";document.querySelector("#welcome").hidden=true;ingestSnapshot(event.data.snapshot);
});

document.querySelector("#welcome-demo").addEventListener("click", () => { document.querySelector("#welcome").hidden = true; document.querySelector(".connection strong").textContent="Connected";document.querySelector(".connection small").textContent="demo stream";showToast("Demo stream started"); });
document.querySelector("#welcome-open").addEventListener("click", openReplayDialog);
document.querySelector("#import-replay").addEventListener("click", openReplayDialog);
document.querySelector("#replay-file").addEventListener("change", event => loadReplayFile(event.target.files?.[0]));
const dropZone = document.querySelector("#drop-zone");
dropZone.addEventListener("dragover", event => { event.preventDefault(); dropZone.classList.add("dragging"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", event => { event.preventDefault(); dropZone.classList.remove("dragging"); loadReplayFile(event.dataTransfer?.files?.[0]); });
document.querySelector("#privacy-audit").addEventListener("click", () => { const drawer = document.querySelector("#audit-drawer"); drawer.classList.add("open"); drawer.setAttribute("aria-hidden", "false"); document.querySelector("#close-audit").focus(); });
document.querySelector("#close-audit").addEventListener("click", () => { const drawer = document.querySelector("#audit-drawer"); drawer.classList.remove("open"); drawer.setAttribute("aria-hidden", "true"); });
document.querySelector("#export-replay").addEventListener("click", exportReplay);
document.querySelectorAll(".profile").forEach(button=>button.addEventListener("click",()=>{state.profile=button.dataset.profile;document.querySelectorAll(".profile").forEach(item=>item.classList.toggle("active",item===button));["summary","organism","research"].forEach(name=>document.querySelector(`#${name}-profile`).hidden=name!==state.profile);document.querySelector("#deep-inspector").hidden=state.profile!=="research";localStorage.setItem("symbiont-observatory-profile",state.profile);renderProfiles();}));
function toggleDrawer(id,open){const drawer=document.querySelector(id);drawer.classList.toggle("open",open);drawer.setAttribute("aria-hidden",String(!open));}
document.querySelector("#open-help").addEventListener("click",()=>toggleDrawer("#help-drawer",true));document.querySelector("#close-help").addEventListener("click",()=>toggleDrawer("#help-drawer",false));
document.querySelector("#open-accessible-table").addEventListener("click",()=>{renderAccessibleTable();document.querySelector("#accessible-dialog").showModal();});
document.querySelectorAll(".population-mode").forEach(button=>button.addEventListener("click",()=>{state.populationMode=button.dataset.populationMode;document.querySelectorAll(".population-mode").forEach(item=>item.classList.toggle("active",item===button));renderPopulation();}));
document.querySelector("#clear-comparison").addEventListener("click",()=>{state.organismA=null;state.organismB=null;renderPopulation();renderPopulationInspector();});
document.querySelectorAll(".inspector-tab").forEach(button => button.addEventListener("click", () => {
  const tab = button.dataset.tab;
  document.querySelectorAll(".inspector-tab").forEach(item => { item.classList.toggle("active", item === button); item.setAttribute("aria-selected", String(item === button)); });
  document.querySelector("#current-panel").hidden = tab !== "current";
  document.querySelector("#history-panel").hidden = tab !== "history";
  document.querySelector("#cognition-panel").hidden = tab !== "cognition";
  document.querySelector("#population-preview").hidden = tab !== "current";
  if (tab === "history") renderHistory();
}));
document.querySelector("#history-search").addEventListener("input", event => { state.query = event.target.value; document.querySelector('[data-tab="history"]').click(); });
document.querySelector("#mark-a").addEventListener("click", event => { if (!state.replay.length) { showToast("Load a replay to compare points"); return; } state.compareA = state.replayIndex; event.currentTarget.classList.add("set"); renderHistory(); showToast(`Point A set at ${state.compareA + 1}`); });
document.querySelector("#mark-b").addEventListener("click", event => { if (!state.replay.length) { showToast("Load a replay to compare points"); return; } state.compareB = state.replayIndex; event.currentTarget.classList.add("set"); renderHistory(); showToast(`Point B set at ${state.compareB + 1}`); });
document.addEventListener("keydown", event => {
  if (event.target instanceof HTMLInputElement || document.querySelector("#replay-dialog").open) return;
  if (event.key === " ") { event.preventDefault(); document.querySelector("#play").click(); }
  if (event.key === "ArrowLeft") advance(-1); if (event.key === "ArrowRight") advance(1);
  if (event.key.toLowerCase() === "o") openReplayDialog();
  if (event.key.toLowerCase() === "h") toggleDrawer("#help-drawer",!document.querySelector("#help-drawer").classList.contains("open"));
  if (["1","2","3"].includes(event.key)) document.querySelectorAll(".profile")[Number(event.key)-1].click();
  if (event.key === "Escape") document.querySelector("#close-audit").click();
});

renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderHistory(); renderProfiles();
connectFleet();
const storedView = localStorage.getItem("symbiont-observatory-view"); if (["individual", "population"].includes(storedView)) switchView(storedView);
const storedProfile=localStorage.getItem("symbiont-observatory-profile");if(["summary","organism","research"].includes(storedProfile))document.querySelector(`[data-profile="${storedProfile}"]`).click();
if ("BroadcastChannel" in window) { const channel=new BroadcastChannel("symbiont-observatory-v1");channel.addEventListener("message",event=>{if(event.data?.type==="symbiont-observatory-snapshot"){state.source="local channel";document.querySelector("#welcome").hidden=true;document.querySelector(".connection strong").textContent="Connected";ingestSnapshot(event.data.snapshot);}}); }
// The "live" branch here only animates the bundled demo data (state.source
// stays "demo" until a real snapshot is ever ingested). Once a real
// same-origin/BroadcastChannel snapshot arrives, this timer must never
// again mutate state.tick on its own — only a new incoming snapshot may —
// or the visible/exported tick silently drifts away from what the runtime
// actually reported (roadmap safety finding A08).
setInterval(() => { if (state.playing && ((state.mode === "live" && state.source === "demo") || state.replay.length)) advance(1); }, 1800);
