import { state } from "../state/store.js";
import { ingestSnapshot } from "../projection/snapshot.js";
import { renderCognitionTopology } from "../render/cognition.js";
import { renderIndividualPerspective } from "../render/individual.js";
import { boundedTopology } from "../projection/topology.js";
import { renderSnapshotCycle } from "../ui/render-cycle.js";
import { updateUiState, resetInstanceProjection } from "../state/transition.js";
import { recordAcceptedSnapshot, recordRejectedSnapshot, updateTelemetry } from "../ui/observability.js";

let currentInstanceSource = null;
let currentInstanceId = null;
// Topology and snapshot arrive as two independent SSE messages, in either
// order. If topology(B) is what happens to arrive first after switching
// from instance A, resetting structural/self state alone is not enough:
// state.senses/state.beliefs/etc. are still A's until B's own first valid
// snapshot lands. Gate topology-triggered rendering on that valid snapshot.
let currentInstanceHasSnapshot = false;
let connectionGeneration = 0;

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) currentInstanceSource.close();
  currentInstanceId = instanceId;
  const generation = ++connectionGeneration;
  updateUiState({ instanceId });
  resetInstanceProjection();
  currentInstanceHasSnapshot = false;
  updateTelemetry({ source: "local server", connection: "connecting", connectionLabel: "Connecting" });
  const source = new EventSource(`/instance/${instanceId}/stream`);
  currentInstanceSource = source;
  source.onmessage = event => {
    if (generation !== connectionGeneration) return;
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      recordRejectedSnapshot("Malformed local SSE event was ignored.");
      return;
    }
    if (payload.run_id || payload.sequence != null) updateUiState({ sequence: payload.sequence ?? null, runId: payload.run_id ?? null });
    if (payload.topology) {
      const topology = boundedTopology(payload.topology);
      if (!topology) { recordRejectedSnapshot("Topology payload did not match the bounded Observatory contract."); return; }
      renderCognitionTopology(payload.topology);
      updateUiState({ topology });
      updateTelemetry({ source: "local server" });
      if (currentInstanceHasSnapshot) renderIndividualPerspective();
      return;
    }
    if (payload.snapshot) {
      updateUiState({ source: "local server" });
      // Keep the pre-ingest assignment for the cross-instance ordering invariant,
      // but revoke it immediately if bounded projection rejects the snapshot.
      currentInstanceHasSnapshot = true;
      const projection = ingestSnapshot(payload.snapshot);
      if (!projection) {
        currentInstanceHasSnapshot = false;
        recordRejectedSnapshot("Snapshot payload did not match a supported Observatory schema.");
        return;
      }
      recordAcceptedSnapshot();
      document.querySelector("#welcome").hidden = true;
      renderSnapshotCycle(projection.cognition);
      updateTelemetry({ source: "local server", sequence: payload.sequence, tick: projection.tick, connection: "local SSE", connectionLabel: "Connected" });
    }
  };
  source.onerror = () => updateTelemetry({ source: "local server", connection: "reconnecting", connectionLabel: "Reconnecting" });
}

function reconnectCurrentInstance() {
  if (!currentInstanceId) return false;
  currentInstanceSource?.close();
  currentInstanceSource = null;
  connectInstance(currentInstanceId);
  return true;
}

export { currentInstanceSource, currentInstanceId, connectInstance, reconnectCurrentInstance };
