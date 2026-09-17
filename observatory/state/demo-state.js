function createDemoSenses() {
  return [
    { id: "system_load", name: "System load", icon: "CPU", quality: .92, active: true, knowledgeSignalId: "signal.system_load" },
    { id: "storage_pressure", name: "Storage pressure", icon: "IO", quality: .84, active: true, knowledgeSignalId: "signal.storage_pressure" },
    { id: "memory_pressure", name: "Memory pressure", icon: "MEM", quality: .68, active: true, knowledgeSignalId: "signal.memory_pressure" },
    { id: "thermal_state", name: "Thermal state", icon: "°C", quality: .48, active: false, knowledgeSignalId: "signal.thermal_state" },
    { id: "power_state", name: "Power state", icon: "PWR", quality: .72, active: true, knowledgeSignalId: "signal.power_state" },
  ];
}

function createDemoBeliefs() {
  return Array.from({ length: 25 }, (_, index) => {
    const angle = index * 2.399;
    const radius = 48 + (index % 5) * 42;
    return {
      id: `belief-${index}`,
      x: 450 + Math.cos(angle) * radius,
      y: 362 + Math.sin(angle) * radius * .82,
      r: 5 + (index % 4) * 2.5,
      certainty: .42 + ((index * 17) % 50) / 100,
      revisions: 1 + (index % 7),
      evidence: 4 + (index * 3) % 19,
      title: ["Workload rhythm", "Storage recovery", "Resource coupling", "Quiet-state memory", "Shared context"][index % 5],
      dissent: index % 6 === 0,
    };
  });
}

function createDemoPopulation() {
  return Array.from({ length: 18 }, (_, i) => {
    const cluster = i % 3;
    const centers = [[280, 230], [610, 250], [470, 500]];
    const a = i * 2.17;
    const d = 28 + (i % 5) * 18;
    return { id: `S-${String(i + 1).padStart(2, "0")}`, cluster, x: centers[cluster][0] + Math.cos(a) * d, y: centers[cluster][1] + Math.sin(a) * d, pressure: .2 + (i % 6) * .12, knowledge: 5 + (i * 7) % 38, contested: i % 5 };
  });
}

function createDemoRelationships(population) {
  const links = [];
  const types = ["ecology", "knowledge", "activity", "dissent"];
  population.forEach((item, index) => {
    const target1 = population[(index + 3) % population.length];
    const type1 = types[index % 4];
    const isConflict1 = type1 === "dissent" || index % 5 === 4;
    links.push({
      source: item.id,
      target: target1.id,
      type: type1,
      strength: 0.4 + (index % 5) * 0.12,
      support: isConflict1 ? 0.2 : 1.5 + (index % 4) * 0.5,
      harm: isConflict1 ? 1.8 : 0.05,
      valence: isConflict1 ? "negative" : "positive",
      reciprocal: index % 2 === 0,
      conflicts: isConflict1 ? (index % 3) + 1 : 0,
      rejections: isConflict1 && index % 2 === 1 ? 1 : 0,
      reliability: 0.75 + (index % 3) * 0.08,
      freshness: 0.85 - (index % 4) * 0.1,
      channel: index % 3 === 0 ? "metabolic" : "epistemic",
    });

    const sameCluster = population.filter(p => p.cluster === item.cluster && p.id !== item.id);
    if (sameCluster.length > 0 && index % 2 === 0) {
      const target2 = sameCluster[(index / 2) % sameCluster.length];
      links.push({
        source: item.id,
        target: target2.id,
        type: index % 4 === 0 ? "knowledge" : "ecology",
        strength: 0.65,
        support: 2.4,
        harm: 0.0,
        valence: "positive",
        reciprocal: true,
        conflicts: 0,
        rejections: 0,
        reliability: 0.92,
        freshness: 0.95,
        channel: "substrate",
      });
    }
  });
  return links;
}

const demoEvents = Array.from({ length: 18 }, (_, index) => ({
  id: `event-${index}`, type: ["perception", "attention", "revision", "contradiction"][index % 4],
  label: ["A normalized input changed", "Attention moved to an uncertain pattern", "A belief incorporated new evidence", "Conflicting evidence remains open"][index % 4],
  explanation: "The organism kept this transition inspectable without assigning a threat label or taking an action.",
  beliefId: `belief-${(index * 3) % 25}`, delta: ((index % 7) - 3) / 10, tick: index * 3,
  chain: ["A bounded perception entered the current context.", "Memory supplied a comparable prior pattern.", "Attention was allocated according to uncertainty.", "The related belief remained revisable."],
}));

