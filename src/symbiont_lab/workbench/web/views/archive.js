/**
 * Archive view entrypoint.
 */
import { renderArchive } from './archive/render.js';

let lastSignature = null;

function archiveSignature(state) {
  const records = state?.records ?? [];
  const studyRecords = state?.study?.records ?? [];
  return `${records.length}:${records[0]?.record_id ?? ''}:${records[records.length - 1]?.record_id ?? ''}|${studyRecords.length}:${studyRecords[0]?.record_id ?? ''}`;
}

export function mount(root, state = null) {
  lastSignature = archiveSignature(state);
  renderArchive(root, state);
}

export function update(root, state) {
  const sig = archiveSignature(state);
  if (sig === lastSignature) return;
  lastSignature = sig;
  renderArchive(root, state);
}

export function unmount() {
  lastSignature = null;
}
