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


def body_schema(**overrides):
    payload = {
        "schema_version": 1,
        "state": "partial",
        "parts": [
            {
                "part_id": "part.sense." + "a" * 32,
                "kind": "sense",
                "existence_confidence_class": 13,
                "health_class": 12,
                "confidence_class": 10,
                "cost_class": 3,
                "maturity_class": 6,
                "recency_class": 1,
            }
        ],
        "dependencies": [],
        "global_state": {},
    }
    payload.update(overrides)
    return payload


class BodySchemaAdapterTests(unittest.TestCase):
    def test_safe_body_schema_selects_v3_without_requiring_cognition(self):
        snapshot = project_tick(result(), body_schema=body_schema())

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertNotIn("cognition", snapshot["organism"])
        self.assertEqual(snapshot["organism"]["body_schema"], body_schema())

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
        snapshot = project_tick(result(cognition=cognition), genome=Obj(), body_schema=body_schema())

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertIn("cognition", snapshot["organism"])
        self.assertIn("body_schema", snapshot["organism"])

    def test_private_checkpoint_export_fails_closed_and_never_leaks_salt(self):
        private = body_schema(id_salt="f" * 32)
        snapshot = project_tick(result(), body_schema=private)
        body = snapshot["organism"]["body_schema"]

        self.assertEqual(snapshot["schema_version"], 3)
        self.assertEqual(body["state"], "undeveloped")
        self.assertEqual(body["parts"], [])
        self.assertNotIn("id_salt", repr(snapshot))

    def test_unexpected_source_identity_is_stripped_at_adapter_boundary(self):
        source = body_schema()
        source["parts"][0]["source_capability_id"] = "compute.logical_cpu"
        snapshot = project_tick(result(), body_schema=source)

        self.assertEqual(snapshot["organism"]["body_schema"]["state"], "partial")
        self.assertNotIn("compute.logical_cpu", repr(snapshot["organism"]["body_schema"]))
        self.assertNotIn("source_capability_id", repr(snapshot["organism"]["body_schema"]))

    def test_contradictory_body_schema_fails_closed_not_partially(self):
        source = body_schema(dependencies=[{"source": "a", "target": "b"}])
        snapshot = project_tick(result(), body_schema=source)

        self.assertEqual(
            snapshot["organism"]["body_schema"],
            {"schema_version": 1, "state": "undeveloped", "parts": [], "dependencies": [], "global_state": {}},
        )

    def test_omitting_body_schema_preserves_historical_v1_contract(self):
        snapshot = project_tick(result())
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertNotIn("body_schema", snapshot["organism"])


if __name__ == "__main__":
    unittest.main()
