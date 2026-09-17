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

function sourceBadge(sourceType) {
  if (sourceType === "observed") {
    return `<span class="source-badge observed" title="Organism-observed: Directly captured from organism runtime">● Organism-observed</span>`;
  }
  if (sourceType === "known") {
    return `<span class="source-badge known" title="Organism-known: Self-knowledge represented by the organism">○ Organism-known</span>`;
  }
  return `<span class="source-badge derived" title="Observer-derived: Structural calculation by Observatory">◇ Observer-derived</span>`;
}

function deconstructConcept(nodeId, inbound, outbound, errCls) {
  const exc = inbound.filter(e => e.kind === "excitatory");
  const inh = inbound.filter(e => e.kind === "inhibitory");
  const pred = inbound.filter(e => e.kind === "predictive");
  const gate = inbound.filter(e => e.kind === "gating");

  let archetype = "Integrador Multimodal";
  let icon = "🔮";
  let roleDesc = "Patrón observador: Agrupa la convergencia de múltiples señales sensoriales en un atractor latente común.";

  if (exc.length > 0 && inh.length > 0) {
    archetype = "Detector Diferencial";
    icon = "⚖️";
    roleDesc = `Patrón observador: Contrasta ${exc.length} entradas excitatorias frente a ${inh.length} inhibitorias.`;
  } else if (pred.length > 0 || gate.length > 0) {
    archetype = "Compuerta Moduladora";
    icon = "🚪";
    roleDesc = `Patrón observador: Integra regulación predictiva (${pred.length}) y compuertas (${gate.length}).`;
  } else if (inbound.length === 1) {
    archetype = "Transductor Directo";
    icon = "📡";
    roleDesc = "Patrón observador: Canaliza la dinámica de un receptor sensorial primario hacia la red cognitiva.";
  }

  // Connectivity role
  let homeoRole = "Proyección latente intermedia hacia otros nodos cognitivos.";
  const readoutTargets = outbound.filter(e => e.targetId.startsWith("readout_"));
  if (readoutTargets.length > 0) {
    const names = readoutTargets.map(e => shorten(e.targetId)).join(", ");
    homeoRole = `Proyección consultiva directa hacia ${names}. Alimenta la lectura fisiológica.`;
  }

  // Predictive status interpretation
  let fidelityDesc = "Estabilidad observada en entradas (sorpresa baja).";
  if (["high", "extreme"].includes(errCls)) {
    fidelityDesc = "Desincronización observada: Las señales contradicen el estado previo. Presión de plasticidad.";
  } else if (errCls === "medium") {
    fidelityDesc = "Tensión predictiva observada en receptores en proceso de ajuste.";
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
  const activations = state.cognition?.activationClasses ?? {};
  const strandedList = state.cognition?.strandedConcepts ?? [];
  const isStranded = strandedList.includes(nodeId);
  const actClass = activations[nodeId] ?? 0;

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
        <h3 class="evidence-title">Discovered Causal & Correlative Dynamics ${sourceBadge("observed")}</h3>
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
        <h3 class="evidence-title">Cognitive Convergence (Synaptic Targets) ${sourceBadge("observed")}</h3>
        <ul class="evidence-list">
          ${outbound.map(e => `<li>Projects to <code>${shorten(e.targetId)}</code> <span class="synapse-kind ${e.kind}">(${e.kind})</span></li>`).join("")}
        </ul>
      `;
    }

    contentEl.innerHTML = `
      <div style="margin-bottom:8px;">${sourceBadge("observed")}</div>
      <div class="metric"><div class="metric-head"><span>Learned Utility</span><strong>${utilPct}%</strong></div><div class="meter"><i style="width:${Math.max(4, Math.min(100, Number(utilPct)))}%;background:${barColor}"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Observations</span><strong>${samples} samples</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Availability</span><strong>${availPct}% uptime</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Attention Tier</span><strong>${tier.toUpperCase()}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Activation Class</span><strong>${actClass} / 15</strong></div><div class="meter"><i style="width:${(actClass / 15) * 100}%;background:var(--cyan)"></i></div></div>
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

    const strandedBanner = isStranded ? `
      <div class="metric" style="border:1px solid rgba(255,189,84,0.3);background:rgba(255,189,84,0.08);padding:8px 10px;border-radius:6px;margin:8px 0;">
        <div class="metric-head"><span style="color:var(--amber);font-weight:600;">⚠️ Concepto Varado (Stranded)</span></div>
        <p class="inspector-summary" style="margin:4px 0 0;font-size:10px;">El concepto existe en la topología, pero actualmente no dispone de una ruta funcional hacia ningún readout.</p>
      </div>` : "";

    contentEl.innerHTML = `
      <div style="margin-bottom:8px;">${sourceBadge("observed")}</div>
      <div class="metric"><div class="metric-head"><span>Activation Class</span><strong>${actClass} / 15</strong></div><div class="meter"><i style="width:${(actClass / 15) * 100}%;background:var(--violet)"></i></div></div>
      ${strandedBanner}
      <div class="deconstruct-card">
        <div class="deconstruct-head">
          <div class="deconstruct-title"><span>${deconstruction.icon}</span> <span>Patrón estructural observado</span> <small style="color:var(--muted);font-size:9.5px;">(Deconstrucción Semántica)</small></div>
          <span class="deconstruct-archetype-badge">${deconstruction.archetype.toUpperCase()}</span>
        </div>
        <div style="margin-bottom:6px;">${sourceBadge("derived")}</div>
        <p class="deconstruct-desc">${deconstruction.roleDesc}</p>
        <p style="font-size:10.5px;color:#94b8d7;margin:0 0 4px;"><strong>Destino Estructural:</strong> ${deconstruction.homeoRole}</p>
        <p style="font-size:10.5px;color:#94b8d7;margin:0 0 6px;"><strong>Madurez Predictiva:</strong> ${deconstruction.fidelityDesc}</p>
        <div class="deconstruct-pipeline">${deconstruction.pipelineHtml}</div>
      </div>

      <div class="metric"><div class="metric-head"><span>Prediction Error</span><strong>${errCls.toUpperCase()}</strong></div><div class="meter"><i style="width:${errPct}%;background:${errColor}"></i></div></div>
      ${topoNode?.bias != null ? `<div class="metric"><div class="metric-head"><span>Basal Bias</span><strong>${topoNode.bias.toFixed(4)}</strong></div></div>` : ""}
      ${topoNode?.tau != null ? `<div class="metric"><div class="metric-head"><span>Time Constant (Tau)</span><strong>${topoNode.tau.toFixed(4)}</strong></div></div>` : ""}
      <div class="metric"><div class="metric-head"><span>Convergent Senses</span><strong>${inbound.length} signals</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Downstream Outputs</span><strong>${outbound.length} projections</strong></div></div>
      <p class="inspector-summary">Representación latente intermedia que sintetiza regularidades estadísticas de señales convergentes sin semántica ontológica impuesta.</p>
      <h3 class="evidence-title">Convergent Input Signals ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${inputList || "<li>No incoming edges configured</li>"}</ul>
      <h3 class="evidence-title">Outgoing Projections ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${outputList || "<li>No outgoing projections configured</li>"}</ul>
    `;
    return;
  }

  if (kind === "state") {
    titleEl.textContent = shorten(nodeId);
    kindEl.textContent = `Recurrent State Node · Tau ${topoNode?.tau != null ? topoNode.tau.toFixed(2) : "1.00"}`;

    const inputList = inbound.map(e => `<li>Input from <code>${escapeHtml(shorten(e.sourceId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");
    const outputList = outbound.map(e => `<li>Projects to <code>${escapeHtml(shorten(e.targetId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");

    contentEl.innerHTML = `
      <div style="margin-bottom:8px;">${sourceBadge("observed")}</div>
      <div class="metric"><div class="metric-head"><span>Activation Class</span><strong>${actClass} / 15</strong></div><div class="meter"><i style="width:${(actClass / 15) * 100}%;background:var(--mint)"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Basal Bias</span><strong>${topoNode?.bias != null ? topoNode.bias.toFixed(4) : "0.0000"}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Time Constant (Tau)</span><strong>${topoNode?.tau != null ? topoNode.tau.toFixed(4) : "1.0000"}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Recurrent Connections</span><strong>${inbound.length} inputs · ${outbound.length} outputs</strong></div></div>
      <p class="inspector-summary">Nodo de estado recurrente. Preserva memoria temporal y dinámica interna a través de su sesgo basal y constante de decaimiento (tau).</p>
      <h3 class="evidence-title">Incoming Synapses ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${inputList || "<li>No incoming synapses</li>"}</ul>
      <h3 class="evidence-title">Outgoing Synapses ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${outputList || "<li>No outgoing synapses</li>"}</ul>
    `;
    return;
  }

  if (kind === "predictor") {
    titleEl.textContent = shorten(nodeId);
    const errCls = errors[nodeId] ?? "trace";
    const errMap = { zero: 4, trace: 18, low: 38, medium: 68, high: 86, extreme: 100 };
    const errPct = errMap[errCls] ?? 20;
    const errColor = ["medium", "high", "extreme"].includes(errCls) ? palette.coral : (errCls === "low" ? palette.amber : palette.mint);

    kindEl.textContent = `Predictive Estimator · Error: ${errCls.toUpperCase()}`;

    const inputList = inbound.map(e => `<li>Context from <code>${escapeHtml(shorten(e.sourceId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");
    const outputList = outbound.map(e => `<li>Anticipates <code>${escapeHtml(shorten(e.targetId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");

    contentEl.innerHTML = `
      <div style="margin-bottom:8px;">${sourceBadge("observed")}</div>
      <div class="metric"><div class="metric-head"><span>Activation Class</span><strong>${actClass} / 15</strong></div><div class="meter"><i style="width:${(actClass / 15) * 100}%;background:var(--amber)"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Prediction Error</span><strong>${errCls.toUpperCase()}</strong></div><div class="meter"><i style="width:${errPct}%;background:${errColor}"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Basal Bias</span><strong>${topoNode?.bias != null ? topoNode.bias.toFixed(4) : "0.0000"}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Time Constant (Tau)</span><strong>${topoNode?.tau != null ? topoNode.tau.toFixed(4) : "1.0000"}</strong></div></div>
      <p class="inspector-summary">Nodo predictor activo. Genera anticipaciones locales sobre dinámicas latentes y cuantiza el error predictivo en clases discretas.</p>
      <h3 class="evidence-title">Context Inputs ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${inputList || "<li>No context inputs</li>"}</ul>
      <h3 class="evidence-title">Anticipation Targets ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${outputList || "<li>No anticipation targets</li>"}</ul>
    `;
    return;
  }

  if (kind === "gate") {
    titleEl.textContent = shorten(nodeId);
    kindEl.textContent = `Modulatory Gate · ${inbound.length} Regulators`;

    const inputList = inbound.map(e => `<li>Regulator from <code>${escapeHtml(shorten(e.sourceId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");
    const outputList = outbound.map(e => `<li>Gates <code>${escapeHtml(shorten(e.targetId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");

    contentEl.innerHTML = `
      <div style="margin-bottom:8px;">${sourceBadge("observed")}</div>
      <div class="metric"><div class="metric-head"><span>Activation Class</span><strong>${actClass} / 15</strong></div><div class="meter"><i style="width:${(actClass / 15) * 100}%;background:#e09f3e"></i></div></div>
      <div class="metric"><div class="metric-head"><span>Basal Bias</span><strong>${topoNode?.bias != null ? topoNode.bias.toFixed(4) : "0.0000"}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Time Constant (Tau)</span><strong>${topoNode?.tau != null ? topoNode.tau.toFixed(4) : "1.0000"}</strong></div></div>
      <p class="inspector-summary">Compuerta sináptica condicional. Modula el paso de activación multiplicativamente según umbrales de contexto.</p>
      <h3 class="evidence-title">Modulating Precursors ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${inputList || "<li>No modulating precursors</li>"}</ul>
      <h3 class="evidence-title">Gated Targets ${sourceBadge("observed")}</h3>
      <ul class="evidence-list">${outputList || "<li>No gated targets</li>"}</ul>
    `;
    return;
  }

  if (kind === "readout") {
    titleEl.textContent = shorten(nodeId);
    kindEl.textContent = "Consultative Readout Stream";
    const val = readouts[nodeId] != null ? Number(readouts[nodeId]).toFixed(4) : "0.0000";
    const inputList = inbound.map(e => `<li>Modulated by <code>${escapeHtml(shorten(e.sourceId))}</code> <span class="synapse-kind ${escapeHtml(e.kind)}">(${escapeHtml(e.kind)})</span></li>`).join("");

    contentEl.innerHTML = `
      <div style="margin-bottom:8px;">${sourceBadge("observed")}</div>
      <div class="metric"><div class="metric-head"><span>Consultative Value</span><strong>${val}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Basal Bias</span><strong>${topoNode?.bias != null ? topoNode.bias.toFixed(4) : "0.0000"}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Time Constant (Tau)</span><strong>${topoNode?.tau != null ? topoNode.tau.toFixed(4) : "1.0000"}</strong></div></div>
      <div class="metric"><div class="metric-head"><span>Driving Precursors</span><strong>${inbound.length} inputs</strong></div></div>
      <p class="inspector-summary">Salida consultiva continua derivada de la topología cognitiva. Alimenta circuitos de regulación fisiológica sin efectos secundarios directos sobre el entorno real.</p>
      <h3 class="evidence-title">Driving Precursors ${sourceBadge("observed")}</h3>
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
    <div style="margin-bottom:8px;">${sourceBadge(b.dissent ? "observed" : "known")}</div>
    <div class="metric"><div class="metric-head"><span>Certainty</span><strong>${b.certainty.toFixed(2)}</strong></div><div class="meter"><i style="width:${b.certainty * 100}%"></i></div></div>
    <div class="metric"><div class="metric-head"><span>Evidence</span><strong>${b.evidence} observations</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Revisions</span><strong>${b.revisions}</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Dissent</span><strong>${b.dissent ? "Preserved" : "None recent"}</strong></div><div class="meter"><i style="width:${b.dissent ? 64 : 10}%;background:${b.dissent ? palette.coral : palette.mint}"></i></div></div>
    <p class="inspector-summary">${b.dissent ? "Recent evidence conflicts with the prior baseline; this belief remains revisable." : "No recent contradictory evidence is recorded for this belief."} No host identity or raw reading is displayed.</p>
    <h3 class="evidence-title">Why it matters now ${sourceBadge("derived")}</h3>
    <ul class="evidence-list"><li>Observed in the current context</li><li>${b.evidence} bounded evidence points retained</li><li>Attention allocation remains read-only</li><li>${b.dissent ? "Contradictory evidence remains visible" : "No recent contradictory evidence"}</li></ul>`;
}

export { renderInspector };
