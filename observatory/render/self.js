import { state } from "../state/store.js";
import { projectSelfSchema } from "../projection/self-schema.js";

function percent(value) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function metric(label, value) {
  const row = document.createElement("div");
  row.className = "self-metric";
  row.style.display = "grid";
  row.style.gridTemplateColumns = "74px minmax(90px, 1fr) 40px";
  row.style.alignItems = "center";
  row.style.gap = "8px";
  row.style.fontSize = "10px";
  const name = document.createElement("span");
  const progress = document.createElement("progress");
  const amount = document.createElement("strong");
  name.textContent = label;
  progress.max = 1;
  progress.value = Math.max(0, Math.min(1, value));
  progress.setAttribute("aria-label", label);
  progress.style.width = "100%";
  progress.style.accentColor = "var(--cyan)";
  amount.textContent = percent(value);
  amount.style.textAlign = "right";
  row.append(name, progress, amount);
  return row;
}

function sectionHeading(text) {
  const heading = document.createElement("h3");
  heading.textContent = text;
  heading.style.margin = "26px 0 10px";
  heading.style.fontSize = "13px";
  heading.style.fontWeight = "560";
  heading.style.color = "var(--text)";
  return heading;
}

function cardShell(label) {
  const card = document.createElement("article");
  card.className = "self-part";
  card.setAttribute("role", "listitem");
  card.setAttribute("aria-label", label);
  card.style.border = "1px solid var(--line)";
  card.style.borderRadius = "10px";
  card.style.padding = "14px";
  card.style.background = "rgba(8, 26, 42, .72)";
  return card;
}

function partHead(titleText, idText) {
  const head = document.createElement("div");
  head.className = "self-part-head";
  head.style.display = "grid";
  head.style.gap = "4px";
  const title = document.createElement("h4");
  const id = document.createElement("code");
  title.textContent = titleText;
  title.style.margin = "0";
  title.style.fontSize = "12px";
  title.style.fontWeight = "560";
  id.textContent = idText;
  id.style.fontSize = "9px";
  id.style.color = "var(--muted)";
  id.style.overflowWrap = "anywhere";
  head.append(title, id);
  return head;
}

function metricsBlock(...rows) {
  const metrics = document.createElement("div");
  metrics.className = "self-metrics";
  metrics.style.display = "grid";
  metrics.style.gap = "7px";
  metrics.style.marginTop = "12px";
  metrics.append(...rows);
  return metrics;
}

function footer(...labels) {
  const node = document.createElement("div");
  node.className = "self-part-footer";
  node.style.display = "flex";
  node.style.justifyContent = "space-between";
  node.style.gap = "12px";
  node.style.marginTop = "12px";
  node.style.color = "var(--muted)";
  node.style.fontSize = "10px";
  labels.forEach(label => {
    const span = document.createElement("span");
    span.textContent = label;
    node.append(span);
  });
  return node;
}

function cardGrid() {
  const grid = document.createElement("div");
  grid.className = "self-parts";
  grid.setAttribute("role", "list");
  grid.style.display = "grid";
  grid.style.gridTemplateColumns = "repeat(auto-fit, minmax(260px, 1fr))";
  grid.style.gap = "12px";
  grid.style.maxWidth = "960px";
  return grid;
}

function renderSensoryParts(panel, parts) {
  panel.append(sectionHeading(`Sensory parts · ${parts.length}`));
  if (!parts.length) {
    const empty = document.createElement("p");
    empty.textContent = "No sensory parts are currently represented in the organism-owned body schema.";
    panel.append(empty);
    return;
  }
  const grid = cardGrid();
  parts.forEach((part, index) => {
    const card = cardShell(`Self-known sensory part ${index + 1}`);
    card.append(
      partHead(`Sensory part ${index + 1}`, part.id),
      metricsBlock(
        metric("Existence", part.existence),
        metric("Health", part.health),
        metric("Confidence", part.confidence),
        metric("Maturity", part.maturity),
      ),
      footer(`Recency · ${part.recency}`, `Cost · ${percent(part.cost)}`),
    );
    grid.append(card);
  });
  panel.append(grid);
}

