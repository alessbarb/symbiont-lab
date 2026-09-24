/**
 * Observer-only presentation animation layer for the Cognitive Atlas.
 *
 * This module never mutates organism state, topology, cognition or 3D physics.
 * It only converts already-observed changes into time-based presentation state.
 */

const DURATIONS = Object.freeze({
  nodeSpawn: 780,
  nodePulse: 500,
  nodeExit: 650,
  edgeBirth: 520,
  edgeExit: 400,
  regionMorph: 650,
  regionBirth: 1350,
  regionExit: 950,
  regionSplit: 2400,
  regionMerge: 2150,
  corridorBirth: 650,
  labelBirth: 450,
  replay: 120,
});

function clamp01(value) {
  return Math.max(0, Math.min(1, Number.isFinite(Number(value)) ? Number(value) : 0));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function easeOutCubic(t) {
  const x = 1 - clamp01(t);
  return 1 - x * x * x;
}

export function easeInOutCubic(t) {
  const x = clamp01(t);
  return x < 0.5
    ? 4 * x * x * x
    : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

export function easeOutQuint(t) {
  return 1 - Math.pow(1 - clamp01(t), 5);
}

export function easeInOutQuint(t) {
  const x = clamp01(t);
  return x < 0.5
    ? 16 * x * x * x * x * x
    : 1 - Math.pow(-2 * x + 2, 5) / 2;
}

export function easeOutBackSoft(t) {
  const x = clamp01(t);
  const c1 = 0.78;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
}

function edgeKey(edge) {
  return `${edge.source?.id ?? edge.sourceId}|${edge.target?.id ?? edge.targetId}|${edge.kind ?? 'edge'}`;
}

function resampleShape(shape, count) {
  const points = shape?.polygon ?? [];
  if (!points.length || count <= 0) return [];
  if (points.length === count) return points.map(point => ({ ...point }));
  const result = [];
  for (let i = 0; i < count; i++) {
    const position = i / count * points.length;
    const base = Math.floor(position) % points.length;
    const next = (base + 1) % points.length;
    const t = position - Math.floor(position);
    result.push({
      x: lerp(points[base].x, points[next].x, t),
      y: lerp(points[base].y, points[next].y, t),
    });
  }
  return result;
}

export function interpolateRegionShape(from, to, progress) {
  if (!from?.polygon?.length) return to;
  if (!to?.polygon?.length) return from;
  const t = clamp01(progress);
  const count = Math.max(from.polygon.length, to.polygon.length);
  const a = resampleShape(from, count);
  const b = resampleShape(to, count);
  const polygon = b.map((point, index) => ({
    x: lerp(a[index].x, point.x, t),
    y: lerp(a[index].y, point.y, t),
  }));
  const center = {
    x: lerp(from.center?.x ?? 0, to.center?.x ?? 0, t),
    y: lerp(from.center?.y ?? 0, to.center?.y ?? 0, t),
  };
  const radius = Math.max(
    ...polygon.map(point => Math.hypot(point.x - center.x, point.y - center.y)),
    0,
  );
  return {
    ...to,
    center,
    polygon,
    radius,
  };
}

export function scaleRegionShape(shape, scale) {
  if (!shape?.polygon?.length) return shape;
  const center = shape.center ?? { x: 0, y: 0 };
  const s = Math.max(0.01, Number(scale) || 1);
  const polygon = shape.polygon.map(point => ({
    x: center.x + (point.x - center.x) * s,
    y: center.y + (point.y - center.y) * s,
  }));
  return {
    ...shape,
    polygon,
    radius: (shape.radius ?? 0) * s,
  };
}

function shapeDistance(a, b) {
  if (!a?.polygon?.length || !b?.polygon?.length) return Infinity;
  const centerDelta = Math.hypot(
    (a.center?.x ?? 0) - (b.center?.x ?? 0),
    (a.center?.y ?? 0) - (b.center?.y ?? 0),
  );
  const radiusDelta = Math.abs((a.radius ?? 0) - (b.radius ?? 0));
  return centerDelta + radiusDelta * 0.6;
}

function averageShape(shapes) {
  const valid = shapes.filter(shape => shape?.polygon?.length);
  if (!valid.length) return null;
  if (valid.length === 1) return valid[0];
  const count = Math.max(...valid.map(shape => shape.polygon.length));
  const sampled = valid.map(shape => resampleShape(shape, count));
  const polygon = Array.from({ length: count }, (_, index) => ({
    x: sampled.reduce((sum, points) => sum + points[index].x, 0) / sampled.length,
    y: sampled.reduce((sum, points) => sum + points[index].y, 0) / sampled.length,
  }));
  const center = {
    x: valid.reduce((sum, shape) => sum + (shape.center?.x ?? 0), 0) / valid.length,
    y: valid.reduce((sum, shape) => sum + (shape.center?.y ?? 0), 0) / valid.length,
  };
  const radius = Math.max(
    ...polygon.map(point => Math.hypot(point.x - center.x, point.y - center.y)),
    0,
  );
  return { ...valid[0], center, polygon, radius };
}

function reducedMotionRequested() {
  try {
    return Boolean(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches);
  } catch {
    return false;
  }
}

function durationFor(kind, reducedMotion, replay = false) {
  if (replay) return DURATIONS.replay;
  const base = DURATIONS[kind] ?? DURATIONS.regionMorph;
  if (!reducedMotion) return base;
  if (kind === 'regionSplit' || kind === 'regionMerge') return 220;
  if (kind.startsWith('region')) return 160;
  return 120;
}

function animationProgress(animation, now) {
  const elapsed = now - animation.startedAt - (animation.delayMs ?? 0);
  if (elapsed <= 0) return 0;
  return clamp01(elapsed / Math.max(1, animation.durationMs));
}

function active(animation, now) {
  return now < animation.startedAt + (animation.delayMs ?? 0) + animation.durationMs;
}

function snapshotNode(node) {
  if (!node) return null;
  return {
    id: node.id,
    x: Number(node.x) || 0,
    y: Number(node.y) || 0,
    radius: Number(node.radius) || Number(node.baseRadius) || 6,
    color: node.color,
    kind: node.kind,
    observerLabel: node.observerLabel,
    label: node.label,
  };
}

function snapshotEdge(edge) {
  if (!edge?.source || !edge?.target) return null;
  return {
    key: edgeKey(edge),
    kind: edge.kind,
    source: snapshotNode(edge.source),
    target: snapshotNode(edge.target),
  };
}

export function createCognitivePresentationAnimator({
  now = () => performance.now(),
  reducedMotion = reducedMotionRequested(),
} = {}) {
  const animations = new Map();
  const ghostNodes = new Map();
  const ghostEdges = new Map();
  const ghostRegions = new Map();
  const lastRegionShapes = new Map();
  const regionTargets = new Map();
  let initialized = false;

  function putAnimation(key, animation) {
    const timestamp = now();
    const previous = animations.get(key);
    if (previous && active(previous, timestamp)) {
      animation.fromPresentation = sampleRaw(previous, timestamp);
    }
    animations.set(key, animation);
    return animation;
  }

  function sampleRaw(animation, timestamp) {
    const p = animationProgress(animation, timestamp);
    return { progress: p, done: p >= 1 };
  }

  function syncTopology(previousNodes, currentNodes, previousEdges, currentEdges, {
    replay = false,
    timestamp = now(),
  } = {}) {
    const currentNodeIds = new Set(currentNodes.map(node => node.id));
    const previousNodeIds = new Set(previousNodes.map(node => node.id));
    const currentEdgeKeys = new Set(currentEdges.map(edgeKey));
    const previousEdgeKeys = new Set(previousEdges.map(edgeKey));

    if (!initialized) {
      initialized = true;
      return;
    }

    if (replay) {
      return;
    }

    const addedNodes = [...currentNodeIds]
      .filter(id => !previousNodeIds.has(id))
      .sort();
    addedNodes.forEach((id, index) => {
      const delayMs = Math.min(index * 38, 380);
      putAnimation(`node:${id}`, {
        kind: 'nodeSpawn',
        entityId: id,
        startedAt: timestamp,
        delayMs,
        durationMs: durationFor('nodeSpawn', reducedMotion),
      });
    });

    for (const node of previousNodes) {
      if (currentNodeIds.has(node.id)) continue;
      const snapshot = snapshotNode(node);
      if (!snapshot) continue;
      ghostNodes.set(node.id, {
        snapshot,
        startedAt: timestamp,
        durationMs: durationFor('nodeExit', reducedMotion),
      });
    }

    const addedSet = new Set(addedNodes);
    for (const edge of currentEdges) {
      const key = edgeKey(edge);
      if (previousEdgeKeys.has(key)) continue;
      const touchesNewNode = addedSet.has(edge.source?.id ?? edge.sourceId) ||
        addedSet.has(edge.target?.id ?? edge.targetId);
      putAnimation(`edge:${key}`, {
        kind: 'edgeBirth',
        entityId: key,
        startedAt: timestamp,
        delayMs: touchesNewNode ? 120 : 0,
        durationMs: durationFor('edgeBirth', reducedMotion),
      });
    }

    for (const edge of previousEdges) {
      const key = edgeKey(edge);
      if (currentEdgeKeys.has(key)) continue;
      const snapshot = snapshotEdge(edge);
      if (!snapshot) continue;
      ghostEdges.set(key, {
        snapshot,
        startedAt: timestamp,
        durationMs: durationFor('edgeExit', reducedMotion),
      });
    }
  }

  function registerRegionEvents(events, {
    replay = false,
    timestamp = now(),
  } = {}) {
    if (replay) return;
    for (const event of events ?? []) {
      if (event.type === 'region-born') {
        putAnimation(`region:${event.label}`, {
          kind: 'regionBirth',
          entityId: event.label,
          startedAt: timestamp,
          durationMs: durationFor('regionBirth', reducedMotion),
          metadata: event,
        });
      } else if (event.type === 'region-disappeared') {
        const shape = lastRegionShapes.get(event.label);
        if (shape) {
          ghostRegions.set(event.label, {
            shape,
            startedAt: timestamp,
            durationMs: durationFor('regionExit', reducedMotion),
          });
        }
      } else if (event.type === 'region-split') {
        const parentShape = lastRegionShapes.get(event.label) ?? null;
        for (const child of event.into ?? []) {
          putAnimation(`region:${child}`, {
            kind: 'regionSplit',
            entityId: child,
            startedAt: timestamp,
            durationMs: durationFor('regionSplit', reducedMotion),
            metadata: { ...event, parentShape },
          });
        }
      } else if (event.type === 'region-merged') {
        const sourceShapes = (event.from ?? [])
          .map(label => lastRegionShapes.get(label))
          .filter(Boolean);
        putAnimation(`region:${event.label}`, {
          kind: 'regionMerge',
          entityId: event.label,
          startedAt: timestamp,
          durationMs: durationFor('regionMerge', reducedMotion),
          metadata: {
            ...event,
            sourceShapes,
            mergedFromShape: averageShape(sourceShapes),
          },
        });
      }
    }
  }

  function nodePresentation(id, timestamp = now()) {
    const animation = animations.get(`node:${id}`);
    if (!animation || !active(animation, timestamp)) {
      if (animation) animations.delete(`node:${id}`);
      return { scale: 1, opacity: 1, pulse: 0 };
    }
    const p = animationProgress(animation, timestamp);
    const eased = easeOutBackSoft(p);
    const scale = lerp(0.12, 1, eased);
    const opacity = easeOutCubic(Math.min(1, p * 1.8));
    const pulseDuration = durationFor('nodePulse', reducedMotion);
    const pulseElapsed = timestamp - animation.startedAt - (animation.delayMs ?? 0);
    const pulse = reducedMotion ? 0 : clamp01(pulseElapsed / Math.max(1, pulseDuration));
    return { scale, opacity, pulse };
  }

  function edgePresentation(edgeOrKey, timestamp = now()) {
    const key = typeof edgeOrKey === 'string' ? edgeOrKey : edgeKey(edgeOrKey);
    const animation = animations.get(`edge:${key}`);
    if (!animation || !active(animation, timestamp)) {
      if (animation) animations.delete(`edge:${key}`);
      return { progress: 1, opacity: 1 };
    }
    const p = animationProgress(animation, timestamp);
    return {
      progress: easeOutCubic(p),
      opacity: easeOutCubic(Math.min(1, p * 1.6)),
    };
  }

  function regionPresentation(label, targetShape, {
    replay = false,
    timestamp = now(),
  } = {}) {
    if (!targetShape?.polygon?.length) return { shape: targetShape, opacity: 1, phase: 'steady' };

    const previousTarget = regionTargets.get(label);
    const existing = animations.get(`region:${label}`);
    const structural = existing && ['regionBirth','regionSplit','regionMerge'].includes(existing.kind);

    if (!structural && previousTarget && shapeDistance(previousTarget, targetShape) > 3.0) {
      const from = lastRegionShapes.get(label) ?? previousTarget;
      putAnimation(`region:${label}`, {
        kind: 'regionMorph',
        entityId: label,
        startedAt: timestamp,
        durationMs: durationFor('regionMorph', reducedMotion, replay),
        metadata: { from },
      });
    }
    regionTargets.set(label, targetShape);

    const animation = animations.get(`region:${label}`);
    let shape = targetShape;
    let opacity = 1;
    let phase = 'steady';

    if (animation && active(animation, timestamp)) {
      const p = animationProgress(animation, timestamp);
      if (animation.kind === 'regionBirth') {
        const eased = easeOutQuint(p);
        shape = scaleRegionShape(targetShape, lerp(0.18, 1, eased));
        opacity = eased;
        phase = 'birth';
      } else if (animation.kind === 'regionMorph') {
        shape = interpolateRegionShape(
          animation.metadata?.from ?? lastRegionShapes.get(label) ?? targetShape,
          targetShape,
          easeInOutCubic(p),
        );
        phase = 'morph';
      } else if (animation.kind === 'regionSplit') {
        const anticipationEnd = 350 / DURATIONS.regionSplit;
        const separationEnd = 1850 / DURATIONS.regionSplit;
        const parent = animation.metadata?.parentShape ?? lastRegionShapes.get(label) ?? targetShape;
        if (p < anticipationEnd) {
          const local = p / anticipationEnd;
          shape = interpolateRegionShape(parent, targetShape, easeInOutCubic(local * 0.18));
          opacity = 1;
          phase = 'split-anticipation';
        } else if (p < separationEnd) {
          const local = (p - anticipationEnd) / (separationEnd - anticipationEnd);
          shape = interpolateRegionShape(parent, targetShape, easeInOutQuint(local));
          opacity = lerp(0.35, 1, easeOutCubic(local));
          phase = 'split-separation';
        } else {
          const local = (p - separationEnd) / (1 - separationEnd);
          shape = interpolateRegionShape(
            interpolateRegionShape(parent, targetShape, 0.94),
            targetShape,
            easeOutCubic(local),
          );
          opacity = 1;
          phase = 'split-settle';
        }
      } else if (animation.kind === 'regionMerge') {
        const attractionEnd = 450 / DURATIONS.regionMerge;
        const fusionEnd = 1600 / DURATIONS.regionMerge;
        const mergedFrom = animation.metadata?.mergedFromShape ??
          lastRegionShapes.get(label) ??
          targetShape;
        if (p < attractionEnd) {
          const local = p / attractionEnd;
          shape = interpolateRegionShape(mergedFrom, targetShape, easeInOutCubic(local * 0.18));
          phase = 'merge-attraction';
        } else if (p < fusionEnd) {
          const local = (p - attractionEnd) / (fusionEnd - attractionEnd);
          shape = interpolateRegionShape(mergedFrom, targetShape, easeInOutQuint(local));
          phase = 'merge-fusion';
        } else {
          const local = (p - fusionEnd) / (1 - fusionEnd);
          shape = interpolateRegionShape(
            interpolateRegionShape(mergedFrom, targetShape, 0.95),
            targetShape,
            easeOutCubic(local),
          );
          phase = 'merge-settle';
        }
      }
    } else if (animation) {
      animations.delete(`region:${label}`);
    }

    lastRegionShapes.set(label, shape);
    return { shape, opacity, phase };
  }

  function ghostNodePresentation(timestamp = now()) {
    const result = [];
    for (const [id, item] of ghostNodes.entries()) {
      const p = clamp01((timestamp - item.startedAt) / Math.max(1, item.durationMs));
      if (p >= 1) {
        ghostNodes.delete(id);
        continue;
      }
      result.push({
        ...item.snapshot,
        opacity: 1 - easeOutCubic(p),
        scale: lerp(1, 0.55, easeInOutCubic(p)),
      });
    }
    return result;
  }

  function ghostEdgePresentation(timestamp = now()) {
    const result = [];
    for (const [key, item] of ghostEdges.entries()) {
      const p = clamp01((timestamp - item.startedAt) / Math.max(1, item.durationMs));
      if (p >= 1) {
        ghostEdges.delete(key);
        continue;
      }
      result.push({
        ...item.snapshot,
        opacity: 1 - easeOutCubic(p),
      });
    }
    return result;
  }

  function ghostRegionPresentation(timestamp = now()) {
    const result = [];
    for (const [label, item] of ghostRegions.entries()) {
      const p = clamp01((timestamp - item.startedAt) / Math.max(1, item.durationMs));
      if (p >= 1) {
        ghostRegions.delete(label);
        continue;
      }
      result.push({
        label,
        shape: scaleRegionShape(item.shape, lerp(1, 0.88, easeInOutCubic(p))),
        opacity: 1 - easeOutCubic(p),
      });
    }
    return result;
  }

  function regionMergeBridges(timestamp = now()) {
    const bridges = [];
    for (const animation of animations.values()) {
      if (animation.kind !== 'regionMerge' || !active(animation, timestamp)) continue;
      const shapes = animation.metadata?.sourceShapes ?? [];
      if (shapes.length < 2) continue;
      const p = animationProgress(animation, timestamp);
      const attractionEnd = 450 / DURATIONS.regionMerge;
      const fusionEnd = 1600 / DURATIONS.regionMerge;
      if (p <= attractionEnd || p >= fusionEnd) continue;
      const local = (p - attractionEnd) / (fusionEnd - attractionEnd);
      const strength = Math.sin(clamp01(local) * Math.PI);
      for (let i = 0; i < shapes.length; i++) {
        for (let j = i + 1; j < shapes.length; j++) {
          bridges.push({
            from: shapes[i],
            to: shapes[j],
            strength,
            label: animation.entityId,
          });
        }
      }
    }
    return bridges;
  }

  function hasActiveAnimations(timestamp = now()) {
    for (const animation of animations.values()) {
      if (active(animation, timestamp)) return true;
    }
    return ghostNodes.size > 0 || ghostEdges.size > 0 || ghostRegions.size > 0;
  }

  function reset() {
    animations.clear();
    ghostNodes.clear();
    ghostEdges.clear();
    ghostRegions.clear();
    lastRegionShapes.clear();
    regionTargets.clear();
    initialized = false;
  }

  return {
    durations: DURATIONS,
    syncTopology,
    registerRegionEvents,
    nodePresentation,
    edgePresentation,
    regionPresentation,
    ghostNodePresentation,
    ghostEdgePresentation,
    ghostRegionPresentation,
    regionMergeBridges,
    hasActiveAnimations,
    reset,
    reducedMotion,
  };
}
