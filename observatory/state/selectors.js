import { state } from "./store.js";
import { demoEvents } from "./demo-state.js";

function availableEvents() {
  const source = state.replay.length
    ? state.replay.flatMap((snapshot, snapshotIndex) => (snapshot.organism?.events ?? []).map(event => ({
        id: String(event.id), type: event.type, label: event.label, explanation: event.explanation ?? "No additional explanation was included.",
        beliefId: event.belief_id ?? null, delta: Number(event.delta) || 0, tick: snapshot.tick, replayIndex: snapshotIndex,
        chain: Array.isArray(event.causal_chain) ? event.causal_chain : [],
      })))
    : (state.source !== "demo" ? state.liveEvents : demoEvents);
  const query = state.query.trim().toLowerCase();
  return source.filter(event => (state.eventFilter === "all" || event.type === state.eventFilter) && (!query || `${event.label} ${event.explanation}`.toLowerCase().includes(query)));
}

function comparisonFor(event) {
  if (!state.replay.length || state.compareA === null || state.compareB === null || !event?.beliefId) return null;
  const find = index => state.replay[index]?.organism?.beliefs?.find(item => item.id === event.beliefId);
  const earlier = find(Math.min(state.compareA, state.compareB)), now = find(Math.max(state.compareA, state.compareB));
  return earlier && now ? { earlier, now } : null;
}

export { availableEvents, comparisonFor };
