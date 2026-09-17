import { state } from "../state/store.js";
import { connectInstance, reconnectCurrentInstance } from "../transport/instance-stream.js";
import { updateUiState } from "../state/transition.js";
import { renderTimeline } from "../render/timeline.js";

const fleetView = { query: "", sort: "liveness", direction: "asc", liveness: "all", schema: "all", physiology: "all", pinned: new Set() };
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
  let detail = stored?.detail ?? (source === "demo" ? "synthetic telemetry" : source === "replay" ? "local file" : "receiving snapshots");
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

function fleetRows(instances = state.fleetInstances ?? []) {
  const metrics = new Map((state.fleetPopulation ?? []).map(item => [item.id, item]));
  return instances.map(instance => ({ ...instance, metrics: metrics.get(instance.instance_id) ?? null }));
}

function fleetSortValue(row, key) {
  const metric = row.metrics;
  const values = {
    resident: row.display_id ?? row.instance_id,
    liveness: livenessRank(row.liveness),
    heartbeat: Date.parse(row.last_heartbeat ?? ""),
    tick: metric?.tick,
    schema: metric?.schemaVersion,
    physiology: metric?.physiology,
    activity: metric?.pressure,
    knowledge: metric?.knowledge,
    dissent: metric?.contested,
    revision: row.topology_revision,
    run: row.run_id,
  };
  return values[key];
}

function compareFleetRows(a, b) {
  const av = fleetSortValue(a, fleetView.sort); const bv = fleetSortValue(b, fleetView.sort);
  const aMissing = av == null || (typeof av === "number" && !Number.isFinite(av));
  const bMissing = bv == null || (typeof bv === "number" && !Number.isFinite(bv));
  if (aMissing !== bMissing) return aMissing ? 1 : -1;
  if (aMissing && bMissing) return 0;
  const direction = fleetView.direction === "desc" ? -1 : 1;
  if (typeof av === "number" && typeof bv === "number") return (av - bv) * direction;
  return String(av).localeCompare(String(bv)) * direction;
}

function fleetValue(value, formatter = String) {
  return value == null || (typeof value === "number" && !Number.isFinite(value)) ? "not published" : formatter(value);
}

function ensureFleetResearchControls() {
  const tools = document.querySelector(".fleet-tools");
  if (!tools || document.querySelector("#fleet-liveness-filter")) return;
  const definitions = [
    ["fleet-liveness-filter", "Liveness", [["all", "All"], ["alive", "Alive"], ["stale", "Stale"]]],
    ["fleet-schema-filter", "Schema", [["all", "All"], ["1", "v1"], ["2", "v2"], ["3", "v3"], ["none", "Not published"]]],
    ["fleet-physiology-filter", "Physiology", [["all", "All"], ["active", "Active"], ["stressed", "Stressed"], ["dormant", "Dormant"], ["agonizing", "Agonizing"], ["dead", "Dead"], ["none", "Not published"]]],
  ];
  definitions.forEach(([id, labelText, options]) => {
    const label = document.createElement("label"); label.textContent = labelText; label.setAttribute("for", id);
    const select = document.createElement("select"); select.id = id; select.setAttribute("aria-label", `${labelText} filter`);
    options.forEach(([value, text]) => { const option = document.createElement("option"); option.value = value; option.textContent = text; select.append(option); });
    select.addEventListener("change", () => {
      if (id === "fleet-liveness-filter") fleetView.liveness = select.value;
      if (id === "fleet-schema-filter") fleetView.schema = select.value;
      if (id === "fleet-physiology-filter") fleetView.physiology = select.value;
      renderFleetTable();
    });
    tools.append(label, select);
  });
}

function renderFleetComparison(rows) {
  const wrap = document.querySelector(".fleet-table-wrap");
  if (!wrap) return;
  let section = document.querySelector("#fleet-shortlist");
  if (!section) {
    section = document.createElement("section"); section.id = "fleet-shortlist"; section.className = "profile-section"; wrap.after(section);
  }
  section.replaceChildren();
  const heading = document.createElement("h3"); heading.textContent = `Fleet shortlist · ${fleetView.pinned.size}/4`;
  const note = document.createElement("p"); note.textContent = "Pinned residents are compared descriptively; no aggregate trust, health or fitness score is computed.";
  section.append(heading, note);
  const pinned = rows.filter(row => fleetView.pinned.has(row.instance_id));
  if (!pinned.length) { const empty = document.createElement("p"); empty.textContent = "Pin up to four residents from the table to compare their latest published observations."; section.append(empty); return; }
  const table = document.createElement("table"); table.className = "fleet-table";
  const header = document.createElement("tr"); ["Resident", "Tick", "Activity", "Knowledge", "Dissent", "Physiology", "Schema"].forEach(text => { const th = document.createElement("th"); th.textContent = text; header.append(th); }); table.append(header);
  pinned.forEach(row => {
    const metric = row.metrics;
    const tr = document.createElement("tr");
    [row.display_id ?? row.instance_id, fleetValue(metric?.tick), fleetValue(metric?.pressure, value => `${Math.round(value * 100)}%`), fleetValue(metric?.knowledge), fleetValue(metric?.contested), fleetValue(metric?.physiology), fleetValue(metric?.schemaVersion, value => `v${value}`)].forEach(value => { const td = document.createElement("td"); td.textContent = value; tr.append(td); });
    table.append(tr);
  });
  section.append(table);
}

