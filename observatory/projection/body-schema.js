const WIRE_SCHEMA_KEYS = new Set(["schema_version", "state", "parts", "dependencies", "global_state"]);
const WIRE_SENSE_KEYS = new Set([
  "part_id",
  "kind",
  "existence_confidence_class",
  "health_class",
  "confidence_class",
  "cost_class",
  "maturity_class",
  "recency_class",
]);
const WIRE_REGION_KEYS = new Set([
  "part_id",
  "kind",
  "existence_confidence_class",
  "confidence_class",
  "activity_class",
  "maturity_class",
  "recency_class",
]);
const WIRE_DEPENDENCY_KEYS = new Set([
  "source_id",
  "target_id",
  "relation",
  "confidence_class",
  "support_class",
]);
const INTERNAL_SCHEMA_KEYS = new Set(["schemaVersion", "state", "parts", "dependencies", "globalState"]);
const INTERNAL_SENSE_KEYS = new Set([
  "partId",
  "kind",
  "existenceConfidenceClass",
  "healthClass",
  "confidenceClass",
  "costClass",
  "maturityClass",
  "recencyClass",
]);
const INTERNAL_REGION_KEYS = new Set([
  "partId",
  "kind",
  "existenceConfidenceClass",
  "confidenceClass",
  "activityClass",
  "maturityClass",
  "recencyClass",
]);
const INTERNAL_DEPENDENCY_KEYS = new Set([
  "sourceId",
  "targetId",
  "relation",
  "confidenceClass",
  "supportClass",
]);
const RELATIONS = new Set(["co_acts_with", "precedes"]);
const MAX_SENSORY_PARTS = 256;
const MAX_COGNITIVE_REGIONS = 32;
const MAX_TOTAL_PARTS = MAX_SENSORY_PARTS + MAX_COGNITIVE_REGIONS;
const MAX_DEPENDENCIES = 256;

function exactKeys(value, allowed) {
  return Object.keys(value).every(key => allowed.has(key));
}

function discreteClass(value, maximum) {
  return Number.isInteger(value) && value >= 0 && value <= maximum ? value : null;
}

function boundedSensePart(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw) || !exactKeys(raw, WIRE_SENSE_KEYS) || raw.kind !== "sense") return null;
  if (typeof raw.part_id !== "string" || !/^part\.sense\.[0-9a-f]{32}$/.test(raw.part_id)) return null;
  const existenceConfidenceClass = discreteClass(raw.existence_confidence_class, 15);
  const healthClass = discreteClass(raw.health_class, 15);
  const confidenceClass = discreteClass(raw.confidence_class, 15);
  const costClass = discreteClass(raw.cost_class, 15);
  const maturityClass = discreteClass(raw.maturity_class, 7);
  const recencyClass = discreteClass(raw.recency_class, 4);
  if ([existenceConfidenceClass, healthClass, confidenceClass, costClass, maturityClass, recencyClass].some(value => value === null)) return null;
  return {
    partId: raw.part_id,
    kind: "sense",
    existenceConfidenceClass,
    healthClass,
    confidenceClass,
    costClass,
    maturityClass,
    recencyClass,
  };
}

function boundedRegionPart(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw) || !exactKeys(raw, WIRE_REGION_KEYS) || raw.kind !== "cognitive_region") return null;
  if (typeof raw.part_id !== "string" || !/^part\.region\.[0-9a-f]{32}$/.test(raw.part_id)) return null;
  const existenceConfidenceClass = discreteClass(raw.existence_confidence_class, 15);
  const confidenceClass = discreteClass(raw.confidence_class, 15);
  const activityClass = discreteClass(raw.activity_class, 15);
  const maturityClass = discreteClass(raw.maturity_class, 7);
  const recencyClass = discreteClass(raw.recency_class, 4);
  if ([existenceConfidenceClass, confidenceClass, activityClass, maturityClass, recencyClass].some(value => value === null)) return null;
  return {
    partId: raw.part_id,
    kind: "cognitive_region",
    existenceConfidenceClass,
    confidenceClass,
    activityClass,
    maturityClass,
    recencyClass,
  };
}

function boundedDependency(raw, regionIds) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw) || !exactKeys(raw, WIRE_DEPENDENCY_KEYS)) return null;
  if (typeof raw.source_id !== "string" || typeof raw.target_id !== "string") return null;
  if (!/^part\.region\.[0-9a-f]{32}$/.test(raw.source_id) || !/^part\.region\.[0-9a-f]{32}$/.test(raw.target_id)) return null;
  if (raw.source_id === raw.target_id || !regionIds.has(raw.source_id) || !regionIds.has(raw.target_id)) return null;
  if (!RELATIONS.has(raw.relation)) return null;
  if (raw.relation === "co_acts_with" && raw.source_id >= raw.target_id) return null;
  const confidenceClass = discreteClass(raw.confidence_class, 15);
  const supportClass = discreteClass(raw.support_class, 15);
  if (confidenceClass === null || supportClass === null) return null;
  return {
    sourceId: raw.source_id,
    targetId: raw.target_id,
    relation: raw.relation,
    confidenceClass,
    supportClass,
  };
}

