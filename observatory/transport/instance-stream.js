import { state } from "../state/store.js";
import { ingestSnapshot } from "../projection/snapshot.js";
import { renderCognitionTopology } from "../render/cognition.js";
import { renderIndividualPerspective } from "../render/individual.js";
import { boundedTopology } from "../projection/topology.js";
import { renderSnapshotCycle } from "../ui/render-cycle.js";
import { updateUiState, resetInstanceProjection } from "../state/transition.js";

let currentInstanceSource = null;
let currentInstanceId = null;
// Topology and snapshot arrive as two independent SSE messages, in either
// order. If topology(B) is what happens to arrive first after switching
// from instance A, resetting structural/self state alone is not enough:
// state.senses/state.beliefs/etc. are still A's until B's own first snapshot
// lands. Gate the topology-triggered render on this instance's own first
// snapshot so no visual composition can mix two individuals.
let currentInstanceHasSnapshot = false;

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) {
    currentInstanceSource.close();
  }
  currentInstanceId = instanceId;
  updateUiState({ instanceId });
  resetInstanceProjection();
  currentInstanceHasSnapshot = false;
  const source = new EventSource(`/instance/${instanceId}/stream`);
  currentInstanceSource = source;
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.topology) {
      renderCognitionTopology(payload.topology);
      updateUiState({ topology: boundedTopology(payload.topology) });
      if (currentInstanceHasSnapshot) renderIndividualPerspective();
      return;
    }
    if (payload.snapshot) {
      updateUiState({ source: "local server" });
      document.querySelector("#welcome").hidden = true;
      document.querySelector(".connection strong").textContent = "Connected";
      currentInstanceHasSnapshot = true;
      const projection = ingestSnapshot(payload.snapshot);
      if (projection) renderSnapshotCycle(projection.cognition);
    }
  };
}

export { currentInstanceSource, currentInstanceId, connectInstance };
