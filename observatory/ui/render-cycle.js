// Browser render orchestration lives outside the snapshot projection. The
// projection normalizes data; this module is the only bridge that asks views
// to repaint after state has been committed.
import { renderSenses } from "../render/senses.js";
import { renderIndividualPerspective } from "../render/individual.js";
import { renderPopulation } from "../render/population.js";
import { renderInspector } from "../render/inspector.js";
import { renderTimeline } from "../render/timeline.js";
import { renderProfiles } from "./profiles.js";
import { renderCognitionState } from "../render/cognition.js";

function renderSnapshotCycle(cognition) {
  renderSenses();
  renderIndividualPerspective();
  renderPopulation("#population-mini", true);
  renderInspector();
  renderTimeline();
  renderProfiles();
  renderCognitionState(cognition);
}

export { renderSnapshotCycle };
