let rootNode = null;
let state = null;
let catalog = { bodies: [], organisms: [], runs: [], definitions: [] };
let selectedDefinition = 'embodiment-nursery-v1';
let selectedBody = null;
let organismMode = 'new';
let organismRef = '';
let bodyMode = 'fresh';
let selectedEnvironment = 'flat-v1';
let lastPhysicsState = null;
let lastPhysicsSignature = null;

function physicsSignature(p) {
  return [
    p?.state,
    p?.run_id,
    p?.run_kind,
    p?.organism_ref,
    p?.body_kind,
    p?.startup_phase,
    p?.error,
    p?.traceback,
  ].join('|');
}

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function loadState() {
  state = await jsonRequest('/api/state');
  lastPhysicsState = currentPhysics().state;
}

async function loadCatalog() {
  const [bodies, organisms, runs, environments, definitions] = await Promise.all([
    jsonRequest('/api/bodies'),
    jsonRequest('/api/organisms'),
    jsonRequest('/api/runs'),
    jsonRequest('/api/environments'),
    jsonRequest('/api/run-definitions'),
  ]);
  catalog = {
    bodies: bodies.items ?? [],
    organisms: organisms.items ?? [],
    runs: runs.items ?? [],
    environments: environments.items ?? [],
    definitions: definitions.items ?? [],
  };
  if (!selectedBody) selectedBody = catalog.bodies[0]?.body_kind ?? null;
  if (!organismRef) organismRef = catalog.organisms[0]?.ref ?? '';
}

// Observer-only organism alias (never part of the Symbiont bundle).
function aliasFor(ref) {
  return catalog.organisms.find(item => item.ref === ref)?.alias ?? null;
}

function organismName(ref, organismId) {
  const alias = aliasFor(ref);
  return alias ? `${alias} · ${organismId || ref}` : (organismId || ref);
}

function currentDefinition() {
  return catalog.definitions.find(item => item.definition_id === selectedDefinition) ?? null;
}

const KIND_LABELS = {
  'acquisition.embodiment': 'Embodiment Experience',
  'acquisition.vision': 'Vision Experience',
  'world.challenge': 'World · Challenge',
  'world.open': 'World · Open',
};

function isAcquisition(kind) {
  return String(kind || '').startsWith('acquisition.');
}

function definitionCards() {
  return catalog.definitions.map(item => `
    <button class="home-choice ${item.definition_id === selectedDefinition ? 'selected' : ''}" data-definition="${esc(item.definition_id)}" ${item.launchable ? '' : 'disabled'} title="${esc(item.unavailable_reason || '')}">
      <strong>${esc(KIND_LABELS[item.kind] || item.kind)}</strong>
      <span>${esc(item.title)} · v${esc(item.version)}</span>
      <small>${item.launchable ? (isAcquisition(item.kind) ? 'Protected: ends before irreversible body loss' : 'Full consequences: the body may die') : 'Unavailable: ' + esc(item.unavailable_reason)}</small>
    </button>
  `).join('');
}

function currentPhysics() {
  return state?.sources?.physics3d ?? { state: 'disabled' };
}

function activeRun() {
  const physics = currentPhysics();
  return ['starting','running','stopping'].includes(physics.state);
}

function organismOptions() {
  if (!catalog.organisms.length) return '<option value="">No saved Symbionts</option>';
  return catalog.organisms.map(item => {
    const label = item.alias ? `${item.alias} · ${item.organism_id || item.ref}` : (item.organism_id || item.ref);
    const tick = Number(item.tick || 0).toLocaleString();
    const lifecycle = item.symbiont_state ? ` · ${item.symbiont_state}` : '';
    const bodyState = item.vital_state === 'dead' ? ' · previous body dead' : '';
    const epoch = item.embodiment_epoch ? ` · e${item.embodiment_epoch}` : '';
    return `<option value="${esc(item.ref)}" ${item.ref === organismRef ? 'selected' : ''}>${esc(label)} · t${tick}${epoch}${lifecycle}${bodyState}</option>`;
  }).join('');
}

function bodyCards() {
  return catalog.bodies.map(body => `
    <button class="home-choice ${body.body_kind === selectedBody ? 'selected' : ''}" data-body="${esc(body.body_kind)}">
      <strong>${esc(body.display_name)}</strong>
      <span>${esc(body.body_kind)}</span>
      <small>${body.motor_dof} DoF · ${body.receptor_count} receptors · ${body.effector_count} effectors</small>
    </button>
  `).join('');
}

