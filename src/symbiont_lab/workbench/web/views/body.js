/**
 * Body view entrypoint.
 *
 * Morphology-neutral rendering lives in ./body/viewer.js.
 */
import { BodyViewer, HumanoidViewer } from './body/viewer.js';

export { BodyViewer, HumanoidViewer };

let globalInstance = null;

export function mount(root) {
  if (globalInstance) unmount();
  globalInstance = new BodyViewer(root);
  return globalInstance;
}

export function update() {}

export function unmount() {
  if (globalInstance) {
    globalInstance.unmount();
    globalInstance = null;
  }
}
