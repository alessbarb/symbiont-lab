import { state } from "../state/store.js";
import { bodySchemaToWire } from "../projection/body-schema.js";
import { boundedSnapshot, ingestSnapshot } from "../projection/snapshot.js";
import { showToast } from "../ui/dialogs.js";
import { renderSnapshotCycle } from "../ui/render-cycle.js";

function openReplayDialog() {
  document.querySelector("#welcome").hidden = true;
  document.querySelector("#replay-dialog").showModal();
}

function validateReplay(documentValue) {
  const snapshots = Array.isArray(documentValue) ? documentValue : documentValue?.snapshots;
  if (!Array.isArray(snapshots) || snapshots.length === 0) throw new Error("The replay must contain a non-empty snapshots array.");
  if (snapshots.length > 10000) throw new Error("The replay exceeds the 10,000 snapshot limit.");
  const firstInvalid = snapshots.findIndex(snapshot => !boundedSnapshot(snapshot));
  if (firstInvalid !== -1) throw new Error(`Snapshot ${firstInvalid + 1} does not match a supported Observatory snapshot schema.`);
  return snapshots;
}

async function loadReplayFile(file) {
  const status = document.querySelector("#import-status");
  const summary = document.querySelector("#replay-summary");
  summary.hidden = true;
  status.className = "import-status";
  try {
    if (!file || file.size > 5 * 1024 * 1024) throw new Error("Choose a JSON file no larger than 5 MB.");
    const parsed = JSON.parse(await file.text());
    state.replay = validateReplay(parsed);
    state.replayIndex = 0;
    state.mode = "replay";
    state.source = "replay";
    state.playing = false;
    document.querySelectorAll(".mode").forEach(button => button.classList.toggle("active", button.dataset.mode === "replay"));
    document.querySelector("#play").classList.add("paused");
    document.querySelector("#play").setAttribute("aria-label", "Resume playback");
    state.topology = null;
    state.cognition = null;
    state.bodySchema = null;
    const projection = ingestSnapshot(state.replay[0], false);
    if (projection) renderSnapshotCycle(projection.cognition);
    document.querySelector(".connection strong").textContent = "Replay ready";
    document.querySelector(".connection small").textContent = "local file";
    document.querySelector("#audit-transport").textContent = "Local replay";
    status.textContent = "✓ Replay ready";
    status.classList.add("success");
    summary.hidden = false;
    summary.textContent = `${file.name} · ${state.replay.length} snapshots · ${(file.size / 1024).toFixed(1)} KB · kept in memory only`;
    window.setTimeout(() => document.querySelector("#replay-dialog").close(), 650);
    showToast(`Loaded ${state.replay.length} snapshots`);
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : "The replay could not be opened.";
    status.classList.add("error");
  }
}

function currentSnapshot() {
  const resourceBudget = { ticks_remaining: state.details.resourceBudget.ticksRemaining };
  ["cpu", "memory", "storage"].forEach(key => {
    if (typeof state.details.resourceBudget[key] === "number") resourceBudget[key] = state.details.resourceBudget[key];
  });
  const events = state.events.slice(0, 64).map(event => {
    const beliefId = event.belief_id ?? event.beliefId ?? null;
    const chain = event.causal_chain ?? event.chain ?? [];
    const out = { id: String(event.id), type: event.type, label: event.label };
    if (event.explanation) out.explanation = event.explanation;
    if (beliefId) out.belief_id = beliefId;
    if (typeof event.delta === "number") out.delta = Math.max(-1, Math.min(1, event.delta));
    if (chain.length) out.causal_chain = chain.slice(0, 8);
    return out;
  });
  const bodySchema = bodySchemaToWire(state.bodySchema);
  const organism = {
    display_id: (state.displayId ?? "local-symbiont").slice(0, 48),
    state: state.organismState,
    narrative: state.details.narrative.slice(0, 600),
    acclimation: state.details.acclimation,
    resource_budget: resourceBudget,
    memory: state.details.memory.slice(0, 32),
    open_questions: state.details.openQuestions.slice(0, 16),
    investigations: state.details.investigations.slice(0, 16),
    regime_changes: state.details.regimeChanges.slice(0, 16),
    percepts: state.senses.slice(0, 32).map(item => ({ id: item.id, label: item.name, quality: item.quality, available: item.active })),
    beliefs: state.beliefs.slice(0, 128).map(item => ({ id: item.id, label: item.title, certainty: item.certainty, evidence_count: item.evidence, revision_count: item.revisions, contested: item.dissent })),
    events,
  };
  if (bodySchema) organism.body_schema = bodySchema;
  return {
    schema_version: bodySchema ? 3 : 1,
    tick: state.realTick ?? state.tick,
    organism,
    population: {
      members: state.population.slice(0, 500).map(item => ({ display_id: item.id, ecology: item.cluster, activity: item.pressure, knowledge_count: item.knowledge, contested_count: item.contested })),
      relationships: state.relationships.slice(0, 1000),
    },
  };
}

function exportReplay() {
  const snapshots = state.replay.length ? state.replay : [currentSnapshot()];
  const url = URL.createObjectURL(new Blob([JSON.stringify({ schema_version: 1, snapshots }, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "symbiont-replay.json";
  link.click();
  URL.revokeObjectURL(url);
  showToast("Replay exported locally");
}

export { openReplayDialog, validateReplay, loadReplayFile, currentSnapshot, exportReplay };
