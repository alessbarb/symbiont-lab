import { state } from "../state/store.js";
import { currentSnapshot } from "../transport/replay.js";
import { showToast } from "./dialogs.js";

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadJson(filename, payload) {
  downloadBlob(filename, new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
}

function clone(value) {
  return typeof structuredClone === "function" ? structuredClone(value) : JSON.parse(JSON.stringify(value));
}

function exportSnapshot() {
  const snapshot = state.lastRawSnapshot ? clone(state.lastRawSnapshot) : currentSnapshot();
  downloadJson("symbiont-snapshot.json", snapshot);
  showToast("Snapshot exported locally");
}

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function researchRows() {
  const rows = [
    ["Metadata", "Source", "observed", state.source],
    ["Metadata", "Schema", "observed", `v${state.schemaVersion}`],
    ["Metadata", "Tick", "observed", state.realTick ?? state.tick],
    ["Metadata", "Sequence", state.sequence == null ? "not published" : "observed", state.sequence ?? ""],
    ["Metadata", "Run", state.runId ? "observed" : "not published", state.runId ?? ""],
  ];
  (state.senses ?? []).forEach(item => rows.push(["Percept", item.name, item.active ? "available" : "unavailable", item.quality]));
  (state.beliefs ?? []).forEach(item => rows.push(["Belief", item.title, item.dissent ? "contested" : "revisable", item.certainty]));
  (state.socialRelations ?? []).forEach(item => rows.push(["Social evidence", `${item.source} → ${item.target}`, item.valence, `${item.observations} observations`]));
  return rows;
}

function exportResearchCsv() {
  const lines = [["Category", "Name", "State", "Value"], ...researchRows()].map(row => row.map(csvCell).join(","));
  downloadBlob("symbiont-research.csv", new Blob([lines.join("\n") + "\n"], { type: "text/csv;charset=utf-8" }));
  showToast("Research table exported locally");
}

async function fetchJson(path) {
  const response = await fetch(path, { method: "GET", cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error(`${response.status}`);
  return response.json();
}

// Capture all browser evidence before any asynchronous server request. Later UI
// transitions must not relabel this export, including in-place object updates.
function captureExportContext() {
  return clone({
    exportedAt: new Date().toISOString(),
    snapshot: state.lastRawSnapshot ?? currentSnapshot(),
    topology: state.topology ?? null,
    provenance: {
      source: state.source,
      instance_id: state.instanceId ?? null,
      run_id: state.runId ?? null,
      sequence: state.sequence ?? null,
      schema_version: state.schemaVersion ?? null,
      tick: state.realTick ?? state.tick ?? null,
      accepted_snapshots_browser_session: state.acceptedSnapshots ?? 0,
      rejected_snapshots_browser_session: state.rejectedSnapshots ?? 0,
      projection: "bounded browser-local",
    },
  });
}

function validateArtifact(artifact, context) {
  if (artifact == null) return;
  if (typeof artifact !== "object" || Array.isArray(artifact)) throw new Error("Invalid provenance artifact");
  const expected = {
    ...context.provenance,
    last_sequence: context.provenance.sequence,
    topology_revision: context.snapshot?.cognition?.topology_revision ?? context.topology?.topologyRevision,
    organism_id: context.snapshot?.organism?.organism_id ?? context.snapshot?.organism_id,
  };
  // History summaries publish run_id and tick_range, not a snapshot sequence.
  // Compare only fields actually published by both sides; never interpret a
  // summary's coverage endpoint as the captured snapshot's revision.
  for (const key of ["instance_id", "run_id", "organism_id", "sequence", "last_sequence", "tick", "schema_version", "topology_revision"]) {
    if (artifact[key] != null && expected[key] != null && artifact[key] !== expected[key]) {
      throw new Error(`Incompatible provenance ${key}`);
    }
  }
}

async function loadProvenanceArtifacts(context) {
  const { source, instance_id } = context.provenance;
  if (source !== "local server" || !instance_id) return { manifest: null, historySummary: null };
  const base = `/instance/${encodeURIComponent(instance_id)}`;
  const [manifest, historySummary] = await Promise.all([
    fetchJson(`${base}/manifest`).catch(() => null),
    fetchJson(`${base}/history-summary`).catch(() => null),
  ]);
  validateArtifact(manifest, context);
  validateArtifact(historySummary, context);
  return { manifest, historySummary };
}

async function exportManifest() {
  const context = captureExportContext();
  const { source, instance_id } = context.provenance;
  if (source !== "local server" || !instance_id) { showToast("Manifest is available only from the local Observatory server"); return; }
  try {
    const manifest = await fetchJson(`/instance/${encodeURIComponent(instance_id)}/manifest`);
    validateArtifact(manifest, context);
    downloadJson("symbiont-manifest.json", manifest);
    showToast("Projected manifest exported locally");
  } catch {
    showToast("No compatible projected manifest is available for this captured snapshot");
  }
}

async function exportEvidenceBundle() {
  const context = captureExportContext();
  try {
    const { manifest, historySummary } = await loadProvenanceArtifacts(context);
    const bundle = {
      bundle_version: 1,
      exported_at: context.exportedAt,
      scope: "bounded Observatory evidence only",
      provenance: context.provenance,
      snapshot: context.snapshot,
      topology: context.topology,
      manifest,
      history_summary: historySummary,
      note: "This bundle contains passive Observatory projections and derived provenance only. It excludes checkpoint contents, raw host readings and control surfaces.",
    };
    downloadJson("symbiont-evidence-bundle.json", bundle);
    showToast("Evidence bundle exported locally");
  } catch {
    showToast("Evidence export cancelled: server provenance is incompatible with the captured snapshot");
  }
}

function addExportButton(container, id, label, handler) {
  if (document.querySelector(`#${id}`)) return;
  const button = document.createElement("button");
  button.id = id;
  button.className = "secondary wide";
  button.textContent = label;
  button.addEventListener("click", handler);
  container.append(button);
}

function installExportActions() {
  const replayButton = document.querySelector("#export-replay");
  if (!replayButton || document.querySelector("#export-snapshot")) return;
  const group = document.createElement("div");
  group.id = "evidence-export-actions";
  replayButton.after(group);
  addExportButton(group, "export-snapshot", "Export snapshot", exportSnapshot);
  addExportButton(group, "export-research-csv", "Export research CSV", exportResearchCsv);
  addExportButton(group, "export-manifest", "Export projected manifest", exportManifest);
  addExportButton(group, "export-evidence-bundle", "Export evidence bundle", exportEvidenceBundle);
}

export { exportSnapshot, exportResearchCsv, exportManifest, exportEvidenceBundle, installExportActions };
