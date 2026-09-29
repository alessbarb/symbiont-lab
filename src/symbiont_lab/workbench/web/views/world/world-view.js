import * as THREE from 'three';
import { pbPos, pbQuat } from '../body/coordinates.js';
import { escapeHtml } from '../shared/dom.js';
import { reconcileWorld, receptorStatus } from './world-state.js';

const LAYERS = [
  ['physical', 'Geometry'],
  ['perception', 'Receptor evidence'],
  ['self', 'Self evidence'],
];
const color = { unknown: 0x718396, perceived: 0x53e3da, sampled: 0xe9b765, unsampled: 0x667382 };
const row = (label, value) => `<div class="body-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value ?? 'Unavailable'))}</strong></div>`;
const vector = (v) => Array.isArray(v) ? v.map(x => Number(x).toFixed(3)).join(', ') : 'Unavailable';
function dispose(object) {
  object.traverse(child => { child.geometry?.dispose(); if (Array.isArray(child.material)) child.material.forEach(m => m.dispose()); else child.material?.dispose(); });
  object.removeFromParent();
}

export class WorldView {
  constructor(viewer) {
    this.viewer = viewer;
    this.state = null;
    this.layers = { physical: true, perception: false, self: false, known: false, predictions: false, truth: true };
    this.entities = new Map();
    this.receptors = new Map();
    this.relations = new THREE.Group();
    viewer.scene.add(this.relations);
    this.contacts = new THREE.Group();
    this.viewer.scene.add(this.contacts);
    this.selected = null;
    this.ray = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.abort = new AbortController();
    this.closed = false;
    this.active = false;
    this.sharedState = null;
    this.recovering = false;
    this.eventGeneration = 0;
    this.recoveryPending = false;
    this.toolbar = document.createElement('div');
    this.toolbar.className = 'body-world-toolbar';
    this.toolbar.setAttribute('aria-label', 'Spatial observation layers');
    this.toolbar.hidden = true;
    for (const [id, label] of LAYERS) {
      const button = document.createElement('button');
      button.textContent = label;
      button.dataset.layer = id;
      button.type = 'button';
      button.setAttribute('aria-pressed', String(this.layers[id]));
      button.addEventListener('click', () => {
        if (!this.active) return;
        this.layers[id] = !this.layers[id];
        button.setAttribute('aria-pressed', String(this.layers[id]));
        this.updateVisibility();
        this.viewer.workspace.setTab('world');
      }, { signal: this.abort.signal });
      this.toolbar.append(button);
    }
    const fit = document.createElement('button');
    fit.type = 'button'; fit.textContent = 'Frame world';
    fit.addEventListener('click', () => this.frameWorld(), { signal: this.abort.signal });
    this.toolbar.append(fit);
    this.legend = document.createElement('div');
    this.legend.className = 'body-world-legend';
    this.legend.hidden = !this.active;
    this.legend.textContent = 'World unavailable · waiting for spatial evidence';
    this.experience = document.createElement('div');
    this.experience.className = 'body-world-experience';
    this.experience.hidden = true;
    viewer.canvasWrap.append(this.toolbar, this.legend, this.experience);
    let down = null;
    viewer.canvas.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; }, { signal: this.abort.signal });
    viewer.canvas.addEventListener('pointerup', e => {
      if (down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) < 5) this.pick(e);
      down = null;
    }, { signal: this.abort.signal });
    this.setActive(viewer.workspace?.activeTab === 'world');
    this.recover();
  }

  setActive(active) {
    active = Boolean(active);
    if (active === this.active) return;
    if (active) {
      const v = this.viewer;
      this.sharedState = {
        objects: [v.baseNode, v.gridHelper, v.legacyGround, v.contactMarkerGroup, v.comMarker,
          v.comProjectionLine, v.trajectoryLine, v.resourceObject, v.resourceGuide]
          .filter(Boolean).map(object => [object, object.visible]),
        materials: new Map(), situationHidden: v.situationEl?.hidden,
        camera: v.camera.position.clone(), target: v.controls.target.clone(),
        far: v.camera.far, pan: v.controls.enablePan,
        maxDistance: v.controls.maxDistance, follow: v.followBody,
      };
    } else if (this.sharedState) {
      const v = this.viewer, saved = this.sharedState;
      for (const [object, visible] of saved.objects) {
        object.visible = visible;
        delete object.userData.worldTruthWasVisible;
      }
      this.restoreSelfMaterials();
      if (v.situationEl) v.situationEl.hidden = saved.situationHidden;
      v.camera.position.copy(saved.camera); v.camera.far = saved.far;
      v.camera.updateProjectionMatrix(); v.controls.target.copy(saved.target);
      v.controls.enablePan = saved.pan; v.controls.maxDistance = saved.maxDistance;
      v.followBody = saved.follow; v.controls.update();
      this.sharedState = null;
    }
    this.active = active;
    // Observer Truth is one scene. Layer controls live in the inspector,
    // not as a second navigation bar across the canvas.
    this.toolbar.hidden = true;
    this.legend.hidden = !active;
    this.experience.hidden = true;
    this.updateVisibility();
  }

  restoreSelfMaterials() {
    for (const [material, saved] of this.sharedState?.materials ?? []) {
      material.emissive.copy(saved.color);
      material.emissiveIntensity = saved.intensity;
    }
    this.sharedState?.materials.clear();
    this.selfWasVisible = false;
  }

  relatedReceptor(id, receptor) {
    const selection = this.selected;
    if (!selection) return false;
    if (selection.kind === 'receptor') return id === selection.id;
    if (selection.kind === 'entity') return receptor.source_entity_id === selection.id;
    if (selection.kind === 'body') return receptor.link === selection.id ||
      (this.viewer.bodyModel.segmentActivityJoints[selection.id] ?? []).includes(receptor.joint);
    return receptor.link === this.state?.contacts.find(c => c.id === selection.id)?.link;
  }

  accept(event) {
    this.eventGeneration += 1;
    const result = reconcileWorld(this.state, event);
    if (result.gap) { this.legend.textContent = 'Spatial update gap · recovering authoritative snapshot'; this.recover(); return; }
    if (result.state === this.state) return;
    const reset = this.state?.world_id !== result.state.world_id;
    if (this.selected?.kind === 'contact' && this.state?.tick !== result.state.tick) this.selected = null;
    this.state = result.state;
    if (reset) {
      this.selected = null;
      for (const item of this.entities.values()) dispose(item.group);
      this.entities.clear();
      for (const item of this.receptors.values()) dispose(item);
      this.receptors.clear();
    }
    this.sync();
    if (reset) this.frameWorld();
  }

  async recover() {
    if (this.closed) return;
    if (this.recovering) { this.recoveryPending = true; return; }
    this.recovering = true;
    const generation = this.eventGeneration;
    try {
      const response = await fetch('/api/world-scene', { cache: 'no-store', signal: this.abort.signal });
      if (!response.ok) return;
      const { scene } = await response.json();
      if (this.closed || !scene) return;
      // A response from an old session cannot roll a newly arrived session back.
      if (generation !== this.eventGeneration && this.state && this.state.world_id !== scene.world_id) return;
      this.accept(scene);
    } catch { /* EventSource reconnect or the next delta retries recovery. */ }
    finally {
      this.recovering = false;
      if (this.recoveryPending && !this.closed) { this.recoveryPending = false; this.recover(); }
    }
  }

  geometry(shape) {
    const d = shape.dimensions;
    if (shape.kind === 'sphere') return new THREE.SphereGeometry(d[0], 24, 16);
    if (shape.kind === 'box') return new THREE.BoxGeometry(d[0], d[2], d[1]);
    if (shape.kind === 'cylinder') return new THREE.CylinderGeometry(d[1], d[1], d[0], 24);
    if (shape.kind === 'capsule') return new THREE.CapsuleGeometry(d[1], d[0], 8, 16);
    if (shape.kind === 'plane') {
      const g = new THREE.PlaneGeometry(80, 80);
      // PyBullet reports the local plane normal in dimensions.
      g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), new THREE.Vector3(...pbPos(...d)).normalize()));
      return g;
    }
    return null;
  }

  entityObject(entity) {
    const group = new THREE.Group();
    group.userData.selection = { kind: 'entity', id: entity.id };
    let isPlane = false;
    for (const shape of entity.shapes ?? []) {
      const geometry = this.geometry(shape);
      if (!geometry) continue;
      const plane = shape.kind === 'plane'; isPlane ||= plane;
      const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
        color: plane ? 0x182d39 : 0x607d91, roughness: 0.85, metalness: 0.05,
        transparent: true, opacity: plane ? 0.86 : 0.30, side: THREE.DoubleSide,
        depthWrite: plane,
      }));
      mesh.position.set(...pbPos(...shape.position));
      mesh.quaternion.copy(pbQuat(...shape.orientation));
      mesh.receiveShadow = true; mesh.castShadow = !plane;
      group.add(mesh);
      if (!plane) {
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: color.unknown, transparent: true, opacity: 0.8 }));
        edges.position.copy(mesh.position); edges.quaternion.copy(mesh.quaternion); group.add(edges);
      }
    }
    if (entity.field) {
      const field = new THREE.Mesh(new THREE.SphereGeometry(entity.field.radius, 24, 16), new THREE.MeshBasicMaterial({
        color: 0xe9b765, transparent: true, opacity: 0.055, wireframe: true, depthWrite: false,
      }));
      field.userData.field = true; group.add(field);
    }
    group.userData.isPlane = isPlane;
    this.viewer.scene.add(group);
    return group;
  }

  sync() {
    const state = this.state;
    for (const [id, item] of this.entities) {
      if (!state.entities[id]) { dispose(item.group); this.entities.delete(id); if (this.selected?.id === id) this.selected = null; }
    }
    for (const [id, entity] of Object.entries(state.entities)) {
      const signature = JSON.stringify([entity.shapes, entity.field]);
      let item = this.entities.get(id);
      if (!item || item.signature !== signature) {
        if (item) dispose(item.group);
        item = { signature, group: this.entityObject(entity) }; this.entities.set(id, item);
      }
      item.group.position.set(...pbPos(...entity.position));
      item.group.quaternion.copy(pbQuat(...entity.orientation));
    }
    const poses = new Map((state.sample_pose?.links ?? []).map(x => [x.link_name, x.position]));
    for (const [rid, marker] of this.receptors) {
      if (!state.receptors[rid]) { dispose(marker); this.receptors.delete(rid); }
    }
    for (const [rid, receptor] of Object.entries(state.receptors)) {
      const position = receptor.link ? poses.get(receptor.link) : state.sample_pose?.base_position;
      if (!position) { const old = this.receptors.get(rid); if (old) { old.visible = false; old.userData.hasPosition = false; } continue; }
      let marker = this.receptors.get(rid);
      if (!marker) {
        marker = new THREE.Mesh(new THREE.SphereGeometry(receptor.modality === 'scalar_field' ? 0.058 : 0.022, 10, 8), new THREE.MeshBasicMaterial({ depthTest: false, transparent: true, opacity: 0.9 }));
        marker.userData.selection = { kind: 'receptor', id: rid };
        marker.renderOrder = 9; this.viewer.scene.add(marker); this.receptors.set(rid, marker);
      }
      marker.position.set(...pbPos(...position));
      marker.userData.hasPosition = true;
      marker.material.color.setHex(color[receptorStatus(state.evidence[rid])] ?? color.unknown);
    }
    while (this.contacts.children.length) dispose(this.contacts.children[0]);
    for (const contact of state.contacts ?? []) {
      const normal = new THREE.Vector3(...pbPos(...contact.normal));
      const arrow = new THREE.ArrowHelper(normal, new THREE.Vector3(...pbPos(...contact.position)), Math.min(0.5, 0.06 + Math.log1p(Math.max(0, contact.normal_force)) * 0.04), 0x79b9ff, 0.035, 0.02);
      arrow.userData.selection = { kind: 'contact', id: contact.id };
      this.contacts.add(arrow);
    }
    if (this.active) {
      if (this.viewer.resourceObject) this.viewer.resourceObject.visible = false;
      if (this.viewer.resourceGuide) this.viewer.resourceGuide.visible = false;
      if (this.viewer.legacyGround) this.viewer.legacyGround.visible = false;
    }
    this.updateVisibility();
    this.viewer.workspace.requestRender();
  }

  updateVisibility() {
    if (!this.active) {
      for (const { group } of this.entities.values()) group.visible = false;
      for (const marker of this.receptors.values()) marker.visible = false;
      this.contacts.visible = false;
      this.relations.visible = false;
      this.experience.hidden = true;
      return;
    }
    for (const { group } of this.entities.values()) {
      group.visible = this.layers.physical && this.layers.truth;
      for (const child of group.children) if (child.userData.field) child.visible = this.layers.perception && this.fieldSelected(group.userData.selection.id) && !!this.state?.entities[group.userData.selection.id]?.field?.active;
    }
    for (const [id, marker] of this.receptors) {
      marker.visible = this.layers.perception && !!marker.userData.hasPosition;
      const focused = this.relatedReceptor(id, this.state?.receptors[id] ?? {});
      marker.material.opacity = this.selected && !focused ? 0.18 : 0.9;
      marker.scale.setScalar(focused ? 1.6 : 1);
    }
    if (this.viewer.resourceObject && this.state) this.viewer.resourceObject.visible = false;
    if (this.viewer.resourceGuide && this.state) this.viewer.resourceGuide.visible = false;
    this.contacts.visible = this.layers.physical && this.layers.truth;
    this.viewer.baseNode.visible = this.layers.physical || this.layers.self;
    if (this.viewer.gridHelper) this.viewer.gridHelper.visible = this.layers.physical && this.layers.truth && !!this.state;
    if (this.viewer.contactMarkerGroup) this.viewer.contactMarkerGroup.visible = !this.state && this.layers.physical;
    this.syncExperience();
    this.legend.textContent = !this.state ? 'World unavailable · no spatial contract in this stream' :
      `${this.layers.truth ? 'WORLD TRUTH · observer geometry' : 'SYMBIONT VIEW · no object-localized world model'} · tick ${this.state.tick}\n` +
      (this.layers.perception ? 'Teal: perceived · amber: sampled · grey: unsampled · select to focus\n' : '') +
      (this.layers.self ? 'Self Model: mapped signal confidence, not anatomical recognition\n' : '') +
      ((this.layers.known || this.layers.predictions) ? 'Object memory / spatial predictions: no exported evidence\n' : '') +
      'Objects shown ≠ objects known · select an element to inspect evidence';
  }

  syncExperience() {
    while (this.relations.children.length) dispose(this.relations.children[0]);
    this.relations.visible = this.active && this.layers.perception;
    this.experience.hidden = true;
    if (!this.relations.visible || !this.state || !this.selected) return;
    const matches = Object.entries(this.state.receptors).filter(([id, r]) => this.relatedReceptor(id, r));
    // Focus one actual sampled anchor. Other related receptors remain highlighted.
    matches.sort(([a], [b]) => Number(!!this.state.evidence[b]?.percept_emitted) - Number(!!this.state.evidence[a]?.percept_emitted));
    const [id, receptor] = matches.find(([rid]) => this.receptors.get(rid)?.userData.hasPosition) ?? [];
    if (!id) return;
    const marker = this.receptors.get(id), evidence = this.state.evidence[id];
    this.experienceAnchor = marker.position.clone();
    const signals = evidence?.signals ?? [];
    const sampled = evidence?.sampled == null ? 'Sampling unavailable' : evidence.sampled ? `Sample ${Number(evidence.sample).toPrecision(3)}` : 'Not sampled';
    const claims = signals.flatMap(s => s.knowledge?.claims ?? []);
    const statuses = [...new Set(claims.map(c => c.status))].join(', ');
    this.experience.innerHTML = `<strong>${escapeHtml(id)} · ${escapeHtml(receptor.modality)}</strong>
      <span>${escapeHtml(sampled)} → ${signals.filter(s => s.percept).length} emitted percepts</span>
      ${signals.slice(0, 2).map(signal => `<span title="${escapeHtml(signal.signal_id ?? signal.id)}">${escapeHtml((signal.signal_id ?? signal.id).slice(0, 22))} · ${signal.percept?.value == null ? 'not emitted' : Number(signal.percept.value).toPrecision(3)}</span>`).join('')}
      <span>${claims.length ? `${claims.length} signal claims · ${escapeHtml(statuses)}` : 'Signal learning: no linked evidence'}</span>
      <small>Pre-action t${escapeHtml(String(this.state.tick))} · observer placement</small>`;
    this.experience.hidden = false;
    const connect = (end, tone, dashed) => {
      const material = dashed ? new THREE.LineDashedMaterial({color:tone, dashSize:.05, gapSize:.04, transparent:true, opacity:.7}) : new THREE.LineBasicMaterial({color:tone, transparent:true, opacity:.8});
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([marker.position, end]), material);
      if (dashed) line.computeLineDistances();
      this.relations.add(line);
    };
    if (this.layers.truth && receptor.source_entity_id) {
      const source = this.entities.get(receptor.source_entity_id)?.group;
      if (source) connect(source.position, 0xe9b765, true);
    }
    // A learned signal relation may be located on apparatus anchors by the observer;
    // it is not an acquired spatial edge or proof of a common external object.
    const related = new Set(claims.filter(c => c.related_signal_id).map(c => c.related_signal_id));
    for (const [rid, other] of Object.entries(this.state.evidence)) {
      if (rid === id || !other.signals.some(s => related.has(s.signal_id))) continue;
      const target = this.receptors.get(rid);
      if (target?.userData.hasPosition) connect(target.position, 0x53e3da, true);
    }
    this.positionExperience();
  }

  positionExperience() {
    if (this.experience.hidden || !this.experienceAnchor) return;
    const point = this.experienceAnchor.clone().project(this.viewer.camera);
    const width = this.viewer.canvas.clientWidth, height = this.viewer.canvas.clientHeight;
    const visible = point.z >= -1 && point.z <= 1 && Math.abs(point.x) <= 1 && Math.abs(point.y) <= 1;
    this.experience.style.visibility = visible ? 'visible' : 'hidden';
    this.experience.style.left = `${Math.max(8, Math.min(width - 250, (point.x + 1) * width / 2 + 18))}px`;
    this.experience.style.top = `${Math.max(100, Math.min(height - 130, (1 - point.y) * height / 2))}px`;
  }

  fieldSelected(id) {
    return this.selected?.kind === 'entity' && this.selected.id === id ||
      this.selected?.kind === 'receptor' && this.state?.receptors[this.selected.id]?.source_entity_id === id;
  }

  frameWorld() {
    if (!this.active || !this.state) return;
    const bounds = new THREE.Box3().setFromObject(this.viewer.baseNode);
    for (const { group } of this.entities.values()) {
      if (!group.userData.isPlane) bounds.expandByPoint(group.position);
    }
    if (bounds.isEmpty()) return;
    const center = bounds.getCenter(new THREE.Vector3());
    const span = Math.max(2.5, bounds.getSize(new THREE.Vector3()).length());
    this.viewer.followBody = false;
    this.viewer.controls.enablePan = true;
    this.viewer.controls.maxDistance = 60;
    this.viewer.camera.far = 200; this.viewer.camera.updateProjectionMatrix();
    this.viewer.controls.target.copy(center);
    this.viewer.camera.position.copy(center).add(new THREE.Vector3(span * 0.7, span * 0.65, span));
    this.viewer.controls.update();
  }

  pick(event) {
    if (!this.active) return;
    const rect = this.viewer.canvas.getBoundingClientRect();
    this.pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    this.ray.setFromCamera(this.pointer, this.viewer.camera);
    const visibleReceptors = [...this.receptors.values()].filter(x => x.visible);
    const targets = [...visibleReceptors, ...[...this.entities.values()].filter(x => x.group.visible).map(x => x.group), ...(this.viewer.baseNode.visible ? [this.viewer.baseNode] : []), ...(this.contacts.visible ? [this.contacts] : [])];
    const hits = this.ray.intersectObjects(targets, true).filter(hit => {
      for (let x = hit.object; x; x = x.parent) if (!x.visible || x.userData.field) return false;
      return true;
    });
    for (const hit of hits) {
      for (let object = hit.object; object; object = object.parent) {
        if (object.userData.selection) { this.selected = object.userData.selection; this.updateVisibility(); this.viewer.workspace.setTab('world'); return; }
        const segment = Object.entries(this.viewer.segmentMeshes).find(([, mesh]) => mesh === object)?.[0];
        if (segment) { this.selected = { kind: 'body', id: segment }; this.updateVisibility(); this.viewer.workspace.setTab('world'); return; }
      }
    }
    this.selected = null; this.updateVisibility(); this.viewer.workspace.requestRender();
  }

  update() {
    if (!this.active) return;
    this.positionExperience();
    // BodyViewer refreshes these overlays on incoming poses. Reapply the epistemic
    // boundary at render time so observer-only trajectories cannot leak into View.
    const truthVisible = this.layers.truth && this.layers.physical;
    for (const object of [this.viewer.comMarker, this.viewer.comProjectionLine, this.viewer.trajectoryLine]) {
      if (!object) continue;
      if (!truthVisible) {
        if (object.visible) object.userData.worldTruthWasVisible = true;
        object.visible = false;
      } else if (object.userData.worldTruthWasVisible) {
        object.visible = true; delete object.userData.worldTruthWasVisible;
      }
    }
    if (this.viewer.situationEl) this.viewer.situationEl.hidden = !this.layers.truth;
    // Existing motion colors are refreshed by BodyViewer; apply optional self evidence last.
    if (!this.layers.self || !this.state) {
      if (this.selfWasVisible) this.restoreSelfMaterials();
      return;
    }
    this.selfWasVisible = true;
    for (const segment of Object.keys(this.viewer.segmentMeshes)) {
      const joints = this.viewer.bodyModel.segmentActivityJoints[segment] ?? [];
      const evidence = Object.entries(this.state.receptors).filter(([, r]) => r.link === segment || joints.includes(r.joint)).flatMap(([id]) => this.state.evidence[id]?.signals ?? []);
      const known = evidence.filter(e => e.self_model);
      const confidence = known.length ? known.reduce((sum, e) => sum + (e.self_model.confidence_class ?? 0) / 15, 0) / known.length : 0;
      this.viewer.forEachSegmentMaterial(segment, material => {
        if (!material.emissive) return;
        if (!this.sharedState.materials.has(material)) this.sharedState.materials.set(material, { color: material.emissive.clone(), intensity: material.emissiveIntensity });
        material.emissive.setHex(known.length ? 0x249caa : 0x1e2835);
        material.emissiveIntensity = known.length ? 0.15 + confidence * 0.8 : 0.1;
      });
    }
  }

  inspector(panel) {
    const s = this.state;
    const head = `<div class="body-inspector-head"><div class="body-inspector-kicker">World · Observer Truth</div><div class="body-inspector-title">${escapeHtml(this.selected?.id ?? 'Situated organism')}</div><div class="body-inspector-sub">Physical reality and observer correlations only. Nothing here becomes organism knowledge.</div></div>`;
    const controls = `
      <div class="world-overlay-controls" aria-label="Observer truth overlays">
        <button type="button" data-world-overlay="physical" aria-pressed="${this.layers.physical}">Geometry</button>
        <button type="button" data-world-overlay="perception" aria-pressed="${this.layers.perception}">Receptor evidence</button>
        <button type="button" data-world-overlay="self" aria-pressed="${this.layers.self}">Self evidence</button>
        <button type="button" data-frame-world>Frame scene</button>
      </div>`;
    if (!s) {
      panel.innerHTML = head + controls + '<p class="body-world-note">No spatial observation available. Older streams cannot establish what exists around this body.</p>';
      this.bindInspectorControls(panel);
      return;
    }
    let html = head + controls;
    if (this.selected?.kind === 'entity') {
      const e = s.entities[this.selected.id];
      if (e) {
        html += '<div class="body-section"><div class="body-section-title">World truth · observer only</div>' + row('Geometry', e.shapes.map(x => x.kind).join(', ')) + row('Position · m, Z-up', vector(e.position)) + row('Orientation · XYZW', vector(e.orientation));
        if (e.material) html += row('Lateral friction · physical', e.material.lateral_friction) + row('Mass · kg', e.material.mass);
        if (e.field) html += row('Field support · m', e.field.radius) + row('Source active', e.field.active);
        const touching = s.contacts.filter(x => x.entity_id === e.id);
        html += row('Contacts · post-action', touching.length) + row('Touching body links', [...new Set(touching.map(x => x.link).filter(Boolean))].join(', ') || 'None in this frame') + '</div>';
        html += '<div class="body-section"><div class="body-section-title">Symbiont evidence</div>' + row('Object identity / location', 'No exported evidence') + row('Object familiarity', 'Unavailable') + row('Spatial prediction', 'Unavailable') + '<p class="body-world-note">A sensed stimulus does not establish recognition of this object. The source attribution below belongs to the observer.</p></div>';
      }
    }
    if (this.selected?.kind === 'body') {
      const name = this.selected.id;
      const link = this.viewer.linkObjs[name];
      const pos = link?.getWorldPosition(new THREE.Vector3());
      html += '<div class="body-section"><div class="body-section-title">Physical anatomy · observer label</div>' + row('Displayed position · m, Y-up', pos ? vector(pos.toArray()) : null) + row('Displayed orientation · XYZW', link ? link.getWorldQuaternion(new THREE.Quaternion()).toArray().map(x => x.toFixed(3)).join(', ') : null) + row('Current contacts', s.contacts.filter(x => x.link === name).length) + '<p class="body-world-note">Mapped signal knowledge below does not imply that the organism has learned this anatomical name.</p></div>';
      const joints = this.viewer.bodyModel.segmentActivityJoints[name] ?? [];
      const dimensions = Object.entries(this.viewer.workspace.selfModel?.snapshot?.observer_semantics?.actionDimensions ?? {}).filter(([, d]) => d.observerJoints?.some(j => joints.includes(j.replaceAll(' ', '_'))));
      if (dimensions.length) html += row('Acquired action dimensions', dimensions.map(([id]) => id).join(', '));
      const touching = s.contacts.filter(x => x.link === name);
      if (touching.length) html += '<div class="body-section"><div class="body-section-title">Body ↔ world · physical contacts</div>' + touching.map(c => row(c.entity_id ?? 'Self contact', `${c.normal_force.toFixed(2)} N · post-action`)).join('') + '</div>';
    }
    if (this.selected?.kind === 'contact') {
      const c = s.contacts.find(x => x.id === this.selected.id);
      if (c) html += '<div class="body-section"><div class="body-section-title">Physical contact · post-action</div>' + row('Link', c.link) + row('Counterpart', c.entity_id ?? 'Self contact') + row('Force · N', c.normal_force.toFixed(3)) + row('Position', vector(c.position)) + row('Normal', vector(c.normal)) + '</div>';
    }
    const ids = Object.entries(s.receptors).filter(([id, r]) => {
      if (!this.selected) return r.modality === 'scalar_field';
      if (this.selected.kind === 'receptor') return id === this.selected.id;
      if (this.selected.kind === 'entity') return r.source_entity_id === this.selected.id;
      if (this.selected.kind === 'body') return r.link === this.selected.id || (this.viewer.bodyModel.segmentActivityJoints[this.selected.id] ?? []).includes(r.joint);
      return r.link === s.contacts.find(c => c.id === this.selected.id)?.link;
    });
    for (const [id, r] of ids) {
      const e = s.evidence[id];
      html += '<div class="body-section"><div class="body-section-title">' + `<button type="button" class="body-world-receptor" data-world-receptor="${escapeHtml(id)}">${escapeHtml(`${id} · ${r.modality}`)}</button>` + '</div>' + row('Can be sampled', 'Apparatus receptor') + row('Sampled this tick', e?.sampled) + row('Recorded value', e?.sample) + row('Nonzero stimulus', e?.sampled ? Math.abs(e.sample ?? 0) > 0 : null) + row('Percept emitted', e?.percept_emitted) + row('Evidence time', `${s.tick} · pre-action`);
      for (const signal of e?.signals ?? []) html += row('Opaque signal', signal.id) + row('Percept value', signal.percept?.value) + row('Self representation', signal.represented) + row('Confidence class', signal.self_model?.confidence_class) + row('Maturity class', signal.self_model?.maturity_class);
      for (const signal of e?.signals ?? []) {
        html += row('Percept → signal reference', signal.signal_id ?? 'Unjustified: no exported reference');
        html += row('Receptor → percept', signal.source_mapping ?? 'Observer lineage');
        for (const claim of signal.knowledge?.claims ?? []) {
          html += row(`${claim.kind} · ${claim.status}`, `${claim.evidence_count ?? '?'} observations · revision ${claim.revision ?? '?'}`);
          if (claim.related_signal_id) html += row('Related signal', claim.related_signal_id);
          if (claim.horizon != null) html += row('Signal horizon · ticks', claim.horizon);
          if (claim.reason_class) html += row('Evidence limitation', claim.reason_class);
        }
      }
      html += '<p class="body-world-note">Dashed links show observer attribution or signal relations located on receptors. They do not establish spatial knowledge or object identity.</p>';
      if (r.modality === 'scalar_field') html += '<p class="body-world-note">Scalar intensity only. No sensed direction, distance or object identity.</p>';
      html += '</div>';
    }
    if (!this.selected) html += '<div class="body-section"><div class="body-section-title">Explore this scene</div><p class="body-world-note">Select a body part, object, receptor or contact. Rotate to inspect, pan to explore, or frame the world.</p>' + row('World entities', Object.keys(s.entities).length) + row('Sampled receptors', Object.values(s.evidence).filter(e => e.sampled).length) + row('Emitted percepts mapped', Object.values(s.evidence).filter(e => e.percept_emitted).length) + '</div>';
    if (!this.selected) html += '<div class="body-section"><div class="body-section-title">Spatial knowledge boundary</div><p class="body-world-note">This runtime exports signal learning and motor evidence, but no object-localized memory or predictions. Inspect acquired dependencies in Self-Model and predictors in Mind. No object is marked known by proxy.</p></div>';
    panel.innerHTML = html;
    this.bindInspectorControls(panel);
    panel.querySelectorAll('[data-world-receptor]').forEach(button => button.addEventListener('click', () => {
      if (!this.active) return;
      this.selected = {kind: 'receptor', id: button.dataset.worldReceptor};
      this.layers.perception = true;
      this.toolbar.querySelector('[data-layer="perception"]')?.setAttribute('aria-pressed', 'true');
      this.updateVisibility();
      this.inspector(panel);
    }));
  }

  bindInspectorControls(panel) {
    panel.querySelectorAll('[data-world-overlay]').forEach(button => {
      button.addEventListener('click', () => {
        if (!this.active) return;
        const layer = button.dataset.worldOverlay;
        this.layers[layer] = !this.layers[layer];
        button.setAttribute('aria-pressed', String(this.layers[layer]));
        this.toolbar.querySelector(`[data-layer="${layer}"]`)?.setAttribute('aria-pressed', String(this.layers[layer]));
        this.updateVisibility();
      });
    });
    panel.querySelector('[data-frame-world]')?.addEventListener('click', () => this.frameWorld());
  }

  dispose() {
    this.setActive(false);
    this.closed = true; this.abort.abort(); this.toolbar.remove(); this.legend.remove(); this.experience.remove();
    for (const { group } of this.entities.values()) dispose(group);
    for (const marker of this.receptors.values()) dispose(marker);
    dispose(this.contacts);
    dispose(this.relations);
  }
}
