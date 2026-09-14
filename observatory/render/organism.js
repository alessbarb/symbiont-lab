import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";
import { renderInspector } from "./inspector.js";

function renderOrganism() {
  const canvas = document.querySelector("#organism-canvas");
  canvas.replaceChildren();
  const defs = svg("defs");
  const radial = svg("radialGradient", { id: "cell-fill" });
  radial.append(svg("stop", { offset: "0", "stop-color": "#17274e", "stop-opacity": ".46" }), svg("stop", { offset: ".75", "stop-color": "#0a2632", "stop-opacity": ".16" }), svg("stop", { offset: "1", "stop-color": "#71e9ba", "stop-opacity": ".08" }));
  defs.append(radial); canvas.append(defs);
  const group = svg("g", { class: "organism-group" });

  const count = state.senses.length;
  const top = 140;
  const bottom = 580;
  const sensePositions = new Map();

  state.senses.forEach((sense, i) => {
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

  state.beliefs.forEach((belief, index) => {
    const neighbor = state.beliefs[(index + 4) % state.beliefs.length];
    group.append(svg("line", { x1: belief.x, y1: belief.y, x2: neighbor.x, y2: neighbor.y, class: "belief-edge" }));
  });
  let focus = null;
  if (state.source === "demo") {
    focus = state.beliefs.length ? state.beliefs[(state.tick + 7) % state.beliefs.length] : null;
  } else if (Array.isArray(state.events) && state.events.length) {
    const attentionEvent = state.events.find(e => e.type === "attention");
    if (attentionEvent) {
      const targetId = attentionEvent.belief_id ?? attentionEvent.beliefId;
      if (targetId) {
        focus = state.beliefs.find(b => b.id === targetId || b.id.slice(0, 64) === targetId.slice(0, 64));
      }
      if (!focus && attentionEvent.label) {
        const match = attentionEvent.label.match(/(?:signal|belief|sense)[._a-zA-Z0-9]+/);
        if (match) {
          focus = state.beliefs.find(b => b.id.includes(match[0]) || b.title.includes(match[0]));
        }
      }
    }
  }
  if (focus) {
    group.append(svg("path", { d: `M ${focus.x} ${focus.y} Q 470 365 555 430`, class: "dissent-path", opacity: focus.dissent ? "1" : ".35" }));
    group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 30, class: "attention-ring" }));
    group.append(svg("circle", { cx: focus.x, cy: focus.y, r: 16, class: "attention-ring" }));
  }

  state.beliefs.forEach(belief => {
    const node = svg("circle", { cx: belief.x, cy: belief.y, r: belief.r, class: `belief-node${state.selected?.id === belief.id ? " selected" : ""}`, opacity: belief.certainty });
    node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderOrganism(); document.querySelector(".inspector").classList.add("open"); });
    group.append(node);
  });
  canvas.append(group);
}

export { renderOrganism };