function renderFleetTable(instances = state.fleetInstances ?? []) {
  const table = document.querySelector("#fleet-table");
  const summary = document.querySelector("#fleet-summary");
  if (!table || !summary) return;
  ensureFleetResearchControls();
  const rows = fleetRows(instances);
  const query = fleetView.query.trim().toLowerCase();
  const visible = rows.filter(row => {
    const metric = row.metrics;
    if (query && !`${row.display_id} ${row.instance_id} ${row.run_id ?? ""}`.toLowerCase().includes(query)) return false;
    if (fleetView.liveness !== "all" && row.liveness !== fleetView.liveness) return false;
    const schema = metric?.schemaVersion == null ? "none" : String(metric.schemaVersion);
    if (fleetView.schema !== "all" && schema !== fleetView.schema) return false;
    const physiology = metric?.physiology ?? "none";
    if (fleetView.physiology !== "all" && physiology !== fleetView.physiology) return false;
    return true;
  });
  const ordered = [...visible].sort(compareFleetRows);
  const counts = rows.reduce((out, item) => { out[item.liveness] = (out[item.liveness] ?? 0) + 1; return out; }, {});
  const filtering = query || fleetView.liveness !== "all" || fleetView.schema !== "all" || fleetView.physiology !== "all";
  summary.textContent = `${rows.length} resident${rows.length === 1 ? "" : "s"} · ${counts.alive ?? 0} alive · ${counts.stale ?? 0} stale${filtering ? ` · ${visible.length} shown` : ""}`;
  table.replaceChildren();
  const columns = [["resident", "Resident"], ["liveness", "Status"], ["heartbeat", "Heartbeat"], ["tick", "Tick"], ["schema", "Schema"], ["physiology", "Physiology"], ["activity", "Activity"], ["knowledge", "Knowledge"], ["dissent", "Dissent"], ["revision", "Revision"], ["run", "Run"]];
  const header = document.createElement("tr");
  columns.forEach(([key, label]) => {
    const cell = document.createElement("th"); cell.scope = "col"; cell.textContent = label; cell.tabIndex = 0; cell.style.cursor = "pointer";
    if (fleetView.sort === key) cell.setAttribute("aria-sort", fleetView.direction === "asc" ? "ascending" : "descending");
    const sort = () => { if (fleetView.sort === key) fleetView.direction = fleetView.direction === "asc" ? "desc" : "asc"; else { fleetView.sort = key; fleetView.direction = "asc"; } renderFleetTable(); };
    cell.addEventListener("click", sort); cell.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); sort(); } }); header.append(cell);
  });
  const compareHeader = document.createElement("th"); compareHeader.scope = "col"; compareHeader.textContent = "Compare"; header.append(compareHeader); table.append(header);
  if (!ordered.length) { const row = document.createElement("tr"); const cell = document.createElement("td"); cell.colSpan = columns.length + 1; cell.className = "fleet-empty"; cell.textContent = filtering ? "No resident matches the current search and filters." : "No residents discovered by the local server."; row.append(cell); table.append(row); renderFleetComparison(rows); return; }
  ordered.forEach(rowData => {
    const metric = rowData.metrics;
    const row = document.createElement("tr"); row.className = rowData.instance_id === state.instanceId ? "selected" : ""; row.tabIndex = 0; row.title = `Select ${rowData.display_id}`;
    const values = [rowData.display_id ?? rowData.instance_id, rowData.liveness ?? "unknown", formatAge(rowData.last_heartbeat), fleetValue(metric?.tick), fleetValue(metric?.schemaVersion, value => `v${value}`), fleetValue(metric?.physiology), fleetValue(metric?.pressure, value => `${Math.round(value * 100)}%`), fleetValue(metric?.knowledge), fleetValue(metric?.contested), `rev ${rowData.topology_revision ?? 0}`, rowData.run_id ? rowData.run_id.slice(0, 8) : "—"];
    values.forEach((value, index) => { const cell = document.createElement(index === 0 ? "th" : "td"); if (index === 0) cell.scope = "row"; cell.textContent = String(value); row.append(cell); });
    const pinCell = document.createElement("td"); const pin = document.createElement("button"); const pinned = fleetView.pinned.has(rowData.instance_id); pin.className = "secondary"; pin.textContent = pinned ? "Pinned" : "Pin"; pin.setAttribute("aria-pressed", String(pinned));
    pin.addEventListener("click", event => { event.stopPropagation(); if (pinned) fleetView.pinned.delete(rowData.instance_id); else if (fleetView.pinned.size < 4) fleetView.pinned.add(rowData.instance_id); renderFleetTable(); }); pinCell.append(pin); row.append(pinCell);
    const select = () => connectInstance(rowData.instance_id);
    row.addEventListener("click", select); row.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } }); table.append(row);
  });
  renderFleetComparison(rows);
  let relationshipNote = document.querySelector("#fleet-relationship-note");
  if (!relationshipNote) { relationshipNote = document.createElement("p"); relationshipNote.id = "fleet-relationship-note"; relationshipNote.className = "comparison-note"; document.querySelector("#fleet-shortlist")?.after(relationshipNote); }
  relationshipNote.textContent = "Fleet relationships are intentionally not synthesized: current local social endpoints are not globally addressable across resident instances.";
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
  ensureFleetResearchControls();
  renderFleetTable();
  document.querySelector("#reconnect-instance")?.addEventListener("click", () => { if (reconnectCurrentInstance()) updateTelemetry({ source: "local server", connection: "connecting", connectionLabel: "Connecting" }); });
  document.querySelector("#follow-live")?.addEventListener("click", returnToLive);
  if (refreshTimer === null) refreshTimer = window.setInterval(refreshOperationalStatus, 1000);
}

export { formatAge, updateTelemetry, renderFleetTable, renderOperationalStatus, recordAcceptedSnapshot, recordRejectedSnapshot, returnToLive, installFleetSearch };
