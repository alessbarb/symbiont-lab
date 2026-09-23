/**
 * body.js — Three.js humanoid body viewer for Symbiont Lab.
 *
 * ES module. Public API:
 *   mount(root: HTMLElement) → void
 *   unmount()               → void
 *
 * Coordinate system note
 * ──────────────────────
 * PyBullet uses Z-up, Three.js uses Y-up.
 * Conversion: THREE [x, y, z] = PyBullet [x, z, −y]
 * Quaternion: THREE.Quaternion.set(qx, qz, −qy, qw)
 *
 * SSE stream: /api/organism
 *   event types: 'body' | 'cognition' | 'vitals'
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ─────────────────────────────────────────────────────────────────────────────
// Coordinate helpers (PyBullet Z-up → Three.js Y-up)
// ─────────────────────────────────────────────────────────────────────────────

/** Convert a PyBullet [px, py, pz] position to Three.js [x, y, z]. */
function pbPos(px, py, pz) {
  return [px, pz, -py];
}

/** Convert a PyBullet [qx, qy, qz, qw] quaternion to a THREE.Quaternion. */
function pbQuat(qx, qy, qz, qw) {
  return new THREE.Quaternion(qx, qz, -qy, qw);
}

// ─────────────────────────────────────────────────────────────────────────────
// Skeleton & Topology Constants
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Segment dimensions [width, depth, height] in metres plus the visual mesh
 * offset in PyBullet coordinates. Offsets are converted to Three.js Y-up
 * when the skeleton is built.
 */
const SEGMENTS = {
  pelvis:          { wdh: [0.32, 0.20, 0.22], offset: [0, 0, 0] },
  torso:           { wdh: [0.40, 0.22, 0.50], offset: [0, 0, 0.21] },
  head:            { wdh: [0.21, 0.21, 0.23], offset: [0, 0, 0.12] },
  left_upper_arm:  { wdh: [0.13, 0.13, 0.31], offset: [0, 0, -0.155] },
  left_forearm:    { wdh: [0.11, 0.11, 0.27], offset: [0, 0, -0.135] },
  left_hand:       { wdh: [0.09, 0.15, 0.18], offset: [0, 0, -0.09] },
  right_upper_arm: { wdh: [0.13, 0.13, 0.31], offset: [0, 0, -0.155] },
  right_forearm:   { wdh: [0.11, 0.11, 0.27], offset: [0, 0, -0.135] },
  right_hand:      { wdh: [0.09, 0.15, 0.18], offset: [0, 0, -0.09] },
  left_thigh:      { wdh: [0.15, 0.15, 0.40], offset: [0, 0, -0.20] },
  left_shin:       { wdh: [0.13, 0.13, 0.40], offset: [0, 0, -0.20] },
  left_foot:       { wdh: [0.11, 0.26, 0.07], offset: [0, -0.075, -0.035] },
  right_thigh:     { wdh: [0.15, 0.15, 0.40], offset: [0, 0, -0.20] },
  right_shin:      { wdh: [0.13, 0.13, 0.40], offset: [0, 0, -0.20] },
  right_foot:      { wdh: [0.11, 0.26, 0.07], offset: [0, -0.075, -0.035] },
};

/**
 * Segment colour palette for MeshStandardMaterial.
 * Keys match SEGMENTS.
 */
const SEGMENT_COLORS = {
  pelvis:          0x2a2a5a,
  torso:           0x1a3a6a,
  head:            0x6a6a7a,
  left_upper_arm:  0x2244aa,
  left_forearm:    0x2244aa,
  left_hand:       0x2244aa,
  right_upper_arm: 0x11aacc,
  right_forearm:   0x11aacc,
  right_hand:      0x11aacc,
  left_thigh:      0x1a5a2a,
  left_shin:       0x1a5a2a,
  left_foot:       0x1a5a2a,
  right_thigh:     0x2a8a3a,
  right_shin:      0x2a8a3a,
  right_foot:      0x2a8a3a,
};

/**
 * Kinematic tree mirrored from the PyBullet humanoid definition.
 *
 * axis:
 *   Y -> yaw
 *   X -> pitch
 *   Z -> roll / deviation
 *
 * All offsets are expressed in PyBullet Z-up coordinates.
 */
