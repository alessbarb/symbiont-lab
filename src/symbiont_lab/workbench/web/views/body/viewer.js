/**
 * Stateful Three.js body renderer.
 * Body morphology is observer-only and selected from the active Physics3D
 * descriptor. Public mounting belongs to ../body.js.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { pbPos, pbQuat } from './coordinates.js';
import {
  SEGMENT_COLORS,
  bodyModelFromCatalog,
  dominantAxis,
  fallbackBodyModel,
} from './model.js';
import { BodyWorkspace } from './workspace.js';
import { mountBodyCameraControls } from './camera-controls.js';
import { BODY_PRESENTATION } from './presentation-config.js';
import { createAnatomicalSegment, createTechnicalJointMarker } from './anatomical-visual.js';


function el(tag, cls, styles = {}) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  Object.assign(node.style, styles);
  return node;
}

export class BodyViewer {
  constructor(rootElement, sseUrl = '/api/organism') {
    if (!(rootElement instanceof HTMLElement)) {
      throw new TypeError('BodyViewer requires a valid HTMLElement root');
    }

    this.root = rootElement;
    this.rootStyleBeforeMount = rootElement.style.cssText;
    this.sseUrl = sseUrl;
    this.unmounted = false;

    this.bodyModels = new Map();
    this.bodyModel = fallbackBodyModel();
    this.activeBodyKind = this.bodyModel.bodyKind;
    this.bodyModels.set(this.activeBodyKind, this.bodyModel);

    // Three.js instances
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.baseNode = null;
    this.skeletonRoot = null;
    this.dirLight = null;
    this.lightOffset = new THREE.Vector3(2, 4, 3);
    this.followBody = true;
    this.followTarget = new THREE.Vector3();
    this.followDelta = new THREE.Vector3();
    
    // Scene objects mapping
    this.jointObjs = {};
    this.linkObjs = {};
    this.segmentMeshes = {};
    this.jointMarkers = {};
    this.jointActivity = new Map();

    // Observer-side body history. These values never feed back into the organism.
    this.previousObservedBasePos = null;
    this.observerStartBasePos = null;
    this.previousJointPositions = new Map();
    this.distanceTravelled = 0;
    this.activeJointCount = 0;
    this.reserveHistory = [];
    this.observerResourceBaseline = null;
    this.observerPathAtResourceBaseline = 0;
    this.resourceObject = null;
    this.resourceGuide = null;
    this.resourceGuidePositions = null;
    this.resourceIndicator = null;
    this.resourceIndicatorArrow = null;
    this.resourceIndicatorLabel = null;
    this.resourceScreenVector = new THREE.Vector3();
    this.trajectoryPoints = [];
    this.trajectoryLine = null;
    this.frameBounds = new THREE.Box3();
    this.frameCenter = new THREE.Vector3();
    this.frameSize = new THREE.Vector3();
    this.lastFrameFitTime = 0;
    this.bodyState = {
      alive: null,
      reserve: null,
      reserveTrend: 0,
      resourceProgress: null,
      resourceDistance: null,
      jointMotion: null,
      contactCount: null,
    };
    
    // Latest authoritative body state. Presentation frames are observer-only:
    // they are never sent back to Physics3D or exposed to the organism.
    this.targetBasePos = new THREE.Vector3(0, 1.05, 0);
    this.targetBaseQuat = new THREE.Quaternion();
    this.targetJointAngles = new Map();
    this.targetLinkTransforms = new Map();
    this.hasAuthoritativeLinkPoses = false;

    // Render one telemetry cadence behind the live stream so Three.js always
    // has two real poses to interpolate between. The delay adapts to SSE
    // cadence but remains bounded and affects presentation only.
    this.poseFrames = [];
    this.poseCadenceMs = null;
    this.poseIntervalsMs = [];
    this.presentationDelayMs = BODY_PRESENTATION.interpolation.initialDelayMs;
    this.MAX_POSE_FRAMES = BODY_PRESENTATION.interpolation.maxPoseFrames;
    this.hasDensePoseStream = false;
    this.presentationSourceTimeMs = null;
    this.presentationStarted = false;

    // Dense physics poses arrive in per-cognition-tick batches. Track the
    // producer's actual wall-clock rate so the renderer consumes simulation
    // time at the rate it is really being produced instead of assuming 1x.
    this.denseProducerTick = null;
    this.denseProducerArrivalMs = null;
    this.denseTickSpanMs = 1000 / BODY_PRESENTATION.interpolation.nominalDenseHz;
    this.producerRateSamples = [];
    this.producerRate = 1;
    this.presentationPlaybackRate = 1;
    this.presentationBufferMs = 1.5 * this.denseTickSpanMs;
    this.clock = new THREE.Clock();
    this.followDistance = BODY_PRESENTATION.camera.initialDistance;

    // UI Throttling State
    this.panelEls = {};
    this.statusEl = null;
    this.uiStateQueue = {};
    this.lastUIDrawTime = 0;
    this.UI_UPDATE_INTERVAL_MS = BODY_PRESENTATION.uiUpdateIntervalMs;
    this.workspace = new BodyWorkspace(this);

    // Event & Render handles
    this.rafId = null;
    this.sse = null;
    this.resizeObs = null;
    this.cameraControls = null;

    this.init();
  }

  init() {
    this.buildDOM();
    this.buildScene();
    this.loadBodyModels();
    this.connectSSE();
    this.animate();
  }

  async loadBodyModels() {
    try {
      const response = await fetch('/api/bodies', { cache: 'no-store' });
      if (!response.ok) return;
      const payload = await response.json();
      for (const item of payload.items ?? []) {
        const model = bodyModelFromCatalog(item);
        if (model?.bodyKind) this.bodyModels.set(model.bodyKind, model);
      }
    } catch {
      // Presentation catalog failure must never affect the running organism.
    }
  }

  ensureBodyModel(bodyKind) {
    const requested = String(bodyKind || this.activeBodyKind || 'anthropomorphic-v6');
    if (requested === this.activeBodyKind) return;
    const model = this.bodyModels.get(requested);
    if (!model) return;
    this.activeBodyKind = requested;
    this.bodyModel = model;
    this.rebuildSkeleton();
  }

  buildDOM() {
    this.root.classList.add('body-view-root');

    // Canvas Wrapper
    this.canvasWrap = el('div', 'body-canvas-wrap');
    this.root.appendChild(this.canvasWrap);

    // Canvas
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'body-canvas';
    this.canvasWrap.appendChild(this.canvas);

    // Status Overlay
    this.statusEl = el('span', 'body-status-pill', {
      pointerEvents: 'none',
      userSelect: 'none',
    });
    this.statusEl.textContent = '○ Waiting for organism…';
    this.canvasWrap.appendChild(this.statusEl);

    this.presentationDebugEl = el('div', 'body-presentation-debug', {
      position: 'absolute',
      left: '14px',
      bottom: '14px',
      zIndex: '3',
      padding: '6px 8px',
      border: '1px solid rgba(116, 151, 178, 0.14)',
      borderRadius: '6px',
      background: 'rgba(7, 15, 22, 0.58)',
      color: 'var(--muted, #8a98a8)',
      fontFamily: 'var(--mono, monospace)',
      fontSize: '10px',
      lineHeight: '1.45',
      letterSpacing: '0.015em',
      pointerEvents: 'none',
      userSelect: 'none',
      whiteSpace: 'pre',
    });
    this.presentationDebugEl.textContent = 'presentation: waiting';
    this.canvasWrap.appendChild(this.presentationDebugEl);

    this.situationEl = el('div', 'body-situation-overlay', {
      position: 'absolute',
      top: '15px',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: '3',
      maxWidth: '58%',
      padding: '7px 11px',
      border: '1px solid rgba(116, 151, 178, 0.18)',
      borderRadius: '8px',
      background: 'rgba(7, 15, 22, 0.66)',
      backdropFilter: 'blur(8px)',
      color: 'var(--text, #e0e0e0)',
      fontFamily: 'var(--mono, monospace)',
      fontSize: '11px',
      letterSpacing: '0.02em',
      textAlign: 'center',
      pointerEvents: 'none',
      userSelect: 'none',
    });
    this.situationEl.textContent = 'Waiting for body telemetry';
    this.canvasWrap.appendChild(this.situationEl);

    this.resourceIndicator = el('div', 'body-resource-indicator', {
      position: 'absolute',
      zIndex: '3',
      display: 'none',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 8px',
      border: '1px solid rgba(139, 207, 99, 0.35)',
      borderRadius: '8px',
      background: 'rgba(8, 17, 25, 0.80)',
      color: '#a8df84',
      fontFamily: 'var(--mono, monospace)',
      fontSize: '11px',
      pointerEvents: 'none',
      userSelect: 'none',
      transform: 'translate(-50%, -50%)',
      whiteSpace: 'nowrap',
      backdropFilter: 'blur(6px)',
    });
    this.resourceIndicatorArrow = document.createElement('span');
    this.resourceIndicatorArrow.className = 'body-resource-indicator-arrow';
    this.resourceIndicatorArrow.textContent = '➜';
    this.resourceIndicatorLabel = document.createElement('span');
    this.resourceIndicatorLabel.textContent = 'Resource';
    this.resourceIndicator.appendChild(this.resourceIndicatorArrow);
    this.resourceIndicator.appendChild(this.resourceIndicatorLabel);
    this.canvasWrap.appendChild(this.resourceIndicator);

    // Camera controls are presentation-only and live outside the renderer.
    this.cameraControls = mountBodyCameraControls(this.canvasWrap, {
      isFollowing: () => this.followBody,
      onToggleFollow: () => {
        this.followBody = !this.followBody;
        if (this.followBody) this.resetCameraToBody();
      },
      onReset: () => this.resetCameraToBody(),
    });
    this.followButton = this.cameraControls.followButton;

    // Side Panel + Mind-style body workspace navigation.
    const panel = el('div', 'body-side-panel');
    this.root.appendChild(panel);
    this.workspace.mount(this.root, this.canvasWrap, panel);
    this.buildPanel(panel);

    // Resize Observer
    this.resizeObs = new ResizeObserver(() => this.handleResize());
    this.resizeObs.observe(this.canvasWrap);
  }

  buildPanel(container) {
    // BodyWorkspace owns the inspector. Keep this method as the compatibility
    // boundary for the renderer lifecycle.
    this.panelEls = {};
    this.workspace.render();
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
      this.workspace?.updateMetric(id, data.text, data.color);
    }
    this.uiStateQueue = {};
    this.lastUIDrawTime = now;
  }

  buildScene() {
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, BODY_PRESENTATION.maxPixelRatio));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.16;
    this.renderer.setClearColor(0x111923, 1);

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(0x111923, 8, 22);

    const ambient = new THREE.AmbientLight(0x63758f, 0.68);
    this.scene.add(ambient);

    // Directional light with dynamic shadow target
    this.dirLight = new THREE.DirectionalLight(0xf2f7ff, 1.05);
    this.dirLight.castShadow = true;
    this.dirLight.shadow.mapSize.set(1024, 1024);
    this.dirLight.shadow.camera.near = 0.5;
    this.dirLight.shadow.camera.far = 20;
    this.dirLight.shadow.camera.left = this.dirLight.shadow.camera.bottom = -3;
    this.dirLight.shadow.camera.right = this.dirLight.shadow.camera.top = 3;
    this.scene.add(this.dirLight);

    const hemi = new THREE.HemisphereLight(0x9bc7e8, 0x465363, 0.78);
    this.scene.add(hemi);

    const fill = new THREE.DirectionalLight(0x8db6d8, 0.34);
    fill.position.set(-3, 2.5, -2);
    this.scene.add(fill);

    const rim = new THREE.DirectionalLight(0xb8d8ef, 0.42);
    rim.position.set(1.5, 2.4, -3.5);
    this.scene.add(rim);

    const gridHelper = new THREE.GridHelper(100, 200, 0x35495b, 0x22313d);
    gridHelper.material.transparent = true;
    gridHelper.material.opacity = 0.48;
    this.scene.add(gridHelper);

    const trajectoryGeometry = new THREE.BufferGeometry();
    const trajectoryMaterial = new THREE.LineBasicMaterial({
      color: 0x4dcce8,
      transparent: true,
      opacity: 0.52,
    });
    this.trajectoryLine = new THREE.Line(trajectoryGeometry, trajectoryMaterial);
    this.trajectoryLine.visible = false;
    this.trajectoryLine.renderOrder = 2;
    this.scene.add(this.trajectoryLine);

    const groundGeo = new THREE.PlaneGeometry(100, 100);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x18212c, transparent: true, opacity: 0.78, roughness: 1, metalness: 0,
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
    this.controls.minDistance = BODY_PRESENTATION.camera.minOrbitDistance;
    this.controls.maxDistance = BODY_PRESENTATION.camera.maxOrbitDistance;
    this.controls.maxPolarAngle = Math.PI * 0.92;

    this.baseNode = new THREE.Object3D();
    this.baseNode.name = 'body_base';
    this.baseNode.position.copy(this.targetBasePos);
    this.scene.add(this.baseNode);

    // Attach light target to baseNode for dynamic shadows
    this.dirLight.target = this.baseNode;

    this.buildSkeleton();
    this.handleResize();
  }

  disposeSkeleton() {
    if (!this.skeletonRoot) return;
    this.skeletonRoot.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((item) => item.dispose());
        else obj.material.dispose();
      }
    });
    this.baseNode.remove(this.skeletonRoot);
    this.skeletonRoot = null;
  }

  rebuildSkeleton() {
    this.disposeSkeleton();
    this.linkObjs = {};
    this.segmentMeshes = {};
    this.jointMarkers = {};
    this.jointObjs = {};
    this.jointActivity.clear();
    this.previousJointPositions.clear();
    this.targetJointAngles.clear();
    this.targetLinkTransforms.clear();
    this.poseFrames.length = 0;
    this.hasAuthoritativeLinkPoses = false;
    this.presentationStarted = false;
    this.presentationSourceTimeMs = null;
    this.buildSkeleton();
    if (this.followBody) this.resetCameraToBody();
  }

  buildSkeleton() {
    const model = this.bodyModel;
    this.skeletonRoot = new THREE.Object3D();
    this.skeletonRoot.name = `${model.bodyKind}_skeleton`;
    this.baseNode.add(this.skeletonRoot);

    const linkNames = new Set([model.baseLink]);
    for (const joint of model.joints) {
      linkNames.add(joint.parent);
      linkNames.add(joint.child);
    }

    for (const name of linkNames) {
      const node = new THREE.Object3D();
      node.name = name;
      this.linkObjs[name] = node;
    }

    for (const [segName, seg] of Object.entries(model.segments)) {
      const linkNode = this.linkObjs[segName];
      if (!linkNode) continue;

      const [tx, ty, tz] = pbPos(...seg.offset);
      const mesh = createAnatomicalSegment(segName, seg, model.bodyKind);
      mesh.position.set(tx, ty, tz);
      linkNode.add(mesh);
      this.segmentMeshes[segName] = mesh;
    }

    for (const jdef of model.joints) {
      const parentNode = this.linkObjs[jdef.parent];
      const childNode = this.linkObjs[jdef.child];
      if (!parentNode || !childNode) continue;

      const [tx, ty, tz] = pbPos(...jdef.offset);
      childNode.position.set(tx, ty, tz);
      parentNode.add(childNode);

      this.jointObjs[jdef.name] = childNode;
      this.targetJointAngles.set(jdef.name, 0);
      this.jointActivity.set(jdef.name, 0);

      const marker = createTechnicalJointMarker(jdef.name);
      marker.visible = true;
      childNode.add(marker);
      this.jointMarkers[jdef.name] = marker;
    }

    const baseLink = this.linkObjs[model.baseLink];
    if (baseLink) this.skeletonRoot.add(baseLink);

    if (!this.resourceObject) {
      const resourceGeo = new THREE.SphereGeometry(0.18, 20, 14);
      const resourceMat = new THREE.MeshStandardMaterial({
        color: 0x8bcf63,
        emissive: 0x294f1c,
        emissiveIntensity: 0.55,
        roughness: 0.55,
        metalness: 0,
      });
      this.resourceObject = new THREE.Mesh(resourceGeo, resourceMat);
      this.resourceObject.name = 'observer_resource';
      this.resourceObject.castShadow = true;
      this.resourceObject.receiveShadow = true;
      this.resourceObject.visible = false;
      this.scene.add(this.resourceObject);

      const guideGeo = new THREE.BufferGeometry();
      this.resourceGuidePositions = new Float32Array(6);
      guideGeo.setAttribute('position', new THREE.BufferAttribute(this.resourceGuidePositions, 3));
      const guideMat = new THREE.LineDashedMaterial({
        color: 0x8bcf63,
        transparent: true,
        opacity: 0.18,
        dashSize: 0.10,
        gapSize: 0.10,
      });
      this.resourceGuide = new THREE.Line(guideGeo, guideMat);
      this.resourceGuide.visible = false;
      this.scene.add(this.resourceGuide);
    }
  }

  resetCameraToBody() {
    if (!this.camera || !this.controls || !this.baseNode) return;
    this.baseNode.updateWorldMatrix(true, true);
    this.frameBounds.setFromObject(this.baseNode);
    if (!this.frameBounds.isEmpty()) {
      this.frameBounds.getCenter(this.frameCenter);
    } else {
      this.frameCenter.copy(this.baseNode.position);
      this.frameCenter.y += 0.5;
    }
    this.followTarget.copy(this.frameCenter);
    this.controls.target.copy(this.frameCenter);
    this.camera.position.copy(this.frameCenter).add(new THREE.Vector3(2.25, 1.35, 2.85));
    this.followDistance = this.camera.position.distanceTo(this.frameCenter);
    this.controls.update();
  }

  fitCameraToBody(now, delta) {
    if (!this.followBody || !this.baseNode) return;

    // Bounds are relatively expensive, so refresh the desired framing at a
    // modest rate. Motion toward that target still happens every render frame.
    if (now - this.lastFrameFitTime >= BODY_PRESENTATION.camera.boundsRefreshMs) {
      this.lastFrameFitTime = now;
      this.baseNode.updateWorldMatrix(true, true);
      this.frameBounds.setFromObject(this.baseNode);
      if (!this.frameBounds.isEmpty()) {
        this.frameBounds.getCenter(this.frameCenter);
        this.frameBounds.getSize(this.frameSize);
        const radius = Math.max(0.55, this.frameSize.length() * 0.5);
        const halfFov = THREE.MathUtils.degToRad(this.camera.fov * 0.5);
        this.followDistance = THREE.MathUtils.clamp(
          (radius / Math.tan(halfFov)) * BODY_PRESENTATION.camera.framingMargin,
          BODY_PRESENTATION.camera.minFollowDistance,
          BODY_PRESENTATION.camera.maxFollowDistance,
        );
        this.followTarget.copy(this.frameCenter);
      }
    }

    const viewDir = this.camera.position.clone().sub(this.controls.target);
    if (viewDir.lengthSq() < 1e-6) viewDir.set(0.6, 0.35, 1);
    viewDir.normalize();

    const targetAlpha = 1 - Math.exp(-delta * BODY_PRESENTATION.camera.targetResponsiveness);
    const cameraAlpha = 1 - Math.exp(-delta * BODY_PRESENTATION.camera.cameraResponsiveness);
    this.controls.target.lerp(this.followTarget, targetAlpha);
    this.followDelta.copy(this.followTarget).addScaledVector(viewDir, this.followDistance);
    this.camera.position.lerp(this.followDelta, cameraAlpha);
  }

  updateResourceGuide() {
    if (!this.resourceGuide || !this.resourceObject?.visible || !this.baseNode) return;
    const start = this.baseNode.position;
    const end = this.resourceObject.position;
    this.resourceGuidePositions[0] = start.x;
    this.resourceGuidePositions[1] = Math.max(0.03, start.y + 0.15);
    this.resourceGuidePositions[2] = start.z;
    this.resourceGuidePositions[3] = end.x;
    this.resourceGuidePositions[4] = Math.max(0.03, end.y);
    this.resourceGuidePositions[5] = end.z;
    this.resourceGuide.geometry.attributes.position.needsUpdate = true;
    this.resourceGuide.computeLineDistances();
  }

  updateResourceIndicator() {
    if (!this.resourceIndicator || !this.resourceObject?.visible || !this.camera || !this.canvasWrap) {
      if (this.resourceIndicator) this.resourceIndicator.style.display = 'none';
      if (this.resourceGuide) this.resourceGuide.visible = false;
      return;
    }

    this.resourceScreenVector.copy(this.resourceObject.position).project(this.camera);
    const ndc = this.resourceScreenVector;
    const inFront = ndc.z >= -1 && ndc.z <= 1;
    const onScreen = inFront && Math.abs(ndc.x) <= 0.92 && Math.abs(ndc.y) <= 0.88;

    // The world-space guide is only useful when both endpoints are actually
    // visible. Off-screen resources use the edge cue instead.
    if (this.resourceGuide) this.resourceGuide.visible = onScreen;
    if (onScreen) {
      this.resourceIndicator.style.display = 'none';
      return;
    }

    let x = ndc.x;
    let y = ndc.y;
    if (!inFront || !Number.isFinite(x) || !Number.isFinite(y)) {
      const worldDir = this.resourceObject.position.clone().sub(this.camera.position).normalize();
      const cameraDir = new THREE.Vector3();
      this.camera.getWorldDirection(cameraDir);
      const right = new THREE.Vector3().crossVectors(cameraDir, this.camera.up).normalize();
      const up = new THREE.Vector3().crossVectors(right, cameraDir).normalize();
      x = worldDir.dot(right);
      y = worldDir.dot(up);
      if (worldDir.dot(cameraDir) < 0) {
        x = -x || 1;
        y = -y;
      }
    }

    const len = Math.max(1e-6, Math.max(Math.abs(x), Math.abs(y)));
    x /= len;
    y /= len;
    const marginX = 54;
    const marginY = 50;
    const halfW = Math.max(1, this.canvasWrap.clientWidth / 2 - marginX);
    const halfH = Math.max(1, this.canvasWrap.clientHeight / 2 - marginY);
    const px = this.canvasWrap.clientWidth / 2 + x * halfW;
    const py = this.canvasWrap.clientHeight / 2 - y * halfH;

    this.resourceIndicator.style.left = `${px}px`;
    this.resourceIndicator.style.top = `${py}px`;
    this.resourceIndicator.style.display = 'flex';
    const angle = Math.atan2(-y, x) * 180 / Math.PI;
    this.resourceIndicatorArrow.style.transform = `rotate(${angle}deg)`;
    const distance = Number.isFinite(this.bodyState.resourceDistance)
      ? ` · ${this.bodyState.resourceDistance.toFixed(2)} m`
      : '';
    this.resourceIndicatorLabel.textContent = `Resource${distance}`;
  }

  setObserverMode(mode) {
    if (this.trajectoryLine) {
      this.trajectoryLine.visible = mode === 'motion' || mode === 'interaction';
    }
    if (this.resourceGuide) {
      this.resourceGuide.material.opacity = mode === 'interaction' ? 0.72 : 0.38;
    }
  }

  updateTrajectory(position) {
    if (!position || !this.trajectoryLine) return;
    const point = position.clone();
    point.y = Math.max(0.025, point.y * 0.02);
    const last = this.trajectoryPoints[this.trajectoryPoints.length - 1];
    if (last && last.distanceTo(point) < BODY_PRESENTATION.trajectory.minPointDistance) return;
    this.trajectoryPoints.push(point);
    if (this.trajectoryPoints.length > BODY_PRESENTATION.trajectory.maxPoints) this.trajectoryPoints.shift();
    this.trajectoryLine.geometry.dispose();
    this.trajectoryLine.geometry = new THREE.BufferGeometry().setFromPoints(this.trajectoryPoints);
  }

  motorActivityLabel() {
    const ratio = this.activeJointCount / Math.max(1, this.bodyModel.joints.length);
    if (ratio >= 0.6) return 'HIGH';
    if (ratio >= 0.25) return 'MEDIUM';
    if (ratio > 0) return 'LOW';
    return 'QUIET';
  }

  updateBodySummary() {
    const parts = [];
    if (this.bodyState.alive === true) parts.push('Alive');
    else if (this.bodyState.alive === false) parts.push('Dead');

    if (Number.isFinite(this.bodyState.reserve)) {
      const reservePct = Math.round(this.bodyState.reserve * 100);
      const trend = this.bodyState.reserveTrend > 0.3 ? '↑' : this.bodyState.reserveTrend < -0.3 ? '↓' : '↔';
      parts.push(`${reservePct}% reserve ${trend}`);
    }

    parts.push(`${this.motorActivityLabel().toLowerCase()} motor activity`);

    if (Number.isFinite(this.bodyState.resourceProgress)) {
      if (this.bodyState.resourceProgress > 0.02) parts.push('approaching resource');
      else if (this.bodyState.resourceProgress < -0.02) parts.push('moving away from resource');
      else parts.push('resource distance stable');
    }

    const summary = parts.length ? parts.join(' · ') : '—';
    if (this.situationEl && this.situationEl.textContent !== summary) {
      this.situationEl.textContent = summary;
    }
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

  observeDenseProducer(tick, receivedAt, tickSpanMs) {
    if (!Number.isFinite(tick) || !Number.isFinite(tickSpanMs) || tickSpanMs <= 0) return;

    this.denseTickSpanMs = tickSpanMs;
    this.presentationBufferMs = THREE.MathUtils.clamp(
      tickSpanMs * 1.5,
      BODY_PRESENTATION.interpolation.minBufferMs,
      BODY_PRESENTATION.interpolation.maxBufferMs,
    );

    if (this.denseProducerTick === null) {
      this.denseProducerTick = tick;
      this.denseProducerArrivalMs = receivedAt;
      return;
    }

    if (tick === this.denseProducerTick) return;

    const tickDelta = tick - this.denseProducerTick;
    const wallDelta = receivedAt - this.denseProducerArrivalMs;
    if (tickDelta > 0 && Number.isFinite(wallDelta) && wallDelta > 1) {
      const producedSimulationMs = tickDelta * tickSpanMs;
      const sample = producedSimulationMs / wallDelta;
      if (
        Number.isFinite(sample) &&
        sample >= BODY_PRESENTATION.interpolation.producerRateMin &&
        sample <= BODY_PRESENTATION.interpolation.producerRateMax
      ) {
        this.producerRateSamples.push(sample);
        if (this.producerRateSamples.length > BODY_PRESENTATION.interpolation.producerSampleWindow) {
          this.producerRateSamples.shift();
        }

        const sorted = [...this.producerRateSamples].sort((a, b) => a - b);
        const middle = Math.floor(sorted.length / 2);
        const median = sorted.length % 2
          ? sorted[middle]
          : (sorted[middle - 1] + sorted[middle]) * 0.5;
        if (this.producerRateSamples.length === 1) {
          this.producerRate = median;
        } else {
          this.producerRate += (median - this.producerRate) * BODY_PRESENTATION.interpolation.producerSmoothing;
        }
      }
    }

    this.denseProducerTick = tick;
    this.denseProducerArrivalMs = receivedAt;
  }

  capturePoseFrame(receivedAt = performance.now(), sourceTimeMs = null) {
    const previous = this.poseFrames[this.poseFrames.length - 1];
    if (previous) {
      const interval = receivedAt - previous.receivedAt;
      if (Number.isFinite(interval) && interval >= 8 && interval <= 2000) {
        this.poseCadenceMs = this.poseCadenceMs === null
          ? interval
          : this.poseCadenceMs * 0.82 + interval * 0.18;

        this.poseIntervalsMs.push(interval);
        if (this.poseIntervalsMs.length > 8) this.poseIntervalsMs.shift();

        // Body poses now arrive once per cognition step (24 Hz by default),
        // so one real source interval is enough to interpolate continuously
        // without slow playback or speculative motion.
        const recentWorstInterval = Math.max(...this.poseIntervalsMs);
        const bufferedCadence = Math.max(
          this.poseCadenceMs * 1.10,
          recentWorstInterval * 1.02,
        );
        this.presentationDelayMs = THREE.MathUtils.clamp(bufferedCadence, 36, 140);
      }
    }

    const linkTransforms = new Map();
    for (const [name, transform] of this.targetLinkTransforms) {
      linkTransforms.set(name, {
        position: transform.position.clone(),
        quaternion: transform.quaternion.clone(),
      });
    }

    this.poseFrames.push({
      receivedAt,
      sourceTimeMs: Number.isFinite(sourceTimeMs) ? sourceTimeMs : null,
      basePosition: this.targetBasePos.clone(),
      baseQuaternion: this.targetBaseQuat.clone(),
      jointAngles: new Map(this.targetJointAngles),
      linkTransforms,
      authoritativeLinks: this.hasAuthoritativeLinkPoses,
    });
    while (this.poseFrames.length > this.MAX_POSE_FRAMES) this.poseFrames.shift();

    // First telemetry sample should appear immediately. Once a second sample
    // exists, the presentation clock intentionally trails the source stream.
    if (this.poseFrames.length === 1) {
      this.applyPresentationPose(this.poseFrames[0], this.poseFrames[0], 0);
    }
  }

  applyPresentationPose(from, to, alpha) {
    this.baseNode.position.lerpVectors(from.basePosition, to.basePosition, alpha);
    this.baseNode.quaternion.slerpQuaternions(from.baseQuaternion, to.baseQuaternion, alpha);

    if (from.authoritativeLinks && to.authoritativeLinks) {
      for (const jdef of this.bodyModel.joints) {
        const node = this.linkObjs[jdef.child];
        const a = from.linkTransforms.get(jdef.child);
        const b = to.linkTransforms.get(jdef.child);
        if (!node || (!a && !b)) continue;
        if (!a || !b) {
          const target = b ?? a;
          node.position.copy(target.position);
          node.quaternion.copy(target.quaternion);
          continue;
        }
        node.position.lerpVectors(a.position, b.position, alpha);
        node.quaternion.slerpQuaternions(a.quaternion, b.quaternion, alpha);
      }
      return;
    }

    // Legacy/demo telemetry has joint angles instead of authoritative link
    // poses. It remains presentation-only and is interpolated deterministically.
    for (const jdef of this.bodyModel.joints) {
      const a = from.jointAngles.get(jdef.name);
      const b = to.jointAngles.get(jdef.name);
      const targetAngle = a === undefined ? b : b === undefined ? a : THREE.MathUtils.lerp(a, b, alpha);
      if (targetAngle === undefined) continue;

      const node = this.jointObjs[jdef.name];
      if (!node) continue;
      switch (dominantAxis(jdef.axisVector ?? jdef.axis)) {
        case 'Y': node.rotation.y = targetAngle; break;
        case 'X': node.rotation.x = targetAngle; break;
        case 'Z': node.rotation.z = -targetAngle; break;
      }
    }
  }

  updatePresentationDebug(latestSourceTimeMs = null) {
    if (!this.presentationDebugEl) return;

    const bufferAheadMs = (
      Number.isFinite(latestSourceTimeMs) &&
      Number.isFinite(this.presentationSourceTimeMs)
    )
      ? Math.max(0, latestSourceTimeMs - this.presentationSourceTimeMs)
      : null;

    const producer = Number.isFinite(this.producerRate)
      ? `${this.producerRate.toFixed(3)}×`
      : '—';
    const playback = Number.isFinite(this.presentationPlaybackRate)
      ? `${this.presentationPlaybackRate.toFixed(3)}×`
      : '—';
    const buffer = bufferAheadMs === null
      ? '—'
      : `${bufferAheadMs.toFixed(1)} ms`;

    const text = [
      'observer presentation',
      `producer ${producer}`,
      `buffer   ${buffer}`,
      `playback ${playback}`,
    ].join('\n');

    if (this.presentationDebugEl.textContent !== text) {
      this.presentationDebugEl.textContent = text;
    }
  }

  interpolatePresentationPose(now, delta) {
    if (this.poseFrames.length === 0) {
      this.updatePresentationDebug();
      return;
    }

    if (this.hasDensePoseStream) {
      const sourceFrames = this.poseFrames.filter(
        (frame) => Number.isFinite(frame.sourceTimeMs),
      );
      if (sourceFrames.length === 0) return;

      const first = sourceFrames[0];
      const latest = sourceFrames[sourceFrames.length - 1];

      if (!this.presentationStarted) {
        const bufferedMs = latest.sourceTimeMs - first.sourceTimeMs;
        if (bufferedMs < this.presentationBufferMs) {
          this.applyPresentationPose(first, first, 0);
          return;
        }
        this.presentationStarted = true;
        this.presentationSourceTimeMs = Math.max(
          first.sourceTimeMs,
          latest.sourceTimeMs - this.presentationBufferMs,
        );
        this.presentationPlaybackRate = this.producerRate;
      } else {
        const bufferAheadMs = latest.sourceTimeMs - this.presentationSourceTimeMs;
        const targetBufferMs = Math.max(1, this.presentationBufferMs);
        const bufferError = (bufferAheadMs - targetBufferMs) / targetBufferMs;

        // Small PLL-like correction around the measured producer rate. This
        // keeps roughly 1.5 source ticks queued without visible speed jumps.
        const occupancyCorrection = THREE.MathUtils.clamp(
          bufferError * 0.08,
          -0.10,
          0.10,
        );
        const desiredPlaybackRate = THREE.MathUtils.clamp(
          this.producerRate * (1 + occupancyCorrection),
          0.05,
          4,
        );
        const rateAlpha = 1 - Math.exp(-delta * 4);
        this.presentationPlaybackRate += (
          desiredPlaybackRate - this.presentationPlaybackRate
        ) * rateAlpha;
        this.presentationSourceTimeMs += (
          delta * 1000 * this.presentationPlaybackRate
        );
      }

      // Presentation never invents a state beyond the newest real sample.
      this.presentationSourceTimeMs = Math.min(
        this.presentationSourceTimeMs,
        latest.sourceTimeMs,
      );

      while (
        this.poseFrames.length > 2 &&
        Number.isFinite(this.poseFrames[1].sourceTimeMs) &&
        this.poseFrames[1].sourceTimeMs <= this.presentationSourceTimeMs
      ) {
        this.poseFrames.shift();
      }

      const from = this.poseFrames[0];
      const to = this.poseFrames[1] ?? from;
      const fromTime = from.sourceTimeMs ?? this.presentationSourceTimeMs;
      const toTime = to.sourceTimeMs ?? fromTime;
      const span = Math.max(1, toTime - fromTime);
      const alpha = from === to
        ? 0
        : THREE.MathUtils.clamp(
            (this.presentationSourceTimeMs - fromTime) / span,
            0,
            1,
          );
      this.applyPresentationPose(from, to, alpha);
      this.updatePresentationDebug(latest.sourceTimeMs);
      return;
    }

    const presentationTime = now - this.presentationDelayMs;
    while (
      this.poseFrames.length > 2 &&
      this.poseFrames[1].receivedAt <= presentationTime
    ) {
      this.poseFrames.shift();
    }

    const from = this.poseFrames[0];
    const to = this.poseFrames[1] ?? from;
    const span = Math.max(1, to.receivedAt - from.receivedAt);
    const alpha = from === to
      ? 0
      : THREE.MathUtils.clamp(
          (presentationTime - from.receivedAt) / span,
          0,
          1,
        );
    this.applyPresentationPose(from, to, alpha);
    this.updatePresentationDebug(
      Number.isFinite(to.sourceTimeMs) ? to.sourceTimeMs : null,
    );
  }

  connectSSE() {
    this.sse = new EventSource(this.sseUrl);
    
    this.sse.addEventListener('message', (ev) => {
      if (this.unmounted) return;

      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      if (!data || !data.type) return;

      switch (data.type) {
        case 'body_pose': this.handleBodyPoseEvent(data);  break;
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

  handleBodyPoseEvent(data) {
    this.ensureBodyModel(data.body_kind);
    const receivedAt = performance.now();
    const sourceTimeMs = Number(data.simulation_time_s) * 1000;
    const tick = Number(data.tick);
    const tickSpanMs = Number(data.tick_simulation_span_s) * 1000;
    if (!Number.isFinite(sourceTimeMs)) return;

    this.hasDensePoseStream = true;
    this.observeDenseProducer(tick, receivedAt, tickSpanMs);

    if (Array.isArray(data.base_position) && data.base_position.length === 3) {
      this.targetBasePos.set(...pbPos(...data.base_position));
    }
    if (Array.isArray(data.base_orientation) && data.base_orientation.length === 4) {
      this.targetBaseQuat.copy(pbQuat(...data.base_orientation));
    }

    if (Array.isArray(data.links) && data.links.length > 0) {
      const world = new Map();
      for (const link of data.links) {
        if (
          !link ||
          typeof link.name !== 'string' ||
          !Array.isArray(link.position) ||
          link.position.length !== 3 ||
          !Array.isArray(link.orientation) ||
          link.orientation.length !== 4
        ) continue;
        world.set(link.name, {
          position: new THREE.Vector3(...pbPos(...link.position)),
          quaternion: pbQuat(...link.orientation),
        });
      }

      const relative = new Map();
      for (const jdef of this.bodyModel.joints) {
        const parent = world.get(jdef.parent);
        const child = world.get(jdef.child);
        if (!parent || !child) continue;

        const inverseParent = parent.quaternion.clone().invert();
        relative.set(jdef.child, {
          position: child.position.clone()
            .sub(parent.position)
            .applyQuaternion(inverseParent),
          quaternion: inverseParent.clone().multiply(child.quaternion),
        });
      }
      if (relative.size > 0) {
        this.targetLinkTransforms = relative;
        this.hasAuthoritativeLinkPoses = true;
      }
    }

    if (Array.isArray(data.joints)) {
      for (const joint of data.joints) {
        if (!joint || !Number.isFinite(joint.position)) continue;
        this.targetJointAngles.set(joint.name, joint.position);
      }
    }

    this.capturePoseFrame(receivedAt, sourceTimeMs);
  }

  handleBodyEvent(data) {
    this.ensureBodyModel(data.body_kind);
    if (this.statusEl && this.statusEl.textContent !== '● Live') {
      this.statusEl.textContent = '● Live';
      this.statusEl.style.color = 'var(--mint, #50fa7b)';
    }

    // Store target positions instead of applying immediately (for lerping)
    if (data.base_position) {
      const nextPos = new THREE.Vector3(...pbPos(...data.base_position));
      if (!this.observerStartBasePos) this.observerStartBasePos = nextPos.clone();
      if (this.previousObservedBasePos) {
        const step = nextPos.distanceTo(this.previousObservedBasePos);
        if (Number.isFinite(step) && step < 2.0) this.distanceTravelled += step;
      }
      this.previousObservedBasePos = nextPos.clone();
      this.updateTrajectory(nextPos);
      if (!this.hasDensePoseStream) this.targetBasePos.copy(nextPos);

      const net = this.observerStartBasePos ? nextPos.distanceTo(this.observerStartBasePos) : 0;
      const directionalEfficiency = this.distanceTravelled > 0.02
        ? Math.max(0, Math.min(1, net / this.distanceTravelled))
        : null;
      this.queueUIUpdate('displacement', `${net.toFixed(2)} m`);
      this.queueUIUpdate('distance_travelled', `${this.distanceTravelled.toFixed(2)} m`);
      this.queueUIUpdate('locomotion_efficiency',
        directionalEfficiency === null ? '—' : `${(directionalEfficiency * 100).toFixed(0)}%`);
    }
    if (data.base_orientation && !this.hasDensePoseStream) {
      this.targetBaseQuat.copy(pbQuat(...data.base_orientation));
    }
    if (Array.isArray(data.links) && data.links.length > 0) {
      const world = new Map();
      for (const link of data.links) {
        if (
          !link ||
          typeof link.name !== 'string' ||
          !Array.isArray(link.position) ||
          link.position.length !== 3 ||
          !Array.isArray(link.orientation) ||
          link.orientation.length !== 4
        ) continue;
        world.set(link.name, {
          position: new THREE.Vector3(...pbPos(...link.position)),
          quaternion: pbQuat(...link.orientation),
        });
      }

      const relative = new Map();
      for (const jdef of this.bodyModel.joints) {
        const parent = world.get(jdef.parent);
        const child = world.get(jdef.child);
        if (!parent || !child) continue;

        const inverseParent = parent.quaternion.clone().invert();
        const localPosition = child.position.clone()
          .sub(parent.position)
          .applyQuaternion(inverseParent);
        const localQuaternion = inverseParent.clone().multiply(child.quaternion);
        relative.set(jdef.child, {
          position: localPosition,
          quaternion: localQuaternion,
        });
      }
      if (relative.size > 0 && !this.hasDensePoseStream) {
        this.targetLinkTransforms = relative;
        this.hasAuthoritativeLinkPoses = true;
      }
    }
    if (Array.isArray(data.resource_position) && data.resource_position.length === 3 && this.resourceObject) {
      this.resourceObject.position.set(...pbPos(...data.resource_position));
      this.resourceObject.visible = true;
      this.updateResourceGuide();
    }
    if (Array.isArray(data.joints)) {
      let active = 0;
      for (const j of data.joints) {
        if (!j || !Number.isFinite(j.position)) continue;
        const previous = this.previousJointPositions.get(j.name);
        const delta = previous === undefined ? 0 : Math.abs(j.position - previous);
        this.previousJointPositions.set(j.name, j.position);
        if (!this.hasDensePoseStream) this.targetJointAngles.set(j.name, j.position);

        const activity = Math.min(1, delta / 0.045);
        this.jointActivity.set(j.name, Math.max(activity, (this.jointActivity.get(j.name) ?? 0) * 0.7));
        if (delta > 0.006) active += 1;
      }
      this.activeJointCount = active;
      const motorActivity = this.motorActivityLabel();
      const activityColor = motorActivity === 'HIGH'
        ? 'var(--amber,#f1fa8c)'
        : motorActivity === 'MEDIUM' ? 'var(--cyan,#8be9fd)' : null;
      this.queueUIUpdate('motor_activity', motorActivity, activityColor);
      this.queueUIUpdate('active_joints', `${active} / ${this.bodyModel.joints.length}`, active > 0 ? 'var(--cyan,#8be9fd)' : null);
      this.updateBodySummary();
    }

    if (!this.hasDensePoseStream) {
      this.capturePoseFrame(performance.now());
    }

    // Queue UI updates (Throttling)
    if (data.tick !== undefined) this.queueUIUpdate('tick', String(data.tick));
    if (data.contact_count !== undefined) this.queueUIUpdate('contact_count', String(data.contact_count));
    if (data.ground_contact_count !== undefined) {
      this.queueUIUpdate('ground_contact_count', String(data.ground_contact_count));
    }
    if (data.self_contact_count !== undefined) {
      this.queueUIUpdate('self_contact_count', String(data.self_contact_count));
    }
    if (data.resource_contact_count !== undefined) {
      this.queueUIUpdate('resource_contact_count', String(data.resource_contact_count));
    }
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
        const tickSpan = old && Number.isFinite(old.tick) && Number.isFinite(Number(data.tick))
          ? Math.max(1, Number(data.tick) - old.tick)
          : null;
        const per100Ticks = tickSpan ? (delta * 10000) / tickSpan : 0;
        this.bodyState.reserveTrend = per100Ticks;
        const arrow = per100Ticks > 0.3 ? '↑' : per100Ticks < -0.3 ? '↓' : '↔';
        const signed = per100Ticks >= 0 ? '+' : '';
        this.queueUIUpdate('reserve_trend', tickSpan ? `${arrow} ${signed}${per100Ticks.toFixed(1)} pp / 100t` : '—',
          per100Ticks < -1 ? 'var(--coral,#ff5555)' : per100Ticks > 1 ? 'var(--mint,#50fa7b)' : null);
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
    if (data.motor_origin !== undefined) this.queueUIUpdate('motor_origin', data.motor_origin);

    const details = [];
    if (data.embodiment_epoch !== undefined) details.push(`epoch ${data.embodiment_epoch}`);
    if (data.reacclimating) details.push(`reacclimating ${data.reacclimation_remaining ?? '?'}t`);
    if (data.schema_confidence !== undefined) details.push(`schema ${data.schema_confidence.toFixed(2)}`);
    if (data.prediction_error !== undefined) details.push(`err ${data.prediction_error.toFixed(3)}`);
    if (data.slm_active !== undefined) details.push(data.slm_active ? 'model active' : 'model inactive');
    this.queueUIUpdate('cognitive_context', details.length ? details.join(' · ') : '—', 'var(--muted,#8a98a8)');
  }

  handleVitalsEvent(data) {
    if (data.alive !== undefined) {
      this.bodyState.alive = Boolean(data.alive);
      this.queueUIUpdate('alive', data.alive ? '● Alive' : '○ Dead', data.alive ? 'var(--mint, #50fa7b)' : 'var(--coral, #ff5555)');
    }
    if (data.joint_motion !== undefined) {
      this.bodyState.jointMotion = Number(data.joint_motion);
    }
    if (data.active_effectors !== undefined) {
      this.queueUIUpdate('active_effectors', String(data.active_effectors));
    }
    if (data.resource_distance !== undefined) {
      const resourceDistance = Number(data.resource_distance);
      this.bodyState.resourceDistance = resourceDistance;
      this.queueUIUpdate('resource_distance', `${Math.max(0, resourceDistance).toFixed(2)} m`);

      if (this.observerResourceBaseline === null && Number.isFinite(resourceDistance)) {
        this.observerResourceBaseline = resourceDistance;
        this.observerPathAtResourceBaseline = this.distanceTravelled;
      }
      if (this.observerResourceBaseline !== null) {
        const path = this.distanceTravelled - this.observerPathAtResourceBaseline;
        if (path > 0.03) {
          const progress = this.observerResourceBaseline - resourceDistance;
          const effectiveness = Math.max(-1, Math.min(1, progress / path));
          const label = effectiveness > 0.08
            ? `${(effectiveness * 100).toFixed(0)}% toward`
            : effectiveness < -0.08
              ? `${Math.abs(effectiveness * 100).toFixed(0)}% away`
              : 'neutral';
          this.queueUIUpdate('motion_effectiveness', label,
            effectiveness > 0.08 ? 'var(--mint,#50fa7b)' : effectiveness < -0.08 ? 'var(--coral,#ff5555)' : null);
        } else {
          this.queueUIUpdate('motion_effectiveness', '—');
        }
      }
    }
    if (data.resource_progress !== undefined) {
      this.bodyState.resourceProgress = Number(data.resource_progress);
      const sign = data.resource_progress > 0 ? '+' : '';
      this.queueUIUpdate('resource_progress', `${sign}${data.resource_progress.toFixed(2)} m`,
        data.resource_progress > 0.02 ? 'var(--mint,#50fa7b)' : data.resource_progress < -0.02 ? 'var(--coral,#ff5555)' : null);
    }
    // displacement_from_origin remains part of telemetry, but BODY compares
    // net displacement and travelled distance over the same observer interval.
    this.updateBodySummary();
  }

  animate = () => {
    if (this.unmounted) return;

    this.rafId = requestAnimationFrame(this.animate);
    const delta = Math.min(Math.max(this.clock.getDelta(), 0), 0.05);
    const now = performance.now();

    // Physics/Symbiont remain untouched. Only the observer presentation clock
    // samples between real telemetry frames at display refresh rate.
    this.interpolatePresentationPose(now, delta);

    if (this.dirLight) {
      this.dirLight.position.copy(this.baseNode.position).add(this.lightOffset);
    }

    // Activity is visible both at joints and over the body segment itself.
    for (const [name, marker] of Object.entries(this.jointMarkers)) {
      const activity = this.jointActivity.get(name) ?? 0;
      const decayed = activity * 0.92;
      this.jointActivity.set(name, decayed);
      marker.visible = true;
      marker.material.opacity = Math.min(0.92, 0.16 + decayed * 0.72);
      marker.material.color.setHex(decayed > 0.08 ? 0x50fa9a : 0x9fd9ff);
      marker.scale.setScalar(0.82 + decayed * 0.72);
    }
    for (const [segmentName, jointNames] of Object.entries(this.bodyModel.segmentActivityJoints)) {
      const mesh = this.segmentMeshes[segmentName];
      if (!mesh) continue;
      const activity = Math.max(0, ...jointNames.map((name) => this.jointActivity.get(name) ?? 0));
      mesh.material.emissive.setHex(activity > 0.06 ? 0x246b59 : 0x000000);
      mesh.material.emissiveIntensity = Math.min(1.05, activity * 1.05);
    }

    this.updateResourceGuide();
    this.fitCameraToBody(now, delta);

    this.flushUIUpdates();
    this.controls.update();
    this.camera.updateMatrixWorld();
    this.updateResourceIndicator();
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

    this.workspace?.dispose();
    this.cameraControls?.dispose();
    this.cameraControls = null;

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
    this.presentationDebugEl = null;
    this.situationEl = null;
    this.resourceObject = null;
    this.resourceGuide = null;
    this.resourceGuidePositions = null;
    this.resourceIndicator = null;
    this.resourceIndicatorArrow = null;
    this.resourceIndicatorLabel = null;
    this.trajectoryLine = null;
    this.trajectoryPoints.length = 0;

    this.jointObjs = {};
    this.linkObjs = {};
    this.segmentMeshes = {};
    this.jointMarkers = {};
    this.panelEls = {};
    this.uiStateQueue = {};
    this.targetJointAngles.clear();
    this.targetLinkTransforms.clear();
    this.poseFrames.length = 0;
    this.poseIntervalsMs.length = 0;
    this.presentationSourceTimeMs = null;
    this.presentationStarted = false;
    this.denseProducerTick = null;
    this.denseProducerArrivalMs = null;
    this.producerRateSamples.length = 0;

    // Restore the host element rather than blindly erasing styles it owned
    // before the viewer was mounted.
    if (this.root) {
      while (this.root.firstChild) {
        this.root.removeChild(this.root.firstChild);
      }
      this.root.classList.remove('body-view-root');
      this.root.style.cssText = this.rootStyleBeforeMount;
      this.root = null;
    }
  }
}

// Compatibility alias for older imports; rendering is morphology-neutral.
export const HumanoidViewer = BodyViewer;
