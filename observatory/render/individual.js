import { state } from "../state/store.js";
import { renderOrganism } from "./organism.js";
import { renderSelf } from "./self.js";
import { renderCognitionGraph } from "./cognition-graph.js";
import { renderRegimeCompass } from "./regime-compass.js";
import { renderSensoryMap } from "./sensory-map.js";

function renderIndividualPerspective() {
  if (state.view !== "individual") return;
  if (state.organismView === "cognition") { renderCognitionGraph(); return; }
  if (state.organismView === "sensory") { renderSensoryMap(); return; }
  if (state.organismView === "regimes") { renderRegimeCompass(); return; }
  if (state.organismView === "self") renderSelf(); else renderOrganism();
}

export { renderIndividualPerspective };
