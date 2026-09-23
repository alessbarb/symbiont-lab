import { tel } from './state.js';

/**
 * Apply one lightweight /api/organism event to shared telemetry state.
 * Returns true when a known telemetry type was consumed.
 */
export function applyTelemetryEvent(data) {
  if (!data?.type) return false;

  if (data.type === 'body') {
    tel.tick = data.tick ?? tel.tick;
    tel.metabolicReserve = data.metabolic_reserve ?? tel.metabolicReserve;
    return true;
  }

  if (data.type === 'cognition') {
    tel.tick = data.tick ?? tel.tick;
    tel.schemaConf = data.schema_confidence ?? tel.schemaConf;
    tel.schemaParts = data.schema_parts ?? tel.schemaParts;
    tel.schemaSensory = data.schema_sensory_parts ?? tel.schemaSensory;
    tel.schemaCognitive = data.schema_cognitive_regions ?? tel.schemaCognitive;
    tel.motorOrigin = data.motor_origin ?? tel.motorOrigin;
    tel.predictorCount = data.predictor_count ?? tel.predictorCount;
    tel.sensorimotorPatterns = data.sensorimotor_patterns ?? tel.sensorimotorPatterns;
    tel.motorPrimitives = data.motor_primitives ?? tel.motorPrimitives;
    tel.cognitiveMotorPrimitives = data.cognitive_motor_primitives ?? tel.cognitiveMotorPrimitives;
    tel.motorRepertoireSize = data.motor_repertoire_size ?? tel.motorRepertoireSize;
    tel.recurrentPrimitiveCandidates = data.recurrent_primitive_candidates ?? tel.recurrentPrimitiveCandidates;
    tel.maxPrimitiveSamples = data.max_primitive_samples ?? tel.maxPrimitiveSamples;
    tel.fullCompetenceGateCandidates = data.full_competence_gate_candidates ?? tel.fullCompetenceGateCandidates;
    tel.motorReadoutNodes = data.motor_readout_nodes ?? tel.motorReadoutNodes;
    tel.primitiveReadoutNodes = data.primitive_readout_nodes ?? tel.primitiveReadoutNodes;
    tel.cognitiveMotorOutputEdges = data.cognitive_motor_output_edges ?? tel.cognitiveMotorOutputEdges;
    tel.cognitiveConcepts = data.cognitive_concepts ?? tel.cognitiveConcepts;
    tel.cognitiveReadouts = data.cognitive_readouts ?? tel.cognitiveReadouts;
    tel.predictionError = data.prediction_error ?? tel.predictionError;
    tel.prospective = data.prospective_selected ?? tel.prospective;
    tel.prospectiveEV = data.prospective_expected_value ?? tel.prospectiveEV;
    tel.slmActive = data.slm_active ?? tel.slmActive;
    tel.slmModels = data.slm_models ?? tel.slmModels;
    return true;
  }

  if (data.type === 'vitals') {
    tel.tick = data.tick ?? tel.tick;
    tel.alive = data.alive ?? tel.alive;
    tel.jointMotion = data.joint_motion ?? tel.jointMotion;
    tel.activeEffectors = data.active_effectors ?? tel.activeEffectors;
    tel.resourceDistance = data.resource_distance ?? tel.resourceDistance;
    tel.resourceProgress = data.resource_progress ?? tel.resourceProgress;
    tel.resourceRemaining = data.resource_remaining ?? tel.resourceRemaining;
    tel.absorbedEnergy = data.absorbed_energy ?? tel.absorbedEnergy;
    tel.displacement = data.displacement_from_origin ?? tel.displacement;
    tel.mechanicalWork = data.mechanical_work_joules ?? tel.mechanicalWork;
    tel.metabolicCost = data.metabolic_work_cost ?? tel.metabolicCost;
    return true;
  }

  return false;
}
