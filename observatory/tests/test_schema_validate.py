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
