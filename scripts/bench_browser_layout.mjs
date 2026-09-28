#!/usr/bin/env node
import { performance } from 'node:perf_hooks';
import {
  forEachNearbyPair2D,
  forEachNearbyPair3D,
} from '../src/symbiont_lab/workbench/web/views/mind/spatial-index.js';

function nodes2D(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: `node.${index}`,
    x: ((index * 97) % 2000) - 1000,
    y: ((index * 193) % 1400) - 700,
  }));
}

function nodes3D(count) {
  const nodes = Array.from({ length: count }, (_, index) => ({ id: `node.${index}` }));
  const positions = new Map(nodes.map((node, index) => [
    node.id,
    {
      x: ((index * 97) % 1200) - 600,
      y: ((index * 193) % 1000) - 500,
      z: ((index * 389) % 900) - 450,
    },
  ]));
  return [nodes, positions];
}

function allPairs2D(nodes, radius) {
  let pairs = 0;
  const r2 = radius * radius;
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[j].x - nodes[i].x;
      const dy = nodes[j].y - nodes[i].y;
      if (dx * dx + dy * dy <= r2) pairs++;
    }
  }
  return pairs;
}

function main() {
  const count = Number(process.argv[2] ?? 2000);
  const n2 = nodes2D(count);

  let started = performance.now();
  const referencePairs = allPairs2D(n2, 520);
  const referenceMs = performance.now() - started;

  let indexedPairs = 0;
  started = performance.now();
  forEachNearbyPair2D(n2, 180, 520, () => { indexedPairs++; });
  const indexed2DMs = performance.now() - started;

  const [n3, positions] = nodes3D(count);
  let indexed3DPairs = 0;
  started = performance.now();
  forEachNearbyPair3D(n3, positions, 96, 288, () => { indexed3DPairs++; });
  const indexed3DMs = performance.now() - started;

  if (indexedPairs !== referencePairs) {
    throw new Error(`2D spatial index mismatch: ${indexedPairs} != ${referencePairs}`);
  }

  console.log(JSON.stringify({
    nodes: count,
    reference_all_pairs_2d_ms: Number(referenceMs.toFixed(3)),
    indexed_2d_ms: Number(indexed2DMs.toFixed(3)),
    indexed_3d_ms: Number(indexed3DMs.toFixed(3)),
    exact_2d_pairs: indexedPairs,
    local_3d_pairs: indexed3DPairs,
    speedup_2d: Number((referenceMs / Math.max(indexed2DMs, 1e-9)).toFixed(3)),
  }, null, 2));
}

main();
