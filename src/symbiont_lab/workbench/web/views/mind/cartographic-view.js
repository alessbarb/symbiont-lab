/**
 * Progressive-disclosure projection for the Cognition Map.
 *
 * Physical actuators remain part of the sensorimotor learning data but are not
 * projected as cognition-map nodes. Motor primitives preserve a collapsed
 * degree so the map can still show that a learned capability has physical
 * composition without drawing the physical substrate itself.
 */

export function cartographicGraph(
  nodes,
  edges,
  selectedNodeId = null,
  viewMode = 'full',
) {
  void selectedNodeId;

  const collapsedMotorDegree = new Map();
  for (const edge of edges) {
    if (edge.kind !== 'motor_component') continue;
    collapsedMotorDegree.set(
      edge.sourceId,
      (collapsedMotorDegree.get(edge.sourceId) ?? 0) + 1,
    );
  }

  const visibleNodes = nodes
    .filter(node => node.kind !== 'actuator')
    .map(node => ({
      ...node,
      collapsedMotorDegree: collapsedMotorDegree.get(node.id) ?? 0,
    }));
  const keep = new Set(visibleNodes.map(node => node.id));

  const visibleEdges = edges.filter(edge => {
    if (!keep.has(edge.sourceId) || !keep.has(edge.targetId)) return false;
    return edge.kind !== 'motor_component' && edge.kind !== 'causal_effect';
  });

  return {
    nodes: visibleNodes,
    edges: visibleEdges,
    hidden: {
      actuators: nodes.filter(node => node.kind === 'actuator').length,
      motorEdges: edges.filter(edge =>
        edge.kind === 'causal_effect' || edge.kind === 'motor_component'
      ).length,
    },
    preservedMotorCapabilities: visibleNodes.filter(node =>
      node.kind === 'motor_primitive' &&
      node.collapsedMotorDegree > 0
    ).length,
    viewMode,
  };
}
