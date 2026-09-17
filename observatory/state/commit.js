import { state } from "./store.js";

// Single state transition for an accepted snapshot projection. Renderers never
// receive partial state: ingestion commits the complete projection first, then
// the application requests a render cycle.
function commitSnapshotProjection(projection) {
  state.tick = projection.tick;
  state.realTick = projection.tick;
  state.senses = projection.senses;
  state.beliefs = projection.beliefs;
  state.population = projection.population;
  state.relationships = projection.relationships;
  state.events = projection.events;
  state.signalKnowledge = projection.signalKnowledge;
  state.knowledgeEvents = projection.knowledgeEvents;
  state.details = projection.details;
  state.sensoryDevelopment = projection.sensoryDevelopment;
  state.sensoryRelations = projection.sensoryRelations;
  state.socialRelations = projection.socialRelations;
  state.socialResourceEvidence = projection.socialResourceEvidence;
  state.degradation = projection.degradation;
  state.physiology = projection.physiology;
  state.development = projection.development;
  state.attention = projection.attention;
  state.sampling = projection.sampling;
  state.schemaVersion = projection.schemaVersion;
  state.cognition = projection.cognition;
  state.culturalClaims = projection.culturalClaims ?? null;
  state.bodySchema = projection.bodySchema;
  state.selected = state.beliefs.find(item => item.id === state.selected?.id) ?? state.beliefs[0] ?? null;
  state.organismState = projection.organismState;

  if (Array.isArray(projection.events) && projection.events.length) {
    const seenEventKeys = new Set(state.liveEvents.map(e => `${e.tick}:${e.id}`));
    projection.events.forEach(event => {
      const key = `${projection.tick}:${event.id}`;
      if (seenEventKeys.has(key)) return;
      seenEventKeys.add(key);
      state.liveEvents.push({
        id: String(event.id), tick: projection.tick, type: event.type,
        label: event.label,
        explanation: event.explanation ?? "No additional explanation was included.",
        beliefId: event.belief_id ?? null, delta: Number(event.delta) || 0,
        chain: Array.isArray(event.causal_chain) ? event.causal_chain : [],
      });
    });
    if (state.liveEvents.length > 2048) state.liveEvents = state.liveEvents.slice(-2048);
  }

  if (Array.isArray(projection.sensoryDevelopment) && projection.sensoryDevelopment.length) {
    projection.sensoryDevelopment.forEach(item => {
      let history = state.senseHistory.get(item.name);
      if (!history) { history = []; state.senseHistory.set(item.name, history); }
      history.push(item.utility);
      if (history.length > 14) history.shift();
    });
  }
}

export { commitSnapshotProjection };
