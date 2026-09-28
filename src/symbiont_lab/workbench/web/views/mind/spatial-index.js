/**
 * Deterministic observer-side spatial bucketing for cognition layout.
 *
 * This is presentation-only. It bounds repulsion work to nearby cells while
 * graph springs, sector anchors and component cohesion retain global structure.
 */

function key2(ix, iy) {
  return `${ix}:${iy}`;
}

function key3(ix, iy, iz) {
  return `${ix}:${iy}:${iz}`;
}

export function forEachNearbyPair2D(nodes, cellSize, radius, callback) {
  const cells = new Map();
  const index = new Map(nodes.map((node, i) => [node, i]));
  const reach = Math.max(1, Math.ceil(radius / cellSize));

  for (const node of nodes) {
    const ix = Math.floor(node.x / cellSize);
    const iy = Math.floor(node.y / cellSize);
    const key = key2(ix, iy);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(node);
  }

  for (const a of nodes) {
    const ai = index.get(a);
    const ax = Math.floor(a.x / cellSize);
    const ay = Math.floor(a.y / cellSize);
    for (let dx = -reach; dx <= reach; dx++) {
      for (let dy = -reach; dy <= reach; dy++) {
        const bucket = cells.get(key2(ax + dx, ay + dy));
        if (!bucket) continue;
        for (const b of bucket) {
          if (index.get(b) <= ai) continue;
          const px = b.x - a.x;
          const py = b.y - a.y;
          if (px * px + py * py <= radius * radius) callback(a, b);
        }
      }
    }
  }
}

export function forEachNearbyPair3D(nodes, positions, cellSize, radius) {
  const cells = new Map();
  const index = new Map(nodes.map((node, i) => [node, i]));
  const reach = Math.max(1, Math.ceil(radius / cellSize));

  for (const node of nodes) {
    const point = positions.get(node.id);
    if (!point) continue;
    const ix = Math.floor(point.x / cellSize);
    const iy = Math.floor(point.y / cellSize);
    const iz = Math.floor(point.z / cellSize);
    const key = key3(ix, iy, iz);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(node);
  }

  for (const a of nodes) {
    const ai = index.get(a);
    const pa = positions.get(a.id);
    if (!pa) continue;
    const ax = Math.floor(pa.x / cellSize);
    const ay = Math.floor(pa.y / cellSize);
    const az = Math.floor(pa.z / cellSize);
    for (let dx = -reach; dx <= reach; dx++) {
      for (let dy = -reach; dy <= reach; dy++) {
        for (let dz = -reach; dz <= reach; dz++) {
          const bucket = cells.get(key3(ax + dx, ay + dy, az + dz));
          if (!bucket) continue;
          for (const b of bucket) {
            if (index.get(b) <= ai) continue;
            const pb = positions.get(b.id);
            const px = pb.x - pa.x;
            const py = pb.y - pa.y;
            const pz = pb.z - pa.z;
            if (px * px + py * py + pz * pz <= radius * radius) callback(a, b);
          }
        }
      }
    }
  }
}
