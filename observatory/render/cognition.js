import { state } from "../state/store.js";

function renderCognitionTopology(topology) {
  if (!topology) return;
  const subtitle = document.querySelector("#cognition-subtitle");
  const summary = document.querySelector("#cognition-topology-summary");
  if (!subtitle || !summary) return;
  subtitle.textContent = `Genome ${topology.genome_id ?? "?"} · revision ${topology.topology_revision ?? 0}`;
  summary.textContent = `${(topology.nodes ?? []).length} nodes, ${(topology.edges ?? []).length} edges`;
}

function renderGenerativeCognition(generative) {
  const summary = document.querySelector("#cognition-generative-summary");
  const hypothesesEl = document.querySelector("#cognition-generative-hypotheses");
  if (!summary || !hypothesesEl) return;
  summary.replaceChildren();
  hypothesesEl.replaceChildren();

  if (!generative) {
    const row = document.createElement("p");
    row.textContent = "No active generative cognition.";
    summary.append(row);
    return;
  }

  const rows = [
    ["Mode", generative.mode ?? "online"],
    ["Target", generative.targetId ?? "—"],
    ["Episode", generative.episodeId ?? "—"],
    ["States", generative.stateCount ?? 0],
    ["Transitions", generative.transitionCount ?? 0],
    ["Branches", generative.branchCount ?? 0],
    ["Max depth", generative.maxDepth ?? 0],
    ["Model queries", generative.modelQueries ?? 0],
    ["Agenda candidates", generative.agendaCandidateCount ?? 0],
    ["Hypotheses", generative.hypothesisCount ?? 0],
    ["Reconciliations", generative.reconciliationCount ?? 0],
    ["Consolidation signals", generative.consolidationSignalCount ?? 0],
    ["Factual contamination", generative.factualContaminationCount ?? 0],
    ["Agenda contamination", generative.agendaContaminationCount ?? 0],
  ];
  for (const [label, value] of rows) {
    const row = document.createElement("p");
    row.textContent = label + ": " + value;
    summary.append(row);
  }

  const hypotheses = Array.isArray(generative.hypotheses) ? generative.hypotheses : [];
  if (!hypotheses.length) {
    const row = document.createElement("p");
    row.textContent = "No active generative hypotheses.";
    hypothesesEl.append(row);
    return;
  }
  for (const hypothesis of hypotheses.slice(0, 12)) {
    const row = document.createElement("p");
    const models = Array.isArray(hypothesis.modelIds) && hypothesis.modelIds.length
      ? hypothesis.modelIds.join(", ")
      : "no model";
    const uncertainty = (Number(hypothesis.uncertainty ?? 0) * 100).toFixed(1);
    row.textContent =
      (hypothesis.status ?? "hypothesized") + " · " +
      (hypothesis.targetId ?? "—") + " · " + models +
      " · uncertainty " + uncertainty + "%";
    hypothesesEl.append(row);
  }
}
function renderCognitionState(cognition) {
  const readoutsEl = document.querySelector("#cognition-readouts");
  const errorsEl = document.querySelector("#cognition-prediction-errors");
  const mutationsEl = document.querySelector("#cognition-mutations");
  const safetyEl = document.querySelector("#cognition-safety-state");
  const subtitleEl = document.querySelector("#cognition-subtitle");
  const summaryEl = document.querySelector("#cognition-topology-summary");
  const metricsEl = document.querySelector("#cognition-developmental-metrics");
  if (!readoutsEl || !errorsEl || !mutationsEl || !safetyEl || !subtitleEl) return;
  readoutsEl.replaceChildren();
  errorsEl.replaceChildren();
  mutationsEl.replaceChildren();
  if (metricsEl) metricsEl.replaceChildren();
  renderGenerativeCognition(cognition?.generative ?? null);
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
  if (metricsEl) {
    const metrics = [
      ["Predictive gain", cognition.predictiveGain ?? cognition.predictive_gain, "value"],
      ["Structural pressure", cognition.structuralPressure ?? cognition.structural_pressure, "fraction"],
      ["Checkpoint quantization error", cognition.quantizationError ?? cognition.quantization_error, "value"],
      ["Relation churn", cognition.relationChurn ?? cognition.relation_churn, "fraction"],
      ["Developmental divergence", cognition.developmentalDivergence ?? cognition.developmental_divergence, "fraction"],
    ];
    metrics.filter(([, value]) => Number.isFinite(value)).forEach(([label, value, kind]) => {
      const row = document.createElement("p");
      const rendered = kind === "fraction" ? `${(value * 100).toFixed(1)}%` : Number(value).toFixed(4);
      row.textContent = `${label}: ${rendered}`;
      metricsEl.append(row);
    });
  }
  safetyEl.textContent = `Frozen: ${cognition.safetyState.frozen}, failures: ${cognition.safetyState.consecutiveFailures}`;
}

export { renderCognitionTopology, renderCognitionState, renderGenerativeCognition };
