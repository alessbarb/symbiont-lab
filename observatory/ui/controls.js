import { state } from "../state/store.js";
import { renderIndividualPerspective } from "../render/individual.js";
import { renderPopulation, renderPopulationInspector } from "../render/population.js";
import { renderInspector } from "../render/inspector.js";
import { renderTimeline, renderHistory } from "../render/timeline.js";
import { renderProfiles, renderAccessibleTable } from "./profiles.js";
import { toggleDrawer } from "./drawers.js";
import { showToast } from "./dialogs.js";
import { openReplayDialog, loadReplayFile, exportReplay } from "../transport/replay.js";
import { ingestSnapshot } from "../projection/snapshot.js";

function formatOrganismState() {
  const value = typeof state.organismState === "string" && state.organismState ? state.organismState : "unknown";
  return value[0].toUpperCase() + value.slice(1);
}

function formatPopulationState() {
  const members = Array.isArray(state.population) ? state.population : [];
  const ecologyCount = new Set(members.map(member => member.cluster).filter(cluster => Number.isInteger(cluster))).size;
  const organismLabel = members.length === 1 ? "organism" : "organisms";
  const ecologyLabel = ecologyCount === 1 ? "ecology" : "ecologies";
  return `${members.length} ${organismLabel} · ${ecologyCount} ${ecologyLabel}`;
}

function applyIndividualCanvasVisibility() {
  const isIndividual = state.view === "individual";
  const isPhenotype = isIndividual && state.organismView === "phenotype";
  const isSelf = isIndividual && state.organismView === "self";
  document.querySelector("#organism-canvas").classList.toggle("hidden", !isPhenotype);
  document.querySelector("#self-panel").classList.toggle("hidden", !isSelf);
  document.querySelector("#organism-view-toggle").classList.toggle("hidden", !isIndividual);
  document.querySelector(".canvas-legend").classList.toggle("hidden", !isPhenotype);
  document.querySelector(".canvas-heading").classList.toggle("hidden", isSelf);
}

function switchOrganismView(organismView) {
  state.organismView = organismView;
  document.querySelectorAll(".organism-view-option").forEach(b => {
    const active = b.dataset.organismView === organismView;
    b.classList.toggle("active", active);
    b.setAttribute("aria-pressed", String(active));
  });
  applyIndividualCanvasVisibility();
  renderIndividualPerspective();
  localStorage.setItem("symbiont-observatory-organism-view", organismView);
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".toggle").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  applyIndividualCanvasVisibility();
  document.querySelector("#population-canvas").classList.toggle("hidden", view !== "population");
  document.querySelector("#population-tools").classList.toggle("hidden", view !== "population");
  document.querySelector("#individual-inspector").hidden = view === "population"; document.querySelector("#population-inspector").hidden = view !== "population";
  document.querySelector("#organism-state").textContent = view === "individual" ? formatOrganismState() : formatPopulationState();
  if (view === "population") { renderPopulation(); renderPopulationInspector(); } else renderIndividualPerspective();
  localStorage.setItem("symbiont-observatory-view", view);
}

function advance(delta = 1) {
  if (state.replay.length) {
    state.replayIndex = (state.replayIndex + delta + state.replay.length) % state.replay.length;
    ingestSnapshot(state.replay[state.replayIndex], false);
    return;
  }
  state.tick = (state.tick + delta + 60) % 60;
  state.selected = state.beliefs.length ? state.beliefs[(state.tick + 12) % state.beliefs.length] : null;
  renderTimeline(); renderInspector(); renderIndividualPerspective();
}

document.querySelectorAll(".toggle").forEach(button => button.addEventListener("click", () => switchView(button.dataset.view)));
document.querySelectorAll(".organism-view-option").forEach(button => button.addEventListener("click", () => switchOrganismView(button.dataset.organismView)));
document.querySelectorAll(".mode").forEach(button => button.addEventListener("click", () => {
  if (button.dataset.mode === "live" && state.source === "replay") { showToast("Live input is not connected"); return; }
  state.mode = button.dataset.mode; document.querySelectorAll(".mode").forEach(b => b.classList.toggle("active", b === button));
}));
document.querySelector("#open-population").addEventListener("click", () => switchView("population"));
document.querySelector("#scrubber").addEventListener("input", event => { const value = Number(event.target.value); if (state.replay.length) state.replayIndex = value; else state.tick = value; state.mode = "replay"; document.querySelectorAll(".mode").forEach(b => b.classList.toggle("active", b.dataset.mode === "replay")); advance(0); });
document.querySelector("#previous").addEventListener("click", () => advance(-1));
document.querySelector("#next").addEventListener("click", () => advance(1));
document.querySelector("#play").addEventListener("click", event => { state.playing = !state.playing; event.currentTarget.classList.toggle("paused", !state.playing); event.currentTarget.setAttribute("aria-label", state.playing ? "Pause playback" : "Resume playback"); });

