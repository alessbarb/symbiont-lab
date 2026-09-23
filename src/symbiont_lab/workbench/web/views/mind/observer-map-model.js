/**
 * Pure observer-map analysis for the Mind view.
 *
 * Nothing here is organism-owned state. Inputs are passive observations and
 * observer-derived analysis; outputs are coordinates in an analytical display.
 */

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finiteNumber(value, 0)));
}

function classRatio(value, maximum) {
  const number = finiteNumber(value, 0);
  return maximum > 0 ? clamp01(number / maximum) : 0;
}

export function computeObserverMapCoordinates({
  senses = [],
  cognition = {},
  observerAnalysis = {},
} = {}) {
  const explicitActivity = senses.filter(sense => typeof sense?.active === 'boolean');
  const activeRatio = explicitActivity.length
    ? explicitActivity.filter(sense => sense.active).length / explicitActivity.length
    : 0;

  // Activation/error classes are observer-derived whenever the canonical
  // observation boundary supplies them separately.
  const activationClasses =
    observerAnalysis?.activationClasses ?? cognition?.activationClasses ?? {};
  const predictionErrors =
    observerAnalysis?.predictionErrors ?? cognition?.predictionErrors ?? {};

  const activationValues = Object.values(activationClasses)
    .map(value => classRatio(value, 15));
  const meanActivation = activationValues.length
    ? activationValues.reduce((sum, value) => sum + value, 0) / activationValues.length
    : 0;

  const readoutValues = Object.values(cognition?.readouts ?? {})
    .map(value => Math.min(1, Math.abs(finiteNumber(value, 0))));
  const meanReadout = readoutValues.length
    ? readoutValues.reduce((sum, value) => sum + value, 0) / readoutValues.length
    : 0;

  const activityNorm = clamp01(
    activeRatio * 0.45 +
    meanActivation * 0.35 +
    meanReadout * 0.20
  );

  const errorMap = {
    zero: 0,
    trace: 0.08,
    low: 0.25,
    medium: 0.55,
    high: 0.8,
    extreme: 1,
  };
  const errorValues = Object.values(predictionErrors)
    .map(value => errorMap[value] ?? 0);
  const meanError = errorValues.length
    ? errorValues.reduce((sum, value) => sum + value, 0) / errorValues.length
    : 0;

  const failurePenalty = clamp01(
    finiteNumber(cognition?.safetyState?.consecutiveFailures, 0) / 4
  );
  const predictiveTension = clamp01(meanError * 0.8 + failurePenalty * 0.2);

  return {
    x: (activityNorm - 0.5) * 520,
    y: (0.5 - predictiveTension) * 440,
    activityNorm,
    predictiveTension,
    explicitActivityCoverage: senses.length
      ? explicitActivity.length / senses.length
      : 0,
  };
}

export function evaluateObserverRegime(position, zones) {
  if (!zones?.length) return null;

  let minDistance = Infinity;
  let nearest = zones[0];
  for (const zone of zones) {
    const distance = Math.hypot(position.x - zone.x, position.y - zone.y);
    if (distance < minDistance) {
      minDistance = distance;
      nearest = zone;
    }
  }

  const distancePct = Math.max(
    0,
    Math.min(100, Math.round((minDistance / 300) * 100)),
  );
  const insideReference = minDistance <= nearest.radius * 1.35;

  return {
    nearest,
    minD: minDistance,
    distancePct,
    insideReference,
  };
}