function boundedBodySchema(bodySchema) {
  if (!bodySchema || typeof bodySchema !== "object" || Array.isArray(bodySchema)) return null;
  if (!exactKeys(bodySchema, WIRE_SCHEMA_KEYS)) return null;
  if (![1, 2].includes(bodySchema.schema_version)) return null;
  if (!Array.isArray(bodySchema.parts) || !Array.isArray(bodySchema.dependencies)) return null;
  const maxParts = bodySchema.schema_version === 1 ? MAX_SENSORY_PARTS : MAX_TOTAL_PARTS;
  if (bodySchema.parts.length > maxParts) return null;
  if (bodySchema.dependencies.length > (bodySchema.schema_version === 1 ? 0 : MAX_DEPENDENCIES)) return null;
  if (!bodySchema.global_state || typeof bodySchema.global_state !== "object" || Array.isArray(bodySchema.global_state) || Object.keys(bodySchema.global_state).length !== 0) return null;
  if (!["undeveloped", "partial"].includes(bodySchema.state)) return null;
  if (bodySchema.state === "undeveloped" && (bodySchema.parts.length !== 0 || bodySchema.dependencies.length !== 0)) return null;
  if (bodySchema.state === "partial" && bodySchema.parts.length === 0) return null;

  const parts = [];
  const seen = new Set();
  let sensoryCount = 0;
  let regionCount = 0;
  for (const raw of bodySchema.parts) {
    let part = null;
    if (raw?.kind === "sense") {
      part = boundedSensePart(raw);
      sensoryCount += part ? 1 : 0;
    } else if (bodySchema.schema_version === 2 && raw?.kind === "cognitive_region") {
      part = boundedRegionPart(raw);
      regionCount += part ? 1 : 0;
    }
    if (!part || seen.has(part.partId)) return null;
    seen.add(part.partId);
    parts.push(part);
  }
  if (sensoryCount > MAX_SENSORY_PARTS || regionCount > MAX_COGNITIVE_REGIONS) return null;

  const regionIds = new Set(parts.filter(part => part.kind === "cognitive_region").map(part => part.partId));
  const dependencies = [];
  const seenDependencies = new Set();
  for (const raw of bodySchema.dependencies) {
    if (bodySchema.schema_version !== 2) return null;
    const dependency = boundedDependency(raw, regionIds);
    if (!dependency) return null;
    const key = `${dependency.relation}:${dependency.sourceId}:${dependency.targetId}`;
    if (seenDependencies.has(key)) return null;
    seenDependencies.add(key);
    dependencies.push(dependency);
  }

  return {
    schemaVersion: bodySchema.schema_version,
    state: bodySchema.state,
    parts,
    dependencies,
    globalState: {},
  };
}

function sensePartToWire(part) {
  if (!part || typeof part !== "object" || Array.isArray(part) || !exactKeys(part, INTERNAL_SENSE_KEYS) || part.kind !== "sense") return null;
  if (typeof part.partId !== "string" || !/^part\.sense\.[0-9a-f]{32}$/.test(part.partId)) return null;
  const existenceConfidenceClass = discreteClass(part.existenceConfidenceClass, 15);
  const healthClass = discreteClass(part.healthClass, 15);
  const confidenceClass = discreteClass(part.confidenceClass, 15);
  const costClass = discreteClass(part.costClass, 15);
  const maturityClass = discreteClass(part.maturityClass, 7);
  const recencyClass = discreteClass(part.recencyClass, 4);
  if ([existenceConfidenceClass, healthClass, confidenceClass, costClass, maturityClass, recencyClass].some(value => value === null)) return null;
  return {
    part_id: part.partId,
    kind: "sense",
    existence_confidence_class: existenceConfidenceClass,
    health_class: healthClass,
    confidence_class: confidenceClass,
    cost_class: costClass,
    maturity_class: maturityClass,
    recency_class: recencyClass,
  };
}

