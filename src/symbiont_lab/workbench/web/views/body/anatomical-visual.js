/**
 * Observer-only anatomical presentation helpers.
 *
 * These meshes are a passive projection of the authoritative Physics3D body.
 * They never generate pose, contacts or actuation and can be replaced by a
 * skinned GLB without changing the physics contract.
 */
import * as THREE from 'three';

const HUMANOID_SKIN = 0xb58b73;
const TECHNICAL_NEUTRAL = 0x708293;

function materialFor(segName, humanoid) {
  const color = humanoid ? HUMANOID_SKIN : TECHNICAL_NEUTRAL;
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: humanoid ? 0.78 : 0.66,
    metalness: 0,
    emissive: 0x000000,
    emissiveIntensity: 0,
  });
  material.name = `${segName}_surface_material`;
  return material;
}

function scaledSphere(material, sx, sy, sz, segments = 28) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(0.5, segments, Math.max(12, Math.round(segments * 0.65))),
    material,
  );
  mesh.scale.set(sx, sy, sz);
  return mesh;
}

function taperedLimb(material, width, depth, height, taper = 0.82) {
  const radius = Math.max(0.025, (width + depth) * 0.25);
  const group = new THREE.Group();

  // Keep a narrow anatomical waist close to the joint. A uniform cylinder
  // makes a bent limb read as one rigid rod, especially at small angles.
  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(radius * taper, radius * 0.92, height * 0.86, 24, 4, false),
    material,
  );
  group.add(shaft);

  const proximal = scaledSphere(
    material,
    radius * 1.76,
    height * 0.17,
    radius * 1.58,
    20,
  );
  proximal.position.y = height * 0.34;
  group.add(proximal);

  const distal = scaledSphere(
    material,
    radius * 1.34,
    height * 0.12,
    radius * 1.28,
    18,
  );
  distal.position.y = -height * 0.39;
  group.add(distal);

  return group;
}

function addJointCap(parent, material, y, radiusX, radiusY, radiusZ) {
  const cap = scaledSphere(material, radiusX, radiusY, radiusZ, 18);
  cap.position.y = y;
  parent.add(cap);
}

function addHandDetails(parent, material, width, depth, height, side) {
  const fingerLength = height * 0.42;
  const fingerRadius = Math.max(0.012, width * 0.075);
  const spacing = width * 0.16;
  for (let i = -1.5; i <= 1.5; i += 1) {
    const finger = new THREE.Mesh(
      new THREE.CylinderGeometry(fingerRadius * 0.82, fingerRadius, fingerLength, 10, 1),
      material,
    );
    finger.position.set(i * spacing, -height * 0.48, 0);
    parent.add(finger);
  }

  const thumb = new THREE.Mesh(
    new THREE.CylinderGeometry(fingerRadius * 0.95, fingerRadius * 1.05, fingerLength * 0.68, 10, 1),
    material,
  );
  thumb.rotation.z = side === 'left' ? -0.72 : 0.72;
  thumb.position.set(
    side === 'left' ? -width * 0.52 : width * 0.52,
    -height * 0.20,
    depth * 0.02,
  );
  parent.add(thumb);
}

function addFootDetails(parent, material, width, depth, height) {
  const toe = scaledSphere(material, width * 0.92, height * 0.72, depth * 0.55, 20);
  toe.position.set(0, 0, -depth * 0.34);
  parent.add(toe);

  const heel = scaledSphere(material, width * 0.72, height * 0.88, depth * 0.34, 18);
  heel.position.set(0, 0, depth * 0.37);
  parent.add(heel);
}

function isHumanoidBody(bodyKind) {
  const kind = String(bodyKind || '').toLowerCase();
  return kind.includes('anthrop') || kind.includes('humanoid');
}

/**
 * Create one smooth observer-side segment while preserving the physical
 * segment origin, scale and parent transform.
 */
