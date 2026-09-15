function discreteClass(value, maximum) {
  return Number.isInteger(value) && value >= 0 && value <= maximum ? value : null;
}

function boundedBodySchema(bodySchema) {
  if (!bodySchema || typeof bodySchema !== "object" || Array.isArray(bodySchema)) return null;
  if (bodySchema.schema_version !== 1 || bodySchema.id_salt !== undefined) return null;
  if (!Array.isArray(bodySchema.parts) || bodySchema.parts.length > 256) return null;
  if (!Array.isArray(bodySchema.dependencies) || bodySchema.dependencies.length !== 0) return null;
  if (!bodySchema.global_state || typeof bodySchema.global_state !== "object" || Array.isArray(bodySchema.global_state) || Object.keys(bodySchema.global_state).length !== 0) return null;
  if (!["undeveloped", "partial"].includes(bodySchema.state)) return null;
  if (bodySchema.state === "undeveloped" && bodySchema.parts.length !== 0) return null;
  if (bodySchema.state === "partial" && bodySchema.parts.length === 0) return null;

  const parts = [];
  for (const raw of bodySchema.parts) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw) || raw.kind !== "sense") return null;
    if (typeof raw.part_id !== "string" || !/^part\.sense\.[0-9a-f]{32}$/.test(raw.part_id)) return null;
    const existenceConfidenceClass = discreteClass(raw.existence_confidence_class, 15);
    const healthClass = discreteClass(raw.health_class, 15);
    const confidenceClass = discreteClass(raw.confidence_class, 15);
    const costClass = discreteClass(raw.cost_class, 15);
    const maturityClass = discreteClass(raw.maturity_class, 7);
    const recencyClass = discreteClass(raw.recency_class, 4);
    if ([existenceConfidenceClass, healthClass, confidenceClass, costClass, maturityClass, recencyClass].some(value => value === null)) return null;
    parts.push({
      partId: raw.part_id,
      kind: "sense",
      existenceConfidenceClass,
      healthClass,
      confidenceClass,
      costClass,
      maturityClass,
      recencyClass,
    });
  }

  return {
    schemaVersion: 1,
    state: bodySchema.state,
    parts,
    dependencies: [],
    globalState: {},
  };
}

function bodySchemaToWire(bodySchema) {
  if (!bodySchema || !["undeveloped", "partial"].includes(bodySchema.state) || !Array.isArray(bodySchema.parts)) return null;
  if (!Array.isArray(bodySchema.dependencies) || bodySchema.dependencies.length !== 0) return null;
  if (!bodySchema.globalState || typeof bodySchema.globalState !== "object" || Object.keys(bodySchema.globalState).length !== 0) return null;
  if (bodySchema.state === "undeveloped" && bodySchema.parts.length !== 0) return null;
  if (bodySchema.state === "partial" && bodySchema.parts.length === 0) return null;

  const parts = [];
  for (const part of bodySchema.parts.slice(0, 256)) {
    if (!part || part.kind !== "sense" || typeof part.partId !== "string" || !/^part\.sense\.[0-9a-f]{32}$/.test(part.partId)) return null;
    const existenceConfidenceClass = discreteClass(part.existenceConfidenceClass, 15);
    const healthClass = discreteClass(part.healthClass, 15);
    const confidenceClass = discreteClass(part.confidenceClass, 15);
    const costClass = discreteClass(part.costClass, 15);
    const maturityClass = discreteClass(part.maturityClass, 7);
    const recencyClass = discreteClass(part.recencyClass, 4);
    if ([existenceConfidenceClass, healthClass, confidenceClass, costClass, maturityClass, recencyClass].some(value => value === null)) return null;
    parts.push({
      part_id: part.partId,
      kind: "sense",
      existence_confidence_class: existenceConfidenceClass,
      health_class: healthClass,
      confidence_class: confidenceClass,
      cost_class: costClass,
      maturity_class: maturityClass,
      recency_class: recencyClass,
    });
  }

  return {
    schema_version: 1,
    state: bodySchema.state,
    parts,
    dependencies: [],
    global_state: {},
  };
}

export { boundedBodySchema, bodySchemaToWire };