function createDemoSignalKnowledge() {
  return [
    {
      signalId: "signal.system_load",
      observedOpportunities: 180,
      validObservations: 172,
      age: "current",
      claims: [
        {
          claimId: "claim_load_lead",
          kind: "lead_prediction",
          relatedSignalId: "signal.storage_pressure",
          status: "supported",
          strengthClass: "high",
          evidenceCount: 142,
          validationOpportunities: 150,
          improvementClass: "significant",
          revision: 2,
          reasonClass: "support_confirmed",
        },
        {
          claimId: "claim_load_stability",
          kind: "stability",
          relatedSignalId: null,
          status: "hypothesis",
          strengthClass: "moderate",
          evidenceCount: 48,
          validationOpportunities: 65,
          improvementClass: "marginal",
          revision: 1,
          reasonClass: "evidence_accumulated",
        },
      ],
    },
    {
      signalId: "signal.storage_pressure",
      observedOpportunities: 160,
      validObservations: 154,
      age: "current",
      claims: [
        {
          claimId: "claim_storage_sync",
          kind: "synchronous_association",
          relatedSignalId: "signal.memory_pressure",
          status: "contested",
          strengthClass: "weak",
          evidenceCount: 18,
          validationOpportunities: 45,
          improvementClass: "none",
          revision: 3,
          reasonClass: "contradiction_detected",
        },
      ],
    },
    {
      signalId: "signal.thermal_state",
      observedOpportunities: 90,
      validObservations: 82,
      age: "recent",
      claims: [
        {
          claimId: "claim_thermal_self",
          kind: "self_relevance",
          relatedSignalId: null,
          status: "hypothesis",
          strengthClass: "moderate",
          evidenceCount: 22,
          validationOpportunities: 30,
          improvementClass: "moderate",
          revision: 1,
          reasonClass: "evidence_accumulated",
        },
      ],
    },
  ];
}

function createDemoKnowledgeEvents() {
  return [
    {
      claimId: "claim_load_lead",
      tick: 17,
      fromStatus: "hypothesis",
      toStatus: "supported",
      reasonClass: "support_confirmed",
      detail: "Hipótesis confirmada tras 150 ensayos comparables (94.6% acierto)",
    },
    {
      claimId: "claim_storage_sync",
      tick: 14,
      fromStatus: "hypothesis",
      toStatus: "contested",
      reasonClass: "contradiction_detected",
      detail: "Contradicción empírica detectada durante transición de régimen",
    },
    {
      claimId: "claim_thermal_self",
      tick: 11,
      fromStatus: "insufficient",
      toStatus: "hypothesis",
      reasonClass: "evidence_accumulated",
      detail: "Nueva hipótesis abierta: posible acoplamiento con tasa metabólica",
    },
  ];
}

function createDemoResourceEvidence() {
  return [
    {
      token: "res_metabolic_substrate",
      requested: 120.0,
      granted: 114.0,
      availability: 0.95,
      observations: 84,
      denied: 6,
      consecutive_denied: 0,
      freshness: 0.92,
      x: 300,
      y: 240,
    },
    {
      token: "res_epistemic_bus",
      requested: 95.0,
      granted: 88.0,
      availability: 0.92,
      observations: 65,
      denied: 7,
      consecutive_denied: 0,
      freshness: 0.88,
      x: 630,
      y: 260,
    },
    {
      token: "res_telemetry_bandwidth",
      requested: 80.0,
      granted: 48.0,
      availability: 0.60,
      observations: 50,
      denied: 22,
      consecutive_denied: 3,
      freshness: 0.74,
      x: 480,
      y: 520,
    },
  ];
}

function createInitialState() {
  const beliefs = createDemoBeliefs();
  const state = { view: "individual", mode: "live", playing: true, tick: 18, realTick: null, sequence: null, runId: null, lastSnapshotAt: null, selected: beliefs[12], selectedSignalId: null, selectedNodeId: null, signalKnowledge: createDemoSignalKnowledge(), knowledgeEvents: createDemoKnowledgeEvents(), replay: [], replayIndex: 0, source: "demo", events: demoEvents, liveEvents: [], lastRawSnapshot: null, eventFilter: "all", query: "", selectedEvent: demoEvents[6], compareA: null, compareB: null, populationMode: "ecology", organismA: null, organismB: null, displayId: null, organismState: "unknown", physiology: null, development: null, attention: null, sensoryDevelopment: [], sensoryRelations: [], socialRelations: [], socialResourceEvidence: createDemoResourceEvidence(), culturalClaims: null, populationTelemetry: null, fleetCommunication: null, degradation: { retainedItems: 0, excretedUnits: 0 }, sampling: { active: 0, probing: 0, dormant: 0, unknown: 0, sampledThisTick: 0, discovered: 0 }, schemaVersion: 1, senseHistory: new Map(), senses: createDemoSenses(), beliefs, topology: null, cognition: null, instanceId: null, organismView: "phenotype", bodySchema: null, fleetInstances: [] };
  state.population = createDemoPopulation();
  state.fleetPopulation = [];
  state.fleetRelationships = [];
  state.fleetConnected = false;
  state.relationships = createDemoRelationships(state.population);
  state.profile = "summary";
  state.details = { narrative:"The organism is observing familiar host rhythms while keeping one uncertain pattern open for another look.", acclimation:.72, resourceBudget:{cpu:.22,memory:.31,storage:.14,ticksRemaining:82}, memory:["Quiet workload rhythm retained","Storage recovery pattern strengthened"], openQuestions:["Will the current load return to its familiar range?"], investigations:["Second look at resource coupling"], regimeChanges:["No confirmed regime change"] };
  return state;
}

export { createDemoSenses, createDemoBeliefs, createDemoPopulation, createDemoRelationships, demoEvents, createInitialState };
