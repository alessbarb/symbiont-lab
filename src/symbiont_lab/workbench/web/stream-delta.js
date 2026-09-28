const CONTRACT = 'observer-live-delta-v1';

function clone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function unescapePointer(segment) {
  return segment.replace(/~1/g, '/').replace(/~0/g, '~');
}

function splitPointer(path) {
  if (path === '') return [];
  if (typeof path !== 'string' || !path.startsWith('/')) {
    throw new Error(`invalid observation delta path: ${path}`);
  }
  return path.slice(1).split('/').map(unescapePointer);
}

function resolveParent(state, path) {
  const parts = splitPointer(path);
  if (parts.length === 0) throw new Error('root pointer has no parent');
  let parent = state;
  for (const segment of parts.slice(0, -1)) {
    if (Array.isArray(parent)) {
      const index = Number(segment);
      if (!Number.isInteger(index) || index < 0 || index >= parent.length) {
        throw new Error('observation delta array path is invalid');
      }
      parent = parent[index];
    } else if (parent && typeof parent === 'object') {
      if (!Object.hasOwn(parent, segment)) throw new Error('observation delta path is absent');
      parent = parent[segment];
    } else {
      throw new Error('observation delta descends through scalar state');
    }
  }
  return [parent, parts.at(-1)];
}

function applyPatch(state, operations) {
  let next = clone(state);
  for (const operation of operations ?? []) {
    const path = String(operation?.path ?? '');
    if (operation?.op === 'set') {
      const value = clone(operation.value);
      if (path === '') {
        next = value;
        continue;
      }
      const [parent, leaf] = resolveParent(next, path);
      if (Array.isArray(parent)) {
        const index = Number(leaf);
        if (!Number.isInteger(index) || index < 0 || index >= parent.length) {
          throw new Error('observation delta array set index is invalid');
        }
        parent[index] = value;
      } else if (parent && typeof parent === 'object') {
        parent[leaf] = value;
      } else {
        throw new Error('observation delta cannot set child on scalar');
      }
      continue;
    }
    if (operation?.op === 'remove') {
      if (path === '') {
        next = null;
        continue;
      }
      const [parent, leaf] = resolveParent(next, path);
      if (Array.isArray(parent)) {
        const index = Number(leaf);
        if (!Number.isInteger(index) || index < 0 || index >= parent.length) {
          throw new Error('observation delta array remove index is invalid');
        }
        parent.splice(index, 1);
      } else if (parent && typeof parent === 'object' && Object.hasOwn(parent, leaf)) {
        delete parent[leaf];
      } else {
        throw new Error('observation delta remove target is absent');
      }
      continue;
    }
    throw new Error(`unsupported observation delta operation: ${operation?.op}`);
  }
  return next;
}

export class LiveObservationDecoder {
  constructor() {
    this.states = new Map();
    this.revisions = new Map();
    this.waitingForAnchor = new Set();
  }

  reset() {
    this.states.clear();
    this.revisions.clear();
    this.waitingForAnchor.clear();
  }

  decode(payload) {
    if (!payload || payload.type !== 'observation_delta') return payload;
    if (payload.contract !== CONTRACT || typeof payload.channel !== 'string') return null;

    const channel = payload.channel;
    const revision = Number(payload.revision);
    if (!Number.isInteger(revision) || revision < 1) return null;

    if (payload.kind === 'anchor') {
      const state = clone(payload.state);
      if (!state || state.type !== channel) return null;
      this.states.set(channel, state);
      this.revisions.set(channel, revision);
      this.waitingForAnchor.delete(channel);
      return state;
    }

    if (payload.kind !== 'delta') return null;
    if (this.waitingForAnchor.has(channel)) return null;

    const knownRevision = this.revisions.get(channel);
    const baseRevision = Number(payload.base_revision);
    if (
      !Number.isInteger(baseRevision) ||
      knownRevision === undefined ||
      baseRevision !== knownRevision ||
      revision !== baseRevision + 1
    ) {
      // Do not risk rendering a state assembled across a transport gap.
      // Periodic anchors or a fresh subscription will recover this channel.
      this.waitingForAnchor.add(channel);
      this.states.delete(channel);
      this.revisions.delete(channel);
      return null;
    }

    try {
      const next = applyPatch(this.states.get(channel), payload.patch);
      if (!next || next.type !== channel) throw new Error('channel identity changed');
      this.states.set(channel, next);
      this.revisions.set(channel, revision);
      return next;
    } catch {
      this.waitingForAnchor.add(channel);
      this.states.delete(channel);
      this.revisions.delete(channel);
      return null;
    }
  }
}

export { CONTRACT as LIVE_OBSERVATION_DELTA_CONTRACT, applyPatch };
