/**
 * Perspective projection for the emergent Cognition Map.
 *
 * This module does not change sector membership or graph semantics. It adds a
 * deterministic observer-side depth coordinate and camera projection only.
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

function kindDepth(kind) {
  switch (kind) {
    case 'sense': return 85;
    case 'predictor': return 45;
    case 'state': return 30;
    case 'concept': return 5;
    case 'gate': return -20;
    case 'readout': return -45;
    case 'motor_primitive': return -105;
    case 'actuator': return -165;
    default: return 0;
  }
}

function sectorDepth(node) {
  const key = node.sectorLabel ?? node.community ?? 'unintegrated';
  return ((hashString(key) % 241) - 120) * 0.55;
}

export function worldDepthForNode(node) {
  const jitter = ((hashString(node.id) % 31) - 15) * 0.8;
  return sectorDepth(node) + kindDepth(node.kind) + jitter;
}

export function projectPoint3D(
  point,
  camera,
  width,
  height,
) {
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

  const perspective = clamp(distance / (distance + z2), 0.42, 2.1);
  return {
    x: width / 2 + x1 * perspective,
    y: height / 2 + y1 * perspective,
    depth: z2,
    scale: perspective,
  };
}

export function buildCognition3DScene(
  nodes,
  camera,
  width,
  height,
) {
  const cx = width / 2;
  const cy = height / 2;

  const projected = nodes.map(node => {
    const world = {
      x: node.x - cx,
      y: node.y - cy,
      z: worldDepthForNode(node),
    };
    const point = projectPoint3D(world, camera, width, height);
    return {
      node,
      world,
      ...point,
      radius: Math.max(2.5, (node.radius ?? 6) * point.scale),
    };
  });

  projected.sort((a, b) => b.depth - a.depth);

  const byId = new Map(projected.map(item => [item.node.id, item]));
  const sectors = new Map();
  for (const item of projected) {
    const key = item.node.community;
    if (!key || key === 'isolated') continue;
    const sector = sectors.get(key) ?? {
      id: key,
      points: [],
      x: 0,
      y: 0,
      depth: 0,
    };
    sector.points.push(item);
    sector.x += item.x;
    sector.y += item.y;
    sector.depth += item.depth;
    sectors.set(key, sector);
  }

  for (const sector of sectors.values()) {
    sector.x /= sector.points.length;
    sector.y /= sector.points.length;
    sector.depth /= sector.points.length;
    sector.radius = Math.max(
      28,
      ...sector.points.map(point =>
        Math.hypot(point.x - sector.x, point.y - sector.y) + point.radius
      ),
    ) + 18;
    sector.depthSpread = Math.max(
      16,
      ...sector.points.map(point => Math.abs(point.depth - sector.depth)),
    );
  }

  return {
    projected,
    byId,
    sectors,
  };
}

export function orbitCamera(camera, deltaX, deltaY) {
  return {
    ...camera,
    yaw: Number(camera?.yaw ?? -0.55) + deltaX * 0.006,
    pitch: clamp(
      Number(camera?.pitch ?? 0.34) + deltaY * 0.005,
      -1.15,
      1.15,
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
