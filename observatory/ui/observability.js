import { state } from "../state/store.js";
import { connectInstance, reconnectCurrentInstance } from "../transport/instance-stream.js";

const fleetView = { query: "", sort: "liveness" };

function formatAge(timestamp) {
  if (!timestamp) return "—";
  const age = Math.max(0, Date.now() - Date.parse(timestamp));
  if (!Number.isFinite(age)) return "unknown";
  if (age < 1000) return "now";
  if (age < 60_000) return `${Math.floor(age / 1000)}s ago`;
  return `${Math.floor(age / 60_000)}m ago`;
}

function updateTelemetry(patch = {}) {
  const source = patch.source ?? state.source;
  const labels = { demo: "DEMO", replay: "REPLAY", "local server": "SERVER", "same-origin message": "LOCAL", "local channel": "LOCAL" };
  const sourceEl = document.querySelector("#telemetry-source");
  const connectionEl = document.querySelector("#telemetry-connection");
  const tickEl = document.querySelector("#telemetry-tick");
  const sequenceEl = document.querySelector("#telemetry-sequence");
  const freshnessEl = document.querySelector("#telemetry-freshness");
  if (!sourceEl || !connectionEl) return;
  sourceEl.textContent = labels[source] ?? String(source).toUpperCase();
  connectionEl.textContent = patch.connection ?? (source === "demo" ? "local preview" : source === "replay" ? "local file" : "receiving snapshots");
  if (tickEl) tickEl.textContent = `t${patch.tick ?? state.realTick ?? state.tick ?? "—"}`;
  if (sequenceEl) sequenceEl.textContent = patch.sequence == null ? (state.sequence == null ? "—" : `#${state.sequence}`) : `#${patch.sequence}`;
  if (freshnessEl) freshnessEl.textContent = patch.timestamp ? formatAge(patch.timestamp) : (state.lastSnapshotAt ? formatAge(state.lastSnapshotAt) : "—");
  document.querySelector(".connection strong")?.replaceChildren(document.createTextNode(patch.connectionLabel ?? (source === "demo" ? "Demo" : source === "replay" ? "Replay ready" : "Connected")));
  document.querySelector(".connection small")?.replaceChildren(document.createTextNode(connectionEl.textContent));
  const reconnect = document.querySelector("#reconnect-instance");
  if (reconnect) reconnect.hidden = source !== "local server" || !state.instanceId;
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

function installFleetSearch() {
  document.querySelector("#fleet-search")?.addEventListener("input", event => { fleetView.query = event.target.value; renderFleetTable(); });
  document.querySelector("#fleet-clear-search")?.addEventListener("click", () => { fleetView.query = ""; const input = document.querySelector("#fleet-search"); if (input) input.value = ""; renderFleetTable(); input?.focus(); });
  renderFleetTable();
  document.querySelector("#reconnect-instance")?.addEventListener("click", () => { if (reconnectCurrentInstance()) updateTelemetry({ source: "local server", connection: "connecting", connectionLabel: "Connecting" }); });
}

export { formatAge, updateTelemetry, renderFleetTable, installFleetSearch };
