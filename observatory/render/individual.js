import { state } from "../state/store.js";
import { renderOrganism } from "./organism.js";
import { renderSelf } from "./self.js";
import { renderCognitionGraph } from "./cognition-graph.js";

function renderIndividualPerspective() {
  if (state.view !== "individual") return;
  if (state.organismView === "cognition") { renderCognitionGraph(); return; }
  if (state.organismView === "self") renderSelf(); else renderOrganism();
}

export { renderIndividualPerspective };
