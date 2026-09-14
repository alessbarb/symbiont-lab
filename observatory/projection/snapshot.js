import { state } from "../state/store.js";
import { renderSenses } from "../render/senses.js";
import { renderOrganism } from "../render/organism.js";
import { renderPopulation } from "../render/population.js";
import { renderInspector } from "../render/inspector.js";
import { renderTimeline } from "../render/timeline.js";
import { renderProfiles } from "../ui/profiles.js";
import { renderCognitionState } from "../render/cognition.js";

function boundedRatioOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(1, Math.max(0, number)) : null;
}

function normalizeSnapshot(raw) {
  if (!raw) return raw;
  if (raw.schema_version === 1) {
    return { ...raw, organism: { ...raw.organism, cognition: null } };
  }
  return raw; // v2 already carries organism.cognition
}

function boundedCognition(cognition) {
  if (!cognition || typeof cognition !== "object") return null;
  const readouts = {};
  Object.entries(cognition.readouts ?? {}).forEach(([id, value]) => { if (typeof id === "string" && Number.isFinite(Number(value))) readouts[id.slice(0, 128)] = Number(value); });
  const predictionErrors = {};
  Object.entries(cognition.prediction_errors ?? {}).forEach(([id, cls]) => { if (typeof id === "string" && typeof cls === "string") predictionErrors[id.slice(0, 128)] = cls; });
  const mutations = (Array.isArray(cognition.mutations) ? cognition.mutations : []).slice(0, 8).map(item => ({
    kind: typeof item?.kind === "string" ? item.kind : "unknown",
    nodeId: typeof item?.node_id === "string" ? item.node_id.slice(0, 128) : null,
    edgeId: typeof item?.edge_id === "string" ? item.edge_id.slice(0, 260) : null,
  }));
  const safety = cognition.safety_state ?? {};
  return {
    topologyRevision: Math.max(0, Number.parseInt(cognition.topology_revision, 10) || 0),
    readouts, predictionErrors, mutations,
    safetyState: { consecutiveFailures: Math.max(0, Number.parseInt(safety.consecutive_failures, 10) || 0), frozen: safety.frozen === true },
  };
}

