let rootNode = null;
let lastState = null;

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function physics(state) {
  return state?.sources?.physics3d ?? {};
}

function hasVisualApparatus(p) {
  return String(p?.body_kind || '').includes('vision');
}

function visionExperienceActive(p) {
  return p?.run_kind === 'acquisition.vision' && ['starting','running','stopping'].includes(p?.state);
}

function render(state) {
  if (!rootNode) return;
  lastState = state;
  const p = physics(state);
  const apparatus = hasVisualApparatus(p);
  const visionLive = visionExperienceActive(p);
  const running = ['starting','running','stopping'].includes(p.state);
  const name = p.organism_alias || p.organism_id || p.organism_ref || 'No active Symbiont';
  const tick = p.tick ?? state?.current?.tick;
  const epoch = p.embodiment_epoch ?? state?.current?.embodiment_epoch;

  rootNode.innerHTML = `
    <div class="view-shell vision-shell">
      <header class="view-header">
        <div>
          <p class="eyebrow">Experience</p>
          <h1>Vision</h1>
          <p class="view-subtitle">Visual acquisition is shown as evidence, prediction and uncertainty — not as a camera feed.</p>
        </div>
        <span class="pill ${apparatus ? '' : 'muted'}">${visionLive ? 'VISION EXPERIENCE LIVE' : apparatus ? 'VISUAL APPARATUS PRESENT' : 'NO VISUAL APPARATUS'}</span>
      </header>

      <section class="v2-hero">
        <div>
          <div class="v2-kicker">Current organism</div>
          <h2>${esc(name)}</h2>
          <p>${tick != null ? 't' + Number(tick).toLocaleString() : 'tick unavailable'}${epoch != null ? ' · embodiment e' + esc(epoch) : ''} · ${visionLive ? 'Vision Experience live' : running ? 'current run: ' + esc(p.run_kind || 'unknown') : 'inactive'}</p>
        </div>
        <div class="v2-status-grid">
          <div><span>Apparatus</span><strong>${apparatus ? '12 × 12 luminance array' : '—'}</strong></div>
          <div><span>Signals</span><strong>${apparatus ? 'opaque receptor ids' : '—'}</strong></div>
          <div><span>Acquired sources</span><strong>not yet validated</strong></div>
          <div><span>Observer truth</span><strong>separate</strong></div>
        </div>
      </section>

      <nav class="v2-segmented" aria-label="Vision modes">
        <button class="active" type="button">Discovery</button>
        <button type="button">Apparatus</button>
        <button type="button">Acquired</button>
      </nav>

      <div class="v2-two-col">
        <section class="card v2-panel">
          <div class="v2-kicker">Discovery</div>
          <h3>Receptor activity → relation → prediction → evidence</h3>
          <div class="vision-field" aria-label="Opaque visual receptor field">
            ${Array.from({length:144},(_,i)=>`<i style="--i:${i}"></i>`).join('')}
          </div>
          <p class="v2-note">${visionLive
            ? 'Vision Experience is active. The grid represents observer-side apparatus topology; receptor identities remain opaque to cognition.'
            : apparatus
              ? 'The body carries a visual apparatus, but the current run is not a Vision Experience. No visual acquisition claim is implied.'
              : 'Start a Vision Experience with anthropomorphic-v6-vision to make the apparatus available.'}</p>
        </section>

        <section class="card v2-panel">
          <div class="v2-kicker">Acquired structure</div>
          <h3>No validated visual source structure yet</h3>
          <div class="v2-empty">
            <strong>Correctly empty.</strong>
            <p>The visual apparatus exists, but D1 has not yet established held-out visual acquisition. This panel will only show organism-owned evidence once it exists.</p>
          </div>
          <div class="v2-facts">
            <div><span>Temporal prediction</span><strong>under study</strong></div>
            <div><span>Coherent sources</span><strong>not validated</strong></div>
            <div><span>Persistence</span><strong>not validated</strong></div>
            <div><span>Self-caused transform</span><strong>not validated</strong></div>
          </div>
        </section>
      </div>

      <section class="card v2-panel">
        <div class="v2-kicker">Epistemic boundary</div>
        <h3>What the observer sees is not what Symbiont knows</h3>
        <p class="v2-note">Physics geometry, object identity, coordinates, depth and semantic labels remain observer-side. Vision receives only the lawful receptor consequences of the apparatus.</p>
      </section>
    </div>`;
}

export function mount(root, state = null) {
  rootNode = root;
  render(state);
}

export function update(root, state) {
  if (root !== rootNode) rootNode = root;
  render(state);
}

export function unmount() {
  rootNode = null;
  lastState = null;
}
