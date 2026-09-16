import { state } from "../state/store.js";
import { ingestSnapshot } from "../projection/snapshot.js";
import { renderCognitionTopology } from "../render/cognition.js";
import { renderIndividualPerspective } from "../render/individual.js";
import { boundedTopology } from "../projection/topology.js";
import { renderSnapshotCycle } from "../ui/render-cycle.js";
import { updateUiState, resetInstanceProjection } from "../state/transition.js";
import { updateTelemetry } from "../ui/observability.js";

let currentInstanceSource = null;
let currentInstanceId = null;
// Topology and snapshot arrive as two independent SSE messages, in either
// order. If topology(B) is what happens to arrive first after switching
// from instance A, resetting structural/self state alone is not enough:
// state.senses/state.beliefs/etc. are still A's until B's own first snapshot
// lands. Gate the topology-triggered render on this instance's own first
// snapshot so no visual composition can mix two individuals.
let currentInstanceHasSnapshot = false;
let connectionGeneration = 0;

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) {
    currentInstanceSource.close();
  }
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
    const payload = JSON.parse(event.data);
    if (payload.run_id || payload.sequence != null) updateUiState({ sequence: payload.sequence ?? null, runId: payload.run_id ?? null });
    if (payload.topology) {
      renderCognitionTopology(payload.topology);
      updateUiState({ topology: boundedTopology(payload.topology) });
      if (currentInstanceHasSnapshot) renderIndividualPerspective();
      return;
    }
    if (payload.snapshot) {
      updateUiState({ source: "local server" });
      updateTelemetry({ source: "local server", sequence: payload.sequence, tick: payload.snapshot?.tick, connection: "local SSE", connectionLabel: "Connected" });
      document.querySelector("#welcome").hidden = true;
      document.querySelector(".connection strong").textContent = "Connected";
      currentInstanceHasSnapshot = true;
      const projection = ingestSnapshot(payload.snapshot);
      if (projection) renderSnapshotCycle(projection.cognition);
    }
  };
}

export { currentInstanceSource, currentInstanceId, connectInstance };
