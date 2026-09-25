import unittest

from observatory._node_harness import ROOT, call_js, requires_node

MODULE = ROOT / "projection" / "body-schema.js"


def bounded(value):
    return call_js(MODULE, "boundedBodySchema", value)


def to_wire(value):
    return call_js(MODULE, "bodySchemaToWire", value)


def sense_part(part_id=None):
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


def region_part(suffix="b"):
    return {
        "part_id": "part.region." + suffix * 32,
        "kind": "cognitive_region",
        "existence_confidence_class": 9,
        "confidence_class": 10,
        "activity_class": 11,
        "maturity_class": 4,
        "recency_class": 1,
    }


def wire_schema_v1(parts=None, **overrides):
    payload = {
        "schema_version": 1,
        "state": "partial",
        "parts": parts if parts is not None else [sense_part()],
        "dependencies": [],
        "global_state": {},
    }
    payload.update(overrides)
    return payload


def wire_schema_v2(**overrides):
    first = region_part("b")
    second = region_part("c")
    payload = {
        "schema_version": 2,
        "state": "partial",
        "parts": [sense_part(), first, second],
        "dependencies": [
            {
                "source_id": first["part_id"],
                "target_id": second["part_id"],
                "relation": "co_acts_with",
                "confidence_class": 12,
                "support_class": 8,
            }
        ],
        "global_state": {},
    }
    payload.update(overrides)
    return payload


@requires_node
class BodySchemaSnapshotTests(unittest.TestCase):
    def test_v1_partial_wire_shape_remains_supported(self):
        result = bounded(wire_schema_v1())
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["parts"][0]["kind"], "sense")
        self.assertEqual(to_wire(result), wire_schema_v1())

    def test_v2_regions_and_dependencies_round_trip(self):
        source = wire_schema_v2()
        internal = bounded(source)
        self.assertEqual(internal["schemaVersion"], 2)
        self.assertEqual(len([p for p in internal["parts"] if p["kind"] == "cognitive_region"]), 2)
        self.assertEqual(internal["dependencies"][0]["relation"], "co_acts_with")
        self.assertEqual(to_wire(internal), source)

    def test_undeveloped_v2_round_trips_without_fabrication(self):
        source = {
            "schema_version": 2,
            "state": "undeveloped",
            "parts": [],
            "dependencies": [],
            "global_state": {},
        }
        internal = bounded(source)
        self.assertEqual(internal["state"], "undeveloped")
        self.assertEqual(to_wire(internal), source)

    def test_v1_rejects_regions_and_dependencies(self):
        self.assertIsNone(bounded(wire_schema_v1(parts=[sense_part(), region_part()])))
        self.assertIsNone(bounded(wire_schema_v1(dependencies=[{"source_id": "x"}])))

    def test_v2_dependency_requires_known_region_endpoints_and_canonical_coactivity(self):
        source = wire_schema_v2()
        source["dependencies"][0]["target_id"] = "part.region." + "d" * 32
        self.assertIsNone(bounded(source))

        source = wire_schema_v2()
        source["dependencies"][0]["source_id"], source["dependencies"][0]["target_id"] = (
            source["dependencies"][0]["target_id"],
            source["dependencies"][0]["source_id"],
        )
        self.assertIsNone(bounded(source))

    def test_private_or_unknown_fields_are_rejected(self):
        source = wire_schema_v2(cognitive_learning={"channel_support": []})
        self.assertIsNone(bounded(source))
        source = wire_schema_v2(id_salt="0" * 32)
        self.assertIsNone(bounded(source))
        part = region_part()
        part["members"] = ["channel.cognition." + "a" * 32]
        self.assertIsNone(bounded(wire_schema_v2(parts=[part])))

    def test_kind_specific_fields_are_closed(self):
        sense = sense_part()
        sense["activity_class"] = 4
        self.assertIsNone(bounded(wire_schema_v2(parts=[sense])))
        region = region_part()
        region["health_class"] = 9
        self.assertIsNone(bounded(wire_schema_v2(parts=[region])))

    def test_duplicate_parts_and_dependencies_are_rejected(self):
        duplicate = sense_part()
        self.assertIsNone(bounded(wire_schema_v2(parts=[duplicate, dict(duplicate)])))
        source = wire_schema_v2()
        source["dependencies"].append(dict(source["dependencies"][0]))
        self.assertIsNone(bounded(source))

    def test_bounds_are_rejected_not_truncated(self):
        senses = [sense_part(f"part.sense.{index:032x}") for index in range(257)]
        self.assertIsNone(bounded(wire_schema_v2(parts=senses)))
        regions = [region_part(f"{index:032x}"[-1]) for index in range(33)]
        # Build unique region ids explicitly; region_part's convenience suffix is one char.
        regions = [{**region_part(), "part_id": f"part.region.{index:032x}"} for index in range(33)]
        self.assertIsNone(bounded(wire_schema_v2(parts=regions, dependencies=[])))

    def test_wire_round_trip_contains_no_private_channel_identity(self):
        result = to_wire(bounded(wire_schema_v2()))
        rendered = repr(result)
        self.assertNotIn("id_salt", rendered)
        self.assertNotIn("channel.cognition", rendered)
        self.assertNotIn("capability", rendered)

    def test_module_is_pure_and_zero_import(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("import ", source)
        self.assertNotIn("state.", source)
        self.assertNotIn("document.", source)


if __name__ == "__main__":
    unittest.main()
