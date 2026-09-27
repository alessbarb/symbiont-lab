/** Pure revision reconciliation; independent of Three.js and physics internals. */
export function reconcileWorld(current, event) {
  if (event?.contract !== 'body-in-world-v1') return { state: current, gap: true };
  if (event.kind === 'snapshot') {
    if (current?.world_id === event.world_id && current.revision >= event.revision) return { state: current, gap: false };
    return { state: structuredClone(event), gap: false };
  }
  if (current?.world_id === event.world_id && event.revision <= current.revision) return { state: current, gap: false };
  if (!current || current.world_id !== event.world_id || current.revision !== event.base_revision) return { state: current, gap: true };
  const entities = { ...current.entities };
  for (const id of event.removals ?? []) delete entities[id];
  Object.assign(entities, structuredClone(event.upserts ?? {}));
  for (const [id, transform] of Object.entries(event.transforms ?? {})) {
    if (!entities[id]) return { state: current, gap: true };
    entities[id] = { ...entities[id], ...transform };
  }
  return { state: { ...current, ...structuredClone(event.changes ?? {}), entities, revision: event.revision }, gap: false };
}

export function receptorStatus(evidence) {
  if (!evidence) return 'unavailable';
  if (evidence.percept_emitted) return 'perceived';
  if (evidence.sampled) return 'sampled';
  if (evidence.sampled == null) return 'unavailable';
  return 'unsampled';
}
