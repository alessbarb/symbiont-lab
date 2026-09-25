import unittest

from observatory._node_harness import ROOT, call_js, requires_node

MODULE = ROOT / "projection" / "self-schema.js"


def project(body_schema):
    return call_js(MODULE, "projectSelfSchema", body_schema)


def sense(recency=0):
    return {
        "partId": "part.sense." + "a" * 32,
        "kind": "sense",
        "existenceConfidenceClass": 15,
        "healthClass": 12,
        "confidenceClass": 9,
        "costClass": 3,
        "maturityClass": 6,
        "recencyClass": recency,
    }


def region(suffix, *, activity=11):
    return {
        "partId": "part.region." + suffix * 32,
        "kind": "cognitive_region",
        "existenceConfidenceClass": 9,
        "confidenceClass": 10,
        "activityClass": activity,
        "maturityClass": 4,
        "recencyClass": 1,
    }


def body_schema_v1(*, recency=0):
    return {
        "schemaVersion": 1,
        "state": "partial",
        "parts": [sense(recency)],
        "dependencies": [],
        "globalState": {},
    }


def body_schema_v2():
    first = region("b")
    second = region("c", activity=8)
    return {
        "schemaVersion": 2,
        "state": "partial",
        "parts": [sense(), first, second],
        "dependencies": [
            {
                "sourceId": first["partId"],
                "targetId": second["partId"],
                "relation": "precedes",
                "confidenceClass": 12,
                "supportClass": 9,
            }
        ],
        "globalState": {},
    }


@requires_node
class SelfSchemaTests(unittest.TestCase):
    def test_null_or_empty_input_is_undeveloped(self):
        self.assertEqual(project(None), {"state": "undeveloped", "parts": [], "dependencies": []})
        self.assertEqual(project({})["state"], "undeveloped")

    def test_v1_sensory_body_remains_supported(self):
        result = project(body_schema_v1())
        part = result["parts"][0]
        self.assertEqual(result["state"], "partial")
        self.assertEqual(part["kind"], "sense")
        self.assertAlmostEqual(part["health"], 12 / 15)
        self.assertAlmostEqual(part["confidence"], 9 / 15)
        self.assertAlmostEqual(part["cost"], 3 / 15)
        self.assertAlmostEqual(part["maturity"], 6 / 7)

    def test_v2_projects_regions_and_dependencies_without_inventing_region_health_or_cost(self):
        result = project(body_schema_v2())
        regions = [part for part in result["parts"] if part["kind"] == "cognitive_region"]
        self.assertEqual(len(regions), 2)
        self.assertAlmostEqual(regions[0]["activity"], 11 / 15)
        self.assertNotIn("health", regions[0])
        self.assertNotIn("cost", regions[0])
        self.assertEqual(len(result["dependencies"]), 1)
        dependency = result["dependencies"][0]
        self.assertEqual(dependency["relation"], "precedes")
        self.assertAlmostEqual(dependency["confidence"], 12 / 15)
        self.assertAlmostEqual(dependency["support"], 9 / 15)

    def test_recency_class_is_rendered_without_inventing_elapsed_ticks(self):
        result = project(body_schema_v1(recency=4))
        self.assertEqual(result["parts"][0]["recency"], "dormant")
        self.assertNotIn("ticks", result["parts"][0])

    def test_dependency_to_unrepresented_region_fails_closed(self):
        malformed = body_schema_v2()
        malformed["dependencies"][0]["targetId"] = "part.region." + "d" * 32
        self.assertEqual(project(malformed)["state"], "undeveloped")

    def test_malformed_region_or_v1_dependency_fails_closed(self):
        malformed = body_schema_v2()
        malformed["parts"][1]["healthClass"] = 12
        self.assertEqual(project(malformed)["state"], "undeveloped")
        legacy = body_schema_v1()
        legacy["dependencies"] = [
            {
                "sourceId": "x",
                "targetId": "y",
                "relation": "precedes",
                "confidenceClass": 9,
                "supportClass": 9,
            }
        ]
        self.assertEqual(project(legacy)["state"], "undeveloped")

    def test_projection_never_accepts_phenotype_shaped_fallback_data(self):
        phenotype = {
            "state": "partial",
            "parts": [{"nodeId": "sense-a", "kind": "sense"}],
            "dependencies": [],
        }
        self.assertEqual(project(phenotype)["state"], "undeveloped")

    def test_module_has_zero_imports_and_no_privileged_phenotype_state(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("import ", source)
        for forbidden in ("topology", "cognition", "percepts", "beliefs", "nodeId"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
