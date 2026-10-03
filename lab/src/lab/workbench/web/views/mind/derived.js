import { snap, tel } from './state.js';

export function currentMotorOutputEdges(topology = snap.topology) {
  return (topology?.edges ?? []).filter((edge) =>
    String(edge.targetId ?? '').startsWith('readout_motor:') ||
    String(edge.targetId ?? '').startsWith('readout_primitive:')
  ).length;
}

export function currentPhysiologyState() {
  return String(
    snap.organismState?.state ??
    (tel.alive === false ? 'dead' : 'active')
  ).toLowerCase();
}


export function topologyComponentStats(topology = snap.topology) {
  const nodes = topology?.nodes ?? [];
  const adjacency = new Map(nodes.map((node) => [node.id, new Set()]));
  for (const edge of topology?.edges ?? []) {
    adjacency.get(edge.sourceId)?.add(edge.targetId);
    adjacency.get(edge.targetId)?.add(edge.sourceId);
  }

  const unseen = new Set(nodes.map((node) => node.id));
  const sizes = [];
  while (unseen.size) {
    const seed = unseen.values().next().value;
    unseen.delete(seed);
    const stack = [seed];
    let size = 0;
    while (stack.length) {
      const id = stack.pop();
      size += 1;
      for (const neighbor of adjacency.get(id) ?? []) {
        if (unseen.delete(neighbor)) stack.push(neighbor);
      }
    }
    sizes.push(size);
  }
  sizes.sort((a, b) => b - a);
  return {
    count: sizes.length,
    main: sizes[0] ?? 0,
    isolates: sizes.filter((size) => size === 1).length,
    secondary: sizes.filter((size) => size > 1).slice(1).length,
    sizes,
  };
}
