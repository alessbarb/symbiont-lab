/**
 * Scientific 3D cognition projection.
 *
 * The 3D geometry is not anatomy. Positions emerge from organism-owned graph
 * evidence. Two observer-side modes are supported:
 *
 * - relational: topology only (edge attraction + node repulsion + inertia)
 * - physicalized: relational forces plus abstract packing/wiring costs
 *
 * The physicalized mode asks what morphology the same network would settle
 * into if connection length and occupied volume carried a cost. It is an
 * observer experiment and never feeds back into Symbiont.
 */

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function neutralSeed(index, count, scale = 110) {
  // Symmetry-breaking only. The seed has no semantic meaning and disappears
  // under relaxation. Unlike the previous implementation it does not depend
  // on node kind, sector identity, or hashed labels.
  const golden = Math.PI * (3 - Math.sqrt(5));
  const t = count <= 1 ? 0 : (index + 0.5) / count;
  const y = 1 - 2 * t;
  const radius = Math.sqrt(Math.max(0, 1 - y * y));
  const angle = index * golden;
  return {
    x: Math.cos(angle) * radius * scale,
    y: y * scale,
    z: Math.sin(angle) * radius * scale,
  };
}

function edgeEvidence(edge) {
  const support = Math.max(0, finite(edge.support, 0));
  const stable = Math.max(0, finite(edge.stableTicks, 0));
  const weight = Math.abs(finite(edge.weight, 0));
  const plasticity = clamp(finite(edge.plasticity, 0), 0, 1);
  return {
    support: Math.log1p(support),
    stable: Math.log1p(stable),
    weight,
    plasticity,
  };
}

function nodeVolumeRadius(node) {
  const importance = clamp(
    finite(node.structuralImportance ?? node.visualValue, 0),
    0,
    1,
  );
  return 5.5 + importance * 7.5;
}

function connectedNeighborCentroid(nodeId, edges, positions) {
  let x = 0, y = 0, z = 0, count = 0;
  for (const edge of edges) {
    const other = edge.source?.id === nodeId
      ? edge.target?.id
      : edge.target?.id === nodeId
        ? edge.source?.id
        : null;
    if (!other) continue;
    const point = positions.get(other);
    if (!point) continue;
    x += point.x; y += point.y; z += point.z; count += 1;
  }
  return count ? { x: x / count, y: y / count, z: z / count } : null;
}

export function ensure3DState(nodes, edges, positions, velocities) {
  const currentIds = new Set(nodes.map(node => node.id));
  for (const id of [...positions.keys()]) {
    if (!currentIds.has(id)) positions.delete(id);
  }
  for (const id of [...velocities.keys()]) {
    if (!currentIds.has(id)) velocities.delete(id);
  }

  const ordered = [...nodes].sort((a, b) => String(a.id).localeCompare(String(b.id)));
  for (let index = 0; index < ordered.length; index++) {
    const node = ordered[index];
    if (!positions.has(node.id)) {
      const neighborCenter = connectedNeighborCentroid(node.id, edges, positions);
      const seed = neutralSeed(index, ordered.length);
      positions.set(node.id, neighborCenter
        ? {
            x: neighborCenter.x + seed.x * 0.12,
            y: neighborCenter.y + seed.y * 0.12,
            z: neighborCenter.z + seed.z * 0.12,
          }
        : seed);
    }
    if (!velocities.has(node.id)) velocities.set(node.id, { x: 0, y: 0, z: 0 });
  }
}

function componentCentroids(nodes, positions) {
  const groups = new Map();
  for (const node of nodes) {
    const rank = finite(node.componentRank, 0);
    const point = positions.get(node.id);
    if (!point) continue;
    const item = groups.get(rank) ?? { x: 0, y: 0, z: 0, n: 0 };
    item.x += point.x; item.y += point.y; item.z += point.z; item.n += 1;
    groups.set(rank, item);
  }
  for (const item of groups.values()) {
    item.x /= Math.max(1, item.n);
    item.y /= Math.max(1, item.n);
    item.z /= Math.max(1, item.n);
  }
  return groups;
}

