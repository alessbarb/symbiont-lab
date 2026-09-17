import { state } from "../state/store.js";
import { commitSnapshotProjection } from "../state/commit.js";
import { boundedBodySchema } from "./body-schema.js";

function boundedRatioOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(1, Math.max(0, number)) : null;
}

function normalizeSnapshot(raw) {
  if (!raw) return raw;
  const organism = raw.organism ?? {};
  // Social reciprocal_observations was added without a reader migration.
  // Absence means "not measured", never zero; normalize old records into the
  // current in-memory shape while leaving the versioned envelope intact.
  const socialRelations = Array.isArray(organism.social_relations)
    ? organism.social_relations.map(item => (
      item && typeof item === "object" && !Object.prototype.hasOwnProperty.call(item, "reciprocal_observations")
        ? { ...item, reciprocal_observations: null }
        : item
    ))
    : organism.social_relations;
  const migratedOrganism = { ...organism, social_relations: socialRelations };
  if (raw.schema_version === 1) {
    return {
      ...raw,
      organism: {
        ...migratedOrganism,
        cognition: organism.cognition ?? null,
        body_schema: organism.body_schema ?? null,
      },
    };
  }
  if (raw.schema_version === 2) {
    return {
      ...raw,
      organism: {
        ...migratedOrganism,
        body_schema: organism.body_schema ?? null,
      },
    };
  }
  return { ...raw, organism: migratedOrganism }; // v3 carries body_schema; cognition remains optional.
}

function boundedCognition(cognition) {
  if (!cognition || typeof cognition !== "object") return null;
  const readouts = {};
  Object.entries(cognition.readouts ?? {}).forEach(([id, value]) => {
    if (typeof id === "string" && Number.isFinite(Number(value))) readouts[id.slice(0, 128)] = Number(value);
  });
  const predictionErrors = {};
  Object.entries(cognition.prediction_errors ?? {}).forEach(([id, cls]) => {
    if (typeof id === "string" && typeof cls === "string") predictionErrors[id.slice(0, 128)] = cls;
  });
  const mutations = (Array.isArray(cognition.mutations) ? cognition.mutations : []).slice(0, 8).map(item => ({
    kind: typeof item?.kind === "string" ? item.kind : "unknown",
    nodeId: typeof item?.node_id === "string" ? item.node_id.slice(0, 128) : null,
    edgeId: typeof item?.edge_id === "string" ? item.edge_id.slice(0, 260) : null,
  }));
  const safety = cognition.safety_state ?? {};
  const allowedHealth = ["germinal", "developing", "connected", "adaptive", "degenerate", "recovering"];
  const topologyHealth = allowedHealth.includes(cognition.topology_health) ? cognition.topology_health : "germinal";
  return {
    topologyRevision: Math.max(0, Number.parseInt(cognition.topology_revision, 10) || 0),
    topologyHealth,
    recovering: cognition.recovering === true,
    readouts,
    predictionErrors,
    mutations,
    safetyState: {
      consecutiveFailures: Math.max(0, Number.parseInt(safety.consecutive_failures, 10) || 0),
      frozen: safety.frozen === true,
    },
  };
}

function boundedSocialRelations(relations) {
  if (!Array.isArray(relations)) return [];
  return relations.slice(0, 128).filter(item => item && typeof item.source === "string" && typeof item.target === "string").map(item => ({
    source: item.source.slice(0, 128),
    target: item.target.slice(0, 128),
    channel: typeof item.channel === "string" ? item.channel.slice(0, 64) : "default",
    valence: ["positive", "negative", "unknown"].includes(item.valence) ? item.valence : "unknown",
    observations: Math.max(0, Number.parseInt(item.observations, 10) || 0),
    reciprocalObservations: item.reciprocal_observations == null ? null : Math.max(0, Number.parseInt(item.reciprocal_observations, 10) || 0),
    conflicts: Math.max(0, Number.parseInt(item.conflicts, 10) || 0),
    rejections: Math.max(0, Number.parseInt(item.rejections, 10) || 0),
    support: Math.max(0, Math.min(1000000, Number(item.support) || 0)),
    harm: Math.max(0, Math.min(1000000, Number(item.harm) || 0)),
    freshness: item.freshness == null ? null : Math.min(1, Math.max(0, Number(item.freshness) || 0)),
    reliability: item.reliability == null ? null : Math.min(1, Math.max(0, Number(item.reliability) || 0)),
    lastTick: item.last_tick == null ? null : Math.max(0, Number.parseInt(item.last_tick, 10) || 0),
  }));
}

