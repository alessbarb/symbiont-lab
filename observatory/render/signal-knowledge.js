import { state } from "../state/store.js";
import { palette } from "./svg.js";

function shorten(id) {
  if (!id) return "";
  const clean = id.replace(/^(signal\.|sense\.|node\.)/, "");
  if (clean.length > 20) {
    return clean.slice(0, 8) + "…" + clean.slice(-6);
  }
  return clean;
}

function getClaimInfo(claim) {
  const rel = claim.relatedSignalId ? shorten(claim.relatedSignalId) : "";
  switch (claim.kind) {
    case "lead_prediction":
      return { label: "Predicción Temporal", icon: "⚡", desc: `Anticipa cambios en ${rel ? "<code>" + rel + "</code>" : "señal par"}` };
    case "synchronous_association":
      return { label: "Asociación Sincrónica", icon: "🔗", desc: `Co-oscila con ${rel ? "<code>" + rel + "</code>" : "señal par"}` };
    case "stability":
      return { label: "Invariante de Estabilidad", icon: "⚖️", desc: "Comportamiento estacionario acotado" };
    case "change":
      return { label: "Detección de Transición", icon: "🌊", desc: "Sensible a regímenes no estacionarios" };
    case "self_relevance":
      return { label: "Auto-Relevancia Metabólica", icon: "🫀", desc: "Refleja gasto energético del organismo" };
    default:
      return { label: claim.kind ?? "claim", icon: "🔬", desc: rel ? `Relación empírica con <code>${rel}</code>` : "Hipótesis formal acotada" };
  }
}

function getStatusBadge(status) {
  switch (status) {
    case "supported":
      return { text: "LEY VALIDADA", color: palette.mint, bg: "rgba(113, 233, 186, 0.15)" };
    case "hypothesis":
      return { text: "EN ENSAYO", color: palette.amber, bg: "rgba(255, 189, 84, 0.15)" };
    case "contested":
      return { text: "FALSADA / EN CONFLICTO", color: palette.coral, bg: "rgba(255, 127, 131, 0.15)" };
    case "stale":
      return { text: "EVIDENCIA CADUCADA", color: "#8fa3b8", bg: "rgba(143, 163, 184, 0.15)" };
    default:
      return { text: "OBSERVANDO", color: "#52708f", bg: "rgba(82, 112, 143, 0.15)" };
  }
}

function formatReason(reasonClass) {
  switch (reasonClass) {
    case "evidence_accumulated": return "Evidencia acumulada suficiente";
    case "contradiction_detected": return "Contradicción empírica detectada";
    case "support_confirmed": return "Confirmada tras múltiples épocas";
    case "stale_evidence": return "Pérdida de soporte temporal";
    case "insufficient_observations": return "Observaciones comparables insuficientes";
    default: return reasonClass ?? "insufficient_observations";
  }
}

function renderClaimCard(claim, targetSignalId) {
  const info = getClaimInfo(claim);
  const badge = getStatusBadge(claim.status);
  const evCount = claim.evidenceCount ?? 0;
  const oppCount = claim.validationOpportunities ?? 0;
  const pct = oppCount > 0 ? Math.round((evCount / oppCount) * 100) : 0;
  const related = claim.relatedSignalId ? ` · relación ${claim.relatedSignalId}` : "";
  const strength = claim.strengthClass ? ` · fuerza ${claim.strengthClass}` : "";
  const improvement = claim.improvementClass ? ` · mejora ${claim.improvementClass}` : "";

  const card = document.createElement("div");
  card.className = "hypothesis-card";

  const head = document.createElement("div");
  head.className = "hypothesis-card-head";

  const title = document.createElement("div");
  title.className = "hypothesis-card-title";
  title.innerHTML = `<span>${info.icon}</span> <span>${info.label}</span>`;
  if (targetSignalId && (!state.selectedSignalId || state.selectedSignalId !== targetSignalId)) {
    title.innerHTML += ` <small style="color:var(--muted);font-weight:normal;">(${shorten(targetSignalId)})</small>`;
  }

  const badgeEl = document.createElement("span");
  badgeEl.className = "claim-badge";
  badgeEl.textContent = badge.text;
  badgeEl.style.color = badge.color;
  badgeEl.style.background = badge.bg;

  head.append(title, badgeEl);

  const desc = document.createElement("p");
  desc.className = "hypothesis-desc";
  desc.innerHTML = info.desc;

  const meter = document.createElement("div");
  meter.className = "meter";
  const fill = document.createElement("i");
  fill.style.width = `${Math.max(4, Math.min(100, pct))}%`;
  fill.style.background = badge.color;
  meter.append(fill);

  const details = document.createElement("p");
  details.className = "hypothesis-metric-text";
  details.textContent = `${claim.kind ?? "claim"}: ${claim.status ?? "insufficient"}${related}${strength} · evidencia comparable ${claim.evidenceCount ?? 0}/${claim.validationOpportunities ?? 0}${improvement} · revisión ${claim.revision ?? 0} · razón ${claim.reasonClass ?? "insufficient_observations"}`;

  card.append(head, desc, meter, details);
  return card;
}

