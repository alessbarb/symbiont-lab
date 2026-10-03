/**
 * Lab view entrypoint.
 *
 * Rendering, forms and network actions live in ./lab/.
 */
import { renderLab } from './lab/render.js';

export function mount(root, state = null) {
  renderLab(root, state);
}

export function update(root, state) {
  renderLab(root, state);
}

export function unmount() {}
