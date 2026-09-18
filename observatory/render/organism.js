import { state } from "../state/store.js";
import { svg, palette } from "./svg.js";
import { renderInspector } from "./inspector.js";
import { renderIndividualPerspective } from "./individual.js";
import { projectPhenotypeMorphology } from "../projection/morphology.js";
import { humanSignalLabel } from "./provenance.js";

function buildIdentitySeed() {
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
  const internalNodes = topologyIsCurrent ? state.topology.nodes : [];
  const edges = topologyIsCurrent ? state.topology.edges : [];
  return {
    identitySeed: buildIdentitySeed(),
    percepts: state.senses.map(sense => ({ id: sense.id, quality: sense.quality, active: sense.active })),
    worldSignals: state.senses.map(sense => ({ id: sense.id })),
    receptors: (state.sensoryPhenotype?.sensors ?? []).map(sensor => ({ id: sensor.sensorId })),
    hasCurrentTopology: topologyIsCurrent,
    structuralSenses,
    internalNodes,
    edges,
    topologyHealth: state.cognition?.topologyHealth ?? null,
    recovering: state.cognition?.recovering ?? false,
    frozen: state.cognition?.safetyState?.frozen ?? false,
  };
}

function resolveBeliefPosition(belief, index, sensePositions) {
  for (const [senseId, pos] of sensePositions.entries()) {
    if (belief.id.includes(senseId) || (senseId.length > 5 && belief.id.includes(senseId.slice(0, 16)))) {
      const dx = pos.x - 450;
      const dy = pos.y - 360;
      const dist = Math.hypot(dx, dy) || 1;
      const targetDist = 95 + (index % 4) * 28;
      return {
        x: Math.round(450 + (dx / dist) * targetDist),
        y: Math.round(360 + (dy / dist) * targetDist * 0.82),
      };
    }
  }
  if (belief.x != null && belief.y != null) {
    return { x: belief.x, y: belief.y };
  }
  const angle = index * 2.399;
  const radius = 48 + (index % 5) * 42;
  return {
    x: Math.round(450 + Math.cos(angle) * radius),
    y: Math.round(360 + Math.sin(angle) * radius * 0.82),
  };
}

function reserveLevel(reserveClass) {
  return ({ depleted: 0.08, low: 0.3, moderate: 0.62, replete: 0.92 })[reserveClass] ?? 0.45;
}

function renderMetabolicCore(group) {
  const reserves = state.metabolism?.reserveClasses ?? {};
  const pressure = state.metabolism?.pressure ?? "unknown";
  const chambers = [
    ["observation", "OBS", -24, -22],
    ["cognition", "COG", 24, -22],
    ["persistence", "MEM", -24, 22],
    ["maintenance", "MNT", 24, 22],
  ];
  const core = svg("g", { class: `phenotype-metabolic-core pressure-${pressure}` });
  const shell = svg("circle", { cx: 450, cy: 360, r: 55, class: "metabolic-core-shell" });
  core.append(shell);

  chambers.forEach(([key, label, dx, dy]) => {
    const level = reserveLevel(reserves[key]);
    const r = 11 + level * 8;
    const chamber = svg("circle", {
      cx: 450 + dx,
      cy: 360 + dy,
      r: r.toFixed(1),
      class: `metabolic-chamber reserve-${reserves[key] ?? "unknown"}`,
      opacity: String(0.38 + level * 0.55),
    });
    const title = svg("title");
    title.textContent = `${key} reserve · ${reserves[key] ?? "unknown"}`;
    chamber.append(title);
    core.append(chamber);
    const text = svg("text", {
      x: 450 + dx,
      y: 363 + dy,
      class: "metabolic-chamber-label",
      "text-anchor": "middle",
    });
    text.textContent = label;
    core.append(text);
  });

  const label = svg("text", { x: 450, y: 430, class: "metabolic-core-label", "text-anchor": "middle" });
  label.textContent = `metabolism · ${pressure}`;
  core.append(label);
  group.append(core);
}

