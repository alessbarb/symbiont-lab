/**
 * Observability-state contract for cognitive panels.
 *
 * An empty panel is ambiguous: the mechanism may not exist, be switched off,
 * not be ready, simply have had nothing to do, or the telemetry that would
 * show it may be missing, old or malformed. This module turns the facts the
 * observer already has into exactly one named state, so a panel never has to
 * guess and never presents "no data" as "nothing there".
 *
 * It is a pure function of its inputs. It reads no DOM, fetches nothing and
 * cannot affect the organism.
 */

export const OBSERVABILITY_STATES = Object.freeze({
  ABSENT: 'absent',
  DISABLED: 'disabled',
  NOT_READY: 'not_ready',
  IDLE: 'idle',
  EMPTY: 'empty',
  ACTIVE: 'active',
  UNAVAILABLE: 'unavailable',
  STALE: 'stale',
  ERROR: 'error',
});

const LIFECYCLES = new Set(['absent', 'disabled', 'not_ready', 'idle', 'active']);

const LABELS = Object.freeze({
  absent: 'Subsystem absent',
  disabled: 'Subsystem disabled',
  not_ready: 'Enabled, not ready',
  idle: 'Ready, no activity in this frame',
  empty: 'Active, nothing produced',
  active: 'Active',
  unavailable: 'Telemetry unavailable',
  stale: 'Telemetry stale',
  error: 'Telemetry error',
});

const REASONS = Object.freeze({
  runtime_has_no_generative_cognition: 'this runtime has no generative cognition',
  zero_budget: 'its budget is zero',
  no_generative_model: 'no generative model is registered',
  no_pass_yet: 'it has not run yet',
  no_pass_this_tick: 'it did not run on this tick',
  pass_without_work: 'it ran and found nothing to do',
  pass_with_work: 'it ran on this tick',
});

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function result(state, detail, extra = {}) {
  return { state, label: LABELS[state], detail, current: false, ...extra };
}

/**
 * @param {object} input
 * @param {*} input.status       lifecycle status reported by the observer (organism facts)
 * @param {*} input.payload      the subsystem snapshot, if any
 * @param {object} input.stream  { status, stale } of the stream the frame came from
 * @param {number|null} input.frameTick  tick of the frame being rendered
 * @param {number|null} input.liveTick   newest tick the observer has seen
 * @param {boolean} input.replay  true when a historical frame is shown on purpose
 * @param {(payload: object) => boolean} input.hasContent  whether an active payload is non-empty
 */
export function classifyObservability({
  status,
  payload,
  stream = null,
  frameTick = null,
  liveTick = null,
  replay = false,
  hasContent = () => true,
} = {}) {
  const S = OBSERVABILITY_STATES;

  if (payload !== null && payload !== undefined && !isPlainObject(payload)) {
    return result(S.ERROR, 'the snapshot is not an object');
  }
  if (status !== null && status !== undefined) {
    if (!isPlainObject(status) || !LIFECYCLES.has(status.lifecycle)) {
      return result(S.ERROR, 'the lifecycle status is malformed');
    }
  }

  // A frame shown on purpose from history is not stale; a live view is stale
  // when its stream says so or when it lags behind the newest tick seen.
  if (!replay) {
    if (stream && (stream.status === 'disconnected' || stream.status === 'waiting')) {
      return result(S.UNAVAILABLE, `stream ${stream.status}`);
    }
    if (stream && (stream.stale === true || stream.status === 'stale')) {
      return result(S.STALE, 'the stream stopped delivering frames');
    }
    if (
      Number.isFinite(frameTick) &&
      Number.isFinite(liveTick) &&
      liveTick > frameTick
    ) {
      return result(S.STALE, `frame t${frameTick} is behind t${liveTick}`);
    }
  }

  if (status === null || status === undefined) {
    // Older runs report a snapshot without a lifecycle status. The snapshot is
    // shown, but without organism facts nothing can be said about its absence.
    if (payload) {
      return hasContent(payload)
        ? result(S.ACTIVE, 'lifecycle not reported by this run', { current: true })
        : result(S.EMPTY, 'lifecycle not reported by this run', { current: true });
    }
    return result(S.UNAVAILABLE, 'this run does not report the subsystem');
  }

  const reason = REASONS[status.reason] ?? String(status.reason ?? '');
  switch (status.lifecycle) {
    case 'absent':
      return result(S.ABSENT, reason, { current: true });
    case 'disabled':
      return result(S.DISABLED, reason, { current: true });
    case 'not_ready':
      return result(S.NOT_READY, reason, { current: true });
    case 'idle':
      return result(S.IDLE, reason, { current: true });
    default:
      if (!payload) return result(S.ERROR, 'active without a snapshot');
      return hasContent(payload)
        ? result(S.ACTIVE, reason, { current: true })
        : result(S.EMPTY, 'it ran and produced an empty result', { current: true });
  }
}

/**
 * Qualify a "nothing here yet" message with what the stream can vouch for.
 *
 * Panels that show accumulated data (milestones, phenotype, topology) have no
 * subsystem lifecycle to report, but their emptiness is still ambiguous: it is
 * a valid empty state only while a live stream is delivering frames.
 */
export function qualifyEmpty(message, stream = null, { replay = false } = {}) {
  const S = OBSERVABILITY_STATES;
  if (!replay && stream) {
    if (stream.status === 'disconnected' || stream.status === 'waiting') {
      return {
        state: S.UNAVAILABLE,
        text: `${LABELS.unavailable} (stream ${stream.status}) — nothing can be said about this panel.`,
      };
    }
    if (stream.stale === true || stream.status === 'stale') {
      return {
        state: S.STALE,
        text: `${LABELS.stale} — the last frames showed: ${message}`,
      };
    }
  }
  return { state: S.EMPTY, text: message };
}

/** Write a qualified empty state into an element and tag it for styling/tests. */
export function applyEmptyState(element, message, stream = null, options = {}) {
  const qualified = qualifyEmpty(message, stream, options);
  element.textContent = qualified.text;
  element.dataset.observability = qualified.state;
  return qualified.state;
}
