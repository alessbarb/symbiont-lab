import { snap } from './state.js';

/**
 * Apply one rich Mind snapshot to the shared passive view state.
 * Returns false only when the payload carries no usable snapshot.
 */
export function applyMindSnapshot(raw) {
  const source = raw?.snapshot ?? raw;
  if (!source) return false;

  snap.senses = source.senses ?? source.percepts ?? [];
  snap.beliefs = source.beliefs ?? [];
  snap.cognition = source.cognition ?? null;
  snap.topology = source.topology ?? null;
  snap.selfModel = source.self_model ?? source.selfModel ?? null;
  snap.bodySchema = source.body_schema ?? source.bodySchema ?? null;
  snap.sensoryPhenotype = source.sensory_phenotype ?? source.sensoryPhenotype ?? null;
  snap.sensoryDevelopment = source.sensory_development ?? source.sensoryDevelopment ?? [];
  snap.sensoryRelations = source.sensory_relations ?? source.sensoryRelations ?? [];
  snap.metabolism = source.metabolism ?? null;
  snap.degradation = source.degradation ?? null;
  snap.development = source.development ?? null;
  snap.sampling = source.sampling ?? null;
  snap.details = source.details ?? null;
  snap.displayId = source.display_id ?? source.displayId ?? null;
  snap.instanceId = source.instance_id ?? source.instanceId ?? null;
  snap.organismState = source.organism_state ?? source.organismState ?? null;
  snap.observerAnalysis = source.observer_analysis ?? source.observerAnalysis ?? null;
  snap.observerSemantics = source.observer_semantics ?? source.observerSemantics ?? null;
  snap.provenance = source.provenance ?? null;
  snap.sensorimotor = source.sensorimotor ?? null;
  snap.embodiment = source.embodiment ?? null;
  snap.outcome = source.outcome ?? null;
  return true;
}