const JOINT_TOPOLOGY = [
  // Trunk
  { name: 'trunk_yaw',            parent: 'pelvis',                    child: 'trunk_yaw_carrier',           offset: [0, 0, 0.10],     axis: 'Y' },
  { name: 'trunk_roll',           parent: 'trunk_yaw_carrier',         child: 'trunk_roll_carrier',          offset: [0, 0, 0],        axis: 'Z' },
  { name: 'trunk_pitch',          parent: 'trunk_roll_carrier',        child: 'torso',                       offset: [0, 0, 0],        axis: 'X' },
  // Neck / Head
  { name: 'neck_yaw',             parent: 'torso',                     child: 'neck_yaw_carrier',            offset: [0, 0, 0.48],     axis: 'Y' },
  { name: 'neck_pitch',           parent: 'neck_yaw_carrier',          child: 'head',                        offset: [0, 0, 0],        axis: 'X' },
  // Left arm
  { name: 'left_shoulder_yaw',    parent: 'torso',                     child: 'left_shoulder_yaw_carrier',   offset: [-0.28, 0, 0.36], axis: 'Y' },
  { name: 'left_shoulder_roll',   parent: 'left_shoulder_yaw_carrier', child: 'left_shoulder_roll_carrier',  offset: [0, 0, 0],        axis: 'Z' },
  { name: 'left_shoulder_pitch',  parent: 'left_shoulder_roll_carrier',child: 'left_upper_arm',              offset: [0, 0, 0],        axis: 'X' },
  { name: 'left_elbow_pitch',     parent: 'left_upper_arm',            child: 'left_elbow_carrier',          offset: [0, 0, -0.31],    axis: 'X' },
  { name: 'left_forearm_roll',    parent: 'left_elbow_carrier',        child: 'left_forearm',                offset: [0, 0, 0],        axis: 'Z' },
  { name: 'left_wrist_pitch',     parent: 'left_forearm',              child: 'left_wrist_carrier',          offset: [0, 0, -0.27],    axis: 'X' },
  { name: 'left_wrist_deviation', parent: 'left_wrist_carrier',        child: 'left_hand',                   offset: [0, 0, 0],        axis: 'Z' },
  // Right arm
  { name: 'right_shoulder_yaw',   parent: 'torso',                     child: 'right_shoulder_yaw_carrier',  offset: [0.28, 0, 0.36],  axis: 'Y' },
  { name: 'right_shoulder_roll',  parent: 'right_shoulder_yaw_carrier',child: 'right_shoulder_roll_carrier', offset: [0, 0, 0],        axis: 'Z' },
  { name: 'right_shoulder_pitch', parent: 'right_shoulder_roll_carrier',child: 'right_upper_arm',            offset: [0, 0, 0],        axis: 'X' },
  { name: 'right_elbow_pitch',    parent: 'right_upper_arm',           child: 'right_elbow_carrier',         offset: [0, 0, -0.31],    axis: 'X' },
  { name: 'right_forearm_roll',   parent: 'right_elbow_carrier',       child: 'right_forearm',               offset: [0, 0, 0],        axis: 'Z' },
  { name: 'right_wrist_pitch',    parent: 'right_forearm',             child: 'right_wrist_carrier',         offset: [0, 0, -0.27],    axis: 'X' },
  { name: 'right_wrist_deviation',parent: 'right_wrist_carrier',       child: 'right_hand',                  offset: [0, 0, 0],        axis: 'Z' },
  // Left leg
  { name: 'left_hip_yaw',         parent: 'pelvis',                    child: 'left_hip_yaw_carrier',        offset: [-0.10, 0, -0.10],axis: 'Y' },
  { name: 'left_hip_roll',        parent: 'left_hip_yaw_carrier',      child: 'left_hip_roll_carrier',       offset: [0, 0, 0],        axis: 'Z' },
  { name: 'left_hip_pitch',       parent: 'left_hip_roll_carrier',     child: 'left_thigh',                  offset: [0, 0, 0],        axis: 'X' },
  { name: 'left_knee_pitch',      parent: 'left_thigh',                child: 'left_shin',                   offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'left_ankle_pitch',     parent: 'left_shin',                 child: 'left_ankle_pitch_carrier',    offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'left_ankle_roll',      parent: 'left_ankle_pitch_carrier',  child: 'left_foot',                   offset: [0, 0, 0],        axis: 'Z' },
  // Right leg
  { name: 'right_hip_yaw',        parent: 'pelvis',                    child: 'right_hip_yaw_carrier',       offset: [0.10, 0, -0.10], axis: 'Y' },
  { name: 'right_hip_roll',       parent: 'right_hip_yaw_carrier',     child: 'right_hip_roll_carrier',      offset: [0, 0, 0],        axis: 'Z' },
  { name: 'right_hip_pitch',      parent: 'right_hip_roll_carrier',    child: 'right_thigh',                 offset: [0, 0, 0],        axis: 'X' },
  { name: 'right_knee_pitch',     parent: 'right_thigh',               child: 'right_shin',                  offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'right_ankle_pitch',    parent: 'right_shin',                child: 'right_ankle_pitch_carrier',   offset: [0, 0, -0.40],    axis: 'X' },
  { name: 'right_ankle_roll',     parent: 'right_ankle_pitch_carrier', child: 'right_foot',                  offset: [0, 0, 0],        axis: 'Z' },
];