export function createAnatomicalSegment(segName, seg, bodyKind) {
  const [width, depth, height] = seg.wdh.map(Number);
  const humanoid = isHumanoidBody(bodyKind);
  const material = materialFor(segName, humanoid);

  let mesh;
  if (!humanoid) {
    mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), material);
  } else if (segName === 'torso') {
    mesh = scaledSphere(material, width, height * 0.94, depth * 0.92, 34);
    const chest = scaledSphere(material, width * 1.05, height * 0.50, depth, 28);
    chest.position.y = height * 0.20;
    mesh.add(chest);
    const abdomen = scaledSphere(material, width * 0.78, height * 0.48, depth * 0.82, 24);
    abdomen.position.y = -height * 0.22;
    mesh.add(abdomen);

    // Shoulder masses bridge the visual gap to the physical shoulder origins.
    for (const side of [-1, 1]) {
      const shoulder = scaledSphere(material, width * 0.30, height * 0.24, depth * 0.62, 20);
      shoulder.position.set(side * width * 0.48, height * 0.24, 0);
      mesh.add(shoulder);
    }
  } else if (segName === 'pelvis') {
    mesh = scaledSphere(material, width * 1.02, height * 0.88, depth, 30);
  } else if (segName === 'head') {
    mesh = scaledSphere(material, width * 0.95, height, depth * 0.92, 34);
    const jaw = scaledSphere(material, width * 0.74, height * 0.42, depth * 0.78, 24);
    jaw.position.y = -height * 0.26;
    mesh.add(jaw);

    // Subtle observer-only landmarks make head orientation readable without
    // adding facial animation or any state that does not exist in Physics3D.
    const nose = scaledSphere(material, width * 0.14, height * 0.16, depth * 0.20, 14);
    nose.position.set(0, height * 0.02, -depth * 0.48);
    mesh.add(nose);
    for (const side of [-1, 1]) {
      const ear = scaledSphere(material, width * 0.11, height * 0.20, depth * 0.10, 14);
      ear.position.set(side * width * 0.48, height * 0.02, 0);
      mesh.add(ear);
    }
    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(width * 0.22, width * 0.25, height * 0.34, 18, 2),
      material,
    );
    neck.position.y = -height * 0.58;
    mesh.add(neck);
  } else if (segName.includes('upper_arm')) {
    mesh = taperedLimb(material, width, depth, height, 0.70);
    const deltoid = scaledSphere(material, width * 0.78, height * 0.24, depth * 0.76, 22);
    deltoid.position.y = height * 0.33;
    mesh.add(deltoid);
    addJointCap(mesh, material, -height * 0.47, width * 0.56, width * 0.42, depth * 0.56);
  } else if (segName.includes('forearm')) {
    mesh = taperedLimb(material, width, depth, height, 0.58);
    const forearmMass = scaledSphere(material, width * 0.62, height * 0.34, depth * 0.60, 20);
    forearmMass.position.y = height * 0.12;
    mesh.add(forearmMass);
    addJointCap(mesh, material, height * 0.46, width * 0.58, width * 0.40, depth * 0.58);
  } else if (segName.includes('thigh')) {
    mesh = taperedLimb(material, width, depth, height, 0.66);
    const quadriceps = scaledSphere(material, width * 0.78, height * 0.44, depth * 0.72, 24);
    quadriceps.position.set(0, height * 0.05, -depth * 0.08);
    mesh.add(quadriceps);
    addJointCap(mesh, material, height * 0.45, width * 0.72, width * 0.54, depth * 0.72);
    addJointCap(mesh, material, -height * 0.47, width * 0.54, width * 0.38, depth * 0.56);
  } else if (segName.includes('shin')) {
    mesh = taperedLimb(material, width, depth, height, 0.52);
    const calf = scaledSphere(material, width * 0.68, height * 0.44, depth * 0.76, 22);
    calf.position.set(0, height * 0.08, depth * 0.09);
    mesh.add(calf);
    addJointCap(mesh, material, height * 0.46, width * 0.54, width * 0.38, depth * 0.56);
  } else if (segName.includes('hand')) {
    mesh = scaledSphere(material, width * 0.90, height * 0.76, depth * 0.74, 22);
    addHandDetails(mesh, material, width, depth, height, segName.startsWith('left') ? 'left' : 'right');
  } else if (segName.includes('foot')) {
    mesh = scaledSphere(material, width * 0.84, height * 0.72, depth * 0.82, 24);
    addFootDetails(mesh, material, width, depth, height);
  } else {
    mesh = scaledSphere(material, width, height, depth, 24);
  }

  mesh.name = `${segName}_mesh`;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData.segmentName = segName;
  mesh.userData.visualRole = 'surface';
  return mesh;
}

export function createTechnicalJointMarker(name) {
  const geometry = new THREE.SphereGeometry(0.024, 16, 12);
  const material = new THREE.MeshBasicMaterial({
    color: 0x9fd9ff,
    transparent: true,
    opacity: 0.16,
    depthWrite: false,
  });
  const marker = new THREE.Mesh(geometry, material);
  marker.name = `${name}_technical_marker`;
  marker.userData.visualRole = 'joint-marker';
  return marker;
}
