import { state } from "../state/store.js";
import { projectSelfSchema } from "../projection/self-schema.js";

function percent(value) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function metric(label, value) {
  const row = document.createElement("div");
  row.className = "self-metric";
  const name = document.createElement("span");
  const progress = document.createElement("progress");
  const amount = document.createElement("strong");
  name.textContent = label;
  progress.max = 1;
  progress.value = Math.max(0, Math.min(1, value));
  progress.setAttribute("aria-label", label);
  amount.textContent = percent(value);
  row.append(name, progress, amount);
  return row;
}

function renderSelf() {
  const panel = document.querySelector("#self-panel");
  const projection = projectSelfSchema(state.bodySchema);
  panel.replaceChildren();
  panel.style.overflowY = "auto";
  panel.style.paddingBottom = "60px";

  const heading = document.createElement("h2");
  const body = document.createElement("p");
  const scope = document.createElement("p");
  scope.className = "self-scope";

  if (projection.state === "undeveloped") {
    heading.textContent = "Body schema not yet developed";
    body.textContent = "This organism does not yet export a model of its own body. Once available, this view will show only what the organism itself believes about its parts and their relationships — never reconstructed from what Observatory can otherwise observe.";
    scope.textContent = "This central view contains only organism-owned self-knowledge. Surrounding Observatory panels remain external scientific instrumentation.";
    panel.append(heading, body, scope);
    return;
  }

  heading.textContent = "Self-known sensory body";
  body.textContent = `The organism currently represents ${projection.parts.length} sensory ${projection.parts.length === 1 ? "part" : "parts"} as belonging to itself. Names, host capabilities and Observatory topology are intentionally absent.`;
  scope.textContent = "Each card below is organism-owned self-knowledge. Geometry, topology and current percept labels are not used to fill gaps.";
  panel.append(heading, body, scope);

  const grid = document.createElement("div");
  grid.className = "self-parts";
  grid.setAttribute("role", "list");
  projection.parts.forEach((part, index) => {
    const card = document.createElement("article");
    card.className = "self-part";
    card.setAttribute("role", "listitem");
    card.setAttribute("aria-label", `Self-known sensory part ${index + 1}`);

    const head = document.createElement("div");
    head.className = "self-part-head";
    const title = document.createElement("h3");
    const id = document.createElement("code");
    title.textContent = `Sensory part ${index + 1}`;
    id.textContent = part.id;
    head.append(title, id);

    const metrics = document.createElement("div");
    metrics.className = "self-metrics";
    metrics.append(
      metric("Existence", part.existence),
      metric("Health", part.health),
      metric("Confidence", part.confidence),
      metric("Maturity", part.maturity),
    );

    const footer = document.createElement("div");
    footer.className = "self-part-footer";
    const recency = document.createElement("span");
    const cost = document.createElement("span");
    recency.textContent = `Recency · ${part.recency}`;
    cost.textContent = `Cost · ${percent(part.cost)}`;
    footer.append(recency, cost);

    card.append(head, metrics, footer);
    grid.append(card);
  });
  panel.append(grid);
}

export { renderSelf };
