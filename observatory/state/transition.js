import { state } from "./store.js";

// Explicit transition boundary for UI/transport metadata. Snapshot data enters
// through commitSnapshotProjection; callers should not mutate it piecemeal.
function updateUiState(patch) {
  Object.assign(state, patch);
  return state;
}

function resetInstanceProjection() {
  updateUiState({ topology: null, cognition: null, bodySchema: null });
}

export { updateUiState, resetInstanceProjection };