function renderDegradationOrgan(group) {
  const retained = Math.max(0, state.degradation?.retainedItems ?? 0);
  const excreted = Math.max(0, state.degradation?.excretedUnits ?? 0);
  const phase = state.development?.phase ?? "unknown";
  const load = Math.min(1, retained / 64);
  const x = 600;
  const y = 470;
  const organ = svg("g", { class: "phenotype-degradation-organ" });

  organ.append(svg("ellipse", {
    cx: x, cy: y,
    rx: 28 + load * 18,
    ry: 18 + load * 12,
    class: `degradation-sac load-${load > .66 ? "high" : load > .25 ? "medium" : "low"}`,
  }));
  organ.append(svg("path", {
    d: `M ${x + 23} ${y + 4} Q ${x + 62} ${y + 16} ${x + 82} ${y + 48}`,
    class: "degradation-duct",
  }));
  const outlet = svg("circle", { cx: x + 84, cy: y + 50, r: 4 + Math.min(5, excreted), class: "degradation-outlet" });
  organ.append(outlet);

  const label = svg("text", { x, y: y - 30, class: "phenotype-organ-label", "text-anchor": "middle" });
  label.textContent = `degradation · ${retained} retained`;
  organ.append(label);
  const sub = svg("text", { x, y: y + 38, class: "phenotype-organ-sub", "text-anchor": "middle" });
  sub.textContent = `excreted ${excreted} · ${phase}`;
  organ.append(sub);
  group.append(organ);
}

function renderNeuralTerritories(group, anchors) {
  const groups = new Map();
  anchors.forEach(anchor => {
    if (anchor.kind === "sense") return;
    const bucket = groups.get(anchor.kind) ?? [];
    bucket.push(anchor);
    groups.set(anchor.kind, bucket);
  });
  const classMap = {
    concept: "concepts",
    state: "state",
    predictor: "prediction",
    gate: "gating",
    readout: "readout",
  };
  groups.forEach((items, kind) => {
    if (!items.length) return;
    const cx = items.reduce((sum, item) => sum + item.x, 0) / items.length;
    const cy = items.reduce((sum, item) => sum + item.y, 0) / items.length;
    const spread = Math.max(28, Math.min(82, 20 + Math.sqrt(items.length) * 11));
    const halo = svg("ellipse", {
      cx: cx.toFixed(1),
      cy: cy.toFixed(1),
      rx: (spread * 1.25).toFixed(1),
      ry: (spread * .82).toFixed(1),
      class: `neural-territory neural-territory-${kind}`,
    });
    group.append(halo);
    const label = svg("text", {
      x: cx.toFixed(1),
      y: (cy - spread * .6).toFixed(1),
      class: "neural-territory-label",
      "text-anchor": "middle",
    });
    label.textContent = classMap[kind] ?? kind;
    group.append(label);
  });
}

function appendReceptorGlyph(group, sensor, anchor, selected) {
  const utility = Math.max(0, Math.min(1, sensor.utility ?? 0));
  const base = 4 + utility * 2.2;
  const cls = `phenotype-receptor organism-owned maturity-${sensor.maturity}${selected ? " selected" : ""}`;
  let node;
  switch (sensor.transduction) {
    case "difference": {
      node = svg("g", { class: cls });
      node.append(
        svg("circle", { cx: anchor.x - base * .65, cy: anchor.y, r: base * .72 }),
        svg("circle", { cx: anchor.x + base * .65, cy: anchor.y, r: base * .72 }),
        svg("line", { x1: anchor.x - base * 1.5, y1: anchor.y - base * 1.6, x2: anchor.x - base * .5, y2: anchor.y - base * .4 }),
        svg("line", { x1: anchor.x + base * 1.5, y1: anchor.y - base * 1.6, x2: anchor.x + base * .5, y2: anchor.y - base * .4 }),
      );
      break;
    }
    case "integrate": {
      node = svg("path", {
        d: `M ${anchor.x - base} ${anchor.y - base * .85} Q ${anchor.x} ${anchor.y - base * 1.65} ${anchor.x + base} ${anchor.y - base * .85} L ${anchor.x + base * .75} ${anchor.y + base} Q ${anchor.x} ${anchor.y + base * 1.45} ${anchor.x - base * .75} ${anchor.y + base} Z`,
        class: cls,
      });
      break;
    }
    case "threshold": {
      const pts = [
        [anchor.x, anchor.y - base * 1.3],
        [anchor.x + base * 1.15, anchor.y + base],
        [anchor.x - base * 1.15, anchor.y + base],
      ].map(([x,y]) => `${x},${y}`).join(" ");
      node = svg("polygon", { points: pts, class: cls });
      break;
    }
    default:
      node = svg("circle", { cx: anchor.x, cy: anchor.y, r: base, class: cls });
      break;
  }
  const title = svg("title");
  title.textContent = `${sensor.sensorId} · ${sensor.transduction} · utility ${sensor.utility.toFixed(3)} · selection ${sensor.selectionCredit.toFixed(3)}`;
  node.append(title);
  group.append(node);
}

