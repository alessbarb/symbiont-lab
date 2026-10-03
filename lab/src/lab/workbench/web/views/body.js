/**
 * Shared entrypoint for the Embodiment and World routes.
 *
 * Morphology-neutral rendering lives in ./body/viewer.js; the route decides
 * the product domain (see ADR-0008).
 */
import { BodyViewer, HumanoidViewer } from './body/viewer.js';

export { BodyViewer, HumanoidViewer };

let globalInstance = null;

export function mount(root, _state = null, { domain = 'world' } = {}) {
  if (globalInstance) unmount();
  globalInstance = new BodyViewer(root, undefined, { domain });
  return globalInstance;
}

export function update() {}

export function unmount() {
  if (globalInstance) {
    globalInstance.unmount();
    globalInstance = null;
  }
}
