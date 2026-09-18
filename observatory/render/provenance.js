import { state } from "../state/store.js";

function provenanceFor(signalId) {
  if (typeof signalId !== "string") return null;
  return (state.observerProvenance ?? []).find(item => item.signalId === signalId) ?? null;
}

function humanSignalLabel(signalId, fallback = null) {
  return provenanceFor(signalId)?.label ?? fallback ?? signalId ?? "Unknown signal";
}

function formatObserverValue(signalId) {
  const item = provenanceFor(signalId);
  if (!item || item.value == null) return "not sampled";
  const value = Math.abs(item.value) >= 1000
    ? item.value.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : item.value.toLocaleString(undefined, { maximumFractionDigits: 3 });
  return `${value}${item.unit ? " " + item.unit : ""}`;
}

function signalHistory(signalId) {
  return state.worldSignalHistory?.get(signalId) ?? [];
}

function sensorHistory(sensorId) {
  return state.sensorHistory?.get(sensorId) ?? [];
}

function signalKnowledge(signalId) {
  return (state.signalKnowledge ?? []).find(item => item.signalId === signalId) ?? null;
}

function knowledgeSummary(signalId) {
  const knowledge = signalKnowledge(signalId);
  if (!knowledge) return "no organism-authored profile yet";
  const supported = knowledge.claims?.filter(claim => claim.status === "supported").length ?? 0;
  return `${knowledge.validObservations} valid observations · ${supported} supported claim${supported === 1 ? "" : "s"}`;
}

export {
  provenanceFor,
  humanSignalLabel,
  formatObserverValue,
  signalHistory,
  sensorHistory,
  signalKnowledge,
  knowledgeSummary,
};
