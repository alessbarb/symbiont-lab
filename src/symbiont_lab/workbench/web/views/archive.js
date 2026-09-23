/**
 * Archive view entrypoint.
 */
import { renderArchive } from './archive/render.js';

export function mount(root, state = null) {
  renderArchive(root, state);
}

export function update(root, state) {
  renderArchive(root, state);
}
