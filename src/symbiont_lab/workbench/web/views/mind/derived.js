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