document.querySelector("#welcome-demo").addEventListener("click", () => { document.querySelector("#welcome").hidden = true; document.querySelector(".connection strong").textContent="Connected";document.querySelector(".connection small").textContent="demo stream";showToast("Demo stream started"); });
document.querySelector("#welcome-open").addEventListener("click", openReplayDialog);
document.querySelector("#import-replay").addEventListener("click", openReplayDialog);
document.querySelector("#replay-file").addEventListener("change", event => loadReplayFile(event.target.files?.[0]));
const dropZone = document.querySelector("#drop-zone");
dropZone.addEventListener("dragover", event => { event.preventDefault(); dropZone.classList.add("dragging"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", event => { event.preventDefault(); dropZone.classList.remove("dragging"); loadReplayFile(event.dataTransfer?.files?.[0]); });
document.querySelector("#privacy-audit").addEventListener("click", () => { const drawer = document.querySelector("#audit-drawer"); drawer.classList.add("open"); drawer.setAttribute("aria-hidden", "false"); document.querySelector("#close-audit").focus(); });
document.querySelector("#close-audit").addEventListener("click", () => { const drawer = document.querySelector("#audit-drawer"); drawer.classList.remove("open"); drawer.setAttribute("aria-hidden", "true"); });
document.querySelector("#export-replay").addEventListener("click", exportReplay);
document.querySelectorAll(".profile").forEach(button=>button.addEventListener("click",()=>{state.profile=button.dataset.profile;document.querySelectorAll(".profile").forEach(item=>item.classList.toggle("active",item===button));["summary","organism","research"].forEach(name=>document.querySelector(`#${name}-profile`).hidden=name!==state.profile);document.querySelector("#deep-inspector").hidden=state.profile!=="research";localStorage.setItem("symbiont-observatory-profile",state.profile);renderProfiles();}));
document.querySelector("#open-help").addEventListener("click",()=>toggleDrawer("#help-drawer",true));document.querySelector("#close-help").addEventListener("click",()=>toggleDrawer("#help-drawer",false));
document.querySelector("#open-accessible-table").addEventListener("click",()=>{renderAccessibleTable();document.querySelector("#accessible-dialog").showModal();});
document.querySelectorAll(".population-mode").forEach(button=>button.addEventListener("click",()=>{state.populationMode=button.dataset.populationMode;document.querySelectorAll(".population-mode").forEach(item=>item.classList.toggle("active",item===button));renderPopulation();}));
document.querySelector("#clear-comparison").addEventListener("click",()=>{state.organismA=null;state.organismB=null;renderPopulation();renderPopulationInspector();});
document.querySelectorAll(".inspector-tab").forEach(button => button.addEventListener("click", () => {
  const tab = button.dataset.tab;
  document.querySelectorAll(".inspector-tab").forEach(item => { item.classList.toggle("active", item === button); item.setAttribute("aria-selected", String(item === button)); });
  document.querySelector("#current-panel").hidden = tab !== "current";
  document.querySelector("#history-panel").hidden = tab !== "history";
  document.querySelector("#cognition-panel").hidden = tab !== "cognition";
  document.querySelector("#population-preview").hidden = tab !== "current";
  if (tab === "history") renderHistory();
}));
document.querySelector("#history-search").addEventListener("input", event => { state.query = event.target.value; document.querySelector('[data-tab="history"]').click(); });
document.querySelector("#mark-a").addEventListener("click", event => { if (!state.replay.length) { showToast("Load a replay to compare points"); return; } state.compareA = state.replayIndex; event.currentTarget.classList.add("set"); renderHistory(); showToast(`Point A set at ${state.compareA + 1}`); });
document.querySelector("#mark-b").addEventListener("click", event => { if (!state.replay.length) { showToast("Load a replay to compare points"); return; } state.compareB = state.replayIndex; event.currentTarget.classList.add("set"); renderHistory(); showToast(`Point B set at ${state.compareB + 1}`); });
document.addEventListener("keydown", event => {
  if (event.target instanceof HTMLInputElement || document.querySelector("#replay-dialog").open) return;
  if (event.key === " ") { event.preventDefault(); document.querySelector("#play").click(); }
  if (event.key === "ArrowLeft") advance(-1); if (event.key === "ArrowRight") advance(1);
  if (event.key.toLowerCase() === "o") openReplayDialog();
  if (event.key.toLowerCase() === "h") toggleDrawer("#help-drawer",!document.querySelector("#help-drawer").classList.contains("open"));
  if (["1","2","3"].includes(event.key)) document.querySelectorAll(".profile")[Number(event.key)-1].click();
  if (event.key === "Escape") document.querySelector("#close-audit").click();
});

export { switchView, advance };