const PANEL_FIELDS = [
  { id: 'tick',                  label: 'Tick' },
  { id: '__state',               label: null, section: 'Body state' },
  { id: 'alive',                 label: 'Life' },
  { id: 'state_summary',         label: 'Situation' },
  { id: 'metabolic_reserve',     label: 'Metabolic reserve' },
  { id: 'reserve_trend',         label: 'Reserve trend' },

  { id: '__motion',              label: null, section: 'Motion' },
  { id: 'joint_motion',          label: 'Joint activity' },
  { id: 'active_joints',         label: 'Active joints' },
  { id: 'active_effectors',      label: 'Active effectors' },
  { id: 'contact_count',         label: 'Ground contacts' },
  { id: 'displacement',          label: 'Net displacement' },
  { id: 'distance_travelled',    label: 'Distance travelled' },
  { id: 'locomotion_efficiency', label: 'Locomotion efficiency' },

  { id: '__environment',         label: null, section: 'Environment' },
  { id: 'resource_distance',     label: 'Resource distance' },
  { id: 'resource_progress',     label: 'Resource progress' },

  { id: '__control',             label: null, section: 'Control context' },
  { id: 'motor_origin',          label: 'Motor origin' },
  { id: 'schema_conf',           label: 'Schema confidence' },
  { id: 'prediction_error',      label: 'Prediction error' },
  { id: 'slm_active',            label: 'Private model' },
  { id: 'prospective',           label: 'Prospective choice' },
];

// ─────────────────────────────────────────────────────────────────────────────
// DOM helpers
// ─────────────────────────────────────────────────────────────────────────────

function el(tag, cls, styles = {}) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  Object.assign(e.style, styles);
  return e;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Viewer Class
// ─────────────────────────────────────────────────────────────────────────────

export class HumanoidViewer {
  constructor(rootElement, sseUrl = '/api/organism') {
    if (!(rootElement instanceof HTMLElement)) {
      throw new TypeError('HumanoidViewer requires a valid HTMLElement root');
    }

    this.root = rootElement;
    this.rootStyleBeforeMount = rootElement.style.cssText;
    this.sseUrl = sseUrl;
    this.unmounted = false;

    // Three.js instances
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.baseNode = null;
    this.dirLight = null;
    this.lightOffset = new THREE.Vector3(2, 4, 3);
    this.followBody = true;
    this.followTarget = new THREE.Vector3();
    this.followDelta = new THREE.Vector3();
    
    // Scene objects mapping
    this.jointObjs = {};
    this.linkObjs = {};
    this.jointMarkers = {};
    this.jointActivity = new Map();

    // Observer-side body history. These values never feed back into the organism.
    this.previousObservedBasePos = null;
    this.previousJointPositions = new Map();
    this.distanceTravelled = 0;
    this.activeJointCount = 0;
    this.reserveHistory = [];
    this.bodyState = {
      alive: null,
      reserve: null,
      reserveTrend: 0,
      resourceProgress: null,
      resourceDistance: null,
      jointMotion: null,
      contactCount: null,
    };
    
    // Target state for Smooth Interpolation (Lerp)
    this.targetBasePos = new THREE.Vector3(0, 1.05, 0);
    this.targetBaseQuat = new THREE.Quaternion();
    this.targetJointAngles = new Map();
    this.clock = new THREE.Clock();

    // UI Throttling State
    this.panelEls = {};
    this.statusEl = null;
    this.uiStateQueue = {};
    this.lastUIDrawTime = 0;
    this.UI_UPDATE_INTERVAL_MS = 66; // ~15 FPS max for UI updates

    // Event & Render handles
    this.rafId = null;
    this.sse = null;
    this.resizeObs = null;

    this.init();
  }

  init() {
    this.buildDOM();
    this.buildScene();
    this.connectSSE();
    this.animate();
  }

