/**
 * True 3D perspective projection for the emergent Cognition Map.
 *
 * Sector membership and relationships come from the shared 2D cartography.
 * This module only gives those same regions a stable volumetric embedding.
 */

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function hashString(value) {
  let hash = 2166136261;
  for (const ch of String(value ?? '')) {
    hash ^= ch.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function hashUnit(value, salt = '') {
  return (hashString(`${value}|${salt}`) % 100000) / 100000;
}

function kindDepth(kind) {
  switch (kind) {
    case 'sense': return 34;
    case 'predictor': return 22;
    case 'state': return 16;
    case 'concept': return 0;
    case 'gate': return -12;
    case 'readout': return -24;
    case 'motor_primitive': return -44;
    case 'actuator': return -66;
    default: return 0;
  }
}

function rotateLocal(point, yaw, pitch, roll) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const cr = Math.cos(roll), sr = Math.sin(roll);

  const x1 = point.x * cr - point.y * sr;
  const y1 = point.x * sr + point.y * cr;
  const z1 = point.z;

  const y2 = y1 * cp - z1 * sp;
  const z2 = y1 * sp + z1 * cp;

  return {
    x: x1 * cy - z2 * sy,
    y: y2,
    z: x1 * sy + z2 * cy,
  };
}

function functionalBias(members, scale) {
  const counts = new Map();
  for (const node of members) counts.set(node.kind, (counts.get(node.kind) ?? 0) + 1);
  const total = Math.max(1, members.length);
  const ratio = kind => (counts.get(kind) ?? 0) / total;

  return {
    x: scale * (
      ratio('sense') * -0.12 +
      ratio('readout') * 0.08 +
      ratio('motor_primitive') * 0.13
    ),
    y: scale * (
      (ratio('predictor') + ratio('state')) * -0.10 +
      ratio('motor_primitive') * 0.12
    ),
    z: scale * (
      ratio('sense') * 0.10 +
      ratio('concept') * 0.02 -
      ratio('readout') * 0.07 -
      ratio('motor_primitive') * 0.15
    ),
  };
}

function sectorEmbedding(key, ordinal, scale, members) {
  const golden = 2.399963229728653;
  const angle = ordinal * golden + hashUnit(key, 'azimuth') * 0.72;
  const elevation = (hashUnit(key, 'elevation') - 0.5) * 1.10;
  const radius = scale * (0.24 + (ordinal % 3) * 0.042);
  const bias = functionalBias(members, scale);

  const horizontal = Math.cos(elevation) * radius;
  return {
    center: {
      x: Math.cos(angle) * horizontal * 1.18 + bias.x,
      y: Math.sin(elevation) * radius * 0.62 + bias.y,
      z: Math.sin(angle) * horizontal * 0.78 + bias.z,
    },
    yaw: hashUnit(key, 'yaw') * Math.PI * 2,
    pitch: (hashUnit(key, 'pitch') - 0.5) * 1.05,
    roll: (hashUnit(key, 'roll') - 0.5) * 0.65,
  };
}

export function projectPoint3D(point, camera, width, height) {
  const yaw = Number(camera?.yaw ?? -0.55);
  const pitch = Number(camera?.pitch ?? 0.34);
  const distance = clamp(Number(camera?.distance ?? 900), 420, 1800);

  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);

  const x1 = point.x * cy - point.z * sy;
  const z1 = point.x * sy + point.z * cy;
  const y1 = point.y * cp - z1 * sp;
  const z2 = point.y * sp + z1 * cp;

  const perspective = clamp(distance / (distance + z2), 0.35, 2.5);
  return {
    x: width / 2 + x1 * perspective,
    y: height / 2 + y1 * perspective,
    depth: z2,
    scale: perspective,
  };
}

function buildSectorWorld(nodes, width, height) {
  const groups = new Map();
  for (const node of nodes) {
    const key = node.community ?? 'isolated';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  }

  const scale = Math.min(width, height);
  const sectors = [...groups.entries()]
    .filter(([key]) => key !== 'isolated')
    .sort((a,b) => String(a[0]).localeCompare(String(b[0])));

  const embeddings = new Map();
  const localCenters = new Map();

  sectors.forEach(([key, members], index) => {
    embeddings.set(key, sectorEmbedding(key, index + 1, scale, members));
    localCenters.set(key, {
      x: members.reduce((sum, node) => sum + Number(node.x ?? 0), 0) / members.length,
      y: members.reduce((sum, node) => sum + Number(node.y ?? 0), 0) / members.length,
    });
  });

  return { groups, embeddings, localCenters, scale };
}

