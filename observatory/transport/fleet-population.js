import { state } from "../state/store.js";
import { boundedSnapshot, normalizeSnapshot } from "../projection/snapshot.js";
import { renderPopulation, renderPopulationInspector } from "../render/population.js";
import { renderFleetTable } from "../ui/observability.js";
import { updateUiState } from "../state/transition.js";

const sources = new Map();
const records = new Map();
const projections = new Map();
const STALE_RETENTION_MS = 30_000;

function memberFromProjection(instance, projection, index, total) {
  const local = projection?.population?.find(item => item.id === projection.displayId) ?? projection?.population?.[0];
  const angle = index * (Math.PI * 2 / Math.max(total, 1)) - Math.PI / 2;
  const radius = Math.min(245, 110 + total * 8);
  return {
    id: instance.instance_id,
    displayId: instance.display_id,
    cluster: local?.cluster ?? 0,
    x: local && projection.population.length > 1 ? local.x : 450 + Math.cos(angle) * radius,
    y: local && projection.population.length > 1 ? local.y : 360 + Math.sin(angle) * radius * .72,
    pressure: local?.pressure ?? null,
    knowledge: local?.knowledge ?? null,
    contested: local?.contested ?? null,
    liveness: instance.liveness,
    tick: projection?.tick ?? null,
    schemaVersion: projection?.schemaVersion ?? null,
    physiology: projection?.physiology?.state ?? null,
    organismState: projection?.organismState ?? null,
    acclimation: projection?.details?.acclimation ?? null,
    attentionConcentration: projection?.attention?.concentration ?? null,
    activeSenses: projection?.sampling?.active ?? null,
    probingSenses: projection?.sampling?.probing ?? null,
    dormantSenses: projection?.sampling?.dormant ?? null,
  };
}

function rebuildFleetPopulation() {
  const now = Date.now();
  for (const [instanceId, record] of records) {
    if (!projections.has(instanceId)) continue;
    if (record.liveness === "expired" || (record.liveness === "stale" && now - record.livenessSince > STALE_RETENTION_MS)) {
      records.delete(instanceId); projections.delete(instanceId);
      sources.get(instanceId)?.close(); sources.delete(instanceId);
    }
  }
  const entries = [...records.entries()].filter(([id]) => projections.has(id));
  const fleetPopulation = entries.map(([id, record], index) => memberFromProjection(record, projections.get(id), index, entries.length));
  const ids = new Set(fleetPopulation.map(item => item.id));
  updateUiState({
    fleetPopulation,
    fleetRelationships: [],
    organismA: state.organismA && ids.has(state.organismA.id) ? state.organismA : null,
    organismB: state.organismB && ids.has(state.organismB.id) ? state.organismB : null,
  });
  renderFleetTable([...records.values()]);
  if (state.view === "population") {
    const ecologyCount = new Set(state.fleetPopulation.map(item => item.cluster)).size;
    const organismLabel = state.fleetPopulation.length === 1 ? "organism" : "organisms";
    const ecologyLabel = ecologyCount === 1 ? "ecology" : "ecologies";
    document.querySelector("#organism-state").textContent = `${state.fleetPopulation.length} ${organismLabel} · ${ecologyCount} ${ecologyLabel}`;
    renderPopulation(); renderPopulationInspector();
  }
}

function ingestFleetSnapshot(instanceId, rawSnapshot) {
  const projection = boundedSnapshot(normalizeSnapshot(rawSnapshot));
  if (!projection || !records.has(instanceId)) return;
  projections.set(instanceId, projection); rebuildFleetPopulation();
}

function openPopulationSource(instance) {
  if (sources.has(instance.instance_id)) return;
  const source = new EventSource(`/instance/${instance.instance_id}/stream`);
  source.onmessage = event => { const payload = JSON.parse(event.data); if (payload.snapshot) ingestFleetSnapshot(instance.instance_id, payload.snapshot); };
  source.onerror = () => { /* Fleet liveness remains authoritative. */ };
  sources.set(instance.instance_id, source);
}

function syncFleetPopulation(instances) {
  const now = Date.now(); const known = new Set(instances.map(instance => instance.instance_id));
  updateUiState({ fleetConnected: true, fleetInstances: instances });
  renderFleetTable(instances);
  instances.forEach(instance => {
    const previous = records.get(instance.instance_id);
    const livenessSince = previous?.liveness === instance.liveness ? previous.livenessSince : now;
    records.set(instance.instance_id, { ...instance, seenAt: now, livenessSince });
    if (instance.liveness === "alive") openPopulationSource(instance);
  });
  for (const [instanceId, source] of sources) if (!known.has(instanceId)) { source.close(); sources.delete(instanceId); }
  rebuildFleetPopulation();
}

export { ingestFleetSnapshot, rebuildFleetPopulation, syncFleetPopulation };