export function relaxCognition3D(
  nodes,
  edges,
  positions,
  velocities,
  mode = 'relational',
  iterations = 1,
) {
  ensure3DState(nodes, edges, positions, velocities);
  if (!nodes.length) return;

  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const maxSupport = Math.max(1, ...edges.map(edge => Math.log1p(Math.max(0, finite(edge.support, 0)))));
  const maxStable = Math.max(1, ...edges.map(edge => Math.log1p(Math.max(0, finite(edge.stableTicks, 0)))));

  for (let iteration = 0; iteration < iterations; iteration++) {
    const forces = new Map(nodes.map(node => [node.id, { x: 0, y: 0, z: 0 }]));

    // Pairwise repulsion and physical exclusion. No type or sector bias.
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      const pa = positions.get(a.id);
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const pb = positions.get(b.id);
        let dx = pb.x - pa.x;
        let dy = pb.y - pa.y;
        let dz = pb.z - pa.z;
        let distSq = dx * dx + dy * dy + dz * dz;
        if (distSq < 1e-5) {
          // Deterministic axis nudge, used only for exact numerical overlap.
          dx = 0.01 * (i + 1);
          dy = 0.01 * (j + 1);
          dz = 0.005 * (i + j + 2);
          distSq = dx * dx + dy * dy + dz * dz;
        }
        const dist = Math.sqrt(distSq);
        const fa = forces.get(a.id);
        const fb = forces.get(b.id);

        const sameComponent = finite(a.componentRank, 0) === finite(b.componentRank, 0);
        const repulsion = (sameComponent ? 1900 : 3600) / Math.max(100, distSq);
        const minDistance = nodeVolumeRadius(a) + nodeVolumeRadius(b) + 4;
        const overlap = Math.max(0, minDistance - dist);
        const exclusion = mode === 'physicalized' ? overlap * 0.055 : overlap * 0.025;
        const magnitude = repulsion + exclusion;

        const ux = dx / dist, uy = dy / dist, uz = dz / dist;
        fa.x -= ux * magnitude; fa.y -= uy * magnitude; fa.z -= uz * magnitude;
        fb.x += ux * magnitude; fb.y += uy * magnitude; fb.z += uz * magnitude;
      }
    }

    // Actual graph edges provide all attractive topology.
    for (const edge of edges) {
      const sourceId = edge.source?.id ?? edge.sourceId;
      const targetId = edge.target?.id ?? edge.targetId;
      const source = nodeById.get(sourceId);
      const target = nodeById.get(targetId);
      const ps = positions.get(sourceId);
      const pt = positions.get(targetId);
      if (!source || !target || !ps || !pt) continue;

      const dx = pt.x - ps.x;
      const dy = pt.y - ps.y;
      const dz = pt.z - ps.z;
      const dist = Math.max(0.001, Math.hypot(dx, dy, dz));
      const evidence = edgeEvidence(edge);
      const supportNorm = evidence.support / maxSupport;
      const stableNorm = evidence.stable / maxStable;

      // Strong, stable evidence is allowed to settle at shorter wiring length.
      const restLength = mode === 'physicalized'
        ? 86 - supportNorm * 25 - stableNorm * 12
        : 100 - supportNorm * 18;
      const stiffness = (
        0.006 +
        supportNorm * 0.014 +
        stableNorm * 0.008 +
        Math.min(1, evidence.weight) * 0.004
      ) * (mode === 'physicalized' ? 1.25 : 1.0);

      const force = (dist - Math.max(34, restLength)) * stiffness;
      const ux = dx / dist, uy = dy / dist, uz = dz / dist;
      const fs = forces.get(sourceId);
      const ft = forces.get(targetId);
      fs.x += ux * force; fs.y += uy * force; fs.z += uz * force;
      ft.x -= ux * force; ft.y -= uy * force; ft.z -= uz * force;
    }

    const centers = componentCentroids(nodes, positions);
    for (const node of nodes) {
      const point = positions.get(node.id);
      const force = forces.get(node.id);
      const center = centers.get(finite(node.componentRank, 0));

      // A component can cohere, but observer-defined communities never pull.
      if (center && finite(node.componentSize, 1) > 1) {
        const componentPull = mode === 'physicalized' ? 0.0018 : 0.0008;
        force.x += (center.x - point.x) * componentPull;
        force.y += (center.y - point.y) * componentPull;
        force.z += (center.z - point.z) * componentPull;
      }

      if (mode === 'physicalized') {
        // Abstract packing pressure. It is isotropic and contains no
        // brain-shaped envelope or functional direction.
        const radius = Math.max(1, Math.hypot(point.x, point.y, point.z));
        const compactPressure = 0.0015;
        force.x -= point.x * compactPressure;
        force.y -= point.y * compactPressure;
        force.z -= point.z * compactPressure;

        // Dense inner regions face a mild radial cost that prevents collapse
        // into a single point while still rewarding shorter wiring.
        if (radius < 45) {
          const outward = (45 - radius) * 0.002;
          force.x += (point.x / radius) * outward;
          force.y += (point.y / radius) * outward;
          force.z += (point.z / radius) * outward;
        }
      }

      const velocity = velocities.get(node.id);
      const plasticity = clamp(
        edges
          .filter(edge => (edge.source?.id ?? edge.sourceId) === node.id || (edge.target?.id ?? edge.targetId) === node.id)
          .reduce((sum, edge) => sum + finite(edge.plasticity, 0), 0) /
          Math.max(1, edges.filter(edge => (edge.source?.id ?? edge.sourceId) === node.id || (edge.target?.id ?? edge.targetId) === node.id).length),
        0,
        1,
      );
      const inertia = mode === 'physicalized'
        ? 0.82 + (1 - plasticity) * 0.08
        : 0.86;

      velocity.x = (velocity.x + force.x) * inertia;
      velocity.y = (velocity.y + force.y) * inertia;
      velocity.z = (velocity.z + force.z) * inertia;

      const maxStep = 8;
      const speed = Math.hypot(velocity.x, velocity.y, velocity.z);
      if (speed > maxStep) {
        const factor = maxStep / speed;
        velocity.x *= factor; velocity.y *= factor; velocity.z *= factor;
      }

      point.x += velocity.x;
      point.y += velocity.y;
      point.z += velocity.z;
    }
  }
}