function selectedOrganism() {
  return catalog.organisms.find(item => item.ref === organismRef) ?? null;
}

function isCompatible() {
  const required = currentDefinition()?.body_kind;
  if (required && selectedBody !== required) return false;
  if (organismMode === 'new') return bodyMode === 'fresh';
  const organism = selectedOrganism();
  const body = catalog.bodies.find(item => item.body_kind === selectedBody);
  if (!organism || !body) return false;
  if (bodyMode === 'resume') {
    const protectedBoundary = isAcquisition(currentDefinition()?.kind) && ['agonizing', 'dormant'].includes(organism.vital_state);
    return Boolean(
      organism.last_body_ref &&
      organism.body_kind === selectedBody &&
      organism.vital_state !== 'dead' &&
      !protectedBoundary
    );
  }
  return true;
}

function compatibilityText() {
  if (organismMode === 'new') return 'A new organism will encounter this body without prior sensorimotor knowledge.';
  const organism = selectedOrganism();
  const body = catalog.bodies.find(item => item.body_kind === selectedBody);
  if (!organism || !body) return 'Select an existing organism and body.';
  if (bodyMode === 'resume') {
    if (organism.vital_state === 'dead') return 'Previous body is dead. Re-embody this Symbiont in a fresh body instead.';
    if (!organism.last_body_ref || organism.body_kind !== selectedBody) return 'No resumable checkpoint exists for this body type.';
    return 'The exact previous physical body checkpoint will be resumed.';
  }
  const knownContract = organism.receptor_count != null && organism.effector_count != null;
  const same = knownContract &&
    Number(organism.receptor_count) === Number(body.receptor_count) &&
    Number(organism.effector_count) === Number(body.effector_count) &&
    organism.body_kind === selectedBody;
  if (same) return 'Fresh body, same opaque contract: acquired sensorimotor knowledge may transfer.';
  return 'Fresh embodiment epoch: identity, memory and cognition persist; body-specific schema is reacquired without channel mapping.';
}

function recentRuns() {
  if (!catalog.runs.length) return '<div class="home-empty">No managed Physics3D runs yet.</div>';
  return catalog.runs.slice(0, 8).map(run => `
    <div class="home-run-row">
      <div>
        <strong>${esc(organismName(run.organism_ref, run.organism_id))}</strong>
        <span>${esc(KIND_LABELS[run.run_kind] || KIND_LABELS['world.open'])} · ${esc(run.body_kind)} · ${esc(run.embodiment_mode)}</span>
      </div>
      <div class="home-run-meta">
        <span>${esc(run.termination_reason || run.status)}</span>
        <span>${run.end_tick != null ? 't' + Number(run.end_tick).toLocaleString() : esc(run.run_id)}</span>
      </div>
    </div>
  `).join('');
}

function restoreScroll(prevScrollTop) {
  if (prevScrollTop <= 0 || !rootNode) return;
  const shell = rootNode.querySelector('.view-shell');
  if (shell) {
    shell.scrollTop = prevScrollTop;
    requestAnimationFrame(() => {
      const el = rootNode?.querySelector('.view-shell');
      if (el) el.scrollTop = prevScrollTop;
    });
  }
}

