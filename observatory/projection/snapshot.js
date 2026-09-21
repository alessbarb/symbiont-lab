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
  const activationClasses = {};
  Object.entries(cognition.activation_classes ?? {}).forEach(([id, cls]) => {
    if (typeof id === "string" && Number.isInteger(Number(cls))) {
      activationClasses[id.slice(0, 128)] = Math.max(0, Math.min(15, Number(cls)));
    }
  });
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
  const strandedConcepts = (Array.isArray(cognition.stranded_concepts) ? cognition.stranded_concepts : [])
    .slice(0, 64)
    .filter(id => typeof id === "string")
    .map(id => id.slice(0, 128));
  const retiringPredictors = (Array.isArray(cognition.retiring_predictors) ? cognition.retiring_predictors : [])
    .slice(0, 128)
    .filter(id => typeof id === "string")
    .map(id => id.slice(0, 128));
  const safety = cognition.safety_state ?? {};
  const allowedHealth = ["germinal", "developing", "connected", "adaptive", "degenerate", "recovering"];
  const topologyHealth = allowedHealth.includes(cognition.topology_health) ? cognition.topology_health : "germinal";
  return {
    topologyRevision: Math.max(0, Number.parseInt(cognition.topology_revision, 10) || 0),
    topologyHealth,
    recovering: cognition.recovering === true,
    activationClasses,
    readouts,
    predictionErrors,
    mutations,
    strandedConcepts,
    predictiveGain: Number.isFinite(Number(cognition.predictive_gain)) ? Number(cognition.predictive_gain) : 0.0,
    retiringPredictors,
    retirementEdges: Math.max(0, Number.parseInt(cognition.retirement_edges, 10) || 0),
    structuralCandidates: Math.min(256, Math.max(0, Number.parseInt(cognition.structural_candidates, 10) || 0)),
    maxContentionLosses: Math.max(0, Number.parseInt(cognition.max_contention_losses, 10) || 0),
    structuralPressure: Number.isFinite(Number(cognition.structural_pressure)) ? Math.max(0, Math.min(1, Number(cognition.structural_pressure))) : null,
    quantizationError: Number.isFinite(Number(cognition.quantization_error)) ? Math.max(0, Number(cognition.quantization_error)) : null,
    relationChurn: Number.isFinite(Number(cognition.relation_churn)) ? Math.max(0, Math.min(1, Number(cognition.relation_churn))) : null,
    developmentalDivergence: Number.isFinite(Number(cognition.developmental_divergence)) ? Math.max(0, Math.min(1, Number(cognition.developmental_divergence))) : null,
    safetyState: {
      consecutiveFailures: Math.max(0, Number.parseInt(safety.consecutive_failures, 10) || 0),
      frozen: safety.frozen === true,
    },
  };
}

