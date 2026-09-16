import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";

function populationMembers() { return state.fleetConnected ? state.fleetPopulation : state.population; }

function renderPopulation(target = "#population-canvas", mini = false) {
  const canvas = document.querySelector(target); canvas.replaceChildren();
  const population = populationMembers();
  const sx = mini ? .34 : 1, sy = mini ? .22 : 1;
  const colors = [palette.cyan, palette.mint, palette.violet, palette.amber, palette.coral, "#7bb7ff", "#b8e986", "#d79cff"];
  if (!mini) [...new Set(population.map(item => item.cluster))].forEach(cluster => {
    const members = population.filter(item => item.cluster === cluster); if (!members.length) return;
    const cx = members.reduce((sum,item)=>sum+item.x,0)/members.length, cy=members.reduce((sum,item)=>sum+item.y,0)/members.length;
    canvas.append(svg("ellipse", { cx, cy, rx:115, ry:92, fill:`${colors[cluster]}0c`, stroke:`${colors[cluster]}55`, class:"population-hull" }));
  });
  const relationships = state.fleetConnected ? state.fleetRelationships : state.relationships;
  relationships.filter(link => mini || link.type === state.populationMode).forEach(link => {
    const item=population.find(member=>member.id===link.source), other=population.find(member=>member.id===link.target); if(!item||!other)return;
    canvas.append(svg("line", { x1:item.x*sx,y1:item.y*sy,x2:other.x*sx,y2:other.y*sy,opacity:String(.25+link.strength*.65),class:`population-edge${link.type === "dissent" ? " dissent" : ""}` }));
  });
  population.forEach((item, i) => {
    const magnitude = state.populationMode === "knowledge" ? Math.min(1,item.knowledge/45) : state.populationMode === "dissent" ? Math.min(1,item.contested/5) : item.pressure;
    const modeColor = state.populationMode === "activity" ? palette.amber : state.populationMode === "dissent" ? palette.coral : colors[item.cluster];
    const selectedClass = state.organismA?.id === item.id ? " selected-a" : state.organismB?.id === item.id ? " selected-b" : "";
    const node = svg("circle", { cx: item.x * sx, cy: item.y * sy, r: (mini ? 4 : 7 + magnitude * 7), fill: `${modeColor}33`, stroke: modeColor, color: modeColor, opacity: item.liveness === "stale" ? ".42" : "1", class: `population-node${selectedClass}` });
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
  const population = populationMembers();
  if (population.length <= 1) { subtitle.textContent="Single organism recorded"; const p=document.createElement("p");p.textContent="This recording only contains one organism, so ecology, knowledge, activity and dissent comparisons have nothing to relate it to yet. Load or record data with more than one organism to use this view.";explanation.append(p); const empty=document.createElement("p");empty.className="comparison-empty";empty.textContent="Comparison needs at least two organisms.";comparison.append(empty);return; }
  if (!selected) { subtitle.textContent="Select an organism"; const p=document.createElement("p");p.textContent="Choose a node to explain its ecological cluster, then choose another to compare them.";explanation.append(p); const empty=document.createElement("p");empty.className="comparison-empty";empty.textContent="No organisms selected.";comparison.append(empty);return; }
  const members=population.filter(item=>item.cluster===selected.cluster); subtitle.textContent=`Ecology ${selected.cluster + 1} · ${members.length} organisms`;
  const title=document.createElement("h3");title.textContent=`Ecology ${selected.cluster + 1}`; const body=document.createElement("p");body.textContent=`These organisms are close because their normalized environments are compatible. This grouping says nothing about which organism is more reliable or correct.`;
  const facts=document.createElement("ul");facts.className="cluster-facts"; [`${members.length} organisms share this context`,`Average activity ${(members.reduce((s,x)=>s+x.pressure,0)/members.length*100).toFixed(0)}%`,`${members.reduce((s,x)=>s+x.contested,0)} contested beliefs remain visible`].forEach(text=>{const li=document.createElement("li");li.textContent=text;facts.append(li)}); explanation.append(title,body,facts);
  if (!state.organismA || !state.organismB) { const empty=document.createElement("p");empty.className="comparison-empty";empty.textContent=`${state.organismA.id} is selected as A. Choose a second organism to compare without collapsing their differences into one score.`;comparison.append(empty);return; }
  const names=document.createElement("div");names.className="comparison-names";[state.organismA,state.organismB].forEach((item,index)=>{const box=document.createElement("div");box.className="comparison-name";const b=document.createElement("b");b.textContent=`${index?"B":"A"} · ${item.id}`;const small=document.createElement("small");small.textContent=`Ecology ${item.cluster+1}`;box.append(b,small);names.append(box)});comparison.append(names);
  const table=document.createElement("table"); [["Ecology",`Context ${state.organismA.cluster+1}`,`Context ${state.organismB.cluster+1}`],["Activity",`${(state.organismA.pressure*100).toFixed(0)}%`,`${(state.organismB.pressure*100).toFixed(0)}%`],["Shared knowledge",state.organismA.knowledge,state.organismB.knowledge],["Contested beliefs",state.organismA.contested,state.organismB.contested]].forEach(row=>{const tr=document.createElement("tr");row.forEach((value,index)=>{const cell=document.createElement(index?"td":"th");cell.textContent=String(value);tr.append(cell)});table.append(tr)});comparison.append(table);
}

export { renderPopulation, selectPopulationMember, renderPopulationInspector };