  buildDOM() {
    this.root.style.cssText = `
      height: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 304px;
      overflow: hidden;
      background: var(--bg-deep, #0d0d12);
    `;

    // Canvas Wrapper
    this.canvasWrap = el('div', 'body-canvas-wrap', {
      position: 'relative',
      overflow: 'hidden',
      background: 'var(--bg-deep, #0d0d12)',
    });
    this.root.appendChild(this.canvasWrap);

    // Canvas
    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'display: block; width: 100%; height: 100%;';
    this.canvasWrap.appendChild(this.canvas);

    // Status Overlay
    this.statusEl = el('span', 'body-status-pill', {
      pointerEvents: 'none',
      userSelect: 'none',
    });
    this.statusEl.textContent = '○ Waiting for organism…';
    this.canvasWrap.appendChild(this.statusEl);

    // Camera controls: BODY is body-centric by default, while Free preserves
    // ordinary OrbitControls inspection when the observer wants it.
    const cameraBar = el('div', 'body-camera-bar', {
      position: 'absolute',
      top: '14px',
      left: '14px',
      zIndex: '4',
      display: 'flex',
      gap: '7px',
      alignItems: 'center',
      padding: '5px',
      border: '1px solid var(--line, #243342)',
      borderRadius: '9px',
      background: 'rgba(8, 17, 25, 0.82)',
      backdropFilter: 'blur(8px)',
      fontFamily: 'var(--mono, monospace)',
      fontSize: '11px',
    });
    this.followButton = document.createElement('button');
    this.followButton.type = 'button';
    this.followButton.textContent = '● Follow body';
    this.followButton.style.cssText = 'border:0;border-radius:6px;padding:6px 9px;background:rgba(80,250,123,.12);color:var(--mint,#50fa7b);font:inherit;cursor:pointer;';
    this.followButton.addEventListener('click', () => {
      this.followBody = !this.followBody;
      this.followButton.textContent = this.followBody ? '● Follow body' : '○ Free camera';
      this.followButton.style.color = this.followBody ? 'var(--mint,#50fa7b)' : 'var(--muted,#8a98a8)';
      if (this.followBody) this.resetCameraToBody();
    });

    const resetButton = document.createElement('button');
    resetButton.type = 'button';
    resetButton.textContent = 'Reset view';
    resetButton.style.cssText = 'border:0;border-radius:6px;padding:6px 9px;background:rgba(255,255,255,.045);color:var(--text,#e0e0e0);font:inherit;cursor:pointer;';
    resetButton.addEventListener('click', () => this.resetCameraToBody());

    cameraBar.appendChild(this.followButton);
    cameraBar.appendChild(resetButton);
    this.canvasWrap.appendChild(cameraBar);

    // Side Panel
    const panel = el('div', 'body-side-panel');
    this.root.appendChild(panel);
    this.buildPanel(panel);

    // Resize Observer
    this.resizeObs = new ResizeObserver(() => this.handleResize());
    this.resizeObs.observe(this.canvasWrap);
  }

  buildPanel(container) {
    container.style.cssText = `
      background: linear-gradient(180deg, rgba(14, 25, 37, 0.96), rgba(10, 19, 28, 0.98));
      border-left: 1px solid var(--line);
      padding: 16px 15px 22px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 7px;
      font-family: var(--mono, monospace);
      font-size: 13px;
      color: var(--text, #e0e0e0);
      min-width: 0;
      box-shadow: inset 1px 0 rgba(255,255,255,0.02);
    `;

    for (const f of PANEL_FIELDS) {
      if (f.section !== undefined) {
        const heading = document.createElement('div');
        heading.textContent = f.section;
        heading.style.cssText = `
          color: var(--muted, #888);
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-top: 14px;
          margin-bottom: 2px;
          border-bottom: 1px solid var(--line, #333);
          padding-bottom: 3px;
        `;
        container.appendChild(heading);
        continue;
      }

      const row = document.createElement('div');
      row.style.cssText = 'display: flex; justify-content: space-between; align-items: baseline; gap: 8px;';

      const labelEl = document.createElement('span');
      labelEl.textContent = f.label;
      labelEl.style.cssText = 'color: var(--muted, #888); font-size: 11px; white-space: nowrap;';

      const valueEl = document.createElement('span');
      valueEl.textContent = '—';
      valueEl.style.cssText = 'font-family: var(--mono, monospace); font-size: 13px; color: var(--text, #e0e0e0); text-align: right;';

      row.appendChild(labelEl);
      row.appendChild(valueEl);
      container.appendChild(row);

      this.panelEls[f.id] = valueEl;

      if (f.id === 'metabolic_reserve') {
        const track = document.createElement('div');
        track.style.cssText = 'height:5px;border-radius:999px;background:rgba(255,255,255,.07);overflow:hidden;margin:1px 0 4px;';
        this.reserveBarFill = document.createElement('div');
        this.reserveBarFill.style.cssText = 'height:100%;width:0%;border-radius:inherit;background:var(--mint,#50fa7b);transition:width 180ms linear,background 180ms linear;';
        track.appendChild(this.reserveBarFill);
        container.appendChild(track);
      }
    }
  }

