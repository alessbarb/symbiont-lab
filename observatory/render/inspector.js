import { state } from "../state/store.js";
import { palette } from "./svg.js";
import { renderSignalKnowledge } from "./signal-knowledge.js";

function renderInspector() {
  const signalPanel = document.querySelector("#signal-knowledge-panel");
  if (signalPanel) renderSignalKnowledge(signalPanel);
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
