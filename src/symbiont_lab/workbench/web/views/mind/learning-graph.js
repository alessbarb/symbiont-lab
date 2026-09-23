/**
 * Build the complete learned-structure view used by the Cognition Map.
 *
 * CognitiveGraph nodes/edges remain canonical. Motor primitives and learned
 * actuator/effect evidence are appended as organism-owned learning layers.
 * Optional receptor nodes are observer-only physical bindings derived from
 * Observatory semantics and never become organism-owned cognition.
 */

function finite(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function primitiveActuators(primitive) {
  const ids = new Set();
  for (const step of primitive?.sequence ?? []) {
    for (const item of step ?? []) {
      if (Array.isArray(item) && item.length >= 2 && finite(item[1], 0) > 0) {
        ids.add(String(item[0]));
      }
    }
  }
  return [...ids].sort();
}

export function augmentLearnedGraph(
  topology,
  sensorimotor,
  observerSemantics,
  prospectiveAgency = null,
  { includePhysicalIO = false } = {},
) {
  const baseNodes = (topology?.nodes ?? []).map(node => ({ ...node }));
  const baseEdges = (topology?.edges ?? []).map(edge => ({ ...edge }));
  const nodes = [...baseNodes];
  const edges = [...baseEdges];
  const ids = new Set(nodes.map(node => node.id));

  const primitives = Array.isArray(sensorimotor?.motor_primitives)
    ? sensorimotor.motor_primitives
    : [];
  const actuatorEvidence = Array.isArray(sensorimotor?.actuator_evidence)
    ? sensorimotor.actuator_evidence
    : [];
  const activeRepertoire = new Set(sensorimotor?.active_motor_repertoire ?? []);
  const motorSemantics = observerSemantics?.motor ?? {};
  const replayId = sensorimotor?.replay_primitive_id ?? null;
  const prospectiveId = prospectiveAgency?.action_id ?? null;

  if (includePhysicalIO) {
    const sensorySemantics = observerSemantics?.sensory ?? {};
    for (const [senseId, semantic] of Object.entries(sensorySemantics)) {
      if (!ids.has(senseId)) continue;
      const sourceIds = Array.isArray(semantic?.sourceIds)
        ? semantic.sourceIds
        : Array.isArray(semantic?.source_ids)
          ? semantic.source_ids
          : [];
      for (const sourceIdRaw of sourceIds) {
        const sourceId = String(sourceIdRaw ?? '').trim();
        if (!sourceId) continue;
        const receptorId = `receptor:${sourceId}`;
        if (!ids.has(receptorId)) {
          nodes.push({
            id: receptorId,
            kind: 'receptor',
            learnedLayer: 'physical',
            observerDerived: true,
            physicalSourceId: sourceId,
            observerLabel: sourceId,
          });
          ids.add(receptorId);
        }
        edges.push({
          sourceId: receptorId,
          targetId: senseId,
          kind: 'sensory_input',
          learnedLayer: 'physical',
          observerDerived: true,
        });
      }
    }
  }

  const ensureActuator = actuatorId => {
    const id = String(actuatorId);
    if (ids.has(id)) return;
    const semantic = motorSemantics[id] ?? null;
    nodes.push({
      id,
      kind: 'actuator',
      learnedLayer: 'motor',
      activeRepertoire: activeRepertoire.has(id),
      observerLabel: semantic?.observerSummary ?? null,
      effectorId: semantic?.effectorId ?? null,
      joint: semantic?.joint ?? null,
      direction: semantic?.direction ?? null,
    });
    ids.add(id);
  };

  for (const state of actuatorEvidence) {
    const actuatorId = String(state?.actuator_id ?? '');
    if (!actuatorId) continue;
    ensureActuator(actuatorId);
    const node = nodes.find(item => item.id === actuatorId);
    if (node) {
      node.effectStrength = finite(state.effect_strength, 0);
      node.activations = finite(state.activations, 0);
      node.activeRepertoire = state.state === 'active' || activeRepertoire.has(actuatorId);
      node.causalRelationCount = (state.relations ?? []).length;
    }
    for (const relation of state.relations ?? []) {
      const perceptId = String(relation?.percept_id ?? '');
      if (!perceptId || !ids.has(perceptId)) continue;
      edges.push({
        sourceId: actuatorId,
        targetId: perceptId,
        kind: 'causal_effect',
        learnedLayer: 'motor',
        correlation: finite(relation.correlation, 0),
        samples: finite(relation.samples, 0),
      });
    }
  }

  for (const primitive of primitives) {
    const primitiveId = String(primitive?.primitive_id ?? '');
    if (!primitiveId) continue;
    const nodeId = `motor_primitive:${primitiveId}`;
    const actuators = primitiveActuators(primitive);
    const observerParts = [...new Set(
      actuators
        .map(actuatorId => motorSemantics[actuatorId]?.joint)
        .filter(Boolean)
    )];
    nodes.push({
      id: nodeId,
      kind: 'motor_primitive',
      learnedLayer: 'motor',
      primitiveId,
      observerLabel: observerParts.length
        ? `${observerParts.slice(0, 3).join(' + ')}${observerParts.length > 3 ? ` +${observerParts.length - 3}` : ''} motor pattern`
        : null,
      samples: finite(primitive.samples, 0),
      controllability: finite(primitive.controllability, 0),
      directionalConsistency: finite(primitive.directional_consistency, 0),
      effectMean: finite(primitive.effect_mean, 0),
      effectVariance: finite(primitive.effect_variance, 0),
      durationTicks: (primitive.sequence ?? []).length,
      cognitive: Boolean(primitive.cognitive),
      replayActive: replayId === primitiveId,
      prospectiveSelected: prospectiveId === primitiveId,
      actuatorIds: actuators,
    });
    ids.add(nodeId);

    const readoutId = `readout_primitive:${primitiveId}`;
    if (ids.has(readoutId)) {
      edges.push({
        sourceId: readoutId,
        targetId: nodeId,
        kind: 'invokes',
        learnedLayer: 'motor',
      });
    }

    for (const actuatorId of actuators) {
      ensureActuator(actuatorId);
      edges.push({
        sourceId: nodeId,
        targetId: actuatorId,
        kind: 'motor_component',
        learnedLayer: 'motor',
      });
    }
  }

  for (const actuatorId of activeRepertoire) {
    ensureActuator(actuatorId);
    const readoutId = `readout_motor:${actuatorId}`;
    if (ids.has(readoutId)) {
      edges.push({
        sourceId: readoutId,
        targetId: String(actuatorId),
        kind: 'invokes',
        learnedLayer: 'motor',
      });
    }
  }

  return {
    nodes,
    edges,
    counts: {
      cognitive: baseNodes.length,
      primitives: primitives.length,
      cognitivePrimitives: primitives.filter(item => item?.cognitive).length,
      receptors: nodes.filter(node => node.kind === 'receptor').length,
      actuators: nodes.filter(node => node.kind === 'actuator').length,
      causalEffects: edges.filter(edge => edge.kind === 'causal_effect').length,
      cognitiveMotorLinks: edges.filter(edge => edge.kind === 'invokes').length,
    },
  };
}