  queueUIUpdate(id, text, color = null) {
    this.uiStateQueue[id] = { text, color: color ?? 'var(--text, #e0e0e0)' };
  }

  flushUIUpdates() {
    const now = performance.now();
    if (now - this.lastUIDrawTime < this.UI_UPDATE_INTERVAL_MS) return;
    
    for (const [id, data] of Object.entries(this.uiStateQueue)) {
      const el = this.panelEls[id];
      if (el) {
        if (el.textContent !== data.text) el.textContent = data.text;
        if (el.style.color !== data.color) el.style.color = data.color;
      }
    }
    this.uiStateQueue = {};
    this.lastUIDrawTime = now;
  }

  buildScene() {
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.setClearColor(0x0d0d12, 1);

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(0x0d0d12, 6, 16);

    const ambient = new THREE.AmbientLight(0x404060, 0.4);
    this.scene.add(ambient);

    // Directional light with dynamic shadow target
    this.dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    this.dirLight.castShadow = true;
    this.dirLight.shadow.mapSize.set(512, 512);
    this.dirLight.shadow.camera.near = 0.5;
    this.dirLight.shadow.camera.far = 20;
    this.dirLight.shadow.camera.left = this.dirLight.shadow.camera.bottom = -3;
    this.dirLight.shadow.camera.right = this.dirLight.shadow.camera.top = 3;
    this.scene.add(this.dirLight);

    const hemi = new THREE.HemisphereLight(0x87ceeb, 0x334455, 0.5);
    this.scene.add(hemi);

    const gridHelper = new THREE.GridHelper(100, 200, 0x2c3d4d, 0x1b2a36);
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.62;
    this.scene.add(gridHelper);

    const groundGeo = new THREE.PlaneGeometry(100, 100);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x111122, transparent: true, opacity: 0.6, roughness: 1, metalness: 0,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);

    this.camera = new THREE.PerspectiveCamera(50, 1, 0.05, 50);
    this.camera.position.set(2.2, 1.7, 3.2);

    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.target.set(0, 0.9, 0);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.rotateSpeed = 0.8;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 0.7;
    this.controls.maxDistance = 10;
    this.controls.maxPolarAngle = Math.PI * 0.92;

    this.baseNode = new THREE.Object3D();
    this.baseNode.name = 'humanoid_base';
    this.baseNode.position.copy(this.targetBasePos);
    this.scene.add(this.baseNode);

    // Attach light target to baseNode for dynamic shadows
    this.dirLight.target = this.baseNode;

