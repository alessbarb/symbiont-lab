import { state } from "../state/store.js";
import { escapeHtml } from "./svg.js";

function messageLabel(sequenceId) {
  return sequenceId ? escapeHtml(sequenceId) : "silence";
}

function renderCommunication() {
  const root = document.querySelector("#communication-panel");
  if (!root) return;
  const culture = state.culturalClaims;
  if (!culture) {
    root.innerHTML = `<div class="panel-heading"><h2>Communication Live</h2><p>No sequence telemetry in this snapshot.</p></div>`;
    return;
  }
  const decisions = Array.isArray(culture.sequenceDecisions) ? culture.sequenceDecisions.slice(-24).reverse() : [];
  const grounding = Array.isArray(culture.sequenceGrounding) ? culture.sequenceGrounding.slice(0, 24) : [];
  const emitted = decisions.filter(item => item.action === "emit").length;
  const html = decisions.length ? decisions.map(item => `<li><code>t${item.tick}</code> <strong>${escapeHtml(item.action)}</strong> <code>${messageLabel(item.sequence_id)}</code> → <code>${escapeHtml(item.recipient_id || "—")}</code> <small>${item.cost} cost</small></li>`).join("") : "<li>No bounded sequence decisions recorded.</li>";
  root.innerHTML = `
    <div class="panel-heading"><h2>Communication Live</h2><p>Organism view · opaque identifiers only</p></div>
    <div class="metric"><div class="metric-head"><span>Sequences known</span><strong>${culture.sequencesKnown}</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Emissions / exposures</span><strong>${culture.sequenceEmissions} / ${culture.sequenceExposures}</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Grounding updates</span><strong>${culture.sequenceGroundingUpdates}</strong></div></div>
    <div class="metric"><div class="metric-head"><span>Decision cost</span><strong>${culture.sequencePolicyCost}</strong></div></div>
    <h3 class="evidence-title">Event stream · ${emitted} recent emissions</h3>
    <ul class="evidence-list communication-events">${html}</ul>
    <h3 class="evidence-title">Convention explorer</h3>
    <ul class="evidence-list communication-grounding">${grounding.length ? grounding.map(item => `<li><code>${escapeHtml(item.sequence_id)}</code> · length ${item.length} · strength ${item.strength} · support ${item.support} · contradiction ${item.contradiction}</li>`).join("") : "<li>No locally grounded sequence association.</li>"}</ul>
    <p class="inspector-summary">This view is passive. It does not expose evaluator labels, meanings, weights, or control actions.</p>
  `;
}

export { renderCommunication };
