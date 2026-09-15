import unittest

from observatory.schema_validate import validate


class SchemaValidateConditionalTests(unittest.TestCase):
    def test_if_then_else_branches_are_enforced(self):
        schema = {
            "type": "object",
            "if": {"properties": {"version": {"const": 1}}},
            "then": {"properties": {"extra": {"type": "null"}}},
            "else": {"required": ["extra"]},
        }
        validate({"version": 1, "extra": None}, schema)
        validate({"version": 2, "extra": "present"}, schema)
        with self.assertRaises(AssertionError):
            validate({"version": 2}, schema)

    def test_all_of_requires_every_subschema(self):
        schema = {
            "type": "object",
            "allOf": [
                {"required": ["a"]},
                {"required": ["b"]},
            ],
        }
        validate({"a": 1, "b": 2}, schema)
        with self.assertRaises(AssertionError):
            validate({"a": 1}, schema)

    def test_any_of_requires_at_least_one_subschema(self):
        schema = {
            "type": "object",
            "anyOf": [
                {"required": ["a"]},
                {"required": ["b"]},
            ],
        }
        validate({"a": 1}, schema)
        validate({"b": 1}, schema)
        with self.assertRaises(AssertionError):
            validate({"c": 1}, schema)

    def test_not_of_any_of_rejects_either_forbidden_property(self):
        schema = {
            "type": "object",
            "not": {
                "anyOf": [
                    {"required": ["cognition"]},
                    {"required": ["body_schema"]},
                ]
            },
        }
        validate({}, schema)
        with self.assertRaises(AssertionError):
            validate({"cognition": {}}, schema)
        with self.assertRaises(AssertionError):
            validate({"body_schema": {}}, schema)


if __name__ == "__main__":
    unittest.main()

class SignalKnowledgeSchemaTests(unittest.TestCase):
    def test_claims_reject_unknown_fields_and_require_identity(self):
        import json
        from pathlib import Path

        schema_path = Path(__file__).parents[1] / "schemas" / "signal_knowledge.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        signal_id = "signal." + "a" * 64
        claim = {
            "claim_id": "claim.example",
            "kind": "stability",
            "status": "hypothesis",
            "evidence_count": 1,
            "validation_opportunities": 1,
            "revision": 0,
            "reason_class": "initial_evidence",
        }
        validate([{
            "signal_id": signal_id,
            "observed_opportunities": 1,
            "valid_observations": 1,
            "last_seen_age_class": "current",
            "claims": [claim],
        }], schema)
        with self.assertRaises(AssertionError):
            validate([{
                "signal_id": signal_id,
                "observed_opportunities": 1,
                "valid_observations": 1,
                "last_seen_age_class": "current",
                "claims": [{**claim, "unexpected": True}],
            }], schema)
        with self.assertRaises(AssertionError):
            validate([{
                "signal_id": signal_id,
                "observed_opportunities": 1,
                "valid_observations": 1,
                "last_seen_age_class": "current",
                "claims": [{k: v for k, v in claim.items() if k != "claim_id"}],
            }], schema)