function boundedSocialResourceEvidence(evidence) {
  if (!Array.isArray(evidence)) return [];
  return evidence.slice(0, 64).filter(item => item && typeof item.token === "string").map(item => ({
    token: item.token.slice(0, 64),
    requested: Math.max(0, Math.min(1000000, Number(item.requested) || 0)),
    granted: Math.min(Math.max(0, Number(item.requested) || 0), Math.max(0, Math.min(1000000, Number(item.granted) || 0))),
    availability: Math.min(1, Math.max(0, Number(item.availability) || 0)),
    observations: Math.max(0, Number.parseInt(item.observations, 10) || 0),
    denied: Math.max(0, Number.parseInt(item.denied, 10) || 0),
    freshness: item.freshness == null ? null : Math.min(1, Math.max(0, Number(item.freshness) || 0)),
    lastTick: item.last_tick == null ? null : Math.max(0, Number.parseInt(item.last_tick, 10) || 0),
  }));
}

function boundedDegradation(degradation) {
  if (!degradation || typeof degradation !== "object") return { retainedItems: 0, excretedUnits: 0 };
  return {
    retainedItems: Math.min(256, Math.max(0, Number.parseInt(degradation.retained_items, 10) || 0)),
    excretedUnits: Math.min(256, Math.max(0, Number.parseInt(degradation.excreted_units, 10) || 0)),
  };
}

function boundedPhysiology(physiology) {
  if (!physiology || typeof physiology !== "object") return null;
  const states = ["active", "stressed", "dormant", "agonizing", "dead", "unknown"];
  return {
    state: states.includes(physiology.state) ? physiology.state : "unknown",
    transitions: Math.max(0, Number.parseInt(physiology.transitions, 10) || 0),
    deathTick: physiology.death_tick == null ? null : Math.max(0, Number.parseInt(physiology.death_tick, 10) || 0),
    restingRequested: physiology.resting_requested === true,
  };
}

function boundedDevelopment(development) {
  if (!development || typeof development !== "object") return null;
  const phases = ["germinal", "developing", "juvenile", "mature", "declining", "terminal", "dead", "unknown"];
  const counter = name => Math.min(1000000, Math.max(0, Number.parseInt(development[name], 10) || 0));
  const ratio = name => Math.min(1, Math.max(0, Number(development[name]) || 0));
  return {
    phase: phases.includes(development.phase) ? development.phase : "unknown",
    tick: counter("tick"),
    stressTicks: counter("stress_ticks"),
    recoveryEvents: counter("recovery_events"),
    repairEvents: counter("repair_events"),
    excretionEvents: counter("excretion_events"),
    maintenanceBurden: ratio("maintenance_burden"),
    senescenceIndex: ratio("senescence_index"),
    actionAttempts: counter("action_attempts"),
    sensoryCount: Math.min(256, counter("sensory_count")),
    topologyHealth: typeof development.topology_health === "string" ? development.topology_health.slice(0, 64) : "unknown",
  };
}

function boundedAttention(attention) {
  if (!attention || typeof attention !== "object") return null;
  return {
    concentration: Math.min(1, Math.max(0, Number(attention.concentration) || 0)),
    entropy: Math.min(1, Math.max(0, Number(attention.entropy) || 0)),
  };
}

