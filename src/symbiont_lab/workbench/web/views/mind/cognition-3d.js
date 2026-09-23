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

function seedVolumePoint(nodeId) {
  const u = hashUnit(nodeId, 'volume-u') * 2 - 1;
  const theta = hashUnit(nodeId, 'volume-theta') * Math.PI * 2;
  const radial = Math.cbrt(0.12 + hashUnit(nodeId, 'volume-radius') * 0.88);
  const planar = Math.sqrt(Math.max(0, 1 - u * u));
  return {
    x: Math.cos(theta) * planar * radial,
    y: Math.sin(theta) * planar * radial,
    z: u * radial,
  };
}

function buildVolumetricLocalPositions(members, edges) {
  const ids = new Set(members.map(node => node.id));
  const neighbors = new Map(members.map(node => [node.id, []]));
  for (const edge of edges ?? []) {
    if (!ids.has(edge.source.id) || !ids.has(edge.target.id)) continue;
    neighbors.get(edge.source.id)?.push(edge.target.id);
    neighbors.get(edge.target.id)?.push(edge.source.id);
  }

  const seeds = new Map(members.map(node => [node.id, seedVolumePoint(node.id)]));
  let positions = new Map(
    [...seeds.entries()].map(([id, point]) => [id, { ...point }])
  );

  // Relationship smoothing in all three axes. A retained seed component keeps
  // the embedding volumetric and prevents collapse onto a line or plane.
  for (let round = 0; round < 7; round++) {
    const next = new Map();
    for (const node of members) {
      const current = positions.get(node.id);
      const seed = seeds.get(node.id);
      const linked = neighbors.get(node.id) ?? [];
      if (!linked.length) {
        next.set(node.id, { ...current });
        continue;
      }
      let x = 0, y = 0, z = 0, count = 0;
      for (const id of linked) {
        const point = positions.get(id);
        if (!point) continue;
        x += point.x; y += point.y; z += point.z; count += 1;
      }
      if (!count) {
        next.set(node.id, { ...current });
        continue;
      }
      x /= count; y /= count; z /= count;

      const relationPull = 0.43;
      const seedRetention = 0.34;
      const selfRetention = 1 - relationPull - seedRetention;
      const point = {
        x: current.x * selfRetention + x * relationPull + seed.x * seedRetention,
        y: current.y * selfRetention + y * relationPull + seed.y * seedRetention,
        z: current.z * selfRetention + z * relationPull + seed.z * seedRetention,
      };

      // Keep every point inside the unit ball while preserving all three axes.
      const length = Math.hypot(point.x, point.y, point.z);
      if (length > 0.96) {
        const factor = 0.96 / length;
        point.x *= factor; point.y *= factor; point.z *= factor;
      }
      next.set(node.id, point);
    }
    positions = next;
  }
  return positions;
}

function buildSectorWorld(nodes, edges, width, height) {
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
  const localPositions = new Map();

  sectors.forEach(([key, members], index) => {
    embeddings.set(key, sectorEmbedding(key, index + 1, scale, members));
    localPositions.set(
      key,
      buildVolumetricLocalPositions(
        members,
        (edges ?? []).filter(edge =>
          members.some(node => node.id === edge.source.id) &&
          members.some(node => node.id === edge.target.id)
        ),
      ),
    );
  });

  return { groups, embeddings, localPositions, scale };
}

function worldPointForNode(node, embedding, localPosition, axes) {
  const local = {
    x: localPosition.x * axes.x,
    y: localPosition.y * axes.y,
    z: localPosition.z * axes.z,
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

export function buildCognition3DScene(nodes, edges, camera, width, height) {
  const { groups, embeddings, localPositions, scale } = buildSectorWorld(nodes, edges, width, height);

  const hullEmbedding = { yaw: 0.08, pitch: -0.06, roll: 0.02 };
  const hullCenter = { x: 0, y: 0, z: 0 };
  const hullAxes = {
    x: scale * 0.50,
    y: scale * 0.31,
    z: scale * 0.38,
  };
  const brainHull = [
    ellipsoidRing(hullCenter, hullAxes, 'xy', hullEmbedding, camera, width, height),
    ellipsoidRing(hullCenter, hullAxes, 'xz', hullEmbedding, camera, width, height),
    ellipsoidRing(hullCenter, hullAxes, 'yz', hullEmbedding, camera, width, height),
  ];

  const sectorAxes = new Map();
  for (const [key, members] of groups.entries()) {
    if (key === 'isolated') continue;
    const base = scale * (0.070 + Math.min(0.055, Math.sqrt(members.length) * 0.006));
    sectorAxes.set(key, {
      x: base * (1.00 + hashUnit(key, 'volume-x') * 0.30),
      y: base * (0.78 + hashUnit(key, 'volume-y') * 0.30),
      z: base * (0.82 + hashUnit(key, 'volume-z') * 0.34),
    });
  }

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
      localPositions.get(node.community).get(node.id),
      sectorAxes.get(node.community),
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
    const axes = sectorAxes.get(key);
    const radius = Math.max(axes.x, axes.y, axes.z);
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

  return { projected, byId, sectors, worldById, brainHull };
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