function boundedSnapshot(snapshot) {
  if (!snapshot || ![1, 2].includes(snapshot.schema_version) || !Number.isInteger(snapshot.tick)) return null;
  const organism = snapshot.organism ?? {};
  const incomingSenses = Array.isArray(organism.percepts) ? organism.percepts.slice(0, 32) : [];
  const incomingBeliefs = Array.isArray(organism.beliefs) ? organism.beliefs.slice(0, 128) : [];
  const incomingMembers = Array.isArray(snapshot.population?.members) ? snapshot.population.members.slice(0, 500) : [];
  const incomingRelationships = Array.isArray(snapshot.population?.relationships) ? snapshot.population.relationships.slice(0, 1000) : [];
  const incomingEvents = Array.isArray(organism.events) ? organism.events.slice(0, 64) : [];
  const incomingSensoryDev = Array.isArray(organism.sensory_development) ? organism.sensory_development.slice(0, 64) : [];
  const incomingSensoryRel = Array.isArray(organism.sensory_relations) ? organism.sensory_relations.slice(0, 24) : [];
  return {
    tick: Math.max(0, snapshot.tick),
    displayId: typeof organism.display_id === "string" ? organism.display_id.slice(0, 48) : null,
    organismState: ["observing", "exploring", "reflecting", "resting", "unknown"].includes(organism.state) ? organism.state : "unknown",
    senses: incomingSenses.filter(item => item && typeof item.id === "string" && typeof item.label === "string").map((item, index) => ({
      id: item.id.slice(0, 64), name: item.label.slice(0, 80), icon: `S${index + 1}`,
      quality: Math.min(1, Math.max(0, Number(item.quality) || 0)), active: item.available === true,
    })),
    beliefs: incomingBeliefs.filter(item => item && typeof item.id === "string" && typeof item.label === "string").map((item, index) => {
      const angle = index * 2.399, radius = 48 + (index % 5) * 42;
      return {
        id: item.id.slice(0, 64), title: item.label.slice(0, 120),
        x: 450 + Math.cos(angle) * radius, y: 362 + Math.sin(angle) * radius * .82,
        r: 5 + (index % 4) * 2.5, certainty: Math.min(1, Math.max(0, Number(item.certainty) || 0)),
        evidence: Math.max(0, Number.parseInt(item.evidence_count, 10) || 0),
        revisions: Math.max(0, Number.parseInt(item.revision_count, 10) || 0), dissent: item.contested === true,
      };
    }),
    details:{ narrative:typeof organism.narrative==="string"?organism.narrative.slice(0,600):state.details.narrative, acclimation:Math.min(1,Math.max(0,Number(organism.acclimation)||0)), resourceBudget:{cpu:boundedRatioOrNull(organism.resource_budget?.cpu),memory:boundedRatioOrNull(organism.resource_budget?.memory),storage:boundedRatioOrNull(organism.resource_budget?.storage),ticksRemaining:Math.max(0,Number.parseInt(organism.resource_budget?.ticks_remaining,10)||0)}, memory:(Array.isArray(organism.memory)?organism.memory:[]).slice(0,32),openQuestions:(Array.isArray(organism.open_questions)?organism.open_questions:[]).slice(0,16),investigations:(Array.isArray(organism.investigations)?organism.investigations:[]).slice(0,16),regimeChanges:(Array.isArray(organism.regime_changes)?organism.regime_changes:[]).slice(0,16)}, population: incomingMembers.filter(item => item && typeof item.display_id === "string").map((item, index) => {
      const cluster = Math.min(7, Math.max(0, Number.parseInt(item.ecology, 10) || 0));
      const centers = [[280, 230], [610, 250], [470, 500], [300, 470], [640, 480], [440, 190], [210, 360], [690, 360]];
      const angle = index * 2.17, distance = 28 + (index % 5) * 18;
      return { id: item.display_id.slice(0, 48), cluster, x: centers[cluster][0] + Math.cos(angle) * distance, y: centers[cluster][1] + Math.sin(angle) * distance, pressure: Math.min(1, Math.max(0, Number(item.activity) || 0)), knowledge:Math.max(0,Number.parseInt(item.knowledge_count,10)||0), contested:Math.max(0,Number.parseInt(item.contested_count,10)||0) };
    }), relationships: incomingRelationships.filter(link=>link&&typeof link.source==="string"&&typeof link.target==="string"), events: incomingEvents,
    cognition: boundedCognition(organism.cognition),
    sensoryDevelopment: incomingSensoryDev.filter(item => item && typeof item.name === "string").map(item => ({
      name: item.name.slice(0, 64),
      samples: Math.max(0, Number.parseInt(item.samples, 10) || 0),
      availability: Math.min(1, Math.max(0, Number(item.availability) || 0)),
      utility: Math.min(1, Math.max(0, Number(item.utility) || 0)),
      tier: ["active", "probing", "dormant"].includes(item.tier) ? item.tier : "dormant",
    })),
    sensoryRelations: incomingSensoryRel.filter(item => item && typeof item.sense_a === "string" && typeof item.sense_b === "string").map(item => ({
      senseA: item.sense_a.slice(0, 64),
      senseB: item.sense_b.slice(0, 64),
      synchronous: item.synchronous === null || item.synchronous === undefined ? null : Math.min(1, Math.max(-1, Number(item.synchronous) || 0)),
      aToB: item.a_to_b === null || item.a_to_b === undefined ? null : Math.min(1, Math.max(-1, Number(item.a_to_b) || 0)),
      bToA: item.b_to_a === null || item.b_to_a === undefined ? null : Math.min(1, Math.max(-1, Number(item.b_to_a) || 0)),
      samples: Math.max(0, Number.parseInt(item.samples, 10) || 0),
    })),
    sampling: {
      active: Math.max(0, Number.parseInt(organism.sampling?.active, 10) || 0),
      probing: Math.max(0, Number.parseInt(organism.sampling?.probing, 10) || 0),
      dormant: Math.max(0, Number.parseInt(organism.sampling?.dormant, 10) || 0),
      unknown: Math.max(0, Number.parseInt(organism.sampling?.unknown, 10) || 0),
      sampledThisTick: Math.max(0, Number.parseInt(organism.sampling?.sampled_this_tick, 10) || 0),
      discovered: Math.max(0, Number.parseInt(organism.sampling?.discovered, 10) || 0),
    },
    schemaVersion: snapshot.schema_version ?? 1,
  };
}

