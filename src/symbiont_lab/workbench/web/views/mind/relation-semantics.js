/**
 * Cognitive Atlas relation semantics.
 *
 * The Atlas can render several kinds of organism-owned relations at once, but
 * not every relation defines persistent cognitive structure.  These helpers
 * keep presentation/layout code from accidentally promoting evidence or
 * episode overlays into topology.
 */

const NON_STRUCTURAL_KINDS = new Set([
  'causal_estimate',
  'affords',
  'intends_with',
  'anticipates',
  'causal_effect',
  'motor_component',
]);

export function isStructuralAtlasEdge(edge) {
  if (!edge) return false;
  if (NON_STRUCTURAL_KINDS.has(edge.kind)) return false;
  if (edge.relation_class === 'causal_model') return false;
  return true;
}

export function relationLayer(edge) {
  if (!edge) return 'unknown';
  if (edge.kind === 'causal_estimate' || edge.relation_class === 'causal_model') {
    return 'causal-evidence';
  }
  if (['affords', 'intends_with', 'anticipates'].includes(edge.kind)) {
    return 'executive-overlay';
  }
  if (['causal_effect', 'motor_component'].includes(edge.kind)) {
    return 'physical-learning';
  }
  return 'structure';
}