export function projectPoint3D(point, camera, width, height) {
  const yaw = finite(camera?.yaw, -0.55);
  const pitch = finite(camera?.pitch, 0.34);
  const distance = clamp(finite(camera?.distance, 900), 360, 2200);

  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);

  const x1 = point.x * cy - point.z * sy;
  const z1 = point.x * sy + point.z * cy;
  const y1 = point.y * cp - z1 * sp;
  const z2 = point.y * sp + z1 * cp;

  const perspective = clamp(distance / (distance + z2), 0.28, 3.0);
  return {
    x: width / 2 + x1 * perspective,
    y: height / 2 + y1 * perspective,
    depth: z2,
    scale: perspective,
  };
}

function sceneMetrics(nodes, edges, positions) {
  let wiringLength = 0;
  let maxRadius = 0;
  let totalVolume = 0;
  for (const node of nodes) {
    const point = positions.get(node.id);
    if (!point) continue;
    maxRadius = Math.max(maxRadius, Math.hypot(point.x, point.y, point.z));
    const radius = nodeVolumeRadius(node);
    totalVolume += (4 / 3) * Math.PI * radius ** 3;
  }
  for (const edge of edges) {
    const a = positions.get(edge.source?.id ?? edge.sourceId);
    const b = positions.get(edge.target?.id ?? edge.targetId);
    if (!a || !b) continue;
    wiringLength += Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
  }
  const enclosingVolume = maxRadius > 0 ? (4 / 3) * Math.PI * maxRadius ** 3 : 1;
  return {
    wiringLength,
    occupiedRadius: maxRadius,
    packingDensity: clamp(totalVolume / enclosingVolume, 0, 1),
  };
}

export function buildCognition3DScene(
  nodes,
  edges,
  camera,
  width,
  height,
  positions,
  mode = 'relational',
) {
  const projected = [];
  const worldById = new Map();
  for (const node of nodes) {
    const world = positions.get(node.id);
    if (!world) continue;
    const point = projectPoint3D(world, camera, width, height);
    const item = {
      node,
      world,
      ...point,
      radius: Math.max(2.5, finite(node.radius, 6) * point.scale),
    };
    projected.push(item);
    worldById.set(node.id, world);
  }

  projected.sort((a, b) => b.depth - a.depth);
  const byId = new Map(projected.map(item => [item.node.id, item]));

  // Component centers are objective graph structure and are exposed only as
  // optional analytical labels, never as enclosing anatomical volumes.
  const componentAcc = new Map();
  for (const item of projected) {
    const rank = finite(item.node.componentRank, 0);
    const acc = componentAcc.get(rank) ?? { x: 0, y: 0, depth: 0, n: 0 };
    acc.x += item.x; acc.y += item.y; acc.depth += item.depth; acc.n += 1;
    componentAcc.set(rank, acc);
  }
  const components = [...componentAcc.entries()].map(([rank, acc]) => ({
    rank,
    x: acc.x / Math.max(1, acc.n),
    y: acc.y / Math.max(1, acc.n),
    depth: acc.depth / Math.max(1, acc.n),
    count: acc.n,
  })).sort((a, b) => a.rank - b.rank);

  return {
    projected,
    byId,
    components,
    worldById,
    mode,
    metrics: sceneMetrics(nodes, edges, positions),
  };
}

export function orbitCamera(camera, deltaX, deltaY) {
  return {
    ...camera,
    yaw: finite(camera?.yaw, -0.55) + deltaX * 0.006,
    pitch: clamp(finite(camera?.pitch, 0.34) + deltaY * 0.005, -1.35, 1.35),
  };
}

export function zoomCamera(camera, delta, {
  sceneRadius = 220,
  sensitivity = 0.00075,
} = {}) {
  const radius = Math.max(60, finite(sceneRadius, 220));
  const minDistance = Math.max(150, radius * 0.82 + 70);
  const maxDistance = Math.max(1200, radius * 7.5 + 520);
  const current = finite(camera?.distance, 900);
  const wheelDelta = clamp(finite(delta, 0), -240, 240);
  const factor = Math.exp(wheelDelta * sensitivity);
  return {
    ...camera,
    distance: clamp(current * factor, minDistance, maxDistance),
  };
}
