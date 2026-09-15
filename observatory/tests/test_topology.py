import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "topology.js"


def bounded(raw):
    return call_js(MODULE, "boundedTopology", raw)


VALID_RAW = {
    "genome_id": "genome-abc",
    "kernel_version": "1.0.0",
    "topology_revision": 3,
    "nodes": [
        {"node_id": "n-sense-1", "kind": "sense", "bias": 0.1, "tau": 1.0},
        {"node_id": "n-concept-1", "kind": "concept", "bias": 0.2, "tau": 2.0},
    ],
    "edges": [
        {"source_id": "n-sense-1", "target_id": "n-concept-1", "kind": "excitatory"},
    ],
}


@requires_node
class BoundedTopologyTests(unittest.TestCase):
    def test_renames_wire_fields_to_normalized_shape(self):
        result = bounded(VALID_RAW)
        self.assertEqual(result["genomeId"], "genome-abc")
        self.assertEqual(result["topologyRevision"], 3)
        self.assertEqual(result["nodes"], [
            {"id": "n-sense-1", "kind": "sense"},
            {"id": "n-concept-1", "kind": "concept"},
        ])
        self.assertEqual(result["edges"], [
            {"sourceId": "n-sense-1", "targetId": "n-concept-1", "kind": "excitatory"},
        ])

    def test_drops_node_with_unknown_kind(self):
        raw = {**VALID_RAW, "nodes": [{"node_id": "x", "kind": "not-a-real-kind", "bias": 0, "tau": 1}]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [])

    def test_drops_duplicate_node_id_keeping_the_first(self):
        raw = {**VALID_RAW, "nodes": [
            {"node_id": "dup", "kind": "sense", "bias": 0, "tau": 1},
            {"node_id": "dup", "kind": "readout", "bias": 0, "tau": 1},
        ]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [{"id": "dup", "kind": "sense"}])

    def test_caps_nodes_at_128(self):
        raw = {**VALID_RAW, "nodes": [
            {"node_id": f"n{i}", "kind": "sense", "bias": 0, "tau": 1} for i in range(140)
        ]}
        result = bounded(raw)
        self.assertEqual(len(result["nodes"]), 128)

    def test_caps_edges_at_1024(self):
        raw = {**VALID_RAW, "edges": [
            {"source_id": "a", "target_id": "b", "kind": "excitatory"} for _ in range(1100)
        ]}
        result = bounded(raw)
        self.assertEqual(len(result["edges"]), 1024)

    def test_edge_with_unresolvable_endpoint_is_still_kept(self):
        raw = {**VALID_RAW, "edges": [
            {"source_id": "no-such-node", "target_id": "also-missing", "kind": "excitatory"},
        ]}
        result = bounded(raw)
        self.assertEqual(len(result["edges"]), 1)

    def test_missing_genome_id_returns_none(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "genome_id"}
        self.assertIsNone(bounded(raw))

    def test_missing_or_malformed_input_returns_none(self):
        self.assertIsNone(bounded(None))
        self.assertIsNone(bounded("not an object"))
        self.assertIsNone(bounded({}))

    def test_non_integer_topology_revision_returns_none(self):
        # 3.8 is a float, not the integer the schema requires -- accepting it
        # via a lossy Number.parseInt would be exactly the leniency this
        # function exists to refuse.
        raw = {**VALID_RAW, "topology_revision": 3.8}
        self.assertIsNone(bounded(raw))

    def test_missing_nodes_array_returns_none(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "nodes"}
        self.assertIsNone(bounded(raw))

    def test_missing_edges_array_returns_none(self):
        raw = {k: v for k, v in VALID_RAW.items() if k != "edges"}
        self.assertIsNone(bounded(raw))

    def test_node_missing_bias_or_tau_is_dropped(self):
        raw = {**VALID_RAW, "nodes": [
            {"node_id": "no-bias", "kind": "sense", "tau": 1.0},
            {"node_id": "no-tau", "kind": "sense", "bias": 0.1},
        ]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [])

    def test_node_with_tau_out_of_range_is_dropped(self):
        raw = {**VALID_RAW, "nodes": [{"node_id": "bad-tau", "kind": "sense", "bias": 0, "tau": 15.0}]}
        result = bounded(raw)
        self.assertEqual(result["nodes"], [])


if __name__ == "__main__":
    unittest.main()