function ingestSnapshot(snapshot, announce = true) {
  const projection = boundedSnapshot(normalizeSnapshot(snapshot));
  if (!projection) return;
  state.tick = projection.tick;
  // The demo/replay animation position (0-59) and the organism's own real
  // tick number are different things — state.tick above only drives
  // decorative animation indexing. state.realTick is what "Tick" actually
  // means once real data has arrived, and it is never touched by the
  // demo/replay animation timer (roadmap safety finding A08).
  state.realTick = projection.tick;
  state.senses = projection.senses;
  state.beliefs = projection.beliefs;
  state.population = projection.population;
  state.relationships = projection.relationships;
  state.events = projection.events;
  if (Array.isArray(projection.events) && projection.events.length) {
    const seenEventKeys = new Set(state.liveEvents.map(e => `${e.tick}:${e.id}`));
    projection.events.forEach(event => {
      const key = `${projection.tick}:${event.id}`;
      if (!seenEventKeys.has(key)) {
        seenEventKeys.add(key);
        state.liveEvents.push({
          id: String(event.id),
          tick: projection.tick,
          type: event.type,
          label: event.label,
          explanation: event.explanation ?? "No additional explanation was included.",
          beliefId: event.belief_id ?? null,
          delta: Number(event.delta) || 0,
          chain: Array.isArray(event.causal_chain) ? event.causal_chain : [],
        });
      }
    });
    if (state.liveEvents.length > 2048) {
      state.liveEvents = state.liveEvents.slice(-2048);
    }
  }
  state.details = projection.details;
  state.sensoryDevelopment = projection.sensoryDevelopment;
  if (Array.isArray(projection.sensoryDevelopment) && projection.sensoryDevelopment.length) {
    projection.sensoryDevelopment.forEach(item => {
      let hist = state.senseHistory.get(item.name);
      if (!hist) { hist = []; state.senseHistory.set(item.name, hist); }
      hist.push(item.utility);
      if (hist.length > 14) hist.shift();
    });
  }
  state.sensoryRelations = projection.sensoryRelations;
  state.sampling = projection.sampling;
  state.schemaVersion = projection.schemaVersion;
  // Re-resolve by id against the freshly-ingested beliefs array rather than
  // keeping the previous snapshot's object — that object's certainty/evidence
  // are now stale even when its id still exists in the new collection
  // (roadmap safety finding B07).
  state.selected = state.beliefs.find(item => item.id === state.selected?.id) ?? state.beliefs[0] ?? null;
  if (projection.displayId) { state.displayId = projection.displayId; document.querySelector("#organism-name").textContent = `Organism ${projection.displayId}`; }
  state.organismState = projection.organismState;
  document.querySelector("#organism-state").textContent = projection.organismState[0].toUpperCase() + projection.organismState.slice(1);
  if (announce) document.querySelector(".connection small").textContent = "snapshot stream";
  renderSenses(); renderOrganism(); renderPopulation("#population-mini", true); renderInspector(); renderTimeline(); renderProfiles();
  renderCognitionState(projection.cognition);
}

export { boundedRatioOrNull, normalizeSnapshot, boundedCognition, boundedSnapshot, ingestSnapshot };
