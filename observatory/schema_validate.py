"""Small structural JSON Schema validator for Observatory's own contracts.

The implementation intentionally covers only the Draft 2020-12 keywords
used by this repository, but every such keyword is enforced, including local
``$ref`` boundaries. It is a test helper, never an input sanitizer for the
runtime server.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate(value, schema, path="$", *, schema_root: str | Path | None = None, _ref_stack=()):
    if "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str):
            raise AssertionError(f"{path}: $ref must be a string")
        if schema_root is None:
            raise AssertionError(f"{path}: schema_root is required to resolve {ref!r}")
        root = Path(schema_root).resolve()
        target = (root / ref).resolve()
        if not (target == root or root in target.parents):
            raise AssertionError(f"{path}: $ref escapes schema root: {ref!r}")
        if target.suffix != ".json":
            raise AssertionError(f"{path}: only local JSON schema refs are supported")
        if target in _ref_stack:
            raise AssertionError(f"{path}: cyclic $ref detected at {ref!r}")
        try:
            resolved = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AssertionError(f"{path}: could not resolve $ref {ref!r}: {exc}") from exc
        validate(value, resolved, path, schema_root=root, _ref_stack=(*_ref_stack, target))
        schema = {key: subvalue for key, subvalue in schema.items() if key != "$ref"}
        if not schema:
            return

    if "const" in schema:
        _require(
            value == schema["const"], f"{path}: expected const {schema['const']!r}, got {value!r}"
        )

    if "allOf" in schema:
        _require(isinstance(schema["allOf"], list), f"{path}: allOf must be an array")
        for subschema in schema["allOf"]:
            validate(value, subschema, path, schema_root=schema_root, _ref_stack=_ref_stack)

    if "anyOf" in schema:
        _require(
            isinstance(schema["anyOf"], list) and schema["anyOf"],
            f"{path}: anyOf must be a non-empty array",
        )
        failures = []
        for subschema in schema["anyOf"]:
            try:
                validate(value, subschema, path, schema_root=schema_root, _ref_stack=_ref_stack)
            except AssertionError as exc:
                failures.append(str(exc))
            else:
                break
        else:
            raise AssertionError(f"{path}: value did not match anyOf: {'; '.join(failures)}")

    if "not" in schema:
        try:
            validate(value, schema["not"], path, schema_root=schema_root, _ref_stack=_ref_stack)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"{path}: value matched forbidden 'not' schema")

    if "if" in schema:
        try:
            validate(value, schema["if"], path, schema_root=schema_root, _ref_stack=_ref_stack)
        except AssertionError:
            if "else" in schema:
                validate(
                    value, schema["else"], path, schema_root=schema_root, _ref_stack=_ref_stack
                )
        else:
            if "then" in schema:
                validate(
                    value, schema["then"], path, schema_root=schema_root, _ref_stack=_ref_stack
                )

    schema_type = schema.get("type")
    if schema_type is not None:
        types = schema_type if isinstance(schema_type, list) else [schema_type]
        type_map = {
            "object": dict,
            "array": list,
            "string": str,
            "boolean": bool,
            "integer": int,
            "number": (int, float),
            "null": type(None),
        }
        ok = False
        for candidate in types:
            py_type = type_map[candidate]
            if candidate == "integer":
                ok = ok or (isinstance(value, int) and not isinstance(value, bool))
            elif candidate == "number":
                ok = ok or (isinstance(value, (int, float)) and not isinstance(value, bool))
            else:
                ok = ok or isinstance(value, py_type)
        _require(
            ok, f"{path}: expected type {schema_type!r}, got {type(value).__name__} ({value!r})"
        )

    if "enum" in schema:
        _require(value in schema["enum"], f"{path}: {value!r} not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema:
            _require(value >= schema["minimum"], f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema:
            _require(value <= schema["maximum"], f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, str):
        if "maxLength" in schema:
            _require(
                len(value) <= schema["maxLength"],
                f"{path}: length {len(value)} exceeds maxLength {schema['maxLength']}",
            )
        if "minLength" in schema:
            _require(
                len(value) >= schema["minLength"],
                f"{path}: length {len(value)} is below minLength {schema['minLength']}",
            )
        if "pattern" in schema:
            _require(
                re.search(schema["pattern"], value) is not None,
                f"{path}: {value!r} does not match pattern {schema['pattern']!r}",
            )

    if isinstance(value, dict):
        if "maxProperties" in schema:
            _require(
                len(value) <= schema["maxProperties"],
                f"{path}: {len(value)} properties exceeds maxProperties {schema['maxProperties']}",
            )
        if "minProperties" in schema:
            _require(
                len(value) >= schema["minProperties"],
                f"{path}: {len(value)} properties is below minProperties {schema['minProperties']}",
            )
        for key in schema.get("required", []):
            _require(key in value, f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unexpected = set(value) - set(properties)
            _require(
                not unexpected,
                f"{path}: unexpected propert{'y' if len(unexpected) == 1 else 'ies'} {sorted(unexpected)}",
            )
        for key, subvalue in value.items():
            if key in properties:
                validate(
                    subvalue,
                    properties[key],
                    f"{path}.{key}",
                    schema_root=schema_root,
                    _ref_stack=_ref_stack,
                )
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(
                    subvalue,
                    schema["additionalProperties"],
                    f"{path}.{key}",
                    schema_root=schema_root,
                    _ref_stack=_ref_stack,
                )

    if isinstance(value, list):
        if "maxItems" in schema:
            _require(
                len(value) <= schema["maxItems"],
                f"{path}: {len(value)} items exceeds maxItems {schema['maxItems']}",
            )
        if "minItems" in schema:
            _require(
                len(value) >= schema["minItems"],
                f"{path}: {len(value)} items is fewer than minItems {schema['minItems']}",
            )
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate(
                    item,
                    item_schema,
                    f"{path}[{index}]",
                    schema_root=schema_root,
                    _ref_stack=_ref_stack,
                )