function worldPointForNode(node, embedding, localCenter) {
  const localScale = 0.72;
  const local = {
    x: (Number(node.x ?? 0) - localCenter.x) * localScale,
    y: (Number(node.y ?? 0) - localCenter.y) * localScale,
    z:
      kindDepth(node.kind) +
      (hashUnit(node.id, 'thickness') - 0.5) * 52,
  };
  const rotated = rotateLocal(
    local,
    embedding.yaw,
    embedding.pitch,
    embedding.roll,
  );
  return {
    x: embedding.center.x + rotated.x,
    y: embedding.center.y + rotated.y,
    z: embedding.center.z + rotated.z,
  };
}

function ellipsoidRing(center, axes, axis, embedding, camera, width, height) {
  const points = [];
  const steps = 40;
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * Math.PI * 2;
    let local;
    if (axis === 'xy') local = { x: Math.cos(t) * axes.x, y: Math.sin(t) * axes.y, z: 0 };
    else if (axis === 'xz') local = { x: Math.cos(t) * axes.x, y: 0, z: Math.sin(t) * axes.z };
    else local = { x: 0, y: Math.cos(t) * axes.y, z: Math.sin(t) * axes.z };
    const rotated = rotateLocal(local, embedding.yaw, embedding.pitch, embedding.roll);
    points.push(projectPoint3D({
      x: center.x + rotated.x,
      y: center.y + rotated.y,
      z: center.z + rotated.z,
    }, camera, width, height));
  }
  return points;
}

export function buildCognition3DScene(nodes, camera, width, height) {
  const { groups, embeddings, localCenters, scale } = buildSectorWorld(nodes, width, height);

  const worldById = new Map();
  const projected = [];

  for (const node of nodes) {
    if (node.community === 'isolated' || !embeddings.has(node.community)) {
      const angle = hashUnit(node.id, 'isolated-angle') * Math.PI * 2;
      const elevation = (hashUnit(node.id, 'isolated-elevation') - 0.5) * 1.2;
      const r = scale * 0.48;
      const world = {
        x: Math.cos(angle) * Math.cos(elevation) * r,
        y: Math.sin(elevation) * r,
        z: Math.sin(angle) * Math.cos(elevation) * r,
      };
      const point = projectPoint3D(world, camera, width, height);
      worldById.set(node.id, world);
      projected.push({
        node, world, ...point,
        radius: Math.max(2.5, (node.radius ?? 6) * point.scale),
      });
      continue;
    }

    const world = worldPointForNode(
      node,
      embeddings.get(node.community),
      localCenters.get(node.community),
    );
    const point = projectPoint3D(world, camera, width, height);
    worldById.set(node.id, world);
    projected.push({
      node,
      world,
      ...point,
      radius: Math.max(2.5, (node.radius ?? 6) * point.scale),
    });
  }

  projected.sort((a,b) => b.depth - a.depth);
  const byId = new Map(projected.map(item => [item.node.id, item]));
  const sectors = new Map();

  for (const [key, members] of groups.entries()) {
    if (key === 'isolated' || !embeddings.has(key)) continue;
    const embedding = embeddings.get(key);
    const memberWorld = members.map(node => worldById.get(node.id)).filter(Boolean);
    const maxDistance = Math.max(
      36,
      ...memberWorld.map(point => Math.hypot(
        point.x - embedding.center.x,
        point.y - embedding.center.y,
        point.z - embedding.center.z,
      )),
    );
    const radius = maxDistance + 28;
    const sizeFactor = 1 + Math.min(0.45, members.length / 120);
    const axes = {
      x: radius * sizeFactor,
      y: radius * (0.72 + hashUnit(key, 'axis-y') * 0.18),
      z: radius * (0.60 + hashUnit(key, 'axis-z') * 0.24),
    };
    const centerProjected = projectPoint3D(
      embedding.center,
      camera,
      width,
      height,
    );
    const stableLabel = members.find(node => node.sectorLabel)?.sectorLabel ?? null;

    sectors.set(key, {
      id: key,
      stableLabel,
      worldCenter: embedding.center,
      axes,
      radius,
      x: centerProjected.x,
      y: centerProjected.y,
      depth: centerProjected.depth,
      scale: centerProjected.scale,
      points: members.map(node => byId.get(node.id)).filter(Boolean),
      wireframes: [
        ellipsoidRing(embedding.center, axes, 'xy', embedding, camera, width, height),
        ellipsoidRing(embedding.center, axes, 'xz', embedding, camera, width, height),
        ellipsoidRing(embedding.center, axes, 'yz', embedding, camera, width, height),
      ],
    });
  }

  return { projected, byId, sectors, worldById };
}

export function orbitCamera(camera, deltaX, deltaY) {
  return {
    ...camera,
    yaw: Number(camera?.yaw ?? -0.55) + deltaX * 0.006,
    pitch: clamp(
      Number(camera?.pitch ?? 0.34) + deltaY * 0.005,
      -1.35,
      1.35,
    ),
  };
}

export function zoomCamera(camera, delta) {
  return {
    ...camera,
    distance: clamp(
      Number(camera?.distance ?? 900) * (delta < 0 ? 0.9 : 1.1),
      420,
      1800,
    ),
  };
}
