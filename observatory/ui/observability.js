import { state } from "../state/store.js";
import { connectInstance, reconnectCurrentInstance } from "../transport/instance-stream.js";
import { updateUiState } from "../state/transition.js";
import { renderTimeline } from "../render/timeline.js";

const fleetView = { query: "", sort: "liveness" };
let refreshTimer = null;

function formatAge(timestamp) {
  if (!timestamp) return "—";
  const age = Math.max(0, Date.now() - Date.parse(timestamp));
  if (!Number.isFinite(age)) return "unknown";
  if (age < 1000) return "now";
  if (age < 60_000) return `${Math.floor(age / 1000)}s ago`;
  if (age < 3_600_000) return `${Math.floor(age / 60_000)}m ago`;
  return `${Math.floor(age / 3_600_000)}h ago`;
}

function selectedInstance() {
  return (state.fleetInstances ?? []).find(item => item.instance_id === state.instanceId) ?? null;
}

function ensureTelemetryExtensions() {
  const strip = document.querySelector(".telemetry-strip");
  if (!strip) return;
  const reconnect = document.querySelector("#reconnect-instance");
  const fields = [
    ["telemetry-schema", "schema"],
    ["telemetry-run", "run"],
    ["telemetry-revision", "revision"],
    ["telemetry-liveness", "liveness"],
  ];
  fields.forEach(([id, label]) => {
    if (document.querySelector(`#${id}`)) return;
    const box = document.createElement("span");
    const value = document.createElement("b");
    const caption = document.createElement("small");
    value.id = id;
    value.textContent = "—";
    caption.textContent = label;
    box.append(value, caption);
    strip.insertBefore(box, reconnect ?? null);
  });
  if (!document.querySelector("#follow-live")) {
    const button = document.createElement("button");
    button.id = "follow-live";
    button.type = "button";
    button.className = "telemetry-reconnect";
    button.textContent = "Return to live";
    button.hidden = true;
    strip.insertBefore(button, reconnect ?? null);
  }
}

function connectionPresentation(source, patch) {
  if (patch.connection !== undefined || patch.connectionLabel !== undefined) {
    updateUiState({
      operationalConnection: {
        source,
        detail: patch.connection ?? "receiving snapshots",
        label: patch.connectionLabel ?? "Connected",
      },
    });
  }
  const stored = state.operationalConnection?.source === source ? state.operationalConnection : null;
  let detail = stored?.detail ?? (source === "demo" ? "local preview" : source === "replay" ? "local file" : "receiving snapshots");
  let label = stored?.label ?? (source === "demo" ? "Demo" : source === "replay" ? "Replay ready" : "Connected");
  const instance = selectedInstance();
  if (source === "local server" && instance?.liveness === "stale" && !["Connecting", "Reconnecting"].includes(label)) {
    detail = `stale heartbeat · ${formatAge(instance.last_heartbeat)}`;
    label = "Stale";
  }
  if (state.lastProjectionStatus === "rejected") {
    detail = state.lastProjectionReason || "snapshot rejected by bounded projection";
    label = "Projection rejected";
  }
  return { detail, label };
}

