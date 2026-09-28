/**
 * Deterministic observer-side local-pair enumeration for cognition layout.
 *
 * Brute force is faster for small/medium graphs in V8 because Map/bucket setup
 * dominates. Large graphs switch to spatial buckets. Both paths enumerate the
 * exact same 2D pairs inside radius; 3D remains the observer-side local-force
 * approximation introduced by P7.
 */

const BRUTE_FORCE_PAIR_THRESHOLD = 2500;

function bucket2(cells, ix, iy) {
  const column = cells.get(ix);
  return column?.get(iy) ?? null;
}

function bucket3(cells, ix, iy, iz) {
  const plane = cells.get(ix);
  const row = plane?.get(iy);
  return row?.get(iz) ?? null;
}

function insert2(cells, ix, iy, index) {
  let column = cells.get(ix);
  if (!column) {
    column = new Map();
    cells.set(ix, column);
  }
  let bucket = column.get(iy);
  if (!bucket) {
    bucket = [];
    column.set(iy, bucket);
  }
  bucket.push(index);
}

function insert3(cells, ix, iy, iz, index) {
  let plane = cells.get(ix);
  if (!plane) {
    plane = new Map();
    cells.set(ix, plane);
  }
  let row = plane.get(iy);
  if (!row) {
    row = new Map();
    plane.set(iy, row);
  }
  let bucket = row.get(iz);
  if (!bucket) {
    bucket = [];
    row.set(iz, bucket);
  }
  bucket.push(index);
}

function bruteForce2D(nodes, radius, callback) {
  const radiusSq = radius * radius;
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const b = nodes[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      if (dx * dx + dy * dy <= radiusSq) callback(a, b);
    }
  }
}

function bruteForce3D(nodes, positions, radius, callback) {
  const radiusSq = radius * radius;
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    const pa = positions.get(a.id);
    if (!pa) continue;
    for (let j = i + 1; j < nodes.length; j++) {
      const b = nodes[j];
      const pb = positions.get(b.id);
      if (!pb) continue;
      const dx = pb.x - pa.x;
      const dy = pb.y - pa.y;
      const dz = pb.z - pa.z;
      if (dx * dx + dy * dy + dz * dz <= radiusSq) callback(a, b);
    }
  }
}

export function forEachNearbyPair2D(nodes, cellSize, radius, callback) {
  if (nodes.length <= BRUTE_FORCE_PAIR_THRESHOLD) {
    bruteForce2D(nodes, radius, callback);
    return;
  }

  // A cell at least as large as the interaction radius means every possible
  // neighbour lies in this cell or one of the 8 adjacent cells.
  const size = Math.max(cellSize, radius);
  const cells = new Map();
  const radiusSq = radius * radius;

  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    insert2(cells, Math.floor(node.x / size), Math.floor(node.y / size), i);
  }

  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    const ax = Math.floor(a.x / size);
    const ay = Math.floor(a.y / size);
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const bucket = bucket2(cells, ax + dx, ay + dy);
        if (!bucket) continue;
        for (const j of bucket) {
          if (j <= i) continue;
          const b = nodes[j];
          const px = b.x - a.x;
          const py = b.y - a.y;
          if (px * px + py * py <= radiusSq) callback(a, b);
        }
      }
    }
  }
}

export function forEachNearbyPair3D(nodes, positions, cellSize, radius, callback) {
  if (nodes.length <= BRUTE_FORCE_PAIR_THRESHOLD) {
    bruteForce3D(nodes, positions, radius, callback);
    return;
  }

  const size = Math.max(cellSize, radius);
  const cells = new Map();
  const radiusSq = radius * radius;

  for (let i = 0; i < nodes.length; i++) {
    const point = positions.get(nodes[i].id);
    if (!point) continue;
    insert3(
      cells,
      Math.floor(point.x / size),
      Math.floor(point.y / size),
      Math.floor(point.z / size),
      i,
    );
  }

  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    const pa = positions.get(a.id);
    if (!pa) continue;
    const ax = Math.floor(pa.x / size);
    const ay = Math.floor(pa.y / size);
    const az = Math.floor(pa.z / size);
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        for (let dz = -1; dz <= 1; dz++) {
          const bucket = bucket3(cells, ax + dx, ay + dy, az + dz);
          if (!bucket) continue;
          for (const j of bucket) {
            if (j <= i) continue;
            const b = nodes[j];
            const pb = positions.get(b.id);
            const px = pb.x - pa.x;
            const py = pb.y - pa.y;
            const pz = pb.z - pa.z;
            if (px * px + py * py + pz * pz <= radiusSq) callback(a, b);
          }
        }
      }
    }
  }
}

export { BRUTE_FORCE_PAIR_THRESHOLD };
