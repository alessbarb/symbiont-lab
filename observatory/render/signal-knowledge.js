import { state } from "../state/store.js";

function renderSignalKnowledge(container) {
  container.replaceChildren();
  const profile = state.signalKnowledge.find(item => item.signalId === state.selectedSignalId);
  const title = document.createElement("h3");
  title.textContent = "Signal knowledge";
  container.append(title);
  if (!profile) {
    const message = document.createElement("p");
    message.textContent = "Symbiont todavía no ha reunido evidencia suficiente.";
    container.append(message);
    return;
  }
  const id = document.createElement("code"); id.textContent = profile.signalId; container.append(id);
  const meta = document.createElement("p");
  meta.textContent = `${profile.observedOpportunities} oportunidades · ${profile.validObservations} observaciones válidas · ${profile.age}`;
  container.append(meta);
  profile.claims.forEach(claim => {
    const item = document.createElement("p");
    item.textContent = `${claim.kind ?? "claim"}: ${claim.status ?? "insufficient"} · evidencia ${claim.evidenceCount ?? 0} · revisión ${claim.revision ?? 0}`;
    container.append(item);
  });
}

export { renderSignalKnowledge };