function renderOrganism() {
  const canvas = document.querySelector("#organism-canvas");
  canvas.replaceChildren();

  const defs = svg("defs");
  const radial = svg("radialGradient", { id: "cell-fill" });

  const health = state.cognition?.topologyHealth;
  const isFrozen = state.cognition?.safetyState?.frozen;
  const isStressed = Array.isArray(state.details?.regimeChanges) && state.details.regimeChanges.length > 0;
  const isAdaptive = health === "adaptive" || health === "connected";

  let coreColor = "#17274e";
  let midColor = "#0a2632";
  let edgeColor = "#71e9ba";

  if (isFrozen) {
    coreColor = "#1a212b";
    midColor = "#141920";
    edgeColor = "#627382";
  } else if (isStressed) {
    coreColor = "#2d1628";
    midColor = "#1f1422";
    edgeColor = "#ff7f83";
  } else if (isAdaptive) {
    coreColor = "#0d2b38";
    midColor = "#0a262e";
    edgeColor = "#71e9ba";
  }

  radial.append(
    svg("stop", { offset: "0", "stop-color": coreColor, "stop-opacity": ".52" }),
    svg("stop", { offset: ".72", "stop-color": midColor, "stop-opacity": ".20" }),
    svg("stop", { offset: "1", "stop-color": edgeColor, "stop-opacity": ".10" })
  );
  defs.append(radial);

  [
    { id: "arrow-exc", color: "rgba(80,217,255,.8)" },
    { id: "arrow-inh", color: "rgba(255,127,131,.8)" },
    { id: "arrow-mod", color: "rgba(255,189,84,.8)" }
  ].forEach(m => {
    const marker = svg("marker", {
      id: m.id,
      viewBox: "0 0 6 6",
      refX: "5",
      refY: "3",
      markerWidth: "4",
      markerHeight: "4",
      orient: "auto"
    });
    marker.append(svg("path", { d: "M 0 1 L 5 3 L 0 5 z", fill: m.color }));
    defs.append(marker);
  });
  canvas.append(defs);

  const group = svg("g", { class: "organism-group" });
  const morphology = projectPhenotypeMorphology(buildMorphologyInput());
  const perceptById = new Map(state.senses.map(sense => [sense.id, sense]));

  const phenotypeSensors = state.sensoryPhenotype?.sensors ?? [];
  const receptorPositions = new Map();
  const worldPositions = new Map();
  const sensePositions = new Map();
  const pendingReceptors = [];

  phenotypeSensors.slice(0, morphology.receptorAnchors.length).forEach((sensor, index) => {
    const anchor = morphology.receptorAnchors[index];
    receptorPositions.set(sensor.sensorId, anchor);
    pendingReceptors.push({ sensor, anchor });
    if (sensor.downstreamName) sensePositions.set(sensor.downstreamName, anchor);
  });

  morphology.externalInputAnchors.forEach((inputAnchor) => {
    const percept = perceptById.get(inputAnchor.id);
    const signalId = percept?.knowledgeSignalId ?? null;
    if (signalId) worldPositions.set(signalId, inputAnchor);

    const label = humanSignalLabel(signalId, percept?.name ?? percept?.id ?? inputAnchor.id);
    const labelNode = svg("text", {
      x: String(inputAnchor.x - 10),
      y: String(inputAnchor.y - 1),
      class: "phenotype-world-label",
      "text-anchor": "end"
    });
    labelNode.textContent = label.slice(0, 22);
    group.append(labelNode);

    const opaqueNode = svg("text", {
      x: String(inputAnchor.x - 10),
      y: String(inputAnchor.y + 10),
      class: "phenotype-world-id",
      "text-anchor": "end"
    });
    opaqueNode.textContent = signalId ? signalId.slice(0, 18) + "…" : inputAnchor.id.slice(0, 18);
    group.append(opaqueNode);

    const worldNode = svg("circle", {
      cx: inputAnchor.x,
      cy: inputAnchor.y,
      r: 3.4,
      class: `phenotype-world-signal ${percept?.active ? "active" : "inactive"}`
    });
    group.append(worldNode);

    const matchingSensors = signalId
      ? phenotypeSensors.filter(sensor => (sensor.signalIds ?? []).includes(signalId))
      : [];

    if (!matchingSensors.length) {
      const unbound = svg("text", {
        x: String(inputAnchor.x + 8),
        y: String(inputAnchor.y + 3),
        class: "phenotype-world-unbound"
      });
      unbound.textContent = "unbound";
      group.append(unbound);
      return;
    }

    matchingSensors.forEach(sensor => {
      const receptorAnchor = receptorPositions.get(sensor.sensorId);
      if (!receptorAnchor) return;
      const activityState = percept?.active ? "active" : "inactive";
      const midX = (inputAnchor.x + receptorAnchor.x) / 2;
      group.append(svg("path", {
        d: `M ${inputAnchor.x} ${inputAnchor.y} C ${inputAnchor.x + 70} ${inputAnchor.y}, ${midX} ${receptorAnchor.y}, ${receptorAnchor.x} ${receptorAnchor.y}`,
        class: `sensor-path phenotype-signal-to-receptor ${activityState}`,
        opacity: activityState === "active" ? ".68" : ".22"
      }));
      sensePositions.set(inputAnchor.id, receptorAnchor);
    });
  });

  if (Array.isArray(state.sensoryRelations) && state.sensoryRelations.length) {
    state.sensoryRelations.forEach(rel => {
      const senseA = (state.senses ?? []).find(item => item.id === rel.senseA || item.name === rel.senseA);
      const senseB = (state.senses ?? []).find(item => item.id === rel.senseB || item.name === rel.senseB);
      const posA = worldPositions.get(senseA?.knowledgeSignalId) ?? null;
      const posB = worldPositions.get(senseB?.knowledgeSignalId) ?? null;
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

  const boundaryClasses = ["phenotype-boundary"];
  if (isStressed) boundaryClasses.push("phenotype-stressed");
  else if (isAdaptive) boundaryClasses.push("phenotype-adaptive");
  else if (health === "recovering") boundaryClasses.push("phenotype-recovering");

  group.append(svg("path", { d: morphology.boundaryPath, fill: "url(#cell-fill)", class: boundaryClasses.join(" ") }));
  group.append(svg("path", { d: morphology.boundaryPath, class: "phenotype-boundary-inner" }));

  // Organism-owned anatomy is rendered only after the membrane, so world
  // signals remain visibly outside while receptors and internal organs remain inside.
  renderNeuralTerritories(group, morphology.internalAnchors);
  renderMetabolicCore(group);
  renderDegradationOrgan(group);

  pendingReceptors.forEach(({ sensor, anchor }) => {
    const selected = state.selectedSensorySensorId === sensor.sensorId;
    appendReceptorGlyph(group, sensor, anchor, selected);
    const transform = svg("text", {
      x: String(anchor.x + 9),
      y: String(anchor.y + 3),
      class: "phenotype-receptor-label"
    });
    transform.textContent = (sensor.transduction || "identity").slice(0, 10);
    group.append(transform);
  });
  group.classList.toggle("phenotype-frozen", morphology.presentation.desaturated);
  group.style.opacity = String(morphology.presentation.boundaryTension);

  morphology.fibres.forEach(fibre => {
    const isExc = fibre.kind === "excitatory";
    const isMod = ["predictive", "gating"].includes(fibre.kind);
    const strokeColor = isExc ? "rgba(80,217,255,.65)" : isMod ? "rgba(255,189,84,.65)" : "rgba(255,127,131,.65)";
    const marker = isExc ? "url(#arrow-exc)" : isMod ? "url(#arrow-mod)" : "url(#arrow-inh)";
    group.append(svg("line", {
      x1: fibre.x1,
      y1: fibre.y1,
      x2: fibre.x2,
      y2: fibre.y2,
      class: `fibre fibre-${fibre.kind}`,
      stroke: strokeColor,
      "marker-end": marker
    }));
  });

  morphology.internalAnchors.forEach(anchor => {
    const isReadout = anchor.kind === "readout";
    const r = isReadout ? 14 : 8.5;
    const kind = anchor.kind;
    const x = anchor.x;
    const y = anchor.y;
    const baseClass = `internal-anchor internal-anchor-${kind}`;

    switch (kind) {
      case "sense": {
        const points = `${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`;
        group.append(svg("polygon", { points, class: baseClass }));
        break;
      }
      case "state": {
        group.append(svg("rect", {
          x: x - r,
          y: y - r,
          width: r * 2,
          height: r * 2,
          rx: 3,
          ry: 3,
          class: baseClass
        }));
        break;
      }
      case "predictor": {
        const h = r * 1.15;
        const points = `${x},${(y - h).toFixed(1)} ${(x + r).toFixed(1)},${(y + h * 0.7).toFixed(1)} ${(x - r).toFixed(1)},${(y + h * 0.7).toFixed(1)}`;
        group.append(svg("polygon", { points, class: baseClass }));
        break;
      }
      case "gate": {
        const pts = [];
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i - Math.PI / 6;
          pts.push(`${(x + r * Math.cos(angle)).toFixed(1)},${(y + r * Math.sin(angle)).toFixed(1)}`);
        }
        group.append(svg("polygon", { points: pts.join(" "), class: baseClass }));
        break;
      }
      case "readout": {
        group.append(svg("circle", { cx: x, cy: y, r, class: baseClass }));
        group.append(svg("circle", { cx: x, cy: y, r: 9, class: "internal-anchor-readout-inner", fill: "none" }));
        break;
      }
      case "concept":
      default: {
        group.append(svg("circle", { cx: x, cy: y, r, class: baseClass }));
        break;
      }
    }

    const errorCls = state.cognition?.predictionErrors?.[anchor.id];
    if (errorCls && ["medium", "high", "extreme"].includes(errorCls)) {
      group.append(svg("circle", {
        cx: anchor.x,
        cy: anchor.y,
        r: r + 5,
        class: "internal-anchor-error",
        fill: "none",
        "stroke-dasharray": "3 2"
      }));
    }

    if (isReadout && state.cognition?.readouts) {
      const val = state.cognition.readouts[anchor.id];
      const text = svg("text", {
        x: anchor.x,
        y: anchor.y + 3,
        class: "internal-readout-label"
      });
      text.textContent = val != null ? Number(val).toFixed(2) : "RO";
      group.append(text);
    }
  });

  if (state.source === "demo") {
    state.beliefs.forEach((belief, index) => {
      const neighbor = state.beliefs[(index + 4) % state.beliefs.length];
      group.append(svg("line", { x1: belief.x, y1: belief.y, x2: neighbor.x, y2: neighbor.y, class: "belief-edge" }));
    });
  }

  let focus = null;
  let focusPos = null;
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

  state.beliefs.forEach((belief, index) => {
    const pos = resolveBeliefPosition(belief, index, sensePositions);
    if (focus && belief.id === focus.id) focusPos = pos;
    const evidence = Number(belief.evidence) || 0;
    const certainty = Number(belief.certainty) || 0;
    const r = Math.max(5, Math.min(13, 5 + Math.sqrt(evidence) * 1.3));

    if (belief.dissent || belief.contested) {
      group.append(svg("circle", {
        cx: pos.x,
        cy: pos.y,
        r: r + 5,
        class: "belief-contested-halo"
      }));
    }

    const node = svg("circle", {
      cx: pos.x,
      cy: pos.y,
      r: r,
      class: `belief-node${state.selected?.id === belief.id ? " selected" : ""}`,
      opacity: String(Math.max(0.35, certainty))
    });
    node.addEventListener("click", () => {
      state.selected = belief;
      state.selectedNodeId = null;
      renderInspector();
      renderIndividualPerspective();
      document.querySelector(".inspector").classList.add("open");
    });
    group.append(node);
  });

  if (focus) {
    const fx = focusPos?.x ?? focus.x;
    const fy = focusPos?.y ?? focus.y;

    let targetX = 555;
    let targetY = 430;
    for (const [senseId, pos] of sensePositions.entries()) {
      if (focus.id.includes(senseId) || (focus.title && focus.title.includes(senseId))) {
        targetX = pos.x;
        targetY = pos.y;
        break;
      }
    }
    const midX = (fx + targetX) / 2;
    const midY = (fy + targetY) / 2;

    group.append(svg("path", {
      d: `M ${fx} ${fy} Q ${midX} ${midY - 20} ${targetX} ${targetY}`,
      class: "dissent-path",
      opacity: focus.dissent ? "1" : ".35"
    }));
    group.append(svg("circle", { cx: fx, cy: fy, r: 28, class: "attention-ring" }));
    group.append(svg("circle", { cx: fx, cy: fy, r: 15, class: "attention-ring" }));
  }

  const sampling = state.sampling ?? {};
  const activeCount = sampling.active ?? state.senses?.filter(s => s.active).length ?? 0;
  const probingCount = sampling.probing ?? 0;
  const dormantCount = sampling.dormant ?? 0;
  const acclimationPct = Math.round((state.details?.acclimation ?? 0) * 100);

  const hudGroup = svg("g", { class: "phenotype-hud", transform: "translate(300, 685)" });
  const hudBg = svg("rect", {
    x: "-12",
    y: "-14",
    width: "320",
    height: "22",
    class: "phenotype-hud-tag"
  });
  hudGroup.append(hudBg);

  const hudText = svg("text", { x: "0", y: "0" });
  const receptorCount = state.sensoryPhenotype?.summary?.active ?? phenotypeSensors.length;
  hudText.textContent = `Acclimation: ${acclimationPct}% · World signals: ${state.senses.length} · Body receptors: ${receptorCount} · ${probingCount} probing`;
  hudGroup.append(hudText);
  group.append(hudGroup);

  canvas.append(group);
}

export { renderOrganism };