function boundedSensoryPhenotype(phenotype) {
  if (!phenotype || typeof phenotype !== "object") return null;
  const modalities = (Array.isArray(phenotype.modalities) ? phenotype.modalities : []).slice(0, 8)
    .filter(item => item && typeof item.modality_id === "string")
    .map(item => ({
      modalityId: item.modality_id.slice(0, 64),
      sensorCount: Math.min(64, Math.max(0, Number.parseInt(item.sensor_count, 10) || 0)),
      maxInputs: Math.min(8, Math.max(1, Number.parseInt(item.max_inputs, 10) || 1)),
      temporalCapacity: Math.min(256, Math.max(1, Number.parseInt(item.temporal_capacity, 10) || 1)),
      allowedTransductions: (Array.isArray(item.allowed_transductions) ? item.allowed_transductions : [])
        .slice(0, 16).filter(value => typeof value === "string").map(value => value.slice(0, 32)),
    }));
  const maturity = new Set(["nascent", "immature", "established", "specialised", "degraded"]);
  const ratio = value => Math.min(1, Math.max(0, Number(value) || 0));
  const sensors = (Array.isArray(phenotype.sensors) ? phenotype.sensors : []).slice(0, 64)
    .filter(item => item && typeof item.sensor_id === "string" && typeof item.modality_id === "string")
    .map(item => ({
      sensorId: item.sensor_id.slice(0, 96),
      modalityId: item.modality_id.slice(0, 64),
      sampleGeometry: typeof item.sample_geometry === "string" ? item.sample_geometry.slice(0, 32) : "scalar",
      transduction: typeof item.transduction === "string" ? item.transduction.slice(0, 32) : "identity",
      bornTick: Math.max(0, Number.parseInt(item.born_tick, 10) || 0),
      ageTicks: Math.max(0, Number.parseInt(item.age_ticks, 10) || 0),
      outputObservations: Math.max(0, Number.parseInt(item.output_observations, 10) || 0),
      utilityObservations: Math.max(0, Number.parseInt(item.utility_observations, 10) || 0),
      sourceCount: Math.min(8, Math.max(1, Number.parseInt(item.source_count, 10) || 1)),
      signalIds: (Array.isArray(item.signal_ids) ? item.signal_ids : []).slice(0, 8)
        .filter(value => typeof value === "string" && value.startsWith("signal."))
        .map(value => value.slice(0, 128)),
      maturity: maturity.has(item.maturity) ? item.maturity : "nascent",
      health: ratio(item.health),
      confidence: ratio(item.confidence),
      utility: ratio(item.utility),
      selectionCredit: ratio(item.selection_credit),
      redundancy: ratio(item.redundancy),
      cost: ratio(item.cost),
      parentSensorIds: (Array.isArray(item.parent_sensor_ids) ? item.parent_sensor_ids : []).slice(0, 4)
        .filter(value => typeof value === "string").map(value => value.slice(0, 96)),
      downstreamName: typeof item.downstream_name === "string" ? item.downstream_name.slice(0, 128) : "",
      coldStart: item.cold_start === true,
    }));
  const rawSummary = phenotype.summary && typeof phenotype.summary === "object" ? phenotype.summary : {};
  const count = key => Math.min(64, Math.max(0, Number.parseInt(rawSummary[key], 10) || 0));
  return {
    schemaVersion: 1, modalities, sensors,
    summary: {
      active: count("active"), nascent: count("nascent"), immature: count("immature"),
      established: count("established"), specialised: count("specialised"), degraded: count("degraded"),
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

function boundedPopulationTelemetry(telemetry) {
  if (!telemetry || typeof telemetry !== "object") return null;
  const kinds = new Set(["EMIT", "DELIVER", "RECEIVE", "RETRANSMIT", "SILENCE"]);
  const events = (Array.isArray(telemetry.events) ? telemetry.events : []).slice(0, 2048)
    .filter(item => item && typeof item.event_id === "string" && kinds.has(item.event_kind)
      && typeof item.sender_id === "string" && typeof item.receiver_id === "string"
      && typeof item.message_id === "string" && Array.isArray(item.symbol_ids)
      && item.symbol_ids.length >= 1 && item.symbol_ids.length <= 4)
    .map(item => ({
      eventId: item.event_id.slice(0, 128), tick: Math.max(0, Number.parseInt(item.tick, 10) || 0), kind: item.event_kind,
      senderId: item.sender_id.slice(0, 128), receiverId: item.receiver_id.slice(0, 128), messageId: item.message_id.slice(0, 128),
      symbols: item.symbol_ids.slice(0, 4).filter(value => typeof value === "string").map(value => value.slice(0, 128)),
      messageLength: Math.max(1, Math.min(4, Number.parseInt(item.message_length, 10) || item.symbol_ids.length)),
      cost: Math.max(0, Number.parseInt(item.cost, 10) || 0), deliveryStatus: typeof item.delivery_status === "string" ? item.delivery_status.slice(0, 16) : "unknown",
      senderGeneration: Number.isInteger(item.sender_generation) ? Math.max(0, item.sender_generation) : null,
      receiverGeneration: Number.isInteger(item.receiver_generation) ? Math.max(0, item.receiver_generation) : null,
    }));
  const groundingEvents = (Array.isArray(telemetry.grounding_events) ? telemetry.grounding_events : []).slice(0, 2048)
    .filter(item => item && typeof item.event_id === "string" && item.event_id && typeof item.organism_id === "string" && item.organism_id && typeof item.message_id === "string" && item.message_id)
    .map(item => ({
      eventId: item.event_id.slice(0, 128), tick: Math.max(0, Number.parseInt(item.tick, 10) || 0),
      organismId: item.organism_id.slice(0, 128), messageId: item.message_id.slice(0, 128),
      exposureCount: Math.min(1000000, Math.max(0, Number.parseInt(item.exposure_count, 10) || 0)),
      associationStrengthBefore: Math.min(1000000, Math.max(0, Number.parseInt(item.association_strength_before, 10) || 0)),
      associationStrengthAfter: Math.min(1000000, Math.max(0, Number.parseInt(item.association_strength_after, 10) || 0)),
      supportDelta: Number.parseInt(item.support_delta, 10) || 0,
      contradictionDelta: Number.parseInt(item.contradiction_delta, 10) || 0,
      cost: Math.min(1000000, Math.max(0, Number.parseInt(item.cost, 10) || 0)),
    }));
  return {
    schemaVersion: 1, events,
    groundingEvents,
    historyTruncated: telemetry.history_truncated === true,
    earliestAvailableTick: Number.isInteger(telemetry.earliest_available_tick) ? Math.max(0, telemetry.earliest_available_tick) : null,
  };
}

function boundedDegradation(degradation) {
  if (!degradation || typeof degradation !== "object") return { retainedItems: 0, excretedUnits: 0 };
  return {
    retainedItems: Math.min(256, Math.max(0, Number.parseInt(degradation.retained_items, 10) || 0)),
    excretedUnits: Math.min(256, Math.max(0, Number.parseInt(degradation.excreted_units, 10) || 0)),
  };
}

function boundedMetabolism(metabolism) {
  if (!metabolism || typeof metabolism !== "object") return null;
  const allowedPressure = new Set(["normal", "elevated", "severe", "unrecoverable", "unknown"]);
  const allowedReserve = new Set(["depleted", "low", "moderate", "replete"]);
  const reserveClasses = {};
  Object.entries(metabolism.reserve_classes ?? {}).slice(0, 8).forEach(([key, value]) => {
    if (typeof key !== "string" || !allowedReserve.has(value)) return;
    reserveClasses[key.slice(0, 32)] = value;
  });
  return {
    pressure: allowedPressure.has(metabolism.pressure) ? metabolism.pressure : "unknown",
    reserveClasses,
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

function boundedObserver(observer) {
  const raw = observer && typeof observer === "object" ? observer : {};
  const allowedCategories = new Set(["compute", "memory", "storage", "network", "thermal", "power", "system", "internal", "unknown"]);
  const allowedQuality = new Set(["nominal", "degraded", "stale", "unavailable"]);
  const rows = (Array.isArray(raw.signal_provenance) ? raw.signal_provenance : [])
    .slice(0, 256)
    .filter(item => item && typeof item.signal_id === "string" && item.signal_id.startsWith("signal."))
    .map(item => ({
      signalId: item.signal_id.slice(0, 128),
      label: typeof item.label === "string" ? item.label.slice(0, 64) : "Aggregate signal",
      category: allowedCategories.has(item.category) ? item.category : "unknown",
      scope: item.scope === "internal" ? "internal" : "external",
      value: item.value == null || !Number.isFinite(Number(item.value)) ? null : Number(item.value),
      unit: typeof item.unit === "string" ? item.unit.slice(0, 16) : "",
      quality: allowedQuality.has(item.quality) ? item.quality : "unavailable",
    }));
  return { signalProvenance: rows };
}

function boundedSnapshot(snapshot) {
  if (!snapshot || ![1, 2, 3].includes(snapshot.schema_version) || !Number.isInteger(snapshot.tick)) return null;
  const organism = snapshot.organism ?? {};
  const observer = boundedObserver(snapshot.observer);
  const cognition = boundedCognition(organism.cognition);
  const bodySchema = boundedBodySchema(organism.body_schema);
  const sensoryPhenotype = boundedSensoryPhenotype(organism.sensory_phenotype);
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
  const metabolism = boundedMetabolism(organism.metabolism);
  const physiology = boundedPhysiology(organism.physiology);
  const development = boundedDevelopment(organism.development);
  const attention = boundedAttention(organism.attention);
  const degradation = boundedDegradation(organism.degradation);
  const populationTelemetry = boundedPopulationTelemetry(snapshot.population_telemetry);
  const culturalClaims = organism.cultural_claims && typeof organism.cultural_claims === "object" ? {
    claimCount: Math.max(0, Number.parseInt(organism.cultural_claims.claim_count, 10) || 0),
    uniqueRoots: Math.max(0, Number.parseInt(organism.cultural_claims.unique_roots, 10) || 0),
    independentRoots: Math.max(0, Number.parseInt(organism.cultural_claims.independent_roots, 10) || 0),
    transmissionDepth: Math.max(0, Number.parseInt(organism.cultural_claims.transmission_depth, 10) || 0),
    mutationDepth: Math.max(0, Number.parseInt(organism.cultural_claims.mutation_depth, 10) || 0),
    confirmedLocally: Math.max(0, Number.parseInt(organism.cultural_claims.confirmed_locally, 10) || 0),
    contradictedLocally: Math.max(0, Number.parseInt(organism.cultural_claims.contradicted_locally, 10) || 0),
    freshness: Array.isArray(organism.cultural_claims.freshness) ? organism.cultural_claims.freshness.slice(0, 128) : [],
    lineage: Array.isArray(organism.cultural_claims.lineage) ? organism.cultural_claims.lineage.slice(0, 128) : [],
    compositeCount: Math.max(0, Number.parseInt(organism.cultural_claims.composite_count, 10) || 0),
    uniqueContributors: Math.max(0, Number.parseInt(organism.cultural_claims.unique_contributors, 10) || 0),
    culturalGeneration: Math.max(0, Number.parseInt(organism.cultural_claims.cultural_generation, 10) || 0),
    compositeLineage: Array.isArray(organism.cultural_claims.composite_lineage) ? organism.cultural_claims.composite_lineage.slice(0, 128) : [],
    culturalDecisions: Array.isArray(organism.cultural_claims.cultural_decisions) ? organism.cultural_claims.cultural_decisions.slice(0, 256) : [],
    culturalPolicyCost: Math.max(0, Number.parseInt(organism.cultural_claims.cultural_policy_cost, 10) || 0),
    symbolsKnown: Math.max(0, Number.parseInt(organism.cultural_claims.symbols_known, 10) || 0),
    symbolsEmitted: Math.max(0, Number.parseInt(organism.cultural_claims.symbols_emitted, 10) || 0),
    symbolExposures: Math.max(0, Number.parseInt(organism.cultural_claims.symbol_exposures, 10) || 0),
    groundingUpdates: Math.max(0, Number.parseInt(organism.cultural_claims.grounding_updates, 10) || 0),
    symbolPolicyCost: Math.max(0, Number.parseInt(organism.cultural_claims.symbol_policy_cost, 10) || 0),
    symbolDecisions: Array.isArray(organism.cultural_claims.symbol_decisions) ? organism.cultural_claims.symbol_decisions.slice(0, 256) : [],
    symbolGrounding: Array.isArray(organism.cultural_claims.symbol_grounding) ? organism.cultural_claims.symbol_grounding.slice(0, 128) : [],
    sequencesKnown: Math.max(0, Number.parseInt(organism.cultural_claims.sequences_known, 10) || 0),
    sequenceEmissions: Math.max(0, Number.parseInt(organism.cultural_claims.sequence_emissions, 10) || 0),
    sequenceExposures: Math.max(0, Number.parseInt(organism.cultural_claims.sequence_exposures, 10) || 0),
    sequenceGroundingUpdates: Math.max(0, Number.parseInt(organism.cultural_claims.sequence_grounding_updates, 10) || 0),
    sequencePolicyCost: Math.max(0, Number.parseInt(organism.cultural_claims.sequence_policy_cost, 10) || 0),
    sequenceDecisions: Array.isArray(organism.cultural_claims.sequence_decisions) ? organism.cultural_claims.sequence_decisions.slice(0, 256) : [],
    sequenceGrounding: Array.isArray(organism.cultural_claims.sequence_grounding) ? organism.cultural_claims.sequence_grounding.slice(0, 128) : [],
  } : null;
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
    culturalClaims,
    observer,
    populationTelemetry,
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
    sensoryPhenotype,
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
    metabolism,
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

export { boundedRatioOrNull, normalizeSnapshot, boundedCognition, boundedObserver, boundedSensoryPhenotype, boundedMetabolism, boundedSocialRelations, boundedSocialResourceEvidence, boundedPopulationTelemetry, boundedDegradation, boundedPhysiology, boundedAttention, boundedSnapshot, ingestSnapshot };
