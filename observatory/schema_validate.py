"""A small, dependency-free structural JSON Schema validator covering the
subset this project's own schemas actually use: type, additionalProperties,
required, properties, items, enum, const, minimum/maximum, minItems/maxItems,
maxLength, and if/then/else. Raises AssertionError with the failing path on
the first violation."""

from __future__ import annotations


def validate(value, schema, path="$"):
    if "const" in schema:
        assert value == schema["const"], f"{path}: expected const {schema['const']!r}, got {value!r}"
        return

    if "if" in schema:
        try:
            validate(value, schema["if"], path)
        except AssertionError:
            if "else" in schema:
                validate(value, schema["else"], path)
        else:
            if "then" in schema:
                validate(value, schema["then"], path)
        # if/then/else has been fully handled for this schema node; the
        # remaining unconditional keywords (type, properties, ...) on this
        # same schema object still apply below, so fall through rather
        # than returning.

    schema_type = schema.get("type")
    if schema_type is not None:
        types = schema_type if isinstance(schema_type, list) else [schema_type]
        type_map = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float), "null": type(None)}
        ok = False
        for candidate in types:
            py_type = type_map[candidate]
            if candidate == "integer":
                ok = ok or (isinstance(value, int) and not isinstance(value, bool))
            elif candidate == "number":
                ok = ok or (isinstance(value, (int, float)) and not isinstance(value, bool))
            else:
                ok = ok or isinstance(value, py_type)
        assert ok, f"{path}: expected type {schema_type!r}, got {type(value).__name__} ({value!r})"

    if "enum" in schema:
        assert value in schema["enum"], f"{path}: {value!r} not in enum {schema['enum']!r}"

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            assert value >= schema["minimum"], f"{path}: {value} < minimum {schema['minimum']}"
        if "maximum" in schema:
            assert value <= schema["maximum"], f"{path}: {value} > maximum {schema['maximum']}"

    if isinstance(value, str) and "maxLength" in schema:
        assert len(value) <= schema["maxLength"], f"{path}: length {len(value)} exceeds maxLength {schema['maxLength']}"

    if isinstance(value, dict):
        for key in schema.get("required", []):
            assert key in value, f"{path}: missing required property {key!r}"
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unexpected = set(value) - set(properties)
            assert not unexpected, f"{path}: unexpected propert{'y' if len(unexpected) == 1 else 'ies'} {sorted(unexpected)}"
        for key, subvalue in value.items():
            if key in properties:
                validate(subvalue, properties[key], f"{path}.{key}")

    if isinstance(value, list):
        if "maxItems" in schema:
            assert len(value) <= schema["maxItems"], f"{path}: {len(value)} items exceeds maxItems {schema['maxItems']}"
        if "minItems" in schema:
            assert len(value) >= schema["minItems"], f"{path}: {len(value)} items is fewer than minItems {schema['minItems']}"
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate(item, item_schema, f"{path}[{index}]")
