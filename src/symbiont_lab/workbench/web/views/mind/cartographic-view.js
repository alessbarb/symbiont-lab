/**
 * Progressive-disclosure projection for the Cognition Map.
 *
 * The complete learned graph remains available. The global cartography hides
 * low-level motor substrate until a motor primitive is selected.
 */

export function cartographicGraph(nodes, edges, selectedNodeId = null) {
  const selected = nodes.find(node => node.id === selectedNodeId) ?? null;
  const expandedActuators = new Set();

  if (selected?.kind === 'motor_primitive') {
    for (const id of selected.actuatorIds ?? []) expandedActuators.add(String(id));
  } else if (selected?.kind === 'actuator') {
    expandedActuators.add(String(selected.id));
  }

  const visibleNodes = nodes.filter(node =>
    node.kind !== 'actuator' || expandedActuators.has(node.id)
  );
  const keep = new Set(visibleNodes.map(node => node.id));

  const visibleEdges = edges.filter(edge => {
    if (!keep.has(edge.sourceId) || !keep.has(edge.targetId)) return false;
    if (edge.kind === 'causal_effect' || edge.kind === 'motor_component') {
      return expandedActuators.has(edge.sourceId) || expandedActuators.has(edge.targetId);
    }
    return true;
  });

  return {
    nodes: visibleNodes,
    edges: visibleEdges,
    hidden: {
      actuators: nodes.filter(node => node.kind === 'actuator' && !keep.has(node.id)).length,
      motorEdges: edges.filter(edge =>
        (edge.kind === 'causal_effect' || edge.kind === 'motor_component') &&
        !(keep.has(edge.sourceId) && keep.has(edge.targetId))
      ).length,
    },
    expandedMotor: expandedActuators.size > 0,
  };
}
