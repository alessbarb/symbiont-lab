import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";
import { renderInspector } from "./inspector.js";
import { renderIndividualPerspective } from "./individual.js";

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
  state.senses.forEach((sense, index) => {
    const row = document.createElement("div");
    row.setAttribute("role", "button");
    row.tabIndex = 0;
    row.className = `sense-row${sense.knowledgeSignalId && sense.knowledgeSignalId === state.selectedSignalId ? " selected" : (index === 0 && !state.selectedSignalId ? " selected" : "")}`;
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
    const selectSense = () => {
      document.querySelectorAll(".sense-row").forEach(el => el.classList.remove("selected"));
      row.classList.add("selected");
      state.selectedSignalId = sense.knowledgeSignalId ?? null;
      state.selectedNodeId = sense.id;
      state.selected = state.beliefs.find(b => b.id === sense.id) ?? null;
      renderInspector();
      renderIndividualPerspective();
      document.querySelector(".inspector").classList.add("open");
    };
    row.addEventListener("click", selectSense);
    row.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectSense();
      }
    });
    list.append(row);
  });
}

export { sparkline, renderSenses };