function render() {
  if (!rootNode) return;
  const prevShell = rootNode.querySelector('.view-shell');
  const prevScrollTop = prevShell ? prevShell.scrollTop : 0;
  const physics = currentPhysics();
  lastPhysicsSignature = physicsSignature(physics);
  if (activeRun()) {
    rootNode.innerHTML = `
      <div class="view-shell home-shell">
        <div class="view-header">
          <div><p class="eyebrow">Symbiont Lab</p><h1>Home</h1></div>
          <span class="pill">Physics3D ${esc(physics.state)}</span>
        </div>
        <section class="home-active card">
          <div>
            <p class="eyebrow">Active run</p>
            <h2>${esc(physics.run_id || 'Physics3D')}</h2>
            <p>${esc(KIND_LABELS[physics.run_kind] || 'Physics3D')} · ${esc(organismName(physics.organism_ref, null))} → ${esc(physics.body_kind || '')}</p>
            ${physics.state === 'starting' ? `<p>Startup: ${esc(physics.startup_phase || 'launching')}</p>` : ''}
          </div>
          <div class="home-actions">
            <button class="btn" data-open="${isAcquisition(physics.run_kind) ? 'embodiment' : 'world'}">${isAcquisition(physics.run_kind) ? 'Open Embodiment' : 'Open World'}</button>
            <button class="btn" data-open="mind">Open Mind</button>
            <button class="btn btn-danger" id="home-stop">Stop run</button>
          </div>
        </section>
        <section class="card"><h3 class="card-title">Recent runs</h3>${recentRuns()}</section>
      </div>`;
    bind();
    restoreScroll(prevScrollTop);
    return;
  }

  const failure = physics.state === 'failed'
    ? `<section class="card home-active"><div><p class="eyebrow">Physics3D failed to start</p><h2>Startup error</h2><p>${esc(physics.error || 'Unknown startup failure')}</p><pre>${esc(physics.traceback || '')}</pre></div></section>`
    : '';

  rootNode.innerHTML = `
    <div class="view-shell home-shell">
      <div class="view-header">
        <div><p class="eyebrow">Symbiont Lab</p><h1>Start a run</h1></div>
        <span class="pill muted">No active embodiment</span>
      </div>
      ${failure}
      <section class="card home-section">
        <div><h3>Run</h3><p>Experiences acquire capability in a protected envelope. Worlds integrate it under complete consequences. Purposes stay with the observer.</p></div>
        <div class="home-choice-grid">${definitionCards()}</div>
      </section>
      <div class="home-launch-grid">
        <section class="card home-section">
          <div class="home-step">1</div>
          <div><h3>Body</h3><p>Select the physical apparatus. Contract details are observer-side only.</p></div>
          <div class="home-choice-grid">${bodyCards()}</div>
        </section>
        <section class="card home-section">
          <div class="home-step">2</div>
          <div><h3>Mind</h3><p>Create a blank Symbiont or re-embody a dormant persistent identity.</p></div>
          <div class="home-radio-row">
            <label><input type="radio" name="organism-mode" value="new" ${organismMode === 'new' ? 'checked' : ''}> New Symbiont</label>
            <label><input type="radio" name="organism-mode" value="existing" ${organismMode === 'existing' ? 'checked' : ''} ${catalog.organisms.length ? '' : 'disabled'}> Dormant / existing Symbiont</label>
          </div>
          <div class="home-radio-row">
            <select id="home-organism" ${organismMode === 'existing' ? '' : 'disabled'}>${organismOptions()}</select>
            <button class="btn" id="home-alias" ${catalog.organisms.length && organismRef && organismRef !== 'legacy-default' ? '' : 'disabled'} title="Observer-only name; Symbiont never sees it">Alias…</button>
          </div>
        </section>
        <section class="card home-section">
          <div class="home-step">3</div>
          <div><h3>Embodiment</h3><p>Choose physical continuity independently from organism continuity.</p></div>
          <div class="home-radio-row">
            <label><input type="radio" name="body-mode" value="fresh" ${bodyMode === 'fresh' ? 'checked' : ''}> Fresh body</label>
            <label><input type="radio" name="body-mode" value="resume" ${bodyMode === 'resume' ? 'checked' : ''} ${organismMode === 'existing' ? '' : 'disabled'}> Resume previous body</label>
          </div>
          <label for="home-environment">Physical environment</label>
          <select id="home-environment" ${bodyMode === 'resume' || currentDefinition()?.environment ? 'disabled' : ''}>${(catalog.environments ?? []).map(name => `<option value="${esc(name)}" ${name === (currentDefinition()?.environment || selectedEnvironment) ? 'selected' : ''}>${esc(name)}</option>`).join('')}</select>
          <p>${bodyMode === 'resume' ? 'Resume restores the saved environment.' : currentDefinition()?.environment ? 'Fixed by the selected definition.' : 'Contact garden adds real surfaces and obstacles. Their identities are not given to Symbiont.'}</p>
          <div class="home-preflight"><strong>Preflight</strong><span>${esc(compatibilityText())}</span></div>
        </section>
      </div>
      <div class="home-start-bar">
        <div><strong>${organismMode === 'new' ? 'New Symbiont' : esc(organismName(organismRef, selectedOrganism()?.organism_id))}</strong><span> → ${esc(selectedBody)} · ${bodyMode} · ${esc(KIND_LABELS[currentDefinition()?.kind] || '')}</span></div>
        <button class="btn btn-primary" id="home-start" ${selectedBody && currentDefinition()?.launchable && (organismMode === 'new' || organismRef) && isCompatible() ? '' : 'disabled'}>Start run</button>
      </div>
      <section class="card home-recent"><h3 class="card-title">Recent runs</h3>${recentRuns()}</section>
    </div>`;
  bind();
  restoreScroll(prevScrollTop);
}

