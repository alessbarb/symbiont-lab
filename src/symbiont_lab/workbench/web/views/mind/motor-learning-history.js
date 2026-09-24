/**
 * Bounded observer-side motor learning history. Scientific time is organism tick.
 */
import { motorEpochEvents, motorHistory, snap, streamState, tel } from './state.js';

export const MOTOR_HISTORY_INTERVAL_TICKS = 50;
export const MOTOR_HISTORY_MAX_SAMPLES = 512;
export const MOTOR_TREND_MIN_SAMPLES = 5;
export const MOTOR_TREND_MIN_TICK_SPAN = 250;

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function currentSample() {
  const sm = snap.sensorimotor ?? {};
  return {
    source: streamState.source,
    runId: streamState.runId,
    instanceId: streamState.instanceId,
    tick: finite(tel.tick ?? streamState.snapshotTick),
    embodimentEpoch: finite(tel.embodimentEpoch ?? snap.embodiment?.epoch),
    explorationCoverage: finite(sm.exploration_coverage),
    controllability: finite(sm.best_controllability),
    directionalConsistency: finite(sm.best_directional_consistency),
    sensorimotorPatterns: finite(tel.sensorimotorPatterns ?? sm.known_patterns),
    motorPrimitives: finite(tel.motorPrimitives ?? sm.primitives),
    recurrentCandidates: finite(tel.recurrentPrimitiveCandidates ?? sm.recurrent_primitive_candidates),
    repertoireSize: finite(tel.motorRepertoireSize),
    cognitivePrimitives: finite(tel.cognitiveMotorPrimitives ?? sm.cognitive_primitives),
    primitiveSamples: finite(tel.maxPrimitiveSamples ?? sm.max_primitive_samples),
    competenceCandidates: finite(tel.fullCompetenceGateCandidates ?? sm.full_competence_gate_candidates),
    motorOrigin: tel.motorOrigin ?? null,
    motorOriginDetail: tel.motorOriginDetail ?? null,
    reacclimating: tel.reacclimating ?? snap.embodiment?.reacclimating ?? null,
  };
}

function sameSession(a, b) {
  return Boolean(a && b &&
    a.source === b.source &&
    a.runId === b.runId &&
    a.instanceId === b.instanceId);
}

function structuralChange(a, b) {
  if (!a || !b) return true;
  return (
    a.embodimentEpoch !== b.embodimentEpoch ||
    a.motorPrimitives !== b.motorPrimitives ||
    a.recurrentCandidates !== b.recurrentCandidates ||
    a.cognitivePrimitives !== b.cognitivePrimitives ||
    a.competenceCandidates !== b.competenceCandidates ||
    a.motorOrigin !== b.motorOrigin ||
    a.reacclimating !== b.reacclimating
  );
}

function trimHistory() {
  while (motorHistory.length > MOTOR_HISTORY_MAX_SAMPLES) {
    let removable = 0;
    for (let i = 1; i < motorHistory.length - 1; i += 1) {
      const item = motorHistory[i];
      const prev = motorHistory[i - 1];
      const next = motorHistory[i + 1];
      if (
        sameSession(prev, item) &&
        sameSession(item, next) &&
        !structuralChange(prev, item) &&
        !structuralChange(item, next)
      ) {
        removable = i;
        break;
      }
    }
    motorHistory.splice(removable, 1);
  }
}

