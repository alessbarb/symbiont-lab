import unittest

from observatory._node_harness import ROOT, call_js, requires_node

MODULE = ROOT / "projection" / "body-schema.js"


def bounded(value):
    return call_js(MODULE, "boundedBodySchema", value)


def to_wire(value):
    return call_js(MODULE, "bodySchemaToWire", value)


def wire_part(part_id=None):
    return {
        "part_id": part_id or "part.sense." + "a" * 32,
        "kind": "sense",
        "existence_confidence_class": 13,
        "health_class": 12,
        "confidence_class": 10,
        "cost_class": 3,
        "maturity_class": 6,
        "recency_class": 2,
    }


def wire_schema(parts=None, **overrides):
    payload = {
        "schema_version": 1,
        "state": "partial",
        "parts": parts if parts is not None else [wire_part()],
        "dependencies": [],
        "global_state": {},
    }
    payload.update(overrides)
    return payload


@requires_node
class BodySchemaSnapshotTests(unittest.TestCase):
    def test_valid_partial_wire_shape_becomes_bounded_internal_state(self):
        result = bounded(wire_schema())

        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["state"], "partial")
        self.assertEqual(result["dependencies"], [])
        self.assertEqual(result["globalState"], {})
        part = result["parts"][0]
        self.assertEqual(part["partId"], "part.sense." + "a" * 32)
        self.assertEqual(part["healthClass"], 12)
        self.assertEqual(part["recencyClass"], 2)

    def test_undeveloped_wire_shape_round_trips_without_fabricating_parts(self):
        source = wire_schema(parts=[], state="undeveloped")
        internal = bounded(source)

        self.assertEqual(internal["state"], "undeveloped")
        self.assertEqual(internal["parts"], [])
        self.assertEqual(to_wire(internal), source)

    def test_private_checkpoint_salt_is_rejected(self):
        source = wire_schema(id_salt="0" * 32)
        self.assertIsNone(bounded(source))

    def test_nonempty_dependencies_or_global_state_are_rejected(self):
        self.assertIsNone(bounded(wire_schema(dependencies=[{"source": "x", "target": "y"}])))
        self.assertIsNone(bounded(wire_schema(global_state={"integrity_class": 12})))

    def test_out_of_range_or_non_integer_classes_are_rejected(self):
        part = wire_part()
        part["health_class"] = 16
        self.assertIsNone(bounded(wire_schema(parts=[part])))

        part = wire_part()
        part["maturity_class"] = 6.5
        self.assertIsNone(bounded(wire_schema(parts=[part])))

    def test_invalid_or_nonopaque_part_ids_are_rejected(self):
        self.assertIsNone(bounded(wire_schema(parts=[wire_part("sense.cpu")])) )
        self.assertIsNone(bounded(wire_schema(parts=[wire_part("part.sense." + "G" * 32)])))

    def test_partial_requires_at_least_one_part_and_undeveloped_requires_zero(self):
        self.assertIsNone(bounded(wire_schema(parts=[])))
        self.assertIsNone(bounded(wire_schema(parts=[wire_part()], state="undeveloped")))

    def test_more_than_256_parts_is_rejected_not_truncated(self):
        parts = [wire_part(f"part.sense.{index:032x}") for index in range(257)]
        self.assertIsNone(bounded(wire_schema(parts=parts)))

    def test_wire_round_trip_contains_no_private_or_source_identity(self):
        internal = bounded(wire_schema())
        result = to_wire(internal)
        rendered = repr(result)

        self.assertNotIn("id_salt", rendered)
        self.assertNotIn("capability", rendered)
        self.assertEqual(result, wire_schema())

    def test_module_is_pure_and_zero_import(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("import ", source)
        self.assertNotIn("state.", source)
        self.assertNotIn("document.", source)


if __name__ == "__main__":
    unittest.main()
