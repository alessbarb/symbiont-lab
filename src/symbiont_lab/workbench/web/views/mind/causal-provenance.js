/**
 * Read-only causal provenance queries for the Mind inspector.
 *
 * This module never derives organism knowledge. It asks the local Lab server
 * for the durable causal journal behind a selected organism-owned reference.
 */

const KIND_BY_NODE = Object.freeze({
  action_intent: 'intent',
  motor_competence: 'competence',
  effect: 'effect',
  action_dimension: 'dimension',
  intervention_signature: 'intervention',
});

export function provenanceRefForNode(node) {
  if (!node?.id) return null;
  const kind = KIND_BY_NODE[node.kind];
  return kind ? { kind, id: String(node.id) } : null;
}

export async function fetchCausalProvenance(node, { depth = 12, signal = null } = {}) {
  const ref = provenanceRefForNode(node);
  if (!ref) return { supported: false, ref: null, payload: null };
  const params = new URLSearchParams({
    kind: ref.kind,
    id: ref.id,
    depth: String(Math.max(1, Math.min(24, Number(depth) || 12))),
  });
  const response = await fetch(`/api/provenance/why?${params.toString()}`, {
    cache: 'no-store',
    signal,
  });
  if (response.status === 404 || response.status === 503) {
    return { supported: true, ref, payload: null };
  }
  if (!response.ok) {
    throw new Error(`provenance query failed (${response.status})`);
  }
  return { supported: true, ref, payload: await response.json() };
}

export function provenanceTreeRows(tree, limit = 24) {
  const rows = [];
  const walk = (node, depth) => {
    if (!node || rows.length >= limit) return;
    const ref = Array.isArray(node.ref) ? node.ref : ['unknown', 'unknown'];
    rows.push({
      depth,
      kind: String(ref[0] ?? 'unknown'),
      id: String(ref[1] ?? 'unknown'),
      root: Boolean(node.root),
      repeated: Boolean(node.repeated),
      truncated: Boolean(node.truncated),
      event: node.event ?? null,
    });
    for (const cause of node.causes ?? []) walk(cause, depth + 1);
  };
  walk(tree, 0);
  return rows;
}
