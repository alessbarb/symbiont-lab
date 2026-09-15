import { projectSelfSchema } from "../projection/self-schema.js";

function renderSelf() {
  const panel = document.querySelector("#self-panel");
  const projection = projectSelfSchema(null);
  panel.replaceChildren();
  const heading = document.createElement("h2");
  const body = document.createElement("p");
  const scope = document.createElement("p");
  if (projection.state === "undeveloped") {
    heading.textContent = "Body schema not yet developed";
    body.textContent = "This organism does not yet export a model of its own body. Once available, this view will show only what the organism itself believes about its parts and their relationships — never reconstructed from what Observatory can otherwise observe.";
    scope.textContent = "This central view contains only organism-owned self-knowledge. Surrounding Observatory panels remain external scientific instrumentation.";
  }
  panel.append(heading, body, scope);
}

export { renderSelf };
