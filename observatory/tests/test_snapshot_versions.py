import json
import unittest
from pathlib import Path

from observatory.schema_validate import validate

ROOT = Path(__file__).resolve().parent.parent
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
        "dependencies": [
            {
                "source_id": first,
                "target_id": second,
                "relation": "co_acts_with",
                "confidence_class": 12,
                "support_class": 8,
            }
        ],
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


def sensory_phenotype(*, selection_credit=None):
    sensor = {
        "sensor_id": "sensor.00000001",
        "modality_id": "modality.alpha",
        "source_count": 1,
        "signal_ids": ["signal." + "a" * 64],
        "maturity": "established",
        "health": 1.0,
        "confidence": 0.8,
        "utility": 0.4,
        "redundancy": 0.0,
        "cost": 0.01,
        "parent_sensor_ids": [],
        "downstream_name": "sensor.00000001",
        "cold_start": False,
    }
    if selection_credit is not None:
        sensor["selection_credit"] = selection_credit
    return {
        "schema_version": 1,
        "modalities": [
            {
                "modality_id": "modality.alpha",
                "sensor_count": 1,
                "max_inputs": 1,
                "temporal_capacity": 2,
            }
        ],
        "sensors": [sensor],
        "summary": {
            "active": 1,
            "nascent": 0,
            "immature": 0,
            "established": 1,
            "specialised": 0,
            "degraded": 0,
        },
    }


def communication_telemetry():
    return {
        "schema_version": 1,
        "events": [
            {
                "event_id": "communication.e1",
                "tick": 3,
                "event_kind": "DELIVER",
                "sender_id": "organism.a",
                "receiver_id": "organism.b",
                "message_id": "sequence.m",
                "symbol_ids": ["symbol.x"],
                "cost": 1,
                "delivery_status": "delivered",
                "sender_generation": 0,
                "receiver_generation": 1,
            }
        ],
        "grounding_events": [
            {
                "event_id": "grounding.g1",
                "tick": 3,
                "organism_id": "organism.b",
                "message_id": "sequence.m",
                "exposure_count": 1,
                "association_strength_before": 0,
                "association_strength_after": 1,
                "support_delta": 1,
                "contradiction_delta": 0,
                "cost": 1,
            }
        ],
        "history_truncated": False,
        "earliest_available_tick": 3,
    }


class SnapshotVersionMatrixTests(unittest.TestCase):
    def test_v1_accepts_no_cognition_and_no_self(self):
        check({"schema_version": 1, "tick": 0, "organism": {}})

    def test_population_telemetry_is_top_level_and_bounded(self):
        check(
            {
                "schema_version": 3,
                "tick": 3,
                "organism": {"body_schema": body_schema_v1()},
                "population_telemetry": communication_telemetry(),
            }
        )

    def test_population_telemetry_rejects_malformed_event(self):
        telemetry = communication_telemetry()
        telemetry["events"][0]["ground_truth"] = "forbidden"
        with self.assertRaises(AssertionError):
            check(
                {
                    "schema_version": 3,
                    "tick": 3,
                    "organism": {"body_schema": body_schema_v1()},
                    "population_telemetry": telemetry,
                }
            )

    def test_population_telemetry_rejects_unknown_schema_version(self):
        telemetry = communication_telemetry()
        telemetry["schema_version"] = 99
        with self.assertRaises(AssertionError):
            check(
                {
                    "schema_version": 3,
                    "tick": 3,
                    "organism": {"body_schema": body_schema_v1()},
                    "population_telemetry": telemetry,
                }
            )

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
            check(
                {
                    "schema_version": 2,
                    "tick": 0,
                    "organism": {"cognition": cognition(), "body_schema": body_schema_v1()},
                }
            )

    def test_v3_accepts_body_schema_v1_or_v2_and_cognition_is_optional(self):
        check({"schema_version": 3, "tick": 0, "organism": {"body_schema": body_schema_v1()}})
        check({"schema_version": 3, "tick": 0, "organism": {"body_schema": body_schema_v2()}})
        check(
            {
                "schema_version": 3,
                "tick": 0,
                "organism": {"body_schema": body_schema_v2(), "cognition": cognition()},
            }
        )
        with self.assertRaises(AssertionError):
            check({"schema_version": 3, "tick": 0, "organism": {"cognition": cognition()}})

    def test_v3_sensory_phenotype_accepts_legacy_and_selection_credit_extension(self):
        legacy = {
            "schema_version": 3,
            "tick": 1,
            "organism": {
                "body_schema": body_schema_v1(),
                "sensory_phenotype": sensory_phenotype(),
            },
        }
        current = {
            "schema_version": 3,
            "tick": 1,
            "organism": {
                "body_schema": body_schema_v1(),
                "sensory_phenotype": sensory_phenotype(selection_credit=0.75),
            },
        }
        check(legacy)
        check(current)

    def test_observer_provenance_is_optional_top_level_and_rejects_leak_into_organism(self):
        observer = {
            "signal_provenance": [
                {
                    "signal_id": "signal." + "a" * 64,
                    "label": "CPU load",
                    "category": "compute",
                    "scope": "external",
                    "value": 42.0,
                    "unit": "%",
                    "quality": "nominal",
                }
            ]
        }
        check(
            {
                "schema_version": 3,
                "tick": 1,
                "organism": {"body_schema": body_schema_v1()},
                "observer": observer,
            }
        )
        with self.assertRaises(AssertionError):
            check(
                {
                    "schema_version": 3,
                    "tick": 1,
                    "organism": {"body_schema": body_schema_v1(), "observer": observer},
                }
            )

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
