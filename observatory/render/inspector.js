import { state } from "../state/store.js";
import { palette, escapeHtml } from "./svg.js";
import { renderSignalKnowledge } from "./signal-knowledge.js";

function shorten(id) {
  if (!id) return "";
  const clean = id.replace(/^(signal\.|sense\.|node\.)/, "");
  if (clean.length > 20) {
    return clean.slice(0, 8) + "…" + clean.slice(-6);
  }
  return clean;
}

function deconstructConcept(nodeId, inbound, outbound, errCls) {
  const exc = inbound.filter(e => e.kind === "excitatory");
  const inh = inbound.filter(e => e.kind === "inhibitory");
  const mod = inbound.filter(e => e.kind === "modulatory" || e.kind === "predictive");

  let archetype = "Integrador Multimodal";
  let icon = "🔮";
  let roleDesc = "Sintetiza la concurrencia de múltiples señales sensoriales en un atractor latente común.";

  if (exc.length > 0 && inh.length > 0) {
    archetype = "Detector Diferencial";
    icon = "⚖️";
    roleDesc = `Contrasta ${exc.length} entradas excitatorias frente a ${inh.length} inhibitorias. Actúa como discriminador de contraste cuando se rompe la correlación habitual entre ambos grupos.`;
  } else if (mod.length > 0) {
    archetype = "Compuerta Moduladora";
    icon = "🚪";
    roleDesc = `Regula y condiciona el paso de activación según umbrales de contexto (${mod.length} conexiones modulatorias).`;
  } else if (inbound.length === 1) {
    archetype = "Transductor Directo";
    icon = "📡";
    roleDesc = "Canaliza y normaliza la dinámica de un receptor sensorial primario hacia la red cognitiva.";
  }

  // Homeostatic role
  let homeoRole = "Proyección latente intermedia hacia otros conceptos.";
  const readoutTargets = outbound.filter(e => e.targetId.startsWith("readout_"));
  if (readoutTargets.length > 0) {
    const names = readoutTargets.map(e => shorten(e.targetId)).join(", ");
    homeoRole = `Modulador efector directo para ${names}. Transfiere estados de predicción hacia la homeostasis biológica.`;
  }

  // Predictive status interpretation
  let fidelityDesc = "Alta estabilidad predictiva. El concepto domina la estadística de sus señales de entrada (sorpresa mínima).";
  if (["high", "extreme"].includes(errCls)) {
    fidelityDesc = "Alerta de Desincronización: Las señales de entrada contradicen el modelo previo. Genera presión estructural de mutación.";
  } else if (errCls === "medium") {
    fidelityDesc = "Tensión Predictiva: Variación no anticipada en los receptores. En proceso de ajuste de pesos sinápticos.";
  }

  // Pipeline badges
  const inBadges = inbound.map(e => `<span class="synapse-kind ${escapeHtml(e.kind)}">${e.kind === "inhibitory" ? "−" : "+"} ${escapeHtml(shorten(e.sourceId))}</span>`).join(" ");
  const outBadges = outbound.map(e => `<span class="synapse-kind ${escapeHtml(e.kind)}">➔ ${escapeHtml(shorten(e.targetId))}</span>`).join(" ");

  return {
    archetype,
    icon,
    roleDesc,
    homeoRole,
    fidelityDesc,
    pipelineHtml: `${inBadges || "<span>sin entradas</span>"} <span class="deconstruct-arrow">━━►</span> <strong style="color:var(--violet)">${escapeHtml(shorten(nodeId))}</strong> <span class="deconstruct-arrow">━━►</span> ${outBadges || "<span>terminal</span>"}`
  };
}

