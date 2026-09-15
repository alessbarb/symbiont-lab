import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";
import { renderInspector } from "./inspector.js";
import { renderIndividualPerspective } from "./individual.js";
import { projectPhenotypeMorphology } from "../projection/morphology.js";

function buildIdentitySeed() {
  // Order matters: demo first (no instance/topology concept applies at
  // all); then a live organism whose topology is actually current (the
  // strongest identity available); then an explicit replay (never has
  // instanceId -- the replay format carries no instance concept); then
  // any other live connection that has an instanceId but no topology yet
  // (e.g. schema-v1, or schema-v2 before its first topology message) --
  // this case must NOT fall into the replay branch, or a live real
  // organism's identity would silently ignore its own instanceId, which
  // is the whole reason instanceId was introduced over the non-unique
  // displayId. Final fallback covers any other combination.
  if (state.source === "demo") return "demo";
  if (state.topology && state.instanceId) return `${state.topology.genomeId}:${state.instanceId}`;
  if (state.source === "replay") return `replay:${state.displayId ?? "unknown"}`;
  if (state.instanceId) return `instance:${state.instanceId}`;
  return `${state.source}:${state.displayId ?? "unknown"}`;
}

function buildMorphologyInput() {
  const topologyIsCurrent = Boolean(
    state.topology && state.cognition &&
    state.topology.topologyRevision === state.cognition.topologyRevision
  );
  const structuralSenses = topologyIsCurrent ? state.topology.nodes.filter(n => n.kind === "sense") : [];
  const internalNodes = topologyIsCurrent ? state.topology.nodes.filter(n => n.kind !== "sense") : [];
  const edges = topologyIsCurrent ? state.topology.edges : [];
  return {
    identitySeed: buildIdentitySeed(),
    percepts: state.senses.map(sense => ({ id: sense.id, quality: sense.quality, active: sense.active })),
    hasCurrentTopology: topologyIsCurrent,
    structuralSenses,
    internalNodes,
    edges,
    topologyHealth: state.cognition?.topologyHealth ?? null,
    recovering: state.cognition?.recovering ?? false,
    frozen: state.cognition?.safetyState?.frozen ?? false,
  };
}

function receptorActivityState(perceptById, anchorId) {
  // A structural sense node with no matching dynamic percept (routine once
  // topology has more SENSE nodes than the 32-percept cap, e.g. worker-3's
  // 58) has zero evidence about its current activity -- it must read as
  // "unknown", never default to "active", or Observatory would be
  // fabricating positive activity for senses it has no reading for at all.
  const percept = perceptById.get(anchorId);
  if (!percept) return "unknown";
  return percept.active ? "active" : "inactive";
}

function renderOrganism() {
  const canvas = document.querySelector("#organism-canvas");
  canvas.replaceChildren();
  const defs = svg("defs");
  const radial = svg("radialGradient", { id: "cell-fill" });
  radial.append(svg("stop", { offset: "0", "stop-color": "#17274e", "stop-opacity": ".46" }), svg("stop", { offset: ".75", "stop-color": "#0a2632", "stop-opacity": ".16" }), svg("stop", { offset: "1", "stop-color": "#71e9ba", "stop-opacity": ".08" }));
  defs.append(radial); canvas.append(defs);
  const group = svg("g", { class: "organism-group" });

  const morphology = projectPhenotypeMorphology(buildMorphologyInput());
  const perceptById = new Map(state.senses.map(sense => [sense.id, sense]));
  const sensePositions = new Map(morphology.receptorAnchors.map(anchor => [anchor.id, anchor]));

  morphology.externalInputAnchors.forEach((inputAnchor, index) => {
    const receptorAnchor = morphology.receptorAnchors[index];
    const activityState = receptorActivityState(perceptById, inputAnchor.id);
    const percept = perceptById.get(inputAnchor.id);
    // quality only ever modulates its own receptor's opacity -- never the
    // whole-organism boundary (that would overload a per-reading signal
    // into a body-wide one it was never meant to carry).
    const pathOpacity = activityState === "active"
      ? String(0.35 + (percept?.quality ?? 1) * 0.5)
      : activityState === "inactive" ? ".25" : ".12";
    const midX = (inputAnchor.x + receptorAnchor.x) / 2;
    group.append(svg("path", { d: `M ${inputAnchor.x} ${inputAnchor.y} C ${inputAnchor.x + 85} ${inputAnchor.y}, ${midX} ${receptorAnchor.y}, ${receptorAnchor.x} ${receptorAnchor.y}`, class: "sensor-path", opacity: pathOpacity }));
    group.append(svg("circle", { cx: receptorAnchor.x, cy: receptorAnchor.y, r: 4, class: `phenotype-receptor phenotype-receptor-${activityState}` }));
    const perceivedThisTick = (state.source === "demo")
      ? activityState === "active"
      : (Array.isArray(state.events) && state.events.some(e => e.type === "perception" && (e.id.includes(inputAnchor.id) || e.label.includes(inputAnchor.id) || (percept?.name && e.label.includes(percept.name)))));
    if (perceivedThisTick && !morphology.presentation.reducedMotion) {
      group.append(svg("circle", { cx: receptorAnchor.x, cy: receptorAnchor.y, r: 3.5, class: "sensor-pulse", opacity: "1" }));
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

  group.append(svg("path", { d: morphology.boundaryPath, fill: "url(#cell-fill)", class: "phenotype-boundary" }));
  group.append(svg("path", { d: morphology.boundaryPath, class: "phenotype-boundary-inner" }));
  group.classList.toggle("phenotype-frozen", morphology.presentation.desaturated);
  group.style.opacity = String(morphology.presentation.boundaryTension);

  // Fibres drawn before internal-anchor nodes so a fibre's line terminates
  // visually under its endpoint node, not drawn on top of it.
  morphology.fibres.forEach(fibre => {
    group.append(svg("line", { x1: fibre.x1, y1: fibre.y1, x2: fibre.x2, y2: fibre.y2, class: `fibre fibre-${fibre.kind}` }));
  });
  morphology.internalAnchors.forEach(anchor => {
    group.append(svg("circle", { cx: anchor.x, cy: anchor.y, r: anchor.kind === "readout" ? 14 : 8, class: `internal-anchor internal-anchor-${anchor.kind}` }));
  });

  if (state.source === "demo") {
    state.beliefs.forEach((belief, index) => {
      const neighbor = state.beliefs[(index + 4) % state.beliefs.length];
      group.append(svg("line", { x1: belief.x, y1: belief.y, x2: neighbor.x, y2: neighbor.y, class: "belief-edge" }));
    });
  }

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
    node.addEventListener("click", () => { state.selected = belief; renderInspector(); renderIndividualPerspective(); document.querySelector(".inspector").classList.add("open"); });
    group.append(node);
  });
  canvas.append(group);
}

export { renderOrganism };
