import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "self-schema.js"


def project(body_schema):
    return call_js(MODULE, "projectSelfSchema", body_schema)


def body_schema(*, recency=0):
    return {
        "schemaVersion": 1,
        "state": "partial",
        "parts": [
            {
                "partId": "part.sense." + "a" * 32,
                "kind": "sense",
                "existenceConfidenceClass": 15,
                "healthClass": 12,
                "confidenceClass": 9,
                "costClass": 3,
                "maturityClass": 6,
                "recencyClass": recency,
            }
        ],
        "dependencies": [],
        "globalState": {},
    }


@requires_node
class SelfSchemaTests(unittest.TestCase):
    def test_null_input_is_undeveloped(self):
        result = project(None)
        self.assertEqual(result, {"state": "undeveloped", "parts": [], "dependencies": []})

    def test_empty_object_input_is_still_undeveloped(self):
        result = project({})
        self.assertEqual(result["state"], "undeveloped")

    def test_partial_body_schema_projects_only_self_owned_part_metrics(self):
        result = project(body_schema())

        self.assertEqual(result["state"], "partial")
        self.assertEqual(result["dependencies"], [])
        self.assertEqual(len(result["parts"]), 1)
        part = result["parts"][0]
        self.assertEqual(part["id"], "part.sense." + "a" * 32)
        self.assertEqual(part["kind"], "sense")
        self.assertAlmostEqual(part["existence"], 1.0)
        self.assertAlmostEqual(part["health"], 12 / 15)
        self.assertAlmostEqual(part["confidence"], 9 / 15)
        self.assertAlmostEqual(part["cost"], 3 / 15)
        self.assertAlmostEqual(part["maturity"], 6 / 7)
        self.assertEqual(part["recency"], "current")

    def test_recency_class_is_rendered_without_inventing_elapsed_ticks(self):
        result = project(body_schema(recency=4))
        self.assertEqual(result["parts"][0]["recency"], "dormant")
        self.assertNotIn("ticks", result["parts"][0])

    def test_malformed_or_dependency_bearing_self_fails_closed(self):
        malformed = body_schema()
        malformed["dependencies"] = [{"source": "x", "target": "y"}]
        self.assertEqual(project(malformed)["state"], "undeveloped")

    def test_projection_never_accepts_phenotype_shaped_fallback_data(self):
        phenotype = {"state": "partial", "parts": [{"nodeId": "sense-a", "kind": "sense"}], "dependencies": []}
        self.assertEqual(project(phenotype)["state"], "undeveloped")

    def test_module_has_zero_imports(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("import ", source)
        for forbidden in ("topology", "cognition", "percepts", "beliefs"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
