import { MindStreams } from './mind/streams.js';
import { applyTelemetryEvent } from './mind/telemetry.js';
import { applyMindSnapshot } from './mind/snapshot.js';
import { snap, streamState, tel } from './mind/state.js';

let rootNode = null;
let lastState = null;
let streams = null;
let activeMode = 'discovery';
let renderQueued = false;

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

function topologyStats() {
  const nodes = snap.topology?.nodes ?? [];
  const senses = nodes.filter(node => node.kind === 'sense').length;
  const concepts = nodes.filter(node => node.kind === 'concept').length;
  const predictors = nodes.filter(node => node.kind === 'predictor').length;
  const readouts = nodes.filter(node => node.kind === 'readout').length;
  return { senses, concepts, predictors, readouts };
}

function sensoryStats() {
  const sensors = Array.isArray(snap.sensoryPhenotype?.sensors)
    ? snap.sensoryPhenotype.sensors
    : [];
  const development = Array.isArray(snap.sensoryDevelopment)
    ? snap.sensoryDevelopment
    : [];
  const relations = Array.isArray(snap.sensoryRelations)
    ? snap.sensoryRelations
    : [];
  return { sensors, development, relations };
}

function fieldCells(apparatus, live) {
  return Array.from({length:144},(_,i)=>{
    const strength = live ? ((i * 17 + 11) % 9) : 0;
    return `<i class="${live ? 'available' : ''}" style="--i:${i};--signal:${strength}"></i>`;
  }).join('');
}

function modeNav() {
  return `
    <nav class="v2-segmented" aria-label="Vision modes">
      ${[
        ['discovery','Discovery'],
        ['apparatus','Apparatus'],
        ['acquired','Acquired'],
      ].map(([id,label]) => `<button class="${activeMode===id?'active':''}" data-vision-mode="${id}" type="button">${label}</button>`).join('')}
    </nav>`;
}

function discoveryBody({ apparatus, visionLive }) {
  const topology = topologyStats();
  const sensory = sensoryStats();
  const predictionError = Number(tel.predictionError);

  return `
    <div class="v2-two-col">
      <section class="card v2-panel">
        <div class="v2-kicker">Discovery</div>
        <h3>Apparatus activity → cognitive representation → prediction</h3>
        <div class="vision-field ${visionLive ? 'live' : ''}" aria-label="Observer-side topology of the visual receptor array">
          ${fieldCells(apparatus, visionLive)}
        </div>
        <p class="v2-note">${visionLive
          ? 'A Vision Experience is live. The 12×12 layout is apparatus truth only. Individual field intensities are not transported to the Workbench yet, so the cells deliberately do not pretend to be a camera feed.'
          : apparatus
            ? 'The body carries the visual apparatus, but the current run is not a Vision Experience.'
            : 'No visual apparatus is bound to the current body.'}</p>
      </section>

      <section class="card v2-panel vision-live-panel">
        <div class="v2-kicker">Passive cognitive observation</div>
        <h3>What can be measured without inventing visual semantics</h3>
        <div class="v2-facts">
          <div><span>Stream</span><strong>${esc(streamState.status || 'disconnected')}</strong></div>
          <div><span>Frame coherence</span><strong>${streamState.coherent ? 'coherent' : 'partial'}</strong></div>
          <div><span>Admitted senses · all modalities</span><strong>${sensory.sensors.length || '—'}</strong></div>
          <div><span>Sense nodes · all modalities</span><strong>${topology.senses}</strong></div>
          <div><span>Predictors · all modalities</span><strong>${topology.predictors}</strong></div>
          <div><span>Prediction error</span><strong>${Number.isFinite(predictionError) ? predictionError.toFixed(3) : '—'}</strong></div>
        </div>
        <div class="v2-empty vision-boundary">
          <strong>Visual attribution is intentionally not inferred.</strong>
          <p>The current Workbench stream does not export a trustworthy mapping from cognitive sense nodes back to the 144 visual receptor sources. These counts therefore remain global cognitive context until that observer-side provenance is transported explicitly.</p>
        </div>
      </section>
    </div>

    <section class="card v2-panel">
      <div class="v2-kicker">Development signals</div>
      <h3>Current evidence available to the observer</h3>
      <div class="vision-development-strip">
        <div><span>Sensory development records</span><strong>${sensory.development.length}</strong></div>
        <div><span>Sensory relations</span><strong>${sensory.relations.length}</strong></div>
        <div><span>Concepts</span><strong>${topology.concepts}</strong></div>
        <div><span>Readouts</span><strong>${topology.readouts}</strong></div>
      </div>
      <p class="v2-note">These are organism-side structures observed passively. They are not claimed to be visual unless causal provenance proves that relation.</p>
    </section>`;
}

function apparatusBody({ apparatus, visionLive }) {
  return `
    <div class="v2-two-col">
      <section class="card v2-panel">
        <div class="v2-kicker">Apparatus truth</div>
        <h3>Head-mounted luminance receptor array</h3>
        <div class="vision-apparatus-diagram">
          <div class="vision-head-node">HEAD</div>
          <div class="vision-apparatus-link"></div>
          <div class="vision-array-node">12 × 12<br><small>144 receptors</small></div>
        </div>
        <div class="v2-facts">
          <div><span>Signal</span><strong>bounded luminance</strong></div>
          <div><span>Identity</span><strong>opaque ids</strong></div>
          <div><span>Topology</span><strong>observer/apparatus side</strong></div>
          <div><span>Depth</span><strong>not supplied</strong></div>
          <div><span>Colour semantics</span><strong>not supplied</strong></div>
          <div><span>Object identity</span><strong>not supplied</strong></div>
        </div>
      </section>
      <section class="card v2-panel">
        <div class="v2-kicker">Transport status</div>
        <h3>${apparatus ? 'Apparatus available' : 'No apparatus bound'}</h3>
        <div class="v2-empty">
          <strong>${visionLive ? 'Acquisition is live.' : 'Acquisition is not active.'}</strong>
          <p>Per-receptor luminance samples are currently consumed by the runtime but are not exported as a Workbench field stream. Adding that observer transport is the next instrumentation gap if we want this view to animate without reading private runtime state.</p>
        </div>
      </section>
    </div>`;
}

