const CENTER = { x: 450, y: 360 };
const VERTICAL_SQUASH = 0.82;
const BOUNDARY_POINTS = 10;
const BASE_RADIUS = 230;
const BOUNDARY_JITTER = 55;
const INTERIOR_MAX_RADIUS = 100; // conservative: worst-case boundary radius is BASE_RADIUS - BOUNDARY_JITTER = 175
const INPUT_ANCHOR_X = 75;
const INPUT_ANCHOR_TOP = 140;
const INPUT_ANCHOR_BOTTOM = 580;
const RECEPTOR_ARC_START = (130 * Math.PI) / 180;
const RECEPTOR_ARC_END = (230 * Math.PI) / 180;

function fnv1aHash(text) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function quantize(value) {
  return Number(value.toFixed(2));
}

function pointOnEllipse(center, angle, radius) {
  return {
    x: quantize(center.x + Math.cos(angle) * radius),
    y: quantize(center.y + Math.sin(angle) * radius * VERTICAL_SQUASH),
  };
}

function generateBoundaryPoints(identitySeed) {
  const rng = mulberry32(fnv1aHash(identitySeed));
  const points = [];
  for (let i = 0; i < BOUNDARY_POINTS; i++) {
    const angle = (i / BOUNDARY_POINTS) * Math.PI * 2;
    const radius = BASE_RADIUS + (rng() * 2 - 1) * BOUNDARY_JITTER;
    points.push(pointOnEllipse(CENTER, angle, radius));
  }
  return points;
}

function segmentControlPoints(points, i) {
  // The exact same p1/c1/c2/p2 quadruple both the rendered SVG path (below)
  // and receptor placement (evaluateBoundaryAt) use -- factored out once so
  // the two can never drift apart into "the curve users see" vs. "the curve
  // receptors think they're on" (the bug this refactor fixes).
  const n = points.length;
  const p0 = points[(i - 1 + n) % n];
  const p1 = points[i];
  const p2 = points[(i + 1) % n];
  const p3 = points[(i + 2) % n];
  return {
    p1,
    p2,
    c1: { x: quantize(p1.x + (p2.x - p0.x) / 6), y: quantize(p1.y + (p2.y - p0.y) / 6) },
    c2: { x: quantize(p2.x - (p3.x - p1.x) / 6), y: quantize(p2.y - (p3.y - p1.y) / 6) },
  };
}

function boundaryPathFromPoints(points) {
  const n = points.length;
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < n; i++) {
    const { c1, c2, p2 } = segmentControlPoints(points, i);
    d += ` C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${p2.x} ${p2.y}`;
  }
  return `${d} Z`;
}

function evaluateBoundaryAt(points, u) {
  // u in [0, 1) parameterizes the whole closed curve; since the control
  // points are placed at evenly-spaced angles, u * 2*PI is also this
  // point's angle. Evaluates the exact cubic Bezier for the matching
  // segment -- this is the same curve the SVG `C` command draws, not an
  // approximation of it, so a receptor placed here is guaranteed to lie
  // exactly on the rendered boundary.
  const n = points.length;
  const scaled = (((u % 1) + 1) % 1) * n;
  const i = Math.floor(scaled) % n;
  const t = scaled - Math.floor(scaled);
  const { p1, c1, c2, p2 } = segmentControlPoints(points, i);
  const mt = 1 - t;
  const x = mt ** 3 * p1.x + 3 * mt ** 2 * t * c1.x + 3 * mt * t ** 2 * c2.x + t ** 3 * p2.x;
  const y = mt ** 3 * p1.y + 3 * mt ** 2 * t * c1.y + 3 * mt * t ** 2 * c2.y + t ** 3 * p2.y;
  return { x: quantize(x), y: quantize(y) };
}

function compareStrings(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function placeInterior(identitySeed, nodeId) {
  const rng = mulberry32(fnv1aHash(`${identitySeed}:${nodeId}`));
  const angle = rng() * Math.PI * 2;
  const radius = rng() * INTERIOR_MAX_RADIUS;
  return pointOnEllipse(CENTER, angle, radius);
}

function projectPhenotypeMorphology({
  identitySeed,
  percepts = [],
  hasCurrentTopology = false,
  structuralSenses = [],
  internalNodes = [],
  edges = [],
  topologyHealth = null,
  recovering = false,
  frozen = false,
}) {
  const boundaryPoints = generateBoundaryPoints(identitySeed);
  const boundaryPath = boundaryPathFromPoints(boundaryPoints);

  const sortedStructuralSenses = [...structuralSenses].sort((a, b) => compareStrings(a.id, b.id));
  const sortedInternalNodes = [...internalNodes].sort((a, b) => compareStrings(a.id, b.id));
  const sortedEdges = [...edges].sort((a, b) =>
    compareStrings(a.sourceId, b.sourceId) || compareStrings(a.targetId, b.targetId) || compareStrings(a.kind, b.kind));

  // hasCurrentTopology (not "does structuralSenses happen to be empty") is
  // what decides the fallback: a real graph with zero SENSE nodes must
  // render zero receptors, not silently borrow percept ids as fake organs.
  // Only the *absence* of any current topology falls back to percepts.
  const receptorSource = hasCurrentTopology
    ? sortedStructuralSenses
    : [...percepts].sort((a, b) => compareStrings(a.id, b.id)).map(p => ({ id: p.id, kind: "sense" }));

  const externalInputAnchors = [];
  const receptorAnchors = [];
  const anchorById = new Map();
  const count = receptorSource.length;

  receptorSource.forEach((node, index) => {
    const inputY = count <= 1
      ? (INPUT_ANCHOR_TOP + INPUT_ANCHOR_BOTTOM) / 2
      : INPUT_ANCHOR_TOP + (index * (INPUT_ANCHOR_BOTTOM - INPUT_ANCHOR_TOP)) / (count - 1);
    externalInputAnchors.push({ id: node.id, x: INPUT_ANCHOR_X, y: quantize(inputY) });

    const angle = count <= 1
      ? (RECEPTOR_ARC_START + RECEPTOR_ARC_END) / 2
      : RECEPTOR_ARC_START + (index / (count - 1)) * (RECEPTOR_ARC_END - RECEPTOR_ARC_START);
    const u = angle / (Math.PI * 2);
    const receptorAnchor = { id: node.id, kind: "sense", ...evaluateBoundaryAt(boundaryPoints, u) };
    receptorAnchors.push(receptorAnchor);
    anchorById.set(node.id, receptorAnchor);
  });

  const internalAnchors = sortedInternalNodes.map(node => {
    const anchor = { id: node.id, kind: node.kind, ...placeInterior(identitySeed, node.id) };
    anchorById.set(node.id, anchor);
    return anchor;
  });

  const fibres = [];
  sortedEdges.forEach(edge => {
    const from = anchorById.get(edge.sourceId);
    const to = anchorById.get(edge.targetId);
    if (!from || !to) return;
    fibres.push({ sourceId: edge.sourceId, targetId: edge.targetId, kind: edge.kind, x1: from.x, y1: from.y, x2: to.x, y2: to.y });
  });

  const presentation = {
    boundaryTension: (recovering || topologyHealth === "recovering" || topologyHealth === "degenerate") ? 0.7 : 1,
    desaturated: frozen === true,
    reducedMotion: frozen === true,
  };

  return { boundaryPath, externalInputAnchors, receptorAnchors, internalAnchors, fibres, presentation };
}

export { projectPhenotypeMorphology };
