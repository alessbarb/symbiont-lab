/**
 * Body view entrypoint.
 *
 * Humanoid rendering lives in ./body/viewer.js.
 */
import { HumanoidViewer } from './body/viewer.js';

export { HumanoidViewer };

let globalInstance = null;

export function mount(root) {
  if (globalInstance) unmount();
  globalInstance = new HumanoidViewer(root);
  return globalInstance;
}

export function unmount() {
  if (globalInstance) {
    globalInstance.unmount();
    globalInstance = null;
  }
}