function updateTelemetry(patch = {}) {
  ensureTelemetryExtensions();
  const source = patch.source ?? state.source;
  const labels = { demo: "DEMO", replay: "REPLAY", "local server": "SERVER", "same-origin message": "LOCAL", "local channel": "LOCAL" };
  const sourceEl = document.querySelector("#telemetry-source");
  const connectionEl = document.querySelector("#telemetry-connection");
  const tickEl = document.querySelector("#telemetry-tick");
  const sequenceEl = document.querySelector("#telemetry-sequence");
  const freshnessEl = document.querySelector("#telemetry-freshness");
  if (!sourceEl || !connectionEl) return;
  const connection = connectionPresentation(source, patch);
  const instance = selectedInstance();
  const revision = state.topology?.topologyRevision ?? instance?.topology_revision ?? null;
  sourceEl.textContent = labels[source] ?? String(source).toUpperCase();
  connectionEl.textContent = connection.detail;
  if (tickEl) tickEl.textContent = `t${patch.tick ?? state.realTick ?? state.tick ?? "—"}`;
  if (sequenceEl) sequenceEl.textContent = patch.sequence == null ? (state.sequence == null ? "—" : `#${state.sequence}`) : `#${patch.sequence}`;
  if (freshnessEl) freshnessEl.textContent = state.lastSnapshotAt ? formatAge(state.lastSnapshotAt) : "—";
  const schemaEl = document.querySelector("#telemetry-schema");
  if (schemaEl) schemaEl.textContent = state.schemaVersion ? `v${state.schemaVersion}` : "—";
  const runEl = document.querySelector("#telemetry-run");
  if (runEl) { runEl.textContent = state.runId ? state.runId.slice(0, 8) : "—"; runEl.title = state.runId ?? "Run id not published"; }
  const revisionEl = document.querySelector("#telemetry-revision");
  if (revisionEl) revisionEl.textContent = revision == null ? "—" : `r${revision}`;
  const livenessEl = document.querySelector("#telemetry-liveness");
  if (livenessEl) livenessEl.textContent = instance?.liveness ?? (source === "local server" ? "unknown" : "n/a");
  document.querySelector(".connection strong")?.replaceChildren(document.createTextNode(connection.label));
  document.querySelector(".connection small")?.replaceChildren(document.createTextNode(connection.detail));
  const reconnect = document.querySelector("#reconnect-instance");
  if (reconnect) reconnect.hidden = source !== "local server" || !state.instanceId;
  const followLive = document.querySelector("#follow-live");
  if (followLive) followLive.hidden = source === "replay" || source === "demo" || state.mode === "live";
  renderOperationalStatus();
}

function rawOrganismHas(field) {
  const organism = state.lastRawSnapshot?.organism;
  return !!organism && Object.prototype.hasOwnProperty.call(organism, field);
}

function dataAvailability() {
  const instance = selectedInstance();
  const snapshotStatus = state.lastProjectionStatus === "rejected"
    ? "Rejected"
    : instance?.liveness === "stale"
      ? "Stale"
      : state.lastSnapshotAt
        ? "Observed"
        : "Not received";
  const selfStatus = state.schemaVersion < 3
    ? "Not in schema"
    : state.bodySchema?.state === "undeveloped"
      ? "Not yet developed"
      : state.bodySchema
        ? "Observed"
        : "Not published";
  const cognitionStatus = state.schemaVersion === 1 ? "Not in schema" : state.cognition ? "Observed" : "Not published";
  const topologyStatus = state.topology ? "Observed" : (instance?.topology_revision ?? 0) > 0 ? "Not received" : "Not applicable";
  return [
    ["Snapshot", snapshotStatus],
    ["Cognition", cognitionStatus],
    ["Self", selfStatus],
    ["Topology", topologyStatus],
    ["Physiology", state.physiology ? "Observed" : "Not published"],
    ["Attention", state.attention ? "Observed" : "Not published"],
    ["Social evidence", rawOrganismHas("social_relations") ? "Observed" : "Not published"],
    ["Resource evidence", rawOrganismHas("social_resource_evidence") ? "Observed" : "Not published"],
  ];
}

function renderOperationalStatus() {
  const research = document.querySelector("#research-details");
  if (!research) return;
  document.querySelector("#operational-status")?.remove();
  const section = document.createElement("section");
  section.id = "operational-status";
  section.className = "profile-section";
  const heading = document.createElement("h3");
  heading.textContent = "Data availability";
  const note = document.createElement("p");
  note.textContent = "Observed, Not published, Not yet developed, Not in schema, Not received, Stale and Rejected are distinct states; Observatory never fills missing data by inference.";
  const list = document.createElement("ul");
  list.className = "detail-list";
  dataAvailability().forEach(([label, value]) => {
    const item = document.createElement("li");
    const name = document.createElement("b");
    const status = document.createElement("span");
    name.textContent = label;
    status.textContent = value;
    item.append(name, status);
    list.append(item);
  });
  const counters = document.createElement("p");
  counters.textContent = `Accepted snapshots this browser session: ${state.acceptedSnapshots ?? 0} · rejected: ${state.rejectedSnapshots ?? 0}`;
  section.append(heading, note, list, counters);
  research.append(section);
}

function recordAcceptedSnapshot() {
  updateUiState({
    acceptedSnapshots: (state.acceptedSnapshots ?? 0) + 1,
    lastProjectionStatus: "accepted",
    lastProjectionReason: null,
  });
}