function boundedSnapshot(snapshot) {
  if (!snapshot || ![1, 2, 3].includes(snapshot.schema_version) || !Number.isInteger(snapshot.tick)) return null;
  const organism = snapshot.organism ?? {};
  const cognition = boundedCognition(organism.cognition);
  const bodySchema = boundedBodySchema(organism.body_schema);
  if (snapshot.schema_version === 1 && (organism.cognition != null || organism.body_schema != null)) return null;
  if (snapshot.schema_version === 2 && (!cognition || organism.body_schema != null)) return null;
  if (snapshot.schema_version === 3 && (!bodySchema || (organism.cognition != null && !cognition))) return null;

  const incomingSenses = Array.isArray(organism.percepts) ? organism.percepts.slice(0, 32) : [];
  const incomingBeliefs = Array.isArray(organism.beliefs) ? organism.beliefs.slice(0, 128) : [];
  const incomingMembers = Array.isArray(snapshot.population?.members) ? snapshot.population.members.slice(0, 500) : [];
  const incomingRelationships = Array.isArray(snapshot.population?.relationships) ? snapshot.population.relationships.slice(0, 1000) : [];
  const incomingEvents = Array.isArray(organism.events) ? organism.events.slice(0, 64) : [];
  const incomingSensoryDev = Array.isArray(organism.sensory_development) ? organism.sensory_development.slice(0, 64) : [];
  const incomingSensoryRel = Array.isArray(organism.sensory_relations) ? organism.sensory_relations.slice(0, 24) : [];
  const incomingKnowledge = Array.isArray(organism.signal_knowledge) ? organism.signal_knowledge.slice(0, 64) : [];
  const incomingSocialRelations = Array.isArray(organism.social_relations) ? organism.social_relations : [];
  const incomingSocialResourceEvidence = Array.isArray(organism.social_resource_evidence) ? organism.social_resource_evidence : [];
  const physiology = boundedPhysiology(organism.physiology);
  const development = boundedDevelopment(organism.development);
  const attention = boundedAttention(organism.attention);
  const degradation = boundedDegradation(organism.degradation);
  return {
    tick: Math.max(0, snapshot.tick),
    displayId: typeof organism.display_id === "string" ? organism.display_id.slice(0, 48) : null,
    organismState: ["observing", "exploring", "reflecting", "resting", "unknown"].includes(organism.state) ? organism.state : "unknown",
    senses: incomingSenses.filter(item => item && typeof item.id === "string" && typeof item.label === "string").map((item, index) => ({
      id: item.id.slice(0, 64),
      name: item.label.slice(0, 80),
      icon: `S${index + 1}`,
      quality: Math.min(1, Math.max(0, Number(item.quality) || 0)),
      active: item.available === true,
      knowledgeSignalId: typeof item.knowledge_signal_id === "string" ? item.knowledge_signal_id : null,
    })),
    beliefs: incomingBeliefs.filter(item => item && typeof item.id === "string" && typeof item.label === "string").map((item, index) => {
      const angle = index * 2.399;
      const radius = 48 + (index % 5) * 42;
      return {
        id: item.id.slice(0, 64),
        title: item.label.slice(0, 120),
        x: 450 + Math.cos(angle) * radius,
        y: 362 + Math.sin(angle) * radius * .82,
        r: 5 + (index % 4) * 2.5,
        certainty: Math.min(1, Math.max(0, Number(item.certainty) || 0)),
        evidence: Math.max(0, Number.parseInt(item.evidence_count, 10) || 0),
        revisions: Math.max(0, Number.parseInt(item.revision_count, 10) || 0),
        dissent: item.contested === true,
      };
    }),
    details: {
      narrative: typeof organism.narrative === "string" ? organism.narrative.slice(0, 600) : state.details.narrative,
      acclimation: Math.min(1, Math.max(0, Number(organism.acclimation) || 0)),
      resourceBudget: {
        cpu: boundedRatioOrNull(organism.resource_budget?.cpu),
        memory: boundedRatioOrNull(organism.resource_budget?.memory),
        storage: boundedRatioOrNull(organism.resource_budget?.storage),
        ticksRemaining: Math.max(0, Number.parseInt(organism.resource_budget?.ticks_remaining, 10) || 0),
      },
      memory: (Array.isArray(organism.memory) ? organism.memory : []).slice(0, 32),
      openQuestions: (Array.isArray(organism.open_questions) ? organism.open_questions : []).slice(0, 16),
      investigations: (Array.isArray(organism.investigations) ? organism.investigations : []).slice(0, 16),
      regimeChanges: (Array.isArray(organism.regime_changes) ? organism.regime_changes : []).slice(0, 16),
    },
    population: incomingMembers.filter(item => item && typeof item.display_id === "string").map((item, index) => {
      const cluster = Math.min(7, Math.max(0, Number.parseInt(item.ecology, 10) || 0));
      const centers = [[280, 230], [610, 250], [470, 500], [300, 470], [640, 480], [440, 190], [210, 360], [690, 360]];
      const angle = index * 2.17;
      const distance = 28 + (index % 5) * 18;
      return {
        id: item.display_id.slice(0, 48),
        cluster,
        x: centers[cluster][0] + Math.cos(angle) * distance,
        y: centers[cluster][1] + Math.sin(angle) * distance,
        pressure: Math.min(1, Math.max(0, Number(item.activity) || 0)),
        knowledge: Math.max(0, Number.parseInt(item.knowledge_count, 10) || 0),
        contested: Math.max(0, Number.parseInt(item.contested_count, 10) || 0),
      };
    }),
    relationships: incomingRelationships.filter(link => link && typeof link.source === "string" && typeof link.target === "string"),
    events: incomingEvents,
    signalKnowledge: incomingKnowledge.filter(item => item && typeof item.signal_id === "string").map(item => ({
      signalId: item.signal_id,
      observedOpportunities: Math.max(0, Number.parseInt(item.observed_opportunities, 10) || 0),
      validObservations: Math.max(0, Number.parseInt(item.valid_observations, 10) || 0),
      age: typeof item.last_seen_age_class === "string" ? item.last_seen_age_class : "never",
      claims: Array.isArray(item.claims) ? item.claims.slice(0, 4).filter(claim => claim && typeof claim.claim_id === "string").map(claim => ({
        claimId: claim.claim_id,
        kind: typeof claim.kind === "string" ? claim.kind : "unknown",
        relatedSignalId: typeof claim.related_signal_id === "string" ? claim.related_signal_id : null,
        status: typeof claim.status === "string" ? claim.status : "insufficient",
        strengthClass: typeof claim.strength_class === "string" ? claim.strength_class : null,
        evidenceCount: Math.max(0, Number.parseInt(claim.evidence_count, 10) || 0),
        validationOpportunities: Math.max(0, Number.parseInt(claim.validation_opportunities, 10) || 0),
        improvementClass: typeof claim.improvement_class === "string" ? claim.improvement_class : null,
        revision: Math.max(0, Number.parseInt(claim.revision, 10) || 0),
        reasonClass: typeof claim.reason_class === "string" ? claim.reason_class : "insufficient_observations",
      })) : [],
    })),
    knowledgeEvents: Array.isArray(organism.knowledge_events) ? organism.knowledge_events.slice(0, 64) : [],
    cognition,
    bodySchema,
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
    socialRelations: boundedSocialRelations(incomingSocialRelations),
    socialResourceEvidence: boundedSocialResourceEvidence(incomingSocialResourceEvidence),
    degradation,
    physiology,
    development,
    attention,
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
  state.lastRawSnapshot = typeof structuredClone === "function" ? structuredClone(snapshot) : JSON.parse(JSON.stringify(snapshot));
  const projection = boundedSnapshot(normalizeSnapshot(snapshot));
  if (!projection) return;
  commitSnapshotProjection(projection);
  if (projection.displayId) {
    state.displayId = projection.displayId;
    document.querySelector("#organism-name").textContent = state.view === "population" ? "Fleet population" : `Organism ${projection.displayId}`;
  }
  state.organismState = projection.organismState;
  state.realTick = projection.tick;
  state.lastSnapshotAt = new Date().toISOString();
  document.querySelector("#organism-state").textContent = projection.organismState[0].toUpperCase() + projection.organismState.slice(1);
  if (announce) document.querySelector(".connection small").textContent = "snapshot stream";
  return projection;
}

export { boundedRatioOrNull, normalizeSnapshot, boundedCognition, boundedSocialRelations, boundedSocialResourceEvidence, boundedDegradation, boundedPhysiology, boundedAttention, boundedSnapshot, ingestSnapshot };
