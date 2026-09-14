import unittest

from observatory.schema_validate import validate


class SchemaValidateIfThenTests(unittest.TestCase):
    def test_if_then_else_branches_are_enforced(self):
        schema = {
            "type": "object",
            "if": {"properties": {"version": {"const": 1}}},
            "then": {"properties": {"extra": {"type": "null"}}},
            "else": {"required": ["extra"]},
        }
        validate({"version": 1, "extra": None}, schema)  # then-branch, should not raise
        validate({"version": 2, "extra": "present"}, schema)  # else-branch, should not raise
        with self.assertRaises(AssertionError):
            validate({"version": 2}, schema)  # else-branch requires "extra"


if __name__ == "__main__":
    unittest.main()