function renderSignalKnowledge(container) {
  container.replaceChildren();

  const title = document.createElement("h3");
  title.textContent = "🔬 Cuaderno Científico de Hipótesis";
  container.append(title);

  const activeSignalId = state.selectedSignalId || (state.selectedNodeId && state.selectedNodeId.startsWith("sense_") ? `signal.${state.selectedNodeId}` : null);
  const profile = state.signalKnowledge.find(item => item.signalId === activeSignalId || item.signalId === state.selectedSignalId);

  // Compute aggregate stats across all claims
  const allClaims = state.signalKnowledge.flatMap(p => (p.claims || []).map(c => ({ ...c, profileSignalId: p.signalId })));
  const supportedCount = allClaims.filter(c => c.status === "supported").length;
  const hypoCount = allClaims.filter(c => c.status === "hypothesis").length;
  const contestedCount = allClaims.filter(c => c.status === "contested").length;

  if (allClaims.length > 0) {
    const summaryBar = document.createElement("div");
    summaryBar.className = "hypothesis-summary-bar";
    summaryBar.innerHTML = `
      <span class="hypothesis-pill"><strong>${allClaims.length}</strong> hipótesis</span>
      <span class="hypothesis-pill" style="border-color:rgba(113,233,186,0.4)"><strong style="color:var(--mint)">${supportedCount}</strong> validadas</span>
      <span class="hypothesis-pill" style="border-color:rgba(255,189,84,0.4)"><strong style="color:var(--amber)">${hypoCount}</strong> en ensayo</span>
      <span class="hypothesis-pill" style="border-color:rgba(255,127,131,0.4)"><strong style="color:var(--coral)">${contestedCount}</strong> en conflicto</span>
    `;
    container.append(summaryBar);
  }

  if (profile) {
    const metaBox = document.createElement("div");
    metaBox.style.marginBottom = "10px";
    metaBox.innerHTML = `
      <p style="font-size:11px;color:var(--muted);margin:0 0 4px;">
        Señal enfocada: <code style="color:var(--cyan)">${shorten(profile.signalId)}</code> · <strong>${profile.observedOpportunities ?? 0}</strong> oportunidades · <strong>${profile.validObservations ?? 0}</strong> observaciones válidas · ${profile.lastSeenAgeClass ?? profile.age ?? "current"}
      </p>
    `;
    container.append(metaBox);

    if (profile.claims && profile.claims.length > 0) {
      profile.claims.forEach(claim => {
        container.append(renderClaimCard(claim, profile.signalId));
      });
    } else {
      const empty = document.createElement("p");
      empty.className = "inspector-summary";
      empty.textContent = "No hay hipótesis formuladas aún para esta señal específica.";
      container.append(empty);
    }
  } else if (allClaims.length > 0) {
    const note = document.createElement("p");
    note.className = "inspector-summary";
    note.style.margin = "6px 0 12px";
    note.textContent = "Mostrando hipótesis activas formuladas por el organismo en el host. Selecciona un sensor para filtrar sus leyes particulares.";
    container.append(note);

    allClaims.slice(0, 8).forEach(claim => {
      container.append(renderClaimCard(claim, claim.profileSignalId));
    });
  } else {
    const message = document.createElement("p");
    message.className = "inspector-summary";
    message.textContent = "Symbiont todavía no ha reunido evidencia suficiente.";
    container.append(message);
  }

  // Knowledge Events Feed (Falsations, Revisions, Confirmations)
  const events = Array.isArray(state.knowledgeEvents) ? state.knowledgeEvents : [];
  if (events.length > 0) {
    const eventsTitle = document.createElement("h4");
    eventsTitle.className = "evidence-title";
    eventsTitle.textContent = "Bitácora de Eventos Epistemológicos";
    container.append(eventsTitle);

    const eventList = document.createElement("div");
    eventList.style.marginTop = "6px";
    events.slice(-5).reverse().forEach(ev => {
      const row = document.createElement("div");
      row.className = "knowledge-event-row";
      const tick = document.createElement("span");
      tick.className = "knowledge-event-tick";
      tick.textContent = `T-${ev.tick ?? "?"}`;

      const text = document.createElement("span");
      const fromSt = ev.fromStatus ? ev.fromStatus : "origen";
      const toSt = ev.toStatus ? ev.toStatus : "actual";
      const reason = formatReason(ev.reasonClass);
      text.innerHTML = `<strong>${shorten(ev.claimId || "Hipótesis")}</strong> pasó de <em>${fromSt}</em> a <strong>${toSt}</strong> (${reason})`;

      row.append(tick, text);
      eventList.append(row);
    });
    container.append(eventList);
  }
}

export { renderSignalKnowledge };
