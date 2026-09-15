import unittest

from observatory._node_harness import ROOT, requires_node, call_js

MODULE = ROOT / "projection" / "self-schema.js"


def project(body_schema):
    return call_js(MODULE, "projectSelfSchema", body_schema)


@requires_node
class SelfSchemaTests(unittest.TestCase):
    def test_null_input_is_undeveloped(self):
        result = project(None)
        self.assertEqual(result, {"state": "undeveloped", "parts": [], "dependencies": []})

    def test_empty_object_input_is_still_undeveloped(self):
        # Regression guard: a truthy-but-empty bodySchema must not be
        # mistaken for "developed" just because it isn't null.
        result = project({})
        self.assertEqual(result["state"], "undeveloped")

    def test_module_has_zero_imports(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("import ", source)


if __name__ == "__main__":
    unittest.main()