function renderCognitiveRegions(panel, regions, labels) {
  panel.append(sectionHeading(`Cognitive regions · ${regions.length}`));
  if (!regions.length) {
    const empty = document.createElement("p");
    empty.textContent = "No cognitive regions have accumulated enough internal evidence to become part of Self yet.";
    panel.append(empty);
    return;
  }
  const grid = cardGrid();
  regions.forEach((region, index) => {
    const label = `Cognitive region ${index + 1}`;
    labels.set(region.id, label);
    const card = cardShell(`Self-known ${label.toLowerCase()}`);
    card.append(
      partHead(label, region.id),
      metricsBlock(
        metric("Existence", region.existence),
        metric("Confidence", region.confidence),
        metric("Activity", region.activity),
        metric("Maturity", region.maturity),
      ),
      footer(`Recency · ${region.recency}`, "Learned internal region"),
    );
    grid.append(card);
  });
  panel.append(grid);
}

function relationLabel(relation) {
  return relation === "co_acts_with" ? "co-acts with" : "precedes";
}

function renderDependencies(panel, dependencies, labels) {
  panel.append(sectionHeading(`Functional dependencies · ${dependencies.length}`));
  if (!dependencies.length) {
    const empty = document.createElement("p");
    empty.textContent = "No functional relationship has accumulated enough support and confidence to enter Self yet.";
    panel.append(empty);
    return;
  }

  const list = document.createElement("div");
  list.className = "self-dependencies";
  list.setAttribute("role", "list");
  list.style.display = "grid";
  list.style.gap = "8px";
  list.style.maxWidth = "960px";
  dependencies.forEach(dependency => {
    const source = labels.get(dependency.sourceId) ?? "Unknown cognitive region";
    const target = labels.get(dependency.targetId) ?? "Unknown cognitive region";
    const row = document.createElement("article");
    row.setAttribute("role", "listitem");
    row.style.display = "grid";
    row.style.gridTemplateColumns = "minmax(220px, 1fr) minmax(180px, .8fr)";
    row.style.gap = "18px";
    row.style.alignItems = "center";
    row.style.border = "1px solid var(--line)";
    row.style.borderRadius = "9px";
    row.style.padding = "11px 13px";
    row.style.background = "rgba(8, 26, 42, .54)";

    const description = document.createElement("div");
    description.style.fontSize = "11px";
    const strong = document.createElement("strong");
    strong.textContent = `${source} ${relationLabel(dependency.relation)} ${target}`;
    const note = document.createElement("small");
    note.textContent = "Organism-inferred relationship; not an Observatory topology edge.";
    note.style.display = "block";
    note.style.marginTop = "4px";
    note.style.color = "var(--muted)";
    description.append(strong, note);

    const measures = document.createElement("div");
    measures.style.display = "grid";
    measures.style.gap = "5px";
    measures.append(
      metric("Confidence", dependency.confidence),
      metric("Support", dependency.support),
    );
    row.append(description, measures);
    list.append(row);
  });
  panel.append(list);
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

  const sensoryParts = projection.parts.filter(part => part.kind === "sense");
  const cognitiveRegions = projection.parts.filter(part => part.kind === "cognitive_region");
  heading.textContent = "Self-known functional body";
  body.textContent = `The organism currently represents ${sensoryParts.length} sensory ${sensoryParts.length === 1 ? "part" : "parts"} and ${cognitiveRegions.length} learned cognitive ${cognitiveRegions.length === 1 ? "region" : "regions"} as belonging to itself.`;
  scope.textContent = "Only organism-owned BodySchema evidence appears here. Region numbers and layout are Observatory presentation labels; topology, current percept labels and graph edges are never used to fill gaps.";
  panel.append(heading, body, scope);

  const regionLabels = new Map();
  renderSensoryParts(panel, sensoryParts);
  renderCognitiveRegions(panel, cognitiveRegions, regionLabels);
  renderDependencies(panel, projection.dependencies, regionLabels);
}

export { renderSelf };