function regionPartToWire(part) {
  if (!part || typeof part !== "object" || Array.isArray(part) || !exactKeys(part, INTERNAL_REGION_KEYS) || part.kind !== "cognitive_region") return null;
  if (typeof part.partId !== "string" || !/^part\.region\.[0-9a-f]{32}$/.test(part.partId)) return null;
  const existenceConfidenceClass = discreteClass(part.existenceConfidenceClass, 15);
  const confidenceClass = discreteClass(part.confidenceClass, 15);
  const activityClass = discreteClass(part.activityClass, 15);
  const maturityClass = discreteClass(part.maturityClass, 7);
  const recencyClass = discreteClass(part.recencyClass, 4);
  if ([existenceConfidenceClass, confidenceClass, activityClass, maturityClass, recencyClass].some(value => value === null)) return null;
  return {
    part_id: part.partId,
    kind: "cognitive_region",
    existence_confidence_class: existenceConfidenceClass,
    confidence_class: confidenceClass,
    activity_class: activityClass,
    maturity_class: maturityClass,
    recency_class: recencyClass,
  };
}

function dependencyToWire(dependency, regionIds) {
  if (!dependency || typeof dependency !== "object" || Array.isArray(dependency) || !exactKeys(dependency, INTERNAL_DEPENDENCY_KEYS)) return null;
  if (typeof dependency.sourceId !== "string" || typeof dependency.targetId !== "string") return null;
  if (dependency.sourceId === dependency.targetId || !regionIds.has(dependency.sourceId) || !regionIds.has(dependency.targetId)) return null;
  if (!RELATIONS.has(dependency.relation)) return null;
  if (dependency.relation === "co_acts_with" && dependency.sourceId >= dependency.targetId) return null;
  const confidenceClass = discreteClass(dependency.confidenceClass, 15);
  const supportClass = discreteClass(dependency.supportClass, 15);
  if (confidenceClass === null || supportClass === null) return null;
  return {
    source_id: dependency.sourceId,
    target_id: dependency.targetId,
    relation: dependency.relation,
    confidence_class: confidenceClass,
    support_class: supportClass,
  };
}

function bodySchemaToWire(bodySchema) {
  if (!bodySchema || typeof bodySchema !== "object" || Array.isArray(bodySchema) || !exactKeys(bodySchema, INTERNAL_SCHEMA_KEYS)) return null;
  if (![1, 2].includes(bodySchema.schemaVersion) || !["undeveloped", "partial"].includes(bodySchema.state)) return null;
  if (!Array.isArray(bodySchema.parts) || !Array.isArray(bodySchema.dependencies)) return null;
  const maxParts = bodySchema.schemaVersion === 1 ? MAX_SENSORY_PARTS : MAX_TOTAL_PARTS;
  if (bodySchema.parts.length > maxParts || bodySchema.dependencies.length > (bodySchema.schemaVersion === 1 ? 0 : MAX_DEPENDENCIES)) return null;
  if (!bodySchema.globalState || typeof bodySchema.globalState !== "object" || Array.isArray(bodySchema.globalState) || Object.keys(bodySchema.globalState).length !== 0) return null;
  if (bodySchema.state === "undeveloped" && (bodySchema.parts.length !== 0 || bodySchema.dependencies.length !== 0)) return null;
  if (bodySchema.state === "partial" && bodySchema.parts.length === 0) return null;

  const parts = [];
  const seen = new Set();
  let sensoryCount = 0;
  let regionCount = 0;
  for (const part of bodySchema.parts) {
    let wire = null;
    if (part?.kind === "sense") {
      wire = sensePartToWire(part);
      sensoryCount += wire ? 1 : 0;
    } else if (bodySchema.schemaVersion === 2 && part?.kind === "cognitive_region") {
      wire = regionPartToWire(part);
      regionCount += wire ? 1 : 0;
    }
    if (!wire || seen.has(wire.part_id)) return null;
    seen.add(wire.part_id);
    parts.push(wire);
  }
  if (sensoryCount > MAX_SENSORY_PARTS || regionCount > MAX_COGNITIVE_REGIONS) return null;

  const regionIds = new Set(parts.filter(part => part.kind === "cognitive_region").map(part => part.part_id));
  const dependencies = [];
  const seenDependencies = new Set();
  for (const dependency of bodySchema.dependencies) {
    if (bodySchema.schemaVersion !== 2) return null;
    const wire = dependencyToWire(dependency, regionIds);
    if (!wire) return null;
    const key = `${wire.relation}:${wire.source_id}:${wire.target_id}`;
    if (seenDependencies.has(key)) return null;
    seenDependencies.add(key);
    dependencies.push(wire);
  }

  return {
    schema_version: bodySchema.schemaVersion,
    state: bodySchema.state,
    parts,
    dependencies,
    global_state: {},
  };
}

export { boundedBodySchema, bodySchemaToWire };
