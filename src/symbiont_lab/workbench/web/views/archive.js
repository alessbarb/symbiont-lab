/**
 * Archive view entrypoint.
 *
 * Archive is a projection of persisted Lab history, not only the current
 * browser/runtime state. Managed runs and organism metadata are loaded from
 * the same read-only endpoints used by Home.
 */
import { renderArchive } from './archive/render.js';

let rootNode = null;
let runtimeState = null;
let catalog = { runs: [], organisms: [] };
let lastPhysicsState = null;
let refreshToken = 0;

async function jsonRequest(url) {
  const response = await fetch(url, { cache: 'no-store' });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function physicsState(state) {
  return state?.sources?.physics3d?.state ?? null;
}

async function refreshCatalog() {
  const token = ++refreshToken;
  try {
    const [runs, organisms] = await Promise.all([
      jsonRequest('/api/runs'),
      jsonRequest('/api/organisms'),
    ]);
    if (token !== refreshToken) return;
    catalog = {
      runs: runs.items ?? [],
      organisms: organisms.items ?? [],
    };
    if (rootNode) renderArchive(rootNode, runtimeState, catalog);
  } catch (error) {
    if (token !== refreshToken) return;
    if (rootNode) renderArchive(rootNode, runtimeState, catalog, error);
  }
}

export function mount(root, state = null) {
  rootNode = root;
  runtimeState = state;
  lastPhysicsState = physicsState(state);
  renderArchive(root, state, catalog);
  void refreshCatalog();
}

export function update(root, state) {
  if (root !== rootNode) rootNode = root;
  const previous = lastPhysicsState;
  runtimeState = state;
  lastPhysicsState = physicsState(state);
  renderArchive(root, state, catalog);

  const wasRunning = ['starting','running','stopping'].includes(previous);
  const isRunning = ['starting','running','stopping'].includes(lastPhysicsState);
  if (wasRunning && !isRunning) void refreshCatalog();
}

export function unmount() {
  rootNode = null;
  runtimeState = null;
  refreshToken += 1;
}
