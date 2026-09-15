import { state } from "../state/store.js";
import { ingestSnapshot } from "../projection/snapshot.js";
import { renderCognitionTopology } from "../render/cognition.js";
import { renderIndividualPerspective } from "../render/individual.js";
import { boundedTopology } from "../projection/topology.js";

let currentInstanceSource = null;
let currentInstanceId = null;
// Topology and snapshot arrive as two independent SSE messages, in either
// order. If topology(B) is what happens to arrive first after switching
// from instance A, resetting state.topology/state.cognition alone is not
// enough: state.senses/state.beliefs/etc. are still A's until B's own first
// snapshot lands, so re-rendering on that lone topology message would draw
// B's identity/boundary around A's percepts/beliefs -- exactly the
// cross-individual mixing the reset was supposed to prevent. Gate the
// topology-triggered render on this instance's own first snapshot having
// already arrived; ingestSnapshot's own renderIndividualPerspective() call (inside
// projection/snapshot.js, unrelated to this file) covers the snapshot-first
// case once the snapshot itself lands.
let currentInstanceHasSnapshot = false;

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) {
    currentInstanceSource.close();
  }
  currentInstanceId = instanceId;
  state.instanceId = instanceId;
  state.topology = null;
  state.cognition = null;
  currentInstanceHasSnapshot = false;
  const source = new EventSource(`/instance/${instanceId}/stream`);
  currentInstanceSource = source;
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.topology) {
      renderCognitionTopology(payload.topology);
      state.topology = boundedTopology(payload.topology);
      if (currentInstanceHasSnapshot) renderIndividualPerspective();
      return;
    }
    if (payload.snapshot) {
      state.source = "local server";
      document.querySelector("#welcome").hidden = true;
      document.querySelector(".connection strong").textContent = "Connected";
      currentInstanceHasSnapshot = true;
      ingestSnapshot(payload.snapshot);
    }
  };
}

export { currentInstanceSource, currentInstanceId, connectInstance };
