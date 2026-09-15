const RECENCY_LABELS = ["current", "short idle", "idle", "long idle", "dormant"];

function undevelopedProjection() {
  return { state: "undeveloped", parts: [], dependencies: [] };
}

function validClass(value, maximum) {
  return Number.isInteger(value) && value >= 0 && value <= maximum;
}

function ratio(value, maximum) {
  return maximum > 0 ? Math.max(0, Math.min(1, value / maximum)) : 0;
}

function projectSelfSchema(bodySchema) {
  if (!bodySchema || typeof bodySchema !== "object" || bodySchema.state !== "partial") {
    return undevelopedProjection();
  }
  if (!Array.isArray(bodySchema.parts) || bodySchema.parts.length === 0 || bodySchema.parts.length > 256) {
    return undevelopedProjection();
  }
  if (!Array.isArray(bodySchema.dependencies) || bodySchema.dependencies.length !== 0) {
    return undevelopedProjection();
  }
  if (!bodySchema.globalState || typeof bodySchema.globalState !== "object" || Object.keys(bodySchema.globalState).length !== 0) {
    return undevelopedProjection();
  }

  const parts = [];
  const seen = new Set();
  for (const part of bodySchema.parts) {
    if (!part || part.kind !== "sense" || typeof part.partId !== "string" || !/^part\.sense\.[0-9a-f]{32}$/.test(part.partId) || seen.has(part.partId)) {
      return undevelopedProjection();
    }
    if (
      !validClass(part.existenceConfidenceClass, 15)
      || !validClass(part.healthClass, 15)
      || !validClass(part.confidenceClass, 15)
      || !validClass(part.costClass, 15)
      || !validClass(part.maturityClass, 7)
      || !validClass(part.recencyClass, 4)
    ) {
      return undevelopedProjection();
    }
    seen.add(part.partId);
    parts.push({
      id: part.partId,
      kind: "sense",
      existence: ratio(part.existenceConfidenceClass, 15),
      health: ratio(part.healthClass, 15),
      confidence: ratio(part.confidenceClass, 15),
      cost: ratio(part.costClass, 15),
      maturity: ratio(part.maturityClass, 7),
      recencyClass: part.recencyClass,
      recency: RECENCY_LABELS[part.recencyClass],
    });
  }

  return {
    state: "partial",
    parts,
    dependencies: [],
  };
}

export { projectSelfSchema };
