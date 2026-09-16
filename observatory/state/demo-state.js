function createDemoSenses() {
  return [
    { id: "system_load", name: "System load", icon: "CPU", quality: .92, active: true },
    { id: "storage_pressure", name: "Storage pressure", icon: "IO", quality: .84, active: true },
    { id: "memory_pressure", name: "Memory pressure", icon: "MEM", quality: .68, active: true },
    { id: "thermal_state", name: "Thermal state", icon: "°C", quality: .48, active: false },
    { id: "power_state", name: "Power state", icon: "PWR", quality: .72, active: true },
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
  return population.map((item, index) => ({ source: item.id, target: population[(index + 4) % population.length].id, type: ["ecology", "knowledge", "activity", "dissent"][index % 4], strength: .35 + (index % 6) * .1 }));
}

const demoEvents = Array.from({ length: 18 }, (_, index) => ({
  id: `event-${index}`, type: ["perception", "attention", "revision", "contradiction"][index % 4],
  label: ["A normalized input changed", "Attention moved to an uncertain pattern", "A belief incorporated new evidence", "Conflicting evidence remains open"][index % 4],
  explanation: "The organism kept this transition inspectable without assigning a threat label or taking an action.",
  beliefId: `belief-${(index * 3) % 25}`, delta: ((index % 7) - 3) / 10, tick: index * 3,
  chain: ["A bounded perception entered the current context.", "Memory supplied a comparable prior pattern.", "Attention was allocated according to uncertainty.", "The related belief remained revisable."],
}));

function createInitialState() {
  const beliefs = createDemoBeliefs();
  const state = { view: "individual", mode: "live", playing: true, tick: 18, realTick: null, selected: beliefs[12], selectedSignalId: null, signalKnowledge: [], knowledgeEvents: [], replay: [], replayIndex: 0, source: "demo", events: demoEvents, liveEvents: [], eventFilter: "all", query: "", selectedEvent: demoEvents[6], compareA: null, compareB: null, populationMode: "ecology", organismA: null, organismB: null, displayId: null, organismState: "unknown", physiology: null, attention: null, sensoryDevelopment: [], sensoryRelations: [], socialRelations: [], socialResourceEvidence: [], degradation: { retainedItems: 0, excretedUnits: 0 }, sampling: { active: 0, probing: 0, dormant: 0, unknown: 0, sampledThisTick: 0, discovered: 0 }, schemaVersion: 1, senseHistory: new Map(), senses: createDemoSenses(), beliefs, topology: null, cognition: null, instanceId: null, organismView: "phenotype", bodySchema: null };
  state.population = createDemoPopulation();
  state.relationships = createDemoRelationships(state.population);
  state.profile = "summary";
  state.details = { narrative:"The organism is observing familiar host rhythms while keeping one uncertain pattern open for another look.", acclimation:.72, resourceBudget:{cpu:.22,memory:.31,storage:.14,ticksRemaining:82}, memory:["Quiet workload rhythm retained","Storage recovery pattern strengthened"], openQuestions:["Will the current load return to its familiar range?"], investigations:["Second look at resource coupling"], regimeChanges:["No confirmed regime change"] };
  return state;
}

export { createDemoSenses, createDemoBeliefs, createDemoPopulation, createDemoRelationships, demoEvents, createInitialState };
