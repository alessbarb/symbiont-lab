import unittest

from observatory._node_harness import ROOT, call_js, requires_node

MODULE = ROOT / "projection" / "morphology.js"


def build_worker3_topology():
    structural_senses = [{"id": f"sense-{i:02d}", "kind": "sense"} for i in range(58)]
    internal_nodes = [{"id": f"concept-{i}", "kind": "concept"} for i in range(5)]
    internal_nodes.append({"id": "readout-0", "kind": "readout"})
    return structural_senses, internal_nodes


@requires_node
class Worker3FixtureTests(unittest.TestCase):
    def test_58_sense_5_concept_1_readout_0_edges_renders_honestly(self) -> None:
        """§33 worker-3 validation protocol: 58 SENSE, 5 CONCEPT, 1 READOUT,
        0 edges must become 58 receptors, 6 internal regions, and zero
        fibres -- Observatory must not invent connectivity to fill the
        visual gap left by a genuinely disconnected graph."""
        structural_senses, internal_nodes = build_worker3_topology()
        result = call_js(
            MODULE,
            "projectPhenotypeMorphology",
            {
                "identitySeed": "worker-3-genome:worker-3-instance",
                "percepts": [],
                "hasCurrentTopology": True,
                "structuralSenses": structural_senses,
                "internalNodes": internal_nodes,
                "edges": [],
                "topologyHealth": "connected",
                "recovering": False,
                "frozen": False,
            },
        )
        self.assertEqual(len(result["receptorAnchors"]), 58)
        self.assertEqual(len(result["internalAnchors"]), 6)
        self.assertEqual(sum(1 for a in result["internalAnchors"] if a["kind"] == "readout"), 1)
        self.assertEqual(sum(1 for a in result["internalAnchors"] if a["kind"] == "concept"), 5)
        self.assertEqual(result["fibres"], [])


if __name__ == "__main__":
    unittest.main()
