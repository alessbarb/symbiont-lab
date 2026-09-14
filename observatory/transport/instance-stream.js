import { state } from "../state/store.js";
import { ingestSnapshot } from "../projection/snapshot.js";
import { renderCognitionTopology } from "../render/cognition.js";

let currentInstanceSource = null;
let currentInstanceId = null;

function connectInstance(instanceId) {
  if (currentInstanceId === instanceId && currentInstanceSource) return;
  if (currentInstanceSource) {
    currentInstanceSource.close();
  }
  currentInstanceId = instanceId;
  const source = new EventSource(`/instance/${instanceId}/stream`);
  currentInstanceSource = source;
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    if (payload.topology) { renderCognitionTopology(payload.topology); return; }
    if (payload.snapshot) { state.source = "local server"; document.querySelector("#welcome").hidden = true; document.querySelector(".connection strong").textContent = "Connected"; ingestSnapshot(payload.snapshot); }
  };
}

export { currentInstanceSource, currentInstanceId, connectInstance };
