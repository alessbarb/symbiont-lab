import json
import unittest
from pathlib import Path

from observatory.schema_validate import validate

ROOT = Path(__file__).parent
SCHEMA = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))


def body_schema_v1():
    return {
        "schema_version": 1,
        "state": "undeveloped",
        "parts": [],
        "dependencies": [],
        "global_state": {},
    }


def body_schema_v2():
    first = "part.region." + "b" * 32
    second = "part.region." + "c" * 32
    return {
        "schema_version": 2,
        "state": "partial",
        "parts": [
            {
                "part_id": first,
                "kind": "cognitive_region",
                "existence_confidence_class": 9,
                "confidence_class": 10,
                "activity_class": 11,
                "maturity_class": 4,
                "recency_class": 0,
            },
            {
                "part_id": second,
                "kind": "cognitive_region",
                "existence_confidence_class": 9,
                "confidence_class": 10,
                "activity_class": 8,
                "maturity_class": 4,
                "recency_class": 0,
            },
        ],
        "dependencies": [{
            "source_id": first,
            "target_id": second,
            "relation": "co_acts_with",
            "confidence_class": 12,
            "support_class": 8,
        }],
        "global_state": {},
    }


def cognition():
    return {
        "topology_revision": 0,
        "topology_health": "germinal",
        "recovering": False,
        "readouts": {},
        "prediction_errors": {},
        "edge_deltas": [],
        "mutations": [],
        "safety_state": {"consecutive_failures": 0, "frozen": False},
    }


def check(snapshot):
    validate(snapshot, SCHEMA, schema_root=ROOT)


class SnapshotVersionMatrixTests(unittest.TestCase):
    def test_v1_accepts_no_cognition_and_no_self(self):
        check({"schema_version": 1, "tick": 0, "organism": {}})

    def test_v1_rejects_cognition_or_self(self):
        with self.assertRaises(AssertionError):
            check({"schema_version": 1, "tick": 0, "organism": {"cognition": cognition()}})
        with self.assertRaises(AssertionError):
            check({"schema_version": 1, "tick": 0, "organism": {"body_schema": body_schema_v1()}})

    def test_v2_requires_cognition_and_forbids_self(self):
        check({"schema_version": 2, "tick": 0, "organism": {"cognition": cognition()}})
        with self.assertRaises(AssertionError):
            check({"schema_version": 2, "tick": 0, "organism": {}})
        with self.assertRaises(AssertionError):
            check({"schema_version": 2, "tick": 0, "organism": {"cognition": cognition(), "body_schema": body_schema_v1()}})

    def test_v3_accepts_body_schema_v1_or_v2_and_cognition_is_optional(self):
        check({"schema_version": 3, "tick": 0, "organism": {"body_schema": body_schema_v1()}})
        check({"schema_version": 3, "tick": 0, "organism": {"body_schema": body_schema_v2()}})
        check({"schema_version": 3, "tick": 0, "organism": {"body_schema": body_schema_v2(), "cognition": cognition()}})
        with self.assertRaises(AssertionError):
            check({"schema_version": 3, "tick": 0, "organism": {"cognition": cognition()}})

    def test_private_body_schema_checkpoint_is_rejected_by_wire_contract(self):
        private = body_schema_v2()
        private["id_salt"] = "0" * 32
        with self.assertRaises(AssertionError):
            check({"schema_version": 3, "tick": 0, "organism": {"body_schema": private}})

    def test_v2_body_schema_rejects_kind_specific_field_leakage(self):
        malformed = body_schema_v2()
        malformed["parts"][0]["health_class"] = 15
        with self.assertRaises(AssertionError):
            check({"schema_version": 3, "tick": 0, "organism": {"body_schema": malformed}})


if __name__ == "__main__":
    unittest.main()
