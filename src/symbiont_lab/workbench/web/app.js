import { mount as mountHome, update as updateHome, unmount as unmountHome } from './views/home.js';
import { mount as mountMind, update as updateMind, unmount as unmountMind } from './views/mind.js';
import { mount as mountLab, update as updateLab, unmount as unmountLab } from './views/lab.js';
import { mount as mountArchive, update as updateArchive, unmount as unmountArchive } from './views/archive.js';
import { RuntimeStatePoller } from './runtime-state.js';

const ROOT_ID = 'view-root';
const ROUTE_ALIASES = { lab: 'experiments' };
const ROUTES = {
  home: {
    mount: (root, state) => mountHome(root, state),
    update: (root, state) => updateHome(root, state),
    unmount: () => unmountHome(),
  },
  experiments: {
    mount: (root, state) => mountLab(root, state),
    update: (root, state) => updateLab(root, state),
    unmount: () => unmountLab(),
  },
  mind: {
    mount: (root, state) => mountMind(root, state),
    update: (root, state) => updateMind(root, state),
    unmount: () => unmountMind(),
  },
  archive: {
    mount: (root, state) => mountArchive(root, state),
    update: (root, state) => updateArchive(root, state),
    unmount: () => unmountArchive(),
  },
  body: {
    load: () => import('./views/body.js'),
  },
};

let currentView = 'home';
let currentState = null;
let mountedView = null;
let mountedModule = null;
let loadToken = 0;

function rootNode() {
  return document.getElementById(ROOT_ID);
}

function setStatus(text) {
  const status = document.getElementById('sb-status');
  if (status) status.textContent = text;
}

function setRunState(text) {
  const node = document.getElementById('sb-run');
  if (node) node.textContent = text;
}

function setDetail(text, visible = true) {
  const detail = document.getElementById('sb-detail');
  const sep = document.getElementById('sb-sep2');
  if (detail) {
    detail.textContent = text;
    detail.hidden = !visible;
  }
  if (sep) sep.hidden = !visible;
}

function updateStatusBar(state) {
  if (!state) return;
  const physics = state.sources?.physics3d ?? {};
  const physicsRunning = ['starting', 'running', 'stopping'].includes(physics.state);
  const running = Boolean(state.running || state.study?.running || physicsRunning);

  setStatus(running ? 'running' : 'ready');
  setRunState(
    physicsRunning
      ? (physics.run_id || 'Physics3D')
      : state.running
        ? `run #${state.experiment_number ?? 0}`
        : state.study?.running
          ? `study ${state.study.phase ?? 'active'}`
          : 'no active run',
  );

  const current = state.current ?? {};
  if (current.step != null && current.total_steps) {
    const pct = ((current.step / current.total_steps) * 100).toFixed(1);
    setDetail(`${pct}% complete`, true);
  } else if (state.study?.phase) {
    setDetail(state.study.phase, true);
  } else {
    setDetail('', false);
  }
}

function normalizeRoute(value) {
  const route = String(value ?? '').replace(/^#/, '').trim();
  const normalized = ROUTE_ALIASES[route] ?? route;
  return Object.hasOwn(ROUTES, normalized) ? normalized : 'home';
}

function parseHash() {
  return normalizeRoute(window.location.hash);
}

function activateRail(viewId) {
  document.querySelectorAll('.rail-item').forEach((node) => {
    const route = normalizeRoute(node.hash);
    const active = route === viewId;
    node.classList.toggle('active', active);
    if (active) node.setAttribute('aria-current', 'page');
    else node.removeAttribute('aria-current');
  });
}

function focusViewRoot() {
  const root = rootNode();
  if (!root) return;
  requestAnimationFrame(() => root.focus({ preventScroll: true }));
}

function clearMountedView() {
  const root = rootNode();
  if (!root) return;

  loadToken += 1;
  try {
    mountedModule?.unmount?.();
  } finally {
    mountedModule = null;
    mountedView = null;
    root.replaceChildren();
  }
}

function renderFailure(message, error = null) {
  const root = rootNode();
  if (!root) return;
  root.replaceChildren();
  const failure = document.createElement('div');
  failure.className = 'empty-state';
  failure.textContent = message;
  root.appendChild(failure);
  if (error) setDetail(String(error), true);
}

async function mountRoute(viewId) {
  const root = rootNode();
  if (!root) return;

  clearMountedView();
  mountedView = viewId;
  const route = ROUTES[viewId];
  const token = ++loadToken;

  if (route.load) {
    const loading = document.createElement('div');
    loading.className = 'empty-state';
    loading.textContent = 'Loading 3D body viewer…';
    root.appendChild(loading);

    try {
      const module = await route.load();
      if (token !== loadToken || currentView !== viewId) return;
      root.replaceChildren();
      mountedModule = module;
      module.mount(root, currentState);
      focusViewRoot();
    } catch (error) {
      if (token !== loadToken || currentView !== viewId) return;
      mountedView = null;
      renderFailure('Body viewer unavailable. The 3D module could not be loaded.', error);
    }
    return;
  }

  mountedModule = route;
  route.mount(root, currentState);
  focusViewRoot();
}

function routeToView(viewId, { updateHash = true } = {}) {
  const next = normalizeRoute(viewId);
  currentView = next;

  if (updateHash && window.location.hash !== `#${next}`) {
    history.replaceState(null, '', `#${next}`);
  }

  activateRail(next);
  void mountRoute(next);
}

function switchView(viewId) {
  routeToView(viewId);
}

function applyRuntimeState(state) {
  currentState = state;
  updateStatusBar(state);

  const root = rootNode();
  if (!root || mountedView !== currentView) return;
  mountedModule?.update?.(root, state);
}

function applyRuntimeError(error) {
  setStatus('offline');
  setRunState('cannot reach server');
  setDetail(String(error), true);
}

const runtimeState = new RuntimeStatePoller({
  onState: applyRuntimeState,
  onError: applyRuntimeError,
});

async function fetchState() {
  await runtimeState.refresh();
}

function initNavigation() {
  document.querySelectorAll('.rail-item').forEach((item) => {
    item.addEventListener('click', (event) => {
      const target = normalizeRoute(item.hash);
      if (!event.defaultPrevented && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
        event.preventDefault();
        routeToView(target);
      }
    });
  });
}

function boot() {
  if (!rootNode()) return;
  initNavigation();
  currentView = parseHash();
  activateRail(currentView);
  void mountRoute(currentView);
  runtimeState.start();
}

window.addEventListener('hashchange', () => {
  const next = parseHash();
  if (next !== currentView) routeToView(next, { updateHash: false });
});

window.addEventListener('pagehide', () => runtimeState.stop(), { once: true });
window.routeToView = routeToView;
window.switchView = switchView;
window.addEventListener('DOMContentLoaded', boot);

export { routeToView, switchView, fetchState };