function renderNodeInspector(nodeId) {
  const titleEl = document.querySelector("#inspector-title");
  const kindEl = document.querySelector("#inspector-kind");
  const contentEl = document.querySelector("#inspector-content");
  if (!titleEl || !kindEl || !contentEl) return;

  const topoNode = (state.topology?.nodes ?? []).find(n => n.id === nodeId);
  const dev = (state.sensoryDevelopment ?? []).find(d => d.name === nodeId);
  const matchingSense = (state.senses ?? []).find(s => s.id === nodeId || s.name === nodeId);
  const kind = topoNode?.kind ?? (nodeId.startsWith("sense_") ? "sense" : (nodeId.startsWith("readout_") ? "readout" : "concept"));
  const edges = state.topology?.edges ?? [];
  const inbound = edges.filter(e => e.targetId === nodeId);
  const outbound = edges.filter(e => e.sourceId === nodeId);
  const errors = state.cognition?.predictionErrors ?? {};
  const readouts = state.cognition?.readouts ?? {};

  if (kind === "sense") {
    titleEl.textContent = matchingSense?.name || shorten(nodeId);
    const tier = dev?.tier ?? (matchingSense?.active ? "active" : "dormant");
    kindEl.textContent = `Sensory Receptor · ${tier.toUpperCase()}`;

    const utilPct = dev ? (dev.utility * 100).toFixed(1) : (matchingSense?.quality ? (matchingSense.quality * 45).toFixed(1) : "0.0");
    const samples = dev ? dev.samples : (matchingSense ? 120 : 0);
    const availPct = dev ? Math.round(dev.availability * 100) : (matchingSense ? Math.round(matchingSense.quality * 100) : 100);
    const barColor = tier === "active" ? palette.cyan : (tier === "probing" ? palette.amber : "#52708f");

    const rels = (state.sensoryRelations ?? []).filter(r => r.senseA === nodeId || r.senseB === nodeId);

    let relsHtml = "";
    if (rels.length > 0) {
      relsHtml = `
        <h3 class="evidence-title">Discovered Causal & Correlative Dynamics</h3>
        <ul class="evidence-list">
          ${rels.map(r => {
            const isA = r.senseA === nodeId;
            const partner = isA ? r.senseB : r.senseA;
            const parts = [];
            if (isA && r.aToB != null) {
              parts.push(`⚡ <strong>Temporal Lead:</strong> Anticipates <code>${escapeHtml(shorten(partner))}</code> (coeff: <strong>${r.aToB.toFixed(3)}</strong>)`);
            } else if (!isA && r.bToA != null) {
              parts.push(`⚡ <strong>Temporal Lead:</strong> Anticipates <code>${escapeHtml(shorten(partner))}</code> (coeff: <strong>${r.bToA.toFixed(3)}</strong>)`);
            } else if (!isA && r.aToB != null) {
              parts.push(`⏳ <strong>Lag Response:</strong> Follows <code>${escapeHtml(shorten(partner))}</code> (coeff: <strong>${r.aToB.toFixed(3)}</strong>)`);
            }
            if (r.synchronous != null) {
              parts.push(`🔗 <strong>Synchronous:</strong> r = <strong>${r.synchronous.toFixed(3)}</strong>`);
            }
            return `<li>${parts.join(" · ")} <small>(${r.samples} observations)</small></li>`;
          }).join("")}
        </ul>
      `;
    } else {
      relsHtml = `
        <h3 class="evidence-title">Discovered Causal Dynamics</h3>
        <p class="inspector-summary" style="margin: 6px 0 14px;">No cross-sensory causal relations validated yet for this signal.</p>
      `;
    }

    let projectionsHtml = "";
    if (outbound.length > 0) {
      projectionsHtml = `
        <h3 class="evidence-title">Cognitive Convergence (Synaptic Targets)</h3>
        <ul class="evidence-list">
          ${outbound.map(e => `<li>Projects to Concept <code>${shorten(e.targetId)}</code> <span class="synapse-kind ${e.kind}">(${e.kind})</span></li>`).join("")}
        </ul>
      `;
    }

    contentEl.innerHTML = `
      <div class="metric"><div class="metric-head"><span>Learned Utility</span><strong>${utilPct}%</strong></div><div class="meter"><i style="width:${Math.max(4, Math.min(100, Number(utilPct)))}%;background:${barColor}"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Observations</span><strong>${samples} samples</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Availability</span><strong>${availPct}% uptime</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Attention Tier</span><strong>${tier.toUpperCase()}</strong></div></div>
      <p class="inspector-summary">Opaque host signal learned autonomously. The organism extracts empirical utility and cross-signal predictive causality without platform semantics.</p>
      ${relsHtml}
      ${projectionsHtml}
    `;
    return;
  }

  if (kind === "concept") {
    titleEl.textContent = shorten(nodeId);
    kindEl.textContent = `Cognitive Concept · ${inbound.length} Convergent Inputs`;

    const errCls = errors[nodeId] ?? "trace";
    const errMap = { zero: 4, trace: 18, low: 38, medium: 68, high: 86, extreme: 100 };
    const errPct = errMap[errCls] ?? 20;
    const errColor = ["medium", "high", "extreme"].includes(errCls) ? palette.coral : (errCls === "low" ? palette.amber : palette.mint);

    const deconstruction = deconstructConcept(nodeId, inbound, outbound, errCls);
    const inputList = inbound.map(e => `<li>Input from <code>${escapeHtml(shorten(e.sourceId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");
    const outputList = outbound.map(e => `<li>Projects to <code>${escapeHtml(shorten(e.targetId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");

    contentEl.innerHTML = `
      <div class="deconstruct-card">
        <div class="deconstruct-head">
          <div class="deconstruct-title"><span>${deconstruction.icon}</span> <span>Deconstrucción Semántica</span></div>
          <span class="deconstruct-archetype-badge">${deconstruction.archetype.toUpperCase()}</span>
        </div>
        <p class="deconstruct-desc">${deconstruction.roleDesc}</p>
        <p style="font-size:10.5px;color:#94b8d7;margin:0 0 4px;"><strong>Destino Homeostático:</strong> ${deconstruction.homeoRole}</p>
        <p style="font-size:10.5px;color:#94b8d7;margin:0 0 6px;"><strong>Madurez Predictiva:</strong> ${deconstruction.fidelityDesc}</p>
        <div class="deconstruct-pipeline">${deconstruction.pipelineHtml}</div>
      </div>

      <div class="metric"><div class="metric-head"><span>Prediction Error</span><strong>${errCls.toUpperCase()}</strong></div><div class="meter"><i style="width:${errPct}%;background:${errColor}"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Convergent Senses</span><strong>${inbound.length} signals</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Downstream Outputs</span><strong>${outbound.length} projections</strong></div></div>
      <p class="inspector-summary">Latent cognitive attractor synthesizing statistical regularities from converging sensory streams into stable internal representations.</p>
      <h3 class="evidence-title">Convergent Input Signals</h3>
      <ul class="evidence-list">${inputList || "<li>No incoming edges configured</li>"}</ul>
      <h3 class="evidence-title">Outgoing Projections</h3>
      <ul class="evidence-list">${outputList || "<li>No outgoing projections configured</li>"}</ul>
    `;
    return;
  }

  if (kind === "readout") {
    titleEl.textContent = shorten(nodeId);
    kindEl.textContent = "Effector Readout Stream";
    const val = readouts[nodeId] != null ? Number(readouts[nodeId]).toFixed(4) : "0.0000";
    const inputList = inbound.map(e => `<li>Modulated by Concept <code>${escapeHtml(shorten(e.sourceId))}</code></li>`).join("");

    contentEl.innerHTML = `
      <div class="metric"><div class="metric-head"><span>Current Activation</span><strong>${val}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Modulating Concepts</span><strong>${inbound.length} drivers</strong></div></div>
      <p class="inspector-summary">Continuous physiological readout derived from the cognitive topology without direct real-world side effects.</p>
      <h3 class="evidence-title">Modulating Precursors</h3>
      <ul class="evidence-list">${inputList || "<li>Direct input</li>"}</ul>
    `;
    return;
  }
}

function renderInspector() {
  const signalPanel = document.querySelector("#signal-knowledge-panel");
  if (signalPanel) renderSignalKnowledge(signalPanel);

  if (state.selectedNodeId) {
    renderNodeInspector(state.selectedNodeId);
    return;
  }

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
    <p class="inspector-summary">${b.dissent ? "Recent evidence conflicts with the prior baseline; this belief remains revisable." : "No recent contradictory evidence is recorded for this belief."} No host identity or raw reading is displayed.</p>
    <h3 class="evidence-title">Why it matters now</h3>
    <ul class="evidence-list"><li>Observed in the current context</li><li>${b.evidence} bounded evidence points retained</li><li>Attention allocation remains read-only</li><li>${b.dissent ? "Contradictory evidence remains visible" : "No recent contradictory evidence"}</li></ul>`;
}

export { renderInspector };
