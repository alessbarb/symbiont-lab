import unittest
from types import SimpleNamespace as Obj

from observatory.adapter import project_tick


def result(*, cognition=None):
    return Obj(
        tick=7,
        percepts=(),
        allocations=(),
        investigated_capability=None,
        drift_observations={},
        dissent=None,
        narrative=(),
        cognition=cognition,
    )


def sense_part(suffix="a"):
    return {
        "part_id": "part.sense." + suffix * 32,
        "kind": "sense",
        "existence_confidence_class": 13,
        "health_class": 12,
        "confidence_class": 10,
        "cost_class": 3,
        "maturity_class": 6,
        "recency_class": 1,
    }


def region_part(suffix="b", *, activity=11):
    return {
        "part_id": "part.region." + suffix * 32,
        "kind": "cognitive_region",
        "existence_confidence_class": 9,
        "confidence_class": 10,
        "activity_class": activity,
        "maturity_class": 4,
        "recency_class": 0,
    }


def body_schema_v1(**overrides):
    payload = {
        "schema_version": 1,
        "state": "partial",
        "parts": [sense_part()],
        "dependencies": [],
        "global_state": {},
    }
    payload.update(overrides)
    return payload


def body_schema_v2(**overrides):
    first = region_part("b")
    second = region_part("c", activity=8)
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
                "support_class": 9,
            }
        ],
        "global_state": {},
    }
    payload.update(overrides)
    return payload


class BodySchemaAdapterTests(unittest.TestCase):
    def test_safe_v1_body_schema_selects_snapshot_v3_without_requiring_cognition(self):
        snapshot = project_tick(result(), body_schema=body_schema_v1())

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertNotIn("cognition", snapshot["organism"])
        self.assertEqual(snapshot["organism"]["body_schema"], body_schema_v1())

    def test_safe_v2_regions_and_dependencies_pass_through_allowlist_rebuild(self):
        expected = body_schema_v2()
        snapshot = project_tick(result(), body_schema=expected)

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertEqual(snapshot["organism"]["body_schema"], expected)
        rendered = repr(snapshot["organism"]["body_schema"])
        self.assertNotIn("channel.cognition", rendered)
        self.assertNotIn("cognitive_learning", rendered)

    def test_v3_can_carry_cognition_and_self_as_orthogonal_surfaces(self):
        cognition = Obj(
            readouts={},
            prediction_errors=(),
            mutations=(),
            consecutive_failures=0,
            frozen=False,
            topology_health="germinal",
            recovering=False,
            topology_revision=0,
        )
        snapshot = project_tick(result(cognition=cognition), genome=Obj(), body_schema=body_schema_v2())

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertIn("cognition", snapshot["organism"])
        self.assertEqual(snapshot["organism"]["body_schema"]["schema_version"], 2)

    def test_private_checkpoint_export_fails_closed_and_never_leaks_salt_or_learning_state(self):
        private = body_schema_v2(
            id_salt="f" * 32,
            cognitive_learning={"channel_support": [{"channel_id": "channel.cognition." + "a" * 32, "support": 9}]},
        )
        snapshot = project_tick(result(), body_schema=private)
        body = snapshot["organism"]["body_schema"]

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertEqual(body, {"schema_version": 2, "state": "undeveloped", "parts": [], "dependencies": [], "global_state": {}})
        self.assertNotIn("id_salt", repr(snapshot))
        self.assertNotIn("channel.cognition", repr(snapshot))
        self.assertNotIn("cognitive_learning", repr(snapshot))

    def test_unexpected_source_identity_fails_closed_instead_of_being_silently_stripped(self):
        source = body_schema_v1()
        source["parts"][0]["source_capability_id"] = "compute.logical_cpu"
        snapshot = project_tick(result(), body_schema=source)

        self.assertEqual(
            snapshot["organism"]["body_schema"],
            {"schema_version": 1, "state": "undeveloped", "parts": [], "dependencies": [], "global_state": {}},
        )
        self.assertNotIn("compute.logical_cpu", repr(snapshot["organism"]["body_schema"]))

    def test_v2_dependency_must_reference_represented_regions(self):
        source = body_schema_v2()
        source["dependencies"][0]["target_id"] = "part.region." + "d" * 32
        snapshot = project_tick(result(), body_schema=source)

        self.assertEqual(snapshot["organism"]["body_schema"]["state"], "undeveloped")
        self.assertEqual(snapshot["organism"]["body_schema"]["schema_version"], 2)

    def test_v1_still_rejects_regions_and_dependencies(self):
        source = body_schema_v1()
        source["parts"].append(region_part())
        snapshot = project_tick(result(), body_schema=source)
        self.assertEqual(snapshot["organism"]["body_schema"]["state"], "undeveloped")

    def test_contradictory_body_schema_fails_closed_not_partially(self):
        source = body_schema_v2(dependencies=[{"source": "a", "target": "b"}])
        snapshot = project_tick(result(), body_schema=source)

        self.assertEqual(
            snapshot["organism"]["body_schema"],
            {"schema_version": 2, "state": "undeveloped", "parts": [], "dependencies": [], "global_state": {}},
        )

    def test_omitting_body_schema_preserves_historical_v1_snapshot_contract(self):
        snapshot = project_tick(result())
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertNotIn("body_schema", snapshot["organism"])


if __name__ == "__main__":
    unittest.main()