function recordRejectedSnapshot(reason = "Snapshot does not match a supported bounded projection.") {
  updateUiState({
    rejectedSnapshots: (state.rejectedSnapshots ?? 0) + 1,
    lastProjectionStatus: "rejected",
    lastProjectionReason: reason,
  });
  updateTelemetry({ connection: "bounded projection rejected the latest snapshot", connectionLabel: "Projection rejected" });
}

function livenessRank(value) { return { alive: 0, stale: 1, expired: 2 }[value] ?? 3; }

function renderFleetTable(instances = state.fleetInstances ?? []) {
  const table = document.querySelector("#fleet-table");
  const summary = document.querySelector("#fleet-summary");
  if (!table || !summary) return;
  const query = fleetView.query.trim().toLowerCase();
  const visible = instances.filter(item => !query || `${item.display_id} ${item.instance_id}`.toLowerCase().includes(query));
  const ordered = [...visible].sort((a, b) => livenessRank(a.liveness) - livenessRank(b.liveness) || String(a.display_id).localeCompare(String(b.display_id)));
  const counts = instances.reduce((out, item) => { out[item.liveness] = (out[item.liveness] ?? 0) + 1; return out; }, {});
  summary.textContent = `${instances.length} resident${instances.length === 1 ? "" : "s"} · ${counts.alive ?? 0} alive · ${counts.stale ?? 0} stale${query ? ` · ${visible.length} shown` : ""}`;
  table.replaceChildren();
  const header = document.createElement("tr");
  ["Resident", "Status", "Heartbeat", "Revision", "Run"].forEach(label => { const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = label; header.append(cell); });
  table.append(header);
  if (!ordered.length) { const row = document.createElement("tr"); const cell = document.createElement("td"); cell.colSpan = 5; cell.className = "fleet-empty"; cell.textContent = query ? "No resident matches this search." : "No residents discovered by the local server."; row.append(cell); table.append(row); return; }
  ordered.forEach(instance => {
    const row = document.createElement("tr");
    row.className = instance.instance_id === state.instanceId ? "selected" : "";
    row.tabIndex = 0;
    row.title = `Select ${instance.display_id}`;
    const values = [instance.display_id ?? instance.instance_id, instance.liveness ?? "unknown", formatAge(instance.last_heartbeat), `rev ${instance.topology_revision ?? 0}`, instance.run_id ? instance.run_id.slice(0, 8) : "—"];
    values.forEach((value, index) => { const cell = document.createElement(index === 0 ? "th" : "td"); if (index === 0) cell.scope = "row"; cell.textContent = String(value); row.append(cell); });
    const select = () => connectInstance(instance.instance_id);
    row.addEventListener("click", select); row.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } });
    table.append(row);
  });
}

function returnToLive() {
  if (state.source === "replay" || state.source === "demo") return false;
  updateUiState({ mode: "live", playing: true });
  document.querySelectorAll(".mode").forEach(button => button.classList.toggle("active", button.dataset.mode === "live"));
  const play = document.querySelector("#play");
  play?.classList.remove("paused");
  play?.setAttribute("aria-label", "Pause playback");
  renderTimeline();
  updateTelemetry();
  return true;
}

function refreshOperationalStatus() {
  renderFleetTable();
  updateTelemetry();
}

function installFleetSearch() {
  document.querySelector("#fleet-search")?.addEventListener("input", event => { fleetView.query = event.target.value; renderFleetTable(); });
  document.querySelector("#fleet-clear-search")?.addEventListener("click", () => { fleetView.query = ""; const input = document.querySelector("#fleet-search"); if (input) input.value = ""; renderFleetTable(); input?.focus(); });
  ensureTelemetryExtensions();
  renderFleetTable();
  document.querySelector("#reconnect-instance")?.addEventListener("click", () => { if (reconnectCurrentInstance()) updateTelemetry({ source: "local server", connection: "connecting", connectionLabel: "Connecting" }); });
  document.querySelector("#follow-live")?.addEventListener("click", returnToLive);
  if (refreshTimer === null) refreshTimer = window.setInterval(refreshOperationalStatus, 1000);
}

export { formatAge, updateTelemetry, renderFleetTable, renderOperationalStatus, recordAcceptedSnapshot, recordRejectedSnapshot, returnToLive, installFleetSearch };