async function startRun() {
  const button = document.getElementById('home-start');
  if (button) button.disabled = true;
  try {
    await jsonRequest('/api/runs', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        body_kind: selectedBody,
        definition_id: selectedDefinition,
        environment: bodyMode === 'resume' || currentDefinition()?.environment ? undefined : selectedEnvironment,
        organism: { mode: organismMode, ref: organismMode === 'existing' ? organismRef : undefined },
        body: { mode: bodyMode },
      }),
    });
    await Promise.all([loadCatalog(), loadState()]);
  } catch (error) {
    window.alert(`Unable to start Physics3D run: ${error.message}`);
  }
  render();
}

async function editAlias() {
  const current = aliasFor(organismRef) ?? '';
  const next = window.prompt('Observer-only alias for this Symbiont (empty clears it):', current);
  if (next === null) return;
  try {
    await jsonRequest('/api/organisms/alias', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ ref: organismRef, alias: next }),
    });
    await loadCatalog();
  } catch (error) {
    window.alert(`Unable to set alias: ${error.message}`);
  }
  render();
}

async function stopRun() {
  try {
    await jsonRequest('/api/runs/stop', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
  } catch (error) {
    window.alert(`Unable to stop Physics3D run: ${error.message}`);
  }
}

function bind() {
  rootNode?.querySelectorAll('[data-definition]').forEach(node => node.addEventListener('click', () => {
    selectedDefinition = node.dataset.definition;
    const required = currentDefinition()?.body_kind;
    if (required) selectedBody = required;
    render();
  }));
  rootNode?.querySelectorAll('[data-body]').forEach(node => node.addEventListener('click', () => {
    selectedBody = node.dataset.body;
    render();
  }));
  rootNode?.querySelectorAll('input[name="organism-mode"]').forEach(node => node.addEventListener('change', () => {
    organismMode = node.value;
    if (organismMode === 'new' && bodyMode === 'resume') bodyMode = 'fresh';
    render();
  }));
  rootNode?.querySelectorAll('input[name="body-mode"]').forEach(node => node.addEventListener('change', () => {
    bodyMode = node.value;
    render();
  }));
  document.getElementById('home-organism')?.addEventListener('change', event => {
    organismRef = event.target.value;
    render();
  });
  rootNode?.querySelector('#home-environment')?.addEventListener('change', event => { selectedEnvironment = event.target.value; });
  document.getElementById('home-start')?.addEventListener('click', startRun);
  document.getElementById('home-alias')?.addEventListener('click', editAlias);
  document.getElementById('home-stop')?.addEventListener('click', stopRun);
  rootNode?.querySelectorAll('[data-open]').forEach(node => node.addEventListener('click', () => window.routeToView?.(node.dataset.open)));
}

export async function mount(root, nextState = null) {
  rootNode = root;
  state = nextState;
  lastPhysicsState = currentPhysics().state;
  lastPhysicsSignature = physicsSignature(currentPhysics());
  root.innerHTML = '<div class="empty-state">Loading run catalog…</div>';
  try {
    await Promise.all([loadCatalog(), loadState()]);
  } catch (error) {
    root.innerHTML = `<div class="empty-state">Run catalog unavailable: ${esc(error.message)}</div>`;
    return;
  }
  render();
}

export function update(root, nextState) {
  if (!rootNode || root !== rootNode) return;
  const previous = lastPhysicsState;
  state = nextState;
  const physics = currentPhysics();
  const next = physics.state;
  const currentSig = physicsSignature(physics);
  lastPhysicsState = next;

  if (['starting','running','stopping'].includes(previous) && !['starting','running','stopping'].includes(next)) {
    lastPhysicsSignature = currentSig;
    loadCatalog().then(render).catch(render);
    return;
  }

  if (currentSig !== lastPhysicsSignature) {
    lastPhysicsSignature = currentSig;
    render();
  }
}

export function unmount() {
  rootNode = null;
  lastPhysicsSignature = null;
}

