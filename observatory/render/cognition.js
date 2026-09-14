import { state } from "../state/store.js";

function renderCognitionTopology(topology) {
  if (!topology) return;
  const subtitle = document.querySelector("#cognition-subtitle");
  const summary = document.querySelector("#cognition-topology-summary");
  if (!subtitle || !summary) return;
  subtitle.textContent = `Genome ${topology.genome_id ?? "?"} · revision ${topology.topology_revision ?? 0}`;
  summary.textContent = `${(topology.nodes ?? []).length} nodes, ${(topology.edges ?? []).length} edges`;
}

function renderCognitionState(cognition) {
  const readoutsEl = document.querySelector("#cognition-readouts");
  const errorsEl = document.querySelector("#cognition-prediction-errors");
  const mutationsEl = document.querySelector("#cognition-mutations");
  const safetyEl = document.querySelector("#cognition-safety-state");
  const subtitleEl = document.querySelector("#cognition-subtitle");
  const summaryEl = document.querySelector("#cognition-topology-summary");
  if (!readoutsEl || !errorsEl || !mutationsEl || !safetyEl || !subtitleEl) return;
  readoutsEl.replaceChildren();
  errorsEl.replaceChildren();
  mutationsEl.replaceChildren();
  if (!cognition) {
    if (state.schemaVersion === 1) {
      subtitleEl.textContent = "Structural cognition not configured";
      if (summaryEl) {
        summaryEl.textContent = "This resident is developing opaque senses autonomously. No owner-authored genome/cognitive graph was loaded.";
      }
    } else {
      subtitleEl.textContent = "No cognition data for this organism";
      if (summaryEl) {
        summaryEl.textContent = "";
      }
    }
    safetyEl.textContent = "";
    return;
  }
  Object.entries(cognition.readouts).forEach(([id, value]) => {
    const row = document.createElement("p"); row.textContent = `${id}: ${value}`; readoutsEl.append(row);
  });
  Object.entries(cognition.predictionErrors).forEach(([id, cls]) => {
    const row = document.createElement("p"); row.textContent = `${id}: ${cls}`; errorsEl.append(row);
  });
  cognition.mutations.forEach(mutation => {
    const row = document.createElement("p"); row.textContent = `${mutation.kind} ${mutation.nodeId ?? mutation.edgeId ?? ""}`; mutationsEl.append(row);
  });
  safetyEl.textContent = `Frozen: ${cognition.safetyState.frozen}, failures: ${cognition.safetyState.consecutiveFailures}`;
}

export { renderCognitionTopology, renderCognitionState };
