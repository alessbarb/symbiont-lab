const NODE_KINDS = new Set(["sense", "concept", "state", "predictor", "gate", "readout"]);
const EDGE_KINDS = new Set(["excitatory", "inhibitory", "predictive", "gating"]);

function boundedTopology(raw) {
  if (!raw || typeof raw !== "object") return null;
  if (typeof raw.genome_id !== "string" || raw.genome_id.length === 0 || raw.genome_id.length > 72) return null;
  if (typeof raw.kernel_version !== "string" || raw.kernel_version.length === 0 || raw.kernel_version.length > 32) return null;
  if (!Number.isInteger(raw.topology_revision) || raw.topology_revision < 0) return null;
  // topology.schema.json requires nodes/edges as arrays (not optional) --
  // this is the real client-side defensive boundary, since the server only
  // checks isinstance(dict) before forwarding whatever the topology file
  // contains, so a missing/malformed key here must reject the whole payload
  // rather than silently substituting an empty array.
  if (!Array.isArray(raw.nodes) || !Array.isArray(raw.edges)) return null;

  const seenIds = new Set();
  const nodes = [];
  raw.nodes.slice(0, 128).forEach(node => {
    if (!node || typeof node.node_id !== "string" || node.node_id.length === 0 || node.node_id.length > 128) return;
    if (!NODE_KINDS.has(node.kind)) return;
    if (!Number.isFinite(node.bias)) return;
    if (!Number.isFinite(node.tau) || node.tau < 0.1 || node.tau > 10.0) return;
    if (seenIds.has(node.node_id)) return;
    seenIds.add(node.node_id);
    nodes.push({ id: node.node_id, kind: node.kind, bias: node.bias, tau: node.tau });
  });

  const edges = [];
  raw.edges.slice(0, 1024).forEach(edge => {
    if (!edge) return;
    const sourceId = edge.source_id;
    const targetId = edge.target_id;
    if (typeof sourceId !== "string" || sourceId.length === 0 || sourceId.length > 128) return;
    if (typeof targetId !== "string" || targetId.length === 0 || targetId.length > 128) return;
    if (!EDGE_KINDS.has(edge.kind)) return;
    edges.push({ sourceId, targetId, kind: edge.kind });
  });

  return { genomeId: raw.genome_id, topologyRevision: raw.topology_revision, nodes, edges };
}

export { boundedTopology };
