import math
import re
import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "morphology.js"

BASE_INPUT = {
    "identitySeed": "genome-x:instance-a",
    "percepts": [],
    "hasCurrentTopology": False,
    "structuralSenses": [],
    "internalNodes": [],
    "edges": [],
    "topologyHealth": None,
    "recovering": False,
    "frozen": False,
}


def project(overrides=None):
    payload = {**BASE_INPUT, **(overrides or {})}
    return call_js(MODULE, "projectPhenotypeMorphology", payload)


def parse_path_segments(d):
    """The boundaryPath's M start point plus each cubic segment's c1/c2/end
    are exactly the control points morphology.js used to draw and evaluate
    the curve -- recover them so tests can check the real rendered curve,
    not an approximation of it, without morphology.js exporting anything
    beyond the single projectPhenotypeMorphology function."""
    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", d)]
    start = (numbers[0], numbers[1])
    segments = []
    prev = start
    rest = numbers[2:]
    for i in range(0, len(rest), 6):
        c1 = (rest[i], rest[i + 1])
        c2 = (rest[i + 2], rest[i + 3])
        end = (rest[i + 4], rest[i + 5])
        segments.append((prev, c1, c2, end))
        prev = end
    return segments


def evaluate_cubic(p1, c1, c2, p2, t):
    mt = 1 - t
    x = mt**3 * p1[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p2[0]
    y = mt**3 * p1[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p2[1]
    return (x, y)


def fine_polygon_from_path(d, steps_per_segment=16):
    """A close approximation of the actual rendered cubic curve (not the
    coarse straight-edged polygon of the 10 control points), by sampling
    each real segment many times."""
    segments = parse_path_segments(d)
    polygon = []
    for p1, c1, c2, p2 in segments:
        for i in range(steps_per_segment):
            polygon.append(evaluate_cubic(p1, c1, c2, p2, i / steps_per_segment))
    return polygon


def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside


@requires_node
class MorphologyDeterminismTests(unittest.TestCase):
    def test_same_input_produces_byte_identical_boundary(self):
        a = project()
        b = project()
        self.assertEqual(a["boundaryPath"], b["boundaryPath"])

    def test_different_identity_seed_produces_different_boundary(self):
        a = project({"identitySeed": "seed-one"})
        b = project({"identitySeed": "seed-two"})
        self.assertNotEqual(a["boundaryPath"], b["boundaryPath"])

    def test_presentation_inputs_never_change_boundary_or_internal_anchors(self):
        nodes = [{"id": "c1", "kind": "concept"}]
        a = project({"internalNodes": nodes, "topologyHealth": "connected", "recovering": False, "frozen": False})
        b = project({"internalNodes": nodes, "topologyHealth": "degenerate", "recovering": True, "frozen": True})
        self.assertEqual(a["boundaryPath"], b["boundaryPath"])
        self.assertEqual(a["internalAnchors"], b["internalAnchors"])
        self.assertNotEqual(a["presentation"], b["presentation"])

    def test_receptor_anchor_lies_exactly_on_the_rendered_curve(self):
        """Regression test for the bug where receptors were placed via a
        separate radius-interpolation approximation that could disagree
        with the actual cubic Bezier the boundaryPath draws. Recomputes the
        expected point independently, from the path string, using the same
        formula morphology.js uses internally, and asserts exact
        (to quantization) agreement -- not just "close enough"."""
        result = project({"hasCurrentTopology": True, "structuralSenses": [{"id": "only-sense", "kind": "sense"}]})
        segments = parse_path_segments(result["boundaryPath"])
        angle = (math.radians(130) + math.radians(230)) / 2  # single receptor -> arc midpoint
        u = (angle / (2 * math.pi)) % 1
        n = len(segments)
        scaled = u * n
        i = int(scaled) % n
        t = scaled - int(scaled)
        p1, c1, c2, p2 = segments[i]
        expected_x, expected_y = evaluate_cubic(p1, c1, c2, p2, t)
        receptor = result["receptorAnchors"][0]
        self.assertAlmostEqual(receptor["x"], round(expected_x, 2), places=2)
        self.assertAlmostEqual(receptor["y"], round(expected_y, 2), places=2)


@requires_node
class MorphologyStructureTests(unittest.TestCase):
    def test_no_edges_means_no_fibres_regardless_of_nodes(self):
        result = project({
            "hasCurrentTopology": True,
            "structuralSenses": [{"id": "s1", "kind": "sense"}],
            "internalNodes": [{"id": "c1", "kind": "concept"}, {"id": "r1", "kind": "readout"}],
            "edges": [],
        })
        self.assertEqual(result["fibres"], [])

    def test_no_topology_falls_back_to_percepts_for_receptors(self):
        result = project({
            "hasCurrentTopology": False,
            "percepts": [{"id": "p1", "quality": 0.5, "active": True}, {"id": "p2", "quality": 0.9, "active": True}],
            "structuralSenses": [],
        })
        self.assertEqual(len(result["receptorAnchors"]), 2)
        self.assertEqual(result["internalAnchors"], [])
        self.assertEqual(result["fibres"], [])

    def test_current_topology_with_zero_sense_nodes_does_not_fall_back_to_percepts(self):
        """The P0 regression this input exists to prevent: a real, current
        topology that genuinely has no SENSE nodes must render zero
        receptors, never borrow percept ids as fabricated sensory organs."""
        result = project({
            "hasCurrentTopology": True,
            "percepts": [{"id": "p1", "quality": 0.5, "active": True}, {"id": "p2", "quality": 0.9, "active": True}],
            "structuralSenses": [],
            "internalNodes": [{"id": "c1", "kind": "concept"}],
        })
        self.assertEqual(result["receptorAnchors"], [])

    def test_sense_concept_readout_chain_keeps_the_sense_incident_edge(self):
        result = project({
            "hasCurrentTopology": True,
            "structuralSenses": [{"id": "s1", "kind": "sense"}],
            "internalNodes": [{"id": "c1", "kind": "concept"}, {"id": "r1", "kind": "readout"}],
            "edges": [
                {"sourceId": "s1", "targetId": "c1", "kind": "excitatory"},
                {"sourceId": "c1", "targetId": "r1", "kind": "predictive"},
            ],
        })
        edge_pairs = {(f["sourceId"], f["targetId"]) for f in result["fibres"]}
        self.assertIn(("s1", "c1"), edge_pairs)
        self.assertIn(("c1", "r1"), edge_pairs)
        self.assertEqual(len(result["fibres"]), 2)

    def test_edge_naming_an_unknown_id_is_dropped(self):
        result = project({
            "hasCurrentTopology": True,
            "internalNodes": [{"id": "c1", "kind": "concept"}],
            "edges": [{"sourceId": "c1", "targetId": "does-not-exist", "kind": "excitatory"}],
        })
        self.assertEqual(result["fibres"], [])

    def test_readout_nodes_are_real_anchors_not_a_synthetic_centroid(self):
        result = project({"hasCurrentTopology": True, "internalNodes": [
            {"id": "r1", "kind": "readout"}, {"id": "r2", "kind": "readout"},
        ]})
        kinds = [a["kind"] for a in result["internalAnchors"]]
        self.assertEqual(kinds.count("readout"), 2)

    def test_array_order_does_not_affect_output(self):
        senses_a = [{"id": "s1", "kind": "sense"}, {"id": "s2", "kind": "sense"}]
        senses_b = [{"id": "s2", "kind": "sense"}, {"id": "s1", "kind": "sense"}]
        nodes_a = [{"id": "c1", "kind": "concept"}, {"id": "c2", "kind": "concept"}]
        nodes_b = [{"id": "c2", "kind": "concept"}, {"id": "c1", "kind": "concept"}]
        edges_a = [
            {"sourceId": "s1", "targetId": "c1", "kind": "excitatory"},
            {"sourceId": "c1", "targetId": "c2", "kind": "predictive"},
        ]
        edges_b = list(reversed(edges_a))
        result_a = project({"hasCurrentTopology": True, "structuralSenses": senses_a, "internalNodes": nodes_a, "edges": edges_a})
        result_b = project({"hasCurrentTopology": True, "structuralSenses": senses_b, "internalNodes": nodes_b, "edges": edges_b})
        self.assertEqual(result_a, result_b)

    def test_receptor_anchors_are_id_paired_with_external_input_anchors_and_monotone(self):
        structural = [{"id": f"s{i}", "kind": "sense"} for i in range(4)]
        result = project({"hasCurrentTopology": True, "structuralSenses": structural})
        inputs = result["externalInputAnchors"]
        receptors = result["receptorAnchors"]
        self.assertEqual(len(inputs), 4)
        self.assertEqual(len(receptors), 4)
        for input_anchor, receptor_anchor in zip(inputs, receptors):
            self.assertEqual(input_anchor["id"], receptor_anchor["id"])
        # index 0's input is nearest the top of the screen (smallest y); the
        # receptor ladder must run in the same direction, not the opposite one.
        input_ys = [a["y"] for a in inputs]
        receptor_ys = [a["y"] for a in receptors]
        self.assertEqual(input_ys, sorted(input_ys))
        self.assertEqual(receptor_ys, sorted(receptor_ys))

    def test_world_receptors_and_cognitive_senses_are_independent_populations(self):
        world = [{"id": f"world-{i}"} for i in range(3)]
        receptors = [{"id": f"sensor-{i}"} for i in range(7)]
        cognitive = [{"id": "sense-node", "kind": "sense"}, {"id": "concept-1", "kind": "concept"}]
        result = project({
            "hasCurrentTopology": True,
            "worldSignals": world,
            "receptors": receptors,
            "structuralSenses": [{"id": "legacy-sense", "kind": "sense"}],
            "internalNodes": cognitive,
            "edges": [{"sourceId": "sense-node", "targetId": "concept-1", "kind": "excitatory"}],
        })
        self.assertEqual([a["id"] for a in result["externalInputAnchors"]], [f"world-{i}" for i in range(3)])
        self.assertEqual({a["id"] for a in result["receptorAnchors"]}, {f"sensor-{i}" for i in range(7)})
        self.assertEqual({a["id"] for a in result["internalAnchors"]}, {"sense-node", "concept-1"})
        self.assertEqual(len(result["fibres"]), 1)

    def test_receptor_population_does_not_depend_on_cognitive_sense_count(self):
        receptors = [{"id": f"sensor-{i:02d}"} for i in range(64)]
        result = project({
            "hasCurrentTopology": True,
            "worldSignals": [{"id": "world-0"}],
            "receptors": receptors,
            "structuralSenses": [{"id": "sense-only", "kind": "sense"}],
            "internalNodes": [{"id": "sense-only", "kind": "sense"}],
        })
        self.assertEqual(len(result["receptorAnchors"]), 64)
        self.assertEqual(len(result["externalInputAnchors"]), 1)
        self.assertEqual(len(result["internalAnchors"]), 1)

    def test_internal_anchors_fall_within_the_generated_boundary_interior(self):
        nodes = [{"id": f"c{i}", "kind": "concept"} for i in range(12)]
        result = project({"identitySeed": "containment-check", "hasCurrentTopology": True, "internalNodes": nodes})
        polygon = fine_polygon_from_path(result["boundaryPath"])
        for anchor in result["internalAnchors"]:
            self.assertTrue(
                point_in_polygon((anchor["x"], anchor["y"]), polygon),
                f"anchor {anchor} outside boundary polygon (sampled from the actual rendered curve)",
            )


if __name__ == "__main__":
    unittest.main()
