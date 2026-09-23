let rootNode = null;
let state = null;
let catalog = { bodies: [], organisms: [], runs: [] };
let selectedBody = null;
let organismMode = 'new';
let organismRef = '';
let bodyMode = 'fresh';
let lastPhysicsState = null;

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function loadCatalog() {
  const [bodies, organisms, runs] = await Promise.all([
    jsonRequest('/api/bodies'),
    jsonRequest('/api/organisms'),
    jsonRequest('/api/runs'),
  ]);
  catalog = { bodies: bodies.items ?? [], organisms: organisms.items ?? [], runs: runs.items ?? [] };
  if (!selectedBody) selectedBody = catalog.bodies[0]?.body_kind ?? null;
  if (!organismRef) organismRef = catalog.organisms[0]?.ref ?? '';
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
    const label = item.organism_id || item.ref;
    const tick = Number(item.tick || 0).toLocaleString();
    return `<option value="${esc(item.ref)}" ${item.ref === organismRef ? 'selected' : ''}>${esc(label)} · t${tick}</option>`;
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
  if (organismMode === 'new') return bodyMode === 'fresh';
  const organism = selectedOrganism();
  const body = catalog.bodies.find(item => item.body_kind === selectedBody);
  if (!organism || !body) return false;
  if (bodyMode === 'resume' && (!organism.last_body_ref || organism.body_kind !== selectedBody)) return false;
  if (organism.receptor_count == null || organism.effector_count == null) return true;
  return Number(organism.receptor_count) === Number(body.receptor_count) &&
    Number(organism.effector_count) === Number(body.effector_count);
}

function compatibilityText() {
  if (organismMode === 'new') return 'A new organism will encounter this body without prior sensorimotor knowledge.';
  const organism = selectedOrganism();
  const body = catalog.bodies.find(item => item.body_kind === selectedBody);
  if (!organism || !body) return 'Select an existing organism and body.';
  const same = (
    organism.receptor_count == null ||
    (Number(organism.receptor_count) === Number(body.receptor_count) &&
     Number(organism.effector_count) === Number(body.effector_count))
  );
  if (!same) return 'Incompatible opaque sensorimotor contract. This transplant is blocked rather than inventing a mapping.';
  if (bodyMode === 'resume' && (!organism.last_body_ref || organism.body_kind !== selectedBody)) return 'No resumable checkpoint exists for this body type.';
  if (bodyMode === 'resume') return 'The exact previous physical body checkpoint will be resumed.';
  return 'Same opaque sensorimotor contract; physical state will start fresh.';
}

function recentRuns() {
  if (!catalog.runs.length) return '<div class="home-empty">No managed Physics3D runs yet.</div>';
  return catalog.runs.slice(0, 8).map(run => `
    <div class="home-run-row">
      <div>
        <strong>${esc(run.organism_id || run.organism_ref)}</strong>
        <span>${esc(run.body_kind)} · ${esc(run.embodiment_mode)}</span>
      </div>
      <div class="home-run-meta">
        <span>${esc(run.status)}</span>
        <span>${run.end_tick != null ? 't' + Number(run.end_tick).toLocaleString() : esc(run.run_id)}</span>
      </div>
    </div>
  `).join('');
}

function render() {
  if (!rootNode) return;
  const physics = currentPhysics();
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
            <p>${esc(physics.organism_ref || '')} → ${esc(physics.body_kind || '')}</p>
          </div>
          <div class="home-actions">
            <button class="btn" data-open="body">Open Body</button>
            <button class="btn" data-open="mind">Open Mind</button>
            <button class="btn btn-danger" id="home-stop">Stop run</button>
          </div>
        </section>
        <section class="card"><h3 class="card-title">Recent runs</h3>${recentRuns()}</section>
      </div>`;
    bind();
    return;
  }

  rootNode.innerHTML = `
    <div class="view-shell home-shell">
      <div class="view-header">
        <div><p class="eyebrow">Symbiont Lab</p><h1>Start a run</h1></div>
        <span class="pill muted">No active embodiment</span>
      </div>
      <div class="home-launch-grid">
        <section class="card home-section">
          <div class="home-step">1</div>
          <div><h3>Body</h3><p>Select the physical apparatus. Contract details are observer-side only.</p></div>
          <div class="home-choice-grid">${bodyCards()}</div>
        </section>
        <section class="card home-section">
          <div class="home-step">2</div>
          <div><h3>Mind</h3><p>Create a blank Symbiont or continue an existing organism identity.</p></div>
          <div class="home-radio-row">
            <label><input type="radio" name="organism-mode" value="new" ${organismMode === 'new' ? 'checked' : ''}> New Symbiont</label>
            <label><input type="radio" name="organism-mode" value="existing" ${organismMode === 'existing' ? 'checked' : ''} ${catalog.organisms.length ? '' : 'disabled'}> Existing Symbiont</label>
          </div>
          <select id="home-organism" ${organismMode === 'existing' ? '' : 'disabled'}>${organismOptions()}</select>
        </section>
        <section class="card home-section">
          <div class="home-step">3</div>
          <div><h3>Embodiment</h3><p>Choose physical continuity independently from organism continuity.</p></div>
          <div class="home-radio-row">
            <label><input type="radio" name="body-mode" value="fresh" ${bodyMode === 'fresh' ? 'checked' : ''}> Fresh body</label>
            <label><input type="radio" name="body-mode" value="resume" ${bodyMode === 'resume' ? 'checked' : ''} ${organismMode === 'existing' ? '' : 'disabled'}> Resume previous body</label>
          </div>
          <div class="home-preflight"><strong>Preflight</strong><span>${esc(compatibilityText())}</span></div>
        </section>
      </div>
      <div class="home-start-bar">
        <div><strong>${organismMode === 'new' ? 'New Symbiont' : esc(selectedOrganism()?.organism_id || organismRef)}</strong><span> → ${esc(selectedBody)} · ${bodyMode}</span></div>
        <button class="btn btn-primary" id="home-start" ${selectedBody && (organismMode === 'new' || organismRef) && isCompatible() ? '' : 'disabled'}>Start run</button>
      </div>
      <section class="card home-recent"><h3 class="card-title">Recent runs</h3>${recentRuns()}</section>
    </div>`;
  bind();
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
        organism: { mode: organismMode, ref: organismMode === 'existing' ? organismRef : undefined },
        body: { mode: bodyMode },
      }),
    });
    await loadCatalog();
  } catch (error) {
    window.alert(`Unable to start Physics3D run: ${error.message}`);
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
  document.getElementById('home-start')?.addEventListener('click', startRun);
  document.getElementById('home-stop')?.addEventListener('click', stopRun);
  rootNode?.querySelectorAll('[data-open]').forEach(node => node.addEventListener('click', () => window.routeToView?.(node.dataset.open)));
}

export async function mount(root, nextState = null) {
  rootNode = root;
  state = nextState;
  lastPhysicsState = currentPhysics().state;
  root.innerHTML = '<div class="empty-state">Loading run catalog…</div>';
  try {
    await loadCatalog();
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
  const next = currentPhysics().state;
  lastPhysicsState = next;
  if (['starting','running','stopping'].includes(previous) && !['starting','running','stopping'].includes(next)) {
    loadCatalog().then(render).catch(render);
    return;
  }
  render();
}

export function unmount() {
  rootNode = null;
}
