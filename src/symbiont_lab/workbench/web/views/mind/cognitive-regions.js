/**
 * Observer-side organic region geometry for the Cognitive Atlas.
 *
 * Shapes are derived from current node positions and graph evidence. They are
 * presentation-only and never feed coordinates, regions or semantics back to
 * Symbiont.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clamp01(value) {
  return Math.max(0, Math.min(1, finite(value, 0)));
}

function centroid(points) {
  if (!points.length) return { x: 0, y: 0 };
  let sx = 0, sy = 0, sw = 0;
  for (const point of points) {
    const w = Math.max(0.05, finite(point.weight, 1));
    sx += point.x * w;
    sy += point.y * w;
    sw += w;
  }
  return { x: sx / sw, y: sy / sw };
}

function polar(point, center) {
  return {
    ...point,
    angle: Math.atan2(point.y - center.y, point.x - center.x),
    distance: Math.hypot(point.x - center.x, point.y - center.y),
  };
}

function chaikin(points, passes = 2) {
  let current = points;
  for (let pass = 0; pass < passes; pass++) {
    if (current.length < 3) break;
    const next = [];
    for (let i = 0; i < current.length; i++) {
      const a = current[i];
      const b = current[(i + 1) % current.length];
      next.push({
        x: a.x * 0.75 + b.x * 0.25,
        y: a.y * 0.75 + b.y * 0.25,
      });
      next.push({
        x: a.x * 0.25 + b.x * 0.75,
        y: a.y * 0.25 + b.y * 0.75,
      });
    }
    current = next;
  }
  return current;
}

function resampleClosed(points, count = 40) {
  if (points.length < 2) return points;
  const lengths = [];
  let total = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    lengths.push(len);
    total += len;
  }
  if (total <= 1e-6) return points;
  const result = [];
  for (let k = 0; k < count; k++) {
    const target = total * k / count;
    let acc = 0;
    for (let i = 0; i < points.length; i++) {
      const len = lengths[i];
      if (acc + len >= target || i === points.length - 1) {
        const t = len > 0 ? (target - acc) / len : 0;
        const a = points[i], b = points[(i + 1) % points.length];
        result.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
        break;
      }
      acc += len;
    }
  }
  return result;
}

export function organicRegionShape(points, {
  padding = 18,
  bins = 20,
  smoothPasses = 2,
  sampleCount = 40,
} = {}) {
  if (!points?.length) return { center: { x: 0, y: 0 }, polygon: [], radius: 0 };
  if (points.length === 1) {
    const p = points[0];
    const radius = finite(p.radius, 6) + padding;
    const polygon = Array.from({ length: sampleCount }, (_, i) => {
      const a = i / sampleCount * Math.PI * 2;
      return { x: p.x + Math.cos(a) * radius, y: p.y + Math.sin(a) * radius };
    });
    return { center: { x: p.x, y: p.y }, polygon, radius };
  }

  const center = centroid(points);
  const bucket = Array.from({ length: bins }, () => null);
  for (const point of points.map(point => polar(point, center))) {
    const normalized = (point.angle + Math.PI) / (Math.PI * 2);
    const index = Math.max(0, Math.min(bins - 1, Math.floor(normalized * bins)));
    const reach = point.distance + finite(point.radius, 5) + padding;
    if (!bucket[index] || reach > bucket[index].reach) {
      bucket[index] = { reach, point };
    }
  }

  const occupied = bucket.map((item, index) => item ? index : -1).filter(index => index >= 0);
  if (!occupied.length) return { center, polygon: [], radius: 0 };

  const envelope = [];
  for (let i = 0; i < bins; i++) {
    let reach;
    if (bucket[i]) {
      reach = bucket[i].reach;
    } else {
      let left = null, right = null;
      for (let d = 1; d < bins; d++) {
        const li = (i - d + bins) % bins;
        const ri = (i + d) % bins;
        if (left == null && bucket[li]) left = { d, value: bucket[li].reach };
        if (right == null && bucket[ri]) right = { d, value: bucket[ri].reach };
        if (left && right) break;
      }
      if (left && right) {
        const total = left.d + right.d;
        reach = (left.value * right.d + right.value * left.d) / total;
        // Pull empty angular sectors inward so the outline remains concave.
        reach *= Math.max(0.62, 1 - Math.min(left.d, right.d) / bins * 1.9);
      } else {
        reach = (left?.value ?? right?.value ?? padding) * 0.68;
      }
    }
    const angle = -Math.PI + (i + 0.5) / bins * Math.PI * 2;
    envelope.push({
      x: center.x + Math.cos(angle) * reach,
      y: center.y + Math.sin(angle) * reach,
    });
  }

  const polygon = resampleClosed(chaikin(envelope, smoothPasses), sampleCount);
  const radius = Math.max(...polygon.map(p => Math.hypot(p.x - center.x, p.y - center.y)), 0);
  return { center, polygon, radius };
}

export function blendRegionShape(previous, current, alpha = 0.22) {
  if (!previous?.polygon?.length || !current?.polygon?.length) return current;
  const count = Math.max(previous.polygon.length, current.polygon.length);
  const a = resampleClosed(previous.polygon, count);
  const b = resampleClosed(current.polygon, count);
  const polygon = b.map((point, i) => ({
    x: a[i].x + (point.x - a[i].x) * alpha,
    y: a[i].y + (point.y - a[i].y) * alpha,
  }));
  const center = {
    x: previous.center.x + (current.center.x - previous.center.x) * alpha,
    y: previous.center.y + (current.center.y - previous.center.y) * alpha,
  };
  const radius = Math.max(...polygon.map(p => Math.hypot(p.x - center.x, p.y - center.y)), 0);
  return { ...current, center, polygon, radius };
}

export function polygonContains(polygon, x, y) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i], b = polygon[j];
    const intersect = ((a.y > y) !== (b.y > y)) &&
      (x < (b.x - a.x) * (y - a.y) / ((b.y - a.y) || 1e-9) + a.x);
    if (intersect) inside = !inside;
  }
  return inside;
}

export function traceRegionPath(ctx, shape) {
  const points = shape?.polygon ?? [];
  if (!points.length) return false;
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
  ctx.closePath();
  return true;
}

export function boundaryTension(region, internalEdgeCount = 0) {
  const bridges = Math.max(0, finite(region?.bridges, 0));
  const nodes = Math.max(1, finite(region?.total, 1));
  const internal = Math.max(0, finite(internalEdgeCount, 0));
  const externalRatio = bridges / Math.max(1, bridges + internal);
  const bridgeLoad = Math.min(1, bridges / Math.max(3, nodes * 2.5));
  return clamp01(externalRatio * 0.62 + bridgeLoad * 0.38);
}

export function functionalCenter(points, mode = 'structure') {
  if (!points?.length) return { x: 0, y: 0, weight: 0 };
  let sx = 0, sy = 0, sw = 0;
  for (const point of points) {
    const score = clamp01(point?.signals?.[mode] ?? point?.atlasScore ?? point?.weight ?? 0);
    const w = 0.12 + score * 0.88;
    sx += point.x * w; sy += point.y * w; sw += w;
  }
  return { x: sx / sw, y: sy / sw, weight: sw / points.length };
}

export function densityHotspots(points, {
  maxHotspots = 4,
  bandwidth = 52,
} = {}) {
  if (!points?.length) return [];
  return points.map(anchor => {
    let density = 0, sx = 0, sy = 0, sw = 0;
    for (const point of points) {
      const d = Math.hypot(point.x - anchor.x, point.y - anchor.y);
      const kernel = Math.exp(-(d * d) / (2 * bandwidth * bandwidth));
      const w = kernel * (0.25 + clamp01(point.weight ?? point.atlasScore ?? 0.5) * 0.75);
      density += w; sx += point.x * w; sy += point.y * w; sw += w;
    }
    return { x: sx / Math.max(sw, 1e-9), y: sy / Math.max(sw, 1e-9), density };
  })
  .sort((a,b) => b.density - a.density)
  .filter((item, index, all) =>
    all.slice(0, index).every(other => Math.hypot(other.x - item.x, other.y - item.y) > bandwidth * 0.8)
  )
  .slice(0, maxHotspots);
}

export function protoSubregions(regionNodes, edges, {
  minimumSize = 3,
} = {}) {
  const ids = new Set(regionNodes.map(node => node.id));
  const internal = edges.filter(edge => ids.has(edge.sourceId) && ids.has(edge.targetId));
  if (internal.length < minimumSize) return [];
  const supports = internal.map(edge => finite(edge.support, 0)).sort((a,b) => a - b);
  const threshold = supports[Math.floor(supports.length * 0.60)] ?? 0;
  const adjacency = new Map(regionNodes.map(node => [node.id, new Set()]));
  for (const edge of internal) {
    if (finite(edge.support, 0) < threshold) continue;
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
  }
  const remaining = new Set(adjacency.keys());
  const components = [];
  while (remaining.size) {
    const seed = remaining.values().next().value;
    remaining.delete(seed);
    const stack = [seed], members = [];
    while (stack.length) {
      const id = stack.pop();
      members.push(id);
      for (const next of adjacency.get(id) ?? []) {
        if (remaining.delete(next)) stack.push(next);
      }
    }
    if (members.length >= minimumSize && members.length < regionNodes.length * 0.86) {
      components.push(members.sort());
    }
  }
  return components.sort((a,b) => b.length - a.length || a[0].localeCompare(b[0]));
}
