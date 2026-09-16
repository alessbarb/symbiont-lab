import { currentInstanceId, connectInstance } from "./instance-stream.js";
import { syncFleetPopulation } from "./fleet-population.js";

function renderFleet(instances) {
  const list = document.querySelector("#fleet-list");
  if (!list) return;
  list.replaceChildren();
  const alive = instances.filter(i => i.liveness === "alive");
  instances.forEach(instance => {
    const row = document.createElement("button");
    row.className = `fleet-row fleet-${instance.liveness}${instance.instance_id === currentInstanceId ? " active" : ""}`;
    row.textContent = `${instance.display_id ?? instance.instance_id} (${instance.liveness})`;
    row.addEventListener("click", () => connectInstance(instance.instance_id));
    list.append(row);
  });
  if (!currentInstanceId && alive.length > 0 && !document.querySelector("#welcome").hidden) {
    connectInstance(alive[0].instance_id);
  }
}

function connectFleet() {
  if (!("EventSource" in window)) return;
  const source = new EventSource("/fleet");
  source.onmessage = event => {
    const payload = JSON.parse(event.data);
    const instances = Array.isArray(payload.instances) ? payload.instances : [];
    renderFleet(instances);
    syncFleetPopulation(instances);
  };
  source.onerror = () => { /* passive: no local server running is a normal, silent state */ };
}

export { renderFleet, connectFleet };