    this.buildSkeleton();
    this.handleResize();
  }

  buildSkeleton() {
    const linkNames = new Set(['pelvis']);
    for (const j of JOINT_TOPOLOGY) {
      linkNames.add(j.parent);
      linkNames.add(j.child);
    }

    for (const name of linkNames) {
      const node = new THREE.Object3D();
      node.name = name;
      this.linkObjs[name] = node;
    }

    for (const [segName, seg] of Object.entries(SEGMENTS)) {
      const linkNode = this.linkObjs[segName];
      if (!linkNode) continue;

      const [w, d, h] = seg.wdh;
      const [tx, ty, tz] = pbPos(...seg.offset);

      const geo = new THREE.BoxGeometry(w, h, d);
      const mat = new THREE.MeshStandardMaterial({
        color: SEGMENT_COLORS[segName] ?? 0x888888,
        roughness: 0.7, metalness: 0.1,
      });

      const mesh = new THREE.Mesh(geo, mat);
      mesh.name = `${segName}_mesh`;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.position.set(tx, ty, tz);
      linkNode.add(mesh);
    }

    for (const jdef of JOINT_TOPOLOGY) {
      const parentNode = this.linkObjs[jdef.parent];
      const childNode = this.linkObjs[jdef.child];
      if (!parentNode || !childNode) {
        console.warn(`[body.js] Unknown link in topology: ${jdef.parent} → ${jdef.child}`);
        continue;
      }

      const [tx, ty, tz] = pbPos(...jdef.offset);
      childNode.position.set(tx, ty, tz);
      parentNode.add(childNode);

      this.jointObjs[jdef.name] = childNode;
      this.targetJointAngles.set(jdef.name, 0); // Initialize targets
      this.jointActivity.set(jdef.name, 0);

      const markerGeo = new THREE.SphereGeometry(0.026, 10, 8);
      const markerMat = new THREE.MeshBasicMaterial({
        color: 0x50fa9a,
        transparent: true,
        opacity: 0,
        depthWrite: false,
      });
      const marker = new THREE.Mesh(markerGeo, markerMat);
      marker.name = `${jdef.name}_activity_marker`;
      marker.visible = false;
      childNode.add(marker);
      this.jointMarkers[jdef.name] = marker;
    }

    this.baseNode.add(this.linkObjs['pelvis']);
  }

  resetCameraToBody() {
    if (!this.camera || !this.controls || !this.baseNode) return;
    const target = this.baseNode.position.clone();
    target.y += 0.55;
    this.controls.target.copy(target);
    this.camera.position.copy(target).add(new THREE.Vector3(2.35, 1.25, 3.05));
    this.controls.update();
  }

  updateBodySummary() {
    const parts = [];
    if (this.bodyState.alive === true) parts.push('Alive');
    else if (this.bodyState.alive === false) parts.push('Dead');

    if (Number.isFinite(this.bodyState.reserve)) {
      if (this.bodyState.reserve < 0.2) parts.push('critical reserve');
      else if (this.bodyState.reserve < 0.35) parts.push('low reserve');
      else parts.push('reserve stable');
    }

    if (Number.isFinite(this.bodyState.jointMotion)) {
      parts.push(this.bodyState.jointMotion > 0.05 ? 'moving' : 'quiet');
    }

    if (Number.isFinite(this.bodyState.resourceProgress)) {
      if (this.bodyState.resourceProgress > 0.02) parts.push('resource progress');
      else if (this.bodyState.resourceProgress < -0.02) parts.push('moving away');
      else parts.push('no resource progress');
    }

    this.queueUIUpdate('state_summary', parts.length ? parts.join(' · ') : '—');
  }

  handleResize() {
    if (!this.canvasWrap) return;
    const w = this.canvasWrap.clientWidth;
    const h = this.canvasWrap.clientHeight;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  }

  connectSSE() {
    this.sse = new EventSource(this.sseUrl);
    
    this.sse.addEventListener('message', (ev) => {
      if (this.unmounted) return;

      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      if (!data || !data.type) return;

      switch (data.type) {
        case 'body':      this.handleBodyEvent(data);      break;
        case 'cognition': this.handleCognitionEvent(data); break;
        case 'vitals':    this.handleVitalsEvent(data);    break;
      }
    });

    this.sse.onerror = () => {
      if (this.unmounted) return;

      if (this.statusEl) {
        this.statusEl.textContent = '○ Connection lost — retrying…';
        this.statusEl.style.color = 'var(--amber, #f1fa8c)';
      }
    };
  }

  handleBodyEvent(data) {
    if (this.statusEl && this.statusEl.textContent !== '● Live') {
      this.statusEl.textContent = '● Live';
      this.statusEl.style.color = 'var(--mint, #50fa7b)';
    }

    // Store target positions instead of applying immediately (for lerping)
    if (data.base_position) {
      const nextPos = new THREE.Vector3(...pbPos(...data.base_position));
      if (this.previousObservedBasePos) {
        const step = nextPos.distanceTo(this.previousObservedBasePos);
        if (Number.isFinite(step) && step < 2.0) this.distanceTravelled += step;
      }
      this.previousObservedBasePos = nextPos.clone();
      this.targetBasePos.copy(nextPos);
      this.queueUIUpdate('distance_travelled', `${this.distanceTravelled.toFixed(2)} m`);
    }
    if (data.base_orientation) {
      this.targetBaseQuat.copy(pbQuat(...data.base_orientation));
    }
    if (Array.isArray(data.joints)) {
      let active = 0;
      for (const j of data.joints) {
        if (!j || !Number.isFinite(j.position)) continue;
        const previous = this.previousJointPositions.get(j.name);
        const delta = previous === undefined ? 0 : Math.abs(j.position - previous);
        this.previousJointPositions.set(j.name, j.position);
        this.targetJointAngles.set(j.name, j.position);

        const activity = Math.min(1, delta / 0.045);
        this.jointActivity.set(j.name, Math.max(activity, (this.jointActivity.get(j.name) ?? 0) * 0.7));
        if (delta > 0.006) active += 1;
      }
      this.activeJointCount = active;
      this.queueUIUpdate('active_joints', `${active} / ${JOINT_TOPOLOGY.length}`, active > 0 ? 'var(--cyan,#8be9fd)' : null);
    }

    // Queue UI updates (Throttling)
    if (data.tick !== undefined) this.queueUIUpdate('tick', String(data.tick));
    if (data.contact_count !== undefined) this.queueUIUpdate('contact_count', String(data.contact_count));
    if (data.metabolic_reserve !== undefined) {
      const reserve = Number(data.metabolic_reserve);
      const pct = (reserve * 100).toFixed(0);
      const color = reserve < 0.2
        ? 'var(--coral, #ff5555)'
        : reserve < 0.35
          ? 'var(--amber, #f1fa8c)'
          : 'var(--text, #e0e0e0)';
      this.queueUIUpdate('metabolic_reserve', `${pct}%`, color);
      this.bodyState.reserve = reserve;

      if (Number.isFinite(reserve)) {
        this.reserveHistory.push({ tick: Number(data.tick), value: reserve });
        if (this.reserveHistory.length > 40) this.reserveHistory.shift();
        const old = this.reserveHistory[0];
        const delta = old ? reserve - old.value : 0;
        this.bodyState.reserveTrend = delta;
        const arrow = delta > 0.003 ? '↑' : delta < -0.003 ? '↓' : '↔';
        const signed = delta >= 0 ? '+' : '';
        this.queueUIUpdate('reserve_trend', `${arrow} ${signed}${(delta * 100).toFixed(1)} pp`,
          delta < -0.01 ? 'var(--coral,#ff5555)' : delta > 0.01 ? 'var(--mint,#50fa7b)' : null);
        if (this.reserveBarFill) {
          this.reserveBarFill.style.width = `${Math.max(0, Math.min(100, reserve * 100))}%`;
          this.reserveBarFill.style.background = reserve < 0.2
            ? 'var(--coral,#ff5555)'
            : reserve < 0.35 ? 'var(--amber,#f1fa8c)' : 'var(--mint,#50fa7b)';
        }
      }
      this.updateBodySummary();
    }
  }

  handleCognitionEvent(data) {
    if (data.schema_confidence !== undefined) this.queueUIUpdate('schema_conf', data.schema_confidence.toFixed(3));
    if (data.motor_origin !== undefined) this.queueUIUpdate('motor_origin', data.motor_origin);
    if (data.predictor_count !== undefined) this.queueUIUpdate('predictor_count', String(data.predictor_count));
    if (data.prediction_error !== undefined) this.queueUIUpdate('prediction_error', data.prediction_error.toFixed(4));
    
    if (data.slm_active !== undefined) {
      const active = Boolean(data.slm_active);
      this.queueUIUpdate('slm_active', active ? 'active' : 'inactive', active ? 'var(--mint, #50fa7b)' : 'var(--muted, #888)');
    }
    if (data.prospective_selected !== undefined) {
      const ev = data.prospective_expected_value !== undefined ? ` ${data.prospective_expected_value.toFixed(3)}` : '';
      this.queueUIUpdate('prospective', data.prospective_selected ? `✓${ev}` : '✗', data.prospective_selected ? 'var(--cyan, #8be9fd)' : 'var(--muted, #888)');
    }
  }

  handleVitalsEvent(data) {
    if (data.alive !== undefined) {
      this.bodyState.alive = Boolean(data.alive);
      this.queueUIUpdate('alive', data.alive ? '● Alive' : '○ Dead', data.alive ? 'var(--mint, #50fa7b)' : 'var(--coral, #ff5555)');
    }
    if (data.joint_motion !== undefined) {
      this.bodyState.jointMotion = Number(data.joint_motion);
      this.queueUIUpdate('joint_motion', data.joint_motion.toFixed(3));
    }
    if (data.active_effectors !== undefined) {
      this.queueUIUpdate('active_effectors', String(data.active_effectors));
    }
    if (data.resource_distance !== undefined) {
      this.bodyState.resourceDistance = Number(data.resource_distance);
      this.queueUIUpdate('resource_distance', `${Math.max(0, data.resource_distance).toFixed(2)} m`);
    }
    if (data.resource_progress !== undefined) {
      this.bodyState.resourceProgress = Number(data.resource_progress);
      const sign = data.resource_progress > 0 ? '+' : '';
      this.queueUIUpdate('resource_progress', `${sign}${data.resource_progress.toFixed(2)} m`,
        data.resource_progress > 0.02 ? 'var(--mint,#50fa7b)' : data.resource_progress < -0.02 ? 'var(--coral,#ff5555)' : null);
    }
    if (data.displacement_from_origin !== undefined) {
      const displacement = Number(data.displacement_from_origin);
      this.queueUIUpdate('displacement', `${displacement.toFixed(2)} m`);
      const efficiency = this.distanceTravelled > 0.05
        ? Math.max(0, Math.min(1, displacement / this.distanceTravelled))
        : 0;
      this.queueUIUpdate('locomotion_efficiency', this.distanceTravelled > 0.05 ? `${(efficiency * 100).toFixed(0)}%` : '—');
    }
    this.updateBodySummary();
  }

  animate = () => {
    if (this.unmounted) return;

    this.rafId = requestAnimationFrame(this.animate);
    const delta = Math.min(Math.max(this.clock.getDelta(), 0.016), 0.05);
    const lerpFactor = 1 - Math.exp(-delta * 10);

    this.baseNode.position.lerp(this.targetBasePos, lerpFactor);
    this.baseNode.quaternion.slerp(this.targetBaseQuat, lerpFactor);

    for (const jdef of JOINT_TOPOLOGY) {
      const targetAngle = this.targetJointAngles.get(jdef.name);
      if (targetAngle === undefined) continue;

      const node = this.jointObjs[jdef.name];
      if (!node) continue;

      switch (jdef.axis) {
        case 'Y': node.rotation.y = THREE.MathUtils.lerp(node.rotation.y, targetAngle, lerpFactor); break;
        case 'X': node.rotation.x = THREE.MathUtils.lerp(node.rotation.x, targetAngle, lerpFactor); break;
        case 'Z': node.rotation.z = THREE.MathUtils.lerp(node.rotation.z, targetAngle, lerpFactor); break;
      }
    }

    if (this.dirLight) {
      this.dirLight.position.copy(this.baseNode.position).add(this.lightOffset);
    }

    // Activity markers turn body motion into something observable instead of
    // forcing the observer to infer it from one aggregate scalar.
    for (const [name, marker] of Object.entries(this.jointMarkers)) {
      const activity = this.jointActivity.get(name) ?? 0;
      const decayed = activity * 0.92;
      this.jointActivity.set(name, decayed);
      marker.visible = decayed > 0.08;
      marker.material.opacity = Math.min(0.9, 0.12 + decayed * 0.78);
      marker.scale.setScalar(0.75 + decayed * 0.9);
    }

    if (this.followBody && this.controls && this.camera) {
      this.followTarget.copy(this.baseNode.position);
      this.followTarget.y += 0.55;
      const before = this.controls.target.clone();
      this.controls.target.lerp(this.followTarget, 0.14);
      this.followDelta.copy(this.controls.target).sub(before);
      this.camera.position.add(this.followDelta);
    }

    this.flushUIUpdates();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * Tear down the viewer completely.
   *
   * Safe to call more than once. Stops rendering and streaming first, then
   * disposes Three.js resources and finally releases DOM/object references.
   */
  unmount() {
    if (this.unmounted) return;
    this.unmounted = true;

    // Stop asynchronous producers before disposing anything they can touch.
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }

    if (this.sse) {
      this.sse.close();
      this.sse = null;
    }

    if (this.resizeObs) {
      this.resizeObs.disconnect();
      this.resizeObs = null;
    }

    // OrbitControls installs DOM listeners, so dispose it explicitly.
    if (this.controls) {
      this.controls.dispose();
      this.controls = null;
    }

    // Dispose scene-owned GPU resources.
    if (this.scene) {
      this.scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();

        if (obj.material) {
          if (Array.isArray(obj.material)) {
            obj.material.forEach((material) => material.dispose());
          } else {
            obj.material.dispose();
          }
        }
      });
      this.scene.clear();
      this.scene = null;
    }

    if (this.renderer) {
      this.renderer.dispose();
      this.renderer = null;
    }

    // Release data structures and Three.js object references.
    this.camera = null;
    this.baseNode = null;
    this.dirLight = null;
    this.canvas = null;
    this.canvasWrap = null;
    this.statusEl = null;

    this.jointObjs = {};
    this.linkObjs = {};
    this.jointMarkers = {};
    this.panelEls = {};
    this.uiStateQueue = {};
    this.targetJointAngles.clear();

    // Restore the host element rather than blindly erasing styles it owned
    // before the viewer was mounted.
    if (this.root) {
      while (this.root.firstChild) {
        this.root.removeChild(this.root.firstChild);
      }
      this.root.style.cssText = this.rootStyleBeforeMount;
      this.root = null;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Public module API
// ─────────────────────────────────────────────────────────────────────────────

let _globalInstance = null;

export function mount(root) {
  if (_globalInstance) unmount();
  _globalInstance = new HumanoidViewer(root);
  return _globalInstance;
}

export function unmount() {
  if (_globalInstance) {
    _globalInstance.unmount();
    _globalInstance = null;
  }
}