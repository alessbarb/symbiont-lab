const RECENCY_LABELS = ["current", "short idle", "idle", "long idle", "dormant"];
const SENSE_KEYS = new Set([
  "partId",
  "kind",
  "existenceConfidenceClass",
  "healthClass",
  "confidenceClass",
  "costClass",
  "maturityClass",
  "recencyClass",
]);
const REGION_KEYS = new Set([
  "partId",
  "kind",
  "existenceConfidenceClass",
  "confidenceClass",
  "activityClass",
  "maturityClass",
  "recencyClass",
]);
const DEPENDENCY_KEYS = new Set([
  "sourceId",
  "targetId",
  "relation",
  "confidenceClass",
  "supportClass",
]);
const RELATIONS = new Set(["co_acts_with", "precedes"]);

function undevelopedProjection() {
  return { state: "undeveloped", parts: [], dependencies: [] };
}

function exactKeys(value, allowed) {
  return Object.keys(value).every(key => allowed.has(key));
}

function validClass(value, maximum) {
  return Number.isInteger(value) && value >= 0 && value <= maximum;
}

function ratio(value, maximum) {
  return maximum > 0 ? Math.max(0, Math.min(1, value / maximum)) : 0;
}

function projectSense(part) {
  if (!part || typeof part !== "object" || Array.isArray(part) || !exactKeys(part, SENSE_KEYS)) return null;
  if (part.kind !== "sense" || typeof part.partId !== "string" || !/^part\.sense\.[0-9a-f]{32}$/.test(part.partId)) return null;
  if (
    !validClass(part.existenceConfidenceClass, 15)
    || !validClass(part.healthClass, 15)
    || !validClass(part.confidenceClass, 15)
    || !validClass(part.costClass, 15)
    || !validClass(part.maturityClass, 7)
    || !validClass(part.recencyClass, 4)
  ) return null;
  return {
    id: part.partId,
    kind: "sense",
    existence: ratio(part.existenceConfidenceClass, 15),
    health: ratio(part.healthClass, 15),
    confidence: ratio(part.confidenceClass, 15),
    cost: ratio(part.costClass, 15),
    maturity: ratio(part.maturityClass, 7),
    recencyClass: part.recencyClass,
    recency: RECENCY_LABELS[part.recencyClass],
  };
}

function projectRegion(part) {
  if (!part || typeof part !== "object" || Array.isArray(part) || !exactKeys(part, REGION_KEYS)) return null;
  if (part.kind !== "cognitive_region" || typeof part.partId !== "string" || !/^part\.region\.[0-9a-f]{32}$/.test(part.partId)) return null;
  if (
    !validClass(part.existenceConfidenceClass, 15)
    || !validClass(part.confidenceClass, 15)
    || !validClass(part.activityClass, 15)
    || !validClass(part.maturityClass, 7)
    || !validClass(part.recencyClass, 4)
  ) return null;
  return {
    id: part.partId,
    kind: "cognitive_region",
    existence: ratio(part.existenceConfidenceClass, 15),
    confidence: ratio(part.confidenceClass, 15),
    activity: ratio(part.activityClass, 15),
    maturity: ratio(part.maturityClass, 7),
    recencyClass: part.recencyClass,
    recency: RECENCY_LABELS[part.recencyClass],
  };
}

function projectSelfSchema(bodySchema) {
  if (!bodySchema || typeof bodySchema !== "object" || ![1, 2].includes(bodySchema.schemaVersion)) {
    return undevelopedProjection();
  }
  if (bodySchema.state === "undeveloped") {
    if (Array.isArray(bodySchema.parts) && bodySchema.parts.length === 0 && Array.isArray(bodySchema.dependencies) && bodySchema.dependencies.length === 0) {
      return undevelopedProjection();
    }
    return undevelopedProjection();
  }
  if (bodySchema.state !== "partial" || !Array.isArray(bodySchema.parts) || bodySchema.parts.length === 0) {
    return undevelopedProjection();
  }
  const maxParts = bodySchema.schemaVersion === 1 ? 256 : 288;
  if (bodySchema.parts.length > maxParts || !Array.isArray(bodySchema.dependencies)) return undevelopedProjection();
  if (bodySchema.dependencies.length > (bodySchema.schemaVersion === 1 ? 0 : 256)) return undevelopedProjection();
  if (!bodySchema.globalState || typeof bodySchema.globalState !== "object" || Array.isArray(bodySchema.globalState) || Object.keys(bodySchema.globalState).length !== 0) {
    return undevelopedProjection();
  }

  const parts = [];
  const seen = new Set();
  let sensoryCount = 0;
  let regionCount = 0;
  for (const part of bodySchema.parts) {
    let projected = null;
    if (part?.kind === "sense") {
      projected = projectSense(part);
      sensoryCount += projected ? 1 : 0;
    } else if (bodySchema.schemaVersion === 2 && part?.kind === "cognitive_region") {
      projected = projectRegion(part);
      regionCount += projected ? 1 : 0;
    }
    if (!projected || seen.has(projected.id)) return undevelopedProjection();
    seen.add(projected.id);
    parts.push(projected);
  }
  if (sensoryCount > 256 || regionCount > 32) return undevelopedProjection();

  const regionIds = new Set(parts.filter(part => part.kind === "cognitive_region").map(part => part.id));
  const dependencies = [];
  const seenDependencies = new Set();
  for (const dependency of bodySchema.dependencies) {
    if (bodySchema.schemaVersion !== 2 || !dependency || typeof dependency !== "object" || Array.isArray(dependency) || !exactKeys(dependency, DEPENDENCY_KEYS)) {
      return undevelopedProjection();
    }
    if (
      typeof dependency.sourceId !== "string"
      || typeof dependency.targetId !== "string"
      || dependency.sourceId === dependency.targetId
      || !regionIds.has(dependency.sourceId)
      || !regionIds.has(dependency.targetId)
      || !RELATIONS.has(dependency.relation)
      || (dependency.relation === "co_acts_with" && dependency.sourceId >= dependency.targetId)
      || !validClass(dependency.confidenceClass, 15)
      || !validClass(dependency.supportClass, 15)
    ) return undevelopedProjection();
    const key = `${dependency.relation}:${dependency.sourceId}:${dependency.targetId}`;
    if (seenDependencies.has(key)) return undevelopedProjection();
    seenDependencies.add(key);
    dependencies.push({
      sourceId: dependency.sourceId,
      targetId: dependency.targetId,
      relation: dependency.relation,
      confidence: ratio(dependency.confidenceClass, 15),
      support: ratio(dependency.supportClass, 15),
    });
  }

  parts.sort((a, b) => a.kind === b.kind ? (a.id < b.id ? -1 : a.id > b.id ? 1 : 0) : (a.kind < b.kind ? -1 : 1));
  dependencies.sort((a, b) => {
    const left = `${a.relation}:${a.sourceId}:${a.targetId}`;
    const right = `${b.relation}:${b.sourceId}:${b.targetId}`;
    return left < right ? -1 : left > right ? 1 : 0;
  });
  return { state: "partial", parts, dependencies };
}

export { projectSelfSchema };
