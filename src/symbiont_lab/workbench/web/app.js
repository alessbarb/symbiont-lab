import { mount as mountMind, unmount as unmountMind } from './views/mind.js';
import { mount as mountLab, update as updateLab } from './views/lab.js';
import { mount as mountArchive, update as updateArchive } from './views/archive.js';

const ROOT_ID = 'view-root';
let currentView = 'lab';
let currentState = null;
let stateTimer = null;
let mountedModule = null;
let bodyModule = null;
let bodyLoadToken = 0;

const NAV_ITEMS = [
  { id: 'lab', label: 'Lab', icon: '⚗' },
  { id: 'body', label: 'Body', icon: '⬡' },
  { id: 'mind', label: 'Mind', icon: '◎' },
  { id: 'archive', label: 'Archive', icon: '▤' },
];
const HASH_TARGETS = ['#lab', '#body', '#mind', '#archive'];

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
  const running = Boolean(state.running || state.study?.running);
  setStatus(running ? 'running' : 'ready');
  setRunState(state.running ? `run #${state.experiment_number ?? 0}` : state.study?.running ? `study ${state.study.phase ?? 'active'}` : 'no active run');

  const current = state.current ?? {};
  if (current?.step != null && current?.total_steps) {
    const pct = ((current.step / current.total_steps) * 100).toFixed(1);
    setDetail(`${pct}% complete`, true);
  } else if (state.study?.phase) {
    setDetail(state.study.phase, true);
  } else {
    setDetail('', false);
  }
}

function parseHash() {
  const hash = window.location.hash.trim();
  if (!hash || !HASH_TARGETS.includes(hash)) {
    return 'lab';
  }
  return hash.replace('#', '');
}

function activateRail(viewId) {
  document.querySelectorAll('.rail-item').forEach((node) => {
    const active = node.dataset.view === viewId;
    node.classList.toggle('active', active);
    node.setAttribute('aria-current', active ? 'page' : 'false');
  });
}

function clearMountedView() {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;
  bodyLoadToken += 1;

  if (mountedModule === 'body' && bodyModule?.unmount) bodyModule.unmount();
  if (mountedModule === 'mind') unmountMind();
  root.innerHTML = '';
  mountedModule = null;
}

function renderLabView(state) {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;
  clearMountedView();
  mountedModule = 'lab';
  mountLab(root, state);
}

function renderArchiveView(state) {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;
  clearMountedView();
  mountedModule = 'archive';
  mountArchive(root, state);
}

async function renderBodyView() {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;

  clearMountedView();
  mountedModule = 'body';
  const token = ++bodyLoadToken;

  const loading = document.createElement('div');
  loading.className = 'empty-state';
  loading.textContent = 'Loading 3D body viewer…';
  root.appendChild(loading);

  try {
    bodyModule ??= await import('./views/body.js');
    if (token !== bodyLoadToken || currentView !== 'body') return;
    root.innerHTML = '';
    bodyModule.mount(root);
  } catch (error) {
    if (token !== bodyLoadToken || currentView !== 'body') return;
    root.innerHTML = '';
    const failure = document.createElement('div');
    failure.className = 'empty-state';
    failure.textContent = 'Body viewer unavailable. The 3D module could not be loaded.';
    root.appendChild(failure);
    setDetail(String(error), true);
  }
}

function renderMindView() {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;
  clearMountedView();
  mountedModule = 'mind';
  mountMind(root);
}

function routeToView(viewId) {
  currentView = viewId;
  window.location.hash = viewId;
  activateRail(viewId);

  if (viewId === 'lab') renderLabView(currentState);
  else if (viewId === 'body') renderBodyView();
  else if (viewId === 'mind') renderMindView();
  else if (viewId === 'archive') renderArchiveView(currentState);
}

function switchView(viewId) {
  routeToView(viewId);
}

async function fetchState() {
  try {
    const response = await fetch('/api/state', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    currentState = await response.json();
    updateStatusBar(currentState);

    if (mountedModule === 'lab') updateLab(document.getElementById(ROOT_ID), currentState);
    if (mountedModule === 'archive') updateArchive(document.getElementById(ROOT_ID), currentState);
  } catch (error) {
    setStatus('offline');
    setRunState('cannot reach server');
    setDetail(String(error), true);
  }
}

function initNavigation() {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;

  document.querySelectorAll('.rail-item').forEach((item) => {
    item.addEventListener('click', (event) => {
      event.preventDefault();
      const next = item.dataset.view;
      if (next) switchView(next);
    });
  });
}

function boot() {
  const root = document.getElementById(ROOT_ID);
  if (!root) return;

  initNavigation();
  const view = parseHash();
  currentView = view;
  activateRail(view);

  if (view === 'lab') renderLabView(currentState);
  else if (view === 'body') renderBodyView();
  else if (view === 'mind') renderMindView();
  else if (view === 'archive') renderArchiveView(currentState);

  fetchState();
  stateTimer = window.setInterval(fetchState, 2500);
}

window.addEventListener('hashchange', () => {
  const next = parseHash();
  if (next && next !== currentView) {
    routeToView(next);
  }
});

window.routeToView = routeToView;
window.switchView = switchView;
window.addEventListener('DOMContentLoaded', boot);

export { routeToView, switchView, fetchState };
