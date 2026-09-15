import { state } from "./state/store.js";
import { renderSenses } from "./render/senses.js";
import { renderIndividualPerspective } from "./render/individual.js";
import { renderPopulation } from "./render/population.js";
import { renderInspector } from "./render/inspector.js";
import { renderTimeline, renderHistory } from "./render/timeline.js";
import { renderProfiles } from "./ui/profiles.js";
import { switchView, advance } from "./ui/controls.js";
import { connectFleet } from "./transport/fleet-stream.js";
import { ingestSnapshot } from "./projection/snapshot.js";

window.addEventListener("message", event => {
  if (event.data?.type !== "symbiont-observatory-snapshot") return;
  if (event.origin !== window.location.origin) return;
  state.source="same-origin message";document.querySelector(".connection strong").textContent="Connected";document.querySelector("#welcome").hidden=true;ingestSnapshot(event.data.snapshot);
});

renderSenses(); renderIndividualPerspective(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderHistory(); renderProfiles();
connectFleet();
const storedView = localStorage.getItem("symbiont-observatory-view"); if (["individual", "population"].includes(storedView)) switchView(storedView);
const storedOrganismView = localStorage.getItem("symbiont-observatory-organism-view");
if (["phenotype", "self"].includes(storedOrganismView)) document.querySelector(`[data-organism-view="${storedOrganismView}"]`).click();
const storedProfile=localStorage.getItem("symbiont-observatory-profile");if(["summary","organism","research"].includes(storedProfile))document.querySelector(`[data-profile="${storedProfile}"]`).click();
if ("BroadcastChannel" in window) { const channel=new BroadcastChannel("symbiont-observatory-v1");channel.addEventListener("message",event=>{if(event.data?.type==="symbiont-observatory-snapshot"){state.source="local channel";document.querySelector("#welcome").hidden=true;document.querySelector(".connection strong").textContent="Connected";ingestSnapshot(event.data.snapshot);}}); }
// The "live" branch here only animates the bundled demo data (state.source
// stays "demo" until a real snapshot is ever ingested). Once a real
// same-origin/BroadcastChannel snapshot arrives, this timer must never
// again mutate state.tick on its own — only a new incoming snapshot may —
// or the visible/exported tick silently drifts away from what the runtime
// actually reported (roadmap safety finding A08).
setInterval(() => { if (state.playing && ((state.mode === "live" && state.source === "demo") || state.replay.length)) advance(1); }, 1800);