function acquiredBody() {
  const topology = topologyStats();
  return `
    <div class="v2-two-col">
      <section class="card v2-panel">
        <div class="v2-kicker">Acquired structure</div>
        <h3>No validated visual source structure yet</h3>
        <div class="v2-empty">
          <strong>Correctly empty.</strong>
          <p>D1 has not yet established held-out visual acquisition. The interface will not turn sense nodes, predictors or observer geometry into visual knowledge by proxy.</p>
        </div>
        <div class="v2-facts">
          <div><span>Persistent sources</span><strong>not validated</strong></div>
          <div><span>Temporal coherence</span><strong>not validated</strong></div>
          <div><span>Occlusion persistence</span><strong>not validated</strong></div>
          <div><span>Self-caused transform</span><strong>not validated</strong></div>
        </div>
      </section>
      <section class="card v2-panel">
        <div class="v2-kicker">Nearby cognitive structure</div>
        <h3>Available, but not classified as visual</h3>
        <div class="vision-development-strip vertical">
          <div><span>Sense nodes</span><strong>${topology.senses}</strong></div>
          <div><span>Concepts</span><strong>${topology.concepts}</strong></div>
          <div><span>Predictors</span><strong>${topology.predictors}</strong></div>
          <div><span>Readouts</span><strong>${topology.readouts}</strong></div>
        </div>
        <p class="v2-note">Once causal source provenance is exported, this panel can separate visual acquisition from the organism's other sensory structure without semantic leakage.</p>
      </section>
    </div>`;
}

function render(state) {
  if (!rootNode) return;
  lastState = state;
  const p = physics(state);
  const apparatus = hasVisualApparatus(p);
  const visionLive = visionExperienceActive(p);
  const running = ['starting','running','stopping'].includes(p.state);
  const name = p.organism_alias || p.organism_id || p.organism_ref || 'No active Symbiont';
  const tick = tel.tick ?? p.tick ?? state?.current?.tick;
  const epoch = tel.embodimentEpoch ?? p.embodiment_epoch ?? state?.current?.embodiment_epoch;

  const body =
    activeMode === 'apparatus' ? apparatusBody({ apparatus, visionLive }) :
    activeMode === 'acquired' ? acquiredBody() :
    discoveryBody({ apparatus, visionLive });

  rootNode.innerHTML = `
    <div class="view-shell vision-shell">
      <header class="view-header">
        <div>
          <p class="eyebrow">Experience</p>
          <h1>Vision</h1>
          <p class="view-subtitle">Visual acquisition is shown as apparatus, evidence and uncertainty — never as an assumed picture of the world.</p>
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
          <div><span>Observer stream</span><strong>${esc(streamState.status || 'disconnected')}</strong></div>
          <div><span>Acquired visual sources</span><strong>not yet validated</strong></div>
          <div><span>Observer truth</span><strong>separate</strong></div>
        </div>
      </section>

      ${modeNav()}
      ${body}

      <section class="card v2-panel">
        <div class="v2-kicker">Epistemic boundary</div>
        <h3>What the observer sees is not what Symbiont knows</h3>
        <p class="v2-note">Physics geometry, object identity, coordinates, depth and semantic labels remain observer-side. Vision receives only lawful receptor consequences through the apparatus.</p>
      </section>
    </div>`;

  rootNode.querySelectorAll('[data-vision-mode]').forEach(button => {
    button.addEventListener('click', () => {
      activeMode = button.dataset.visionMode || 'discovery';
      render(lastState);
    });
  });
}

function requestRender() {
  if (renderQueued || !rootNode) return;
  renderQueued = true;
  requestAnimationFrame(() => {
    renderQueued = false;
    render(lastState);
  });
}

function connectStreams() {
  if (streams) return;
  streams = new MindStreams({
    onTelemetry: (data, meta = {}) => {
      if (!applyTelemetryEvent(data)) return;
      streamState.lastTelemetryAt = Date.now();
      streamState.telemetryTick = meta.frameTick ?? data.tick ?? streamState.telemetryTick;
      updateCoherence();
      requestRender();
    },
    onSnapshot: (snapshot, meta = {}) => {
      if (!applyMindSnapshot(snapshot)) return;
      streamState.lastSnapshotAt = Date.now();
      streamState.snapshotTick = meta.tick ?? snapshot?.tick ?? snapshot?.snapshot?.tick ?? null;
      updateCoherence();
      requestRender();
    },
    onSourceState: (next) => {
      Object.assign(streamState, {
        status: next.status,
        source: next.source ?? null,
        instanceId: next.instanceId ?? null,
        runId: next.runId ?? null,
        stale: next.status !== 'live',
        reason: next.reason ?? null,
      });
      updateCoherence();
      requestRender();
    },
  });
  streams.connect();
}

function updateCoherence() {
  streamState.coherent =
    streamState.telemetryTick != null &&
    streamState.snapshotTick != null &&
    streamState.telemetryTick === streamState.snapshotTick;
}

export function mount(root, state = null) {
  rootNode = root;
  lastState = state;
  connectStreams();
  render(state);
}

export function update(root, state) {
  if (root !== rootNode) rootNode = root;
  lastState = state;
  requestRender();
}

export function unmount() {
  streams?.close();
  streams = null;
  rootNode = null;
  lastState = null;
  renderQueued = false;
}