export function recordMotorHistory() {
  if (streamState.status !== 'live' || !streamState.coherent) return null;
  const sample = currentSample();
  if (sample.tick == null) return null;
  const previous = motorHistory.at(-1) ?? null;

  if (previous && sameSession(previous, sample) && sample.tick < previous.tick) return null;

  if (
    previous &&
    sameSession(previous, sample) &&
    previous.embodimentEpoch != null &&
    sample.embodimentEpoch != null &&
    previous.embodimentEpoch !== sample.embodimentEpoch
  ) {
    motorEpochEvents.push({
      type: 'reembodiment',
      source: sample.source,
      runId: sample.runId,
      instanceId: sample.instanceId,
      tick: sample.tick,
      fromEpoch: previous.embodimentEpoch,
      toEpoch: sample.embodimentEpoch,
    });
  }

  const mustRecord =
    !previous ||
    !sameSession(previous, sample) ||
    structuralChange(previous, sample) ||
    sample.tick - previous.tick >= MOTOR_HISTORY_INTERVAL_TICKS;
  if (!mustRecord) return null;

  motorHistory.push(sample);
  trimHistory();
  return sample;
}

export function historyForCurrentSession() {
  return motorHistory.filter(item =>
    item.source === streamState.source &&
    item.runId === streamState.runId &&
    item.instanceId === streamState.instanceId
  );
}

export function currentEpochStartTick() {
  const history = historyForCurrentSession();
  const epoch = finite(tel.embodimentEpoch ?? snap.embodiment?.epoch);
  if (epoch == null) return null;
  return history.find(item => item.embodimentEpoch === epoch)?.tick ?? null;
}

export function deriveTrend(key, history = historyForCurrentSession()) {
  const usable = history.filter(item => finite(item[key]) != null);
  if (usable.length < MOTOR_TREND_MIN_SAMPLES) return { state: 'insufficient-data', per1kTicks: null };
  const first = usable[0];
  const last = usable.at(-1);
  const span = last.tick - first.tick;
  if (span < MOTOR_TREND_MIN_TICK_SPAN) return { state: 'insufficient-data', per1kTicks: null };
  const per1kTicks = ((Number(last[key]) - Number(first[key])) / span) * 1000;
  const epsilon = 1e-6;
  return {
    state: per1kTicks > epsilon ? 'rising' : per1kTicks < -epsilon ? 'falling' : 'stable',
    per1kTicks,
  };
}

export function embodimentEpochs(history = historyForCurrentSession()) {
  const epochs = new Map();
  for (const sample of history) {
    if (sample.embodimentEpoch == null) continue;
    const entry = epochs.get(sample.embodimentEpoch) ?? {
      epoch: sample.embodimentEpoch,
      startTick: sample.tick,
      endTick: sample.tick,
      startingControllability: sample.controllability,
      peakControllability: sample.controllability,
      startingConsistency: sample.directionalConsistency,
      peakConsistency: sample.directionalConsistency,
      startingCognitivePrimitives: sample.cognitivePrimitives,
      endingCognitivePrimitives: sample.cognitivePrimitives,
      tickToFirstRecurrent: null,
      tickToFirstCognitivePrimitive: null,
      tickToFirstCognitiveControl: null,
    };
    entry.endTick = sample.tick;
    if (sample.controllability != null) {
      entry.peakControllability = Math.max(entry.peakControllability ?? -Infinity, sample.controllability);
    }
    if (sample.directionalConsistency != null) {
      entry.peakConsistency = Math.max(entry.peakConsistency ?? -Infinity, sample.directionalConsistency);
    }
    entry.endingCognitivePrimitives = sample.cognitivePrimitives;
    if (entry.tickToFirstRecurrent == null && (sample.recurrentCandidates ?? 0) > 0) {
      entry.tickToFirstRecurrent = sample.tick - entry.startTick;
    }
    if (entry.tickToFirstCognitivePrimitive == null && (sample.cognitivePrimitives ?? 0) > 0) {
      entry.tickToFirstCognitivePrimitive = sample.tick - entry.startTick;
    }
    const origin = String(sample.motorOrigin ?? '').toLowerCase();
    if (entry.tickToFirstCognitiveControl == null && (origin.includes('cognition') || origin.includes('primitive'))) {
      entry.tickToFirstCognitiveControl = sample.tick - entry.startTick;
    }
    epochs.set(sample.embodimentEpoch, entry);
  }
  return [...epochs.values()];
}
