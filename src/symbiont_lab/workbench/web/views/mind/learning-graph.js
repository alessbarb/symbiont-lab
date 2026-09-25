/**
 * Build the complete learned-structure view used by the Cognition Map.
 *
 * CognitiveGraph nodes/edges remain canonical. Motor primitives and learned
 * actuator/effect evidence are appended as organism-owned learning layers.
 * Observer semantics are annotations only.
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
  motorKnowledge = null,
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

  const competences = Array.isArray(motorKnowledge?.competences) ? motorKnowledge.competences : [];
  const effects = Array.isArray(motorKnowledge?.effects) ? motorKnowledge.effects : [];
  const bindings = Array.isArray(motorKnowledge?.bindings) ? motorKnowledge.bindings : [];
  const showEmbodiment = Boolean(motorKnowledge?.showEmbodiment);

  const knownEffectIds = new Set();
  for (const effect of effects) {
    const effectId = String(effect?.effect_id ?? '');
    if (!effectId || ids.has(effectId)) continue;
    nodes.push({ id: effectId, kind: 'effect', learnedLayer: 'motor', support: finite(effect.support, 0), confidence: finite(effect.confidence, 0) });
    ids.add(effectId);
    knownEffectIds.add(effectId);
  }

  const knownCompetenceIds = new Set();
  const knownControllerIds = new Set();
  for (const competence of competences) {
    const competenceId = String(competence?.competence_id ?? '');
    if (!competenceId || ids.has(competenceId)) continue;
    nodes.push({
      id: competenceId,
      kind: 'motor_competence',
      learnedLayer: 'motor',
      maturity: competence.maturity ?? null,
      support: finite(competence.support, 0),
      controllability: finite(competence.controllability, 0),
    });
    ids.add(competenceId);
    knownCompetenceIds.add(competenceId);
    const effectId = String(competence?.effect_id ?? '');
    if (effectId && knownEffectIds.has(effectId)) {
      edges.push({ sourceId: competenceId, targetId: effectId, kind: 'produces', learnedLayer: 'motor' });
    }
    // Controller is distinct from competence (spec Sec 12): only the
    // opaque id/strategy ref the organism itself recorded, no fabricated
    // strategy classification.
    const controllerId = String(competence?.controller_id ?? '');
    if (controllerId) {
      if (!ids.has(controllerId)) {
        nodes.push({
          id: controllerId,
          kind: 'controller',
          learnedLayer: 'motor',
          strategyRef: competence.controller_strategy_ref ?? null,
        });
        ids.add(controllerId);
        knownControllerIds.add(controllerId);
      }
      edges.push({ sourceId: competenceId, targetId: controllerId, kind: 'requires', learnedLayer: 'motor' });
    }
  }

  if (showEmbodiment) {
    for (const binding of bindings) {
      const competenceId = String(binding?.competence_id ?? '');
      if (!competenceId) continue;
      const bindingId = `binding.${competenceId}`;
      if (!ids.has(bindingId)) {
        nodes.push({
          id: bindingId,
          kind: 'embodiment_binding',
          learnedLayer: 'embodiment',
          surfaceFingerprint: binding.surface_fingerprint ?? null,
          reliability: finite(binding.reliability, 0),
          controllability: finite(binding.controllability, 0),
        });
        ids.add(bindingId);
      }
      if (knownCompetenceIds.has(competenceId)) {
        edges.push({ sourceId: bindingId, targetId: competenceId, kind: 'bound_to', learnedLayer: 'embodiment' });
      }
    }
  }

  // Body schema (spec Sec 17): cognitive body-model knowledge, not anatomy.
  // Always shown in Relational -- it is organism-owned knowledge, not a
  // physical actuator, so it does not wait behind Show embodiment.
  const bodySchemaParts = Array.isArray(motorKnowledge?.bodySchema?.parts) ? motorKnowledge.bodySchema.parts : [];
  const bodySchemaDependencies = Array.isArray(motorKnowledge?.bodySchema?.dependencies) ? motorKnowledge.bodySchema.dependencies : [];
  const knownBodySchemaIds = new Set();
  for (const part of bodySchemaParts) {
    const partId = String(part?.part_id ?? '');
    if (!partId || ids.has(partId)) continue;
    nodes.push({
      id: partId,
      kind: 'body_schema',
      learnedLayer: 'body_schema',
      subkind: part.kind ?? null,
      confidenceClass: part.confidence_class ?? null,
      maturityClass: part.maturity_class ?? null,
    });
    ids.add(partId);
    knownBodySchemaIds.add(partId);
  }
  for (const dependency of bodySchemaDependencies) {
    const sourceId = String(dependency?.source_id ?? '');
    const targetId = String(dependency?.target_id ?? '');
    if (!knownBodySchemaIds.has(sourceId) || !knownBodySchemaIds.has(targetId)) continue;
    edges.push({
      sourceId,
      targetId,
      kind: dependency.relation ?? 'correlates',
      learnedLayer: 'body_schema',
    });
  }

  return {
    nodes,
    edges,
    counts: {
      cognitive: baseNodes.length,
      primitives: primitives.length,
      cognitivePrimitives: primitives.filter(item => item?.cognitive).length,
      actuators: nodes.filter(node => node.kind === 'actuator').length,
      causalEffects: edges.filter(edge => edge.kind === 'causal_effect').length,
      cognitiveMotorLinks: edges.filter(edge => edge.kind === 'invokes').length,
      motorCompetences: knownCompetenceIds.size,
      embodimentBindings: nodes.filter(node => node.kind === 'embodiment_binding').length,
      controllers: knownControllerIds.size,
      bodySchemaParts: knownBodySchemaIds.size,
    },
  };
}
