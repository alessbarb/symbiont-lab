"""Keyed structural path-delta codec for telemetry v4.1."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, TextIO

from .telemetry_compaction import StatePatcher, canonical_json_bytes, payload_sha256
from .telemetry_numeric import (
    FrameSchemaRegistryReader,
    FrameSchemaRegistryWriter,
    FrameStreamReader,
    FrameStreamWriter,
)

_ID_CANDIDATES = (
    "node_id",
    "primitive_id",
    "actuator_id",
    "percept_id",
    "signal_id",
    "concept_id",
    "record_id",
    "capability_id",
    "sensor_id",
    "effector_id",
    "claim_id",
    "id",
)


def _identity_token(value: Any) -> str:
    if value is None:
        return "n:"
    if isinstance(value, bool):
        return f"b:{int(value)}"
    if isinstance(value, int):
        return f"i:{value}"
    if isinstance(value, float):
        return f"f:{value!r}"
    return f"s:{value}"


def _key_tokens_for_list(
    items: list[Any],
) -> tuple[str, list[str]] | None:
    if not items or not all(isinstance(item, Mapping) for item in items):
        return None
    for candidate in _ID_CANDIDATES:
        if all(candidate in item for item in items):
            tokens = [_identity_token(item[candidate]) for item in items]
            if len(tokens) == len(set(tokens)):
                return candidate, tokens
    edge_fields = ("source_id", "target_id", "kind", "delay_ticks")
    if all(all(field in item for field in edge_fields) for item in items):
        tokens = [
            "edge:" + canonical_json_bytes([item[field] for field in edge_fields]).decode("utf-8")
            for item in items
        ]
        if len(tokens) == len(set(tokens)):
            return "edge", tokens
    return None


def structural_view(value: Any) -> Any:
    """Collision-free AST optimized for keyed temporal deltas."""
    if isinstance(value, Mapping):
        return {"@m": {str(key): structural_view(value[key]) for key in sorted(value, key=str)}}
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        keyed = _key_tokens_for_list(value)
        if keyed is None:
            return {"@l": [structural_view(item) for item in value]}
        label, tokens = keyed
        return {
            "@k": {
                "n": label,
                "o": list(tokens),
                "i": {
                    token: structural_view(dict(item))
                    for item, token in zip(value, tokens, strict=True)
                },
            }
        }
    return {"@v": deepcopy(value)}


def logical_view(value: Any) -> Any:
    if not isinstance(value, Mapping) or len(value) != 1:
        raise ValueError("invalid structural AST node")
    tag, payload = next(iter(value.items()))
    if tag == "@v":
        return deepcopy(payload)
    if tag == "@m":
        if not isinstance(payload, Mapping):
            raise ValueError("invalid structural mapping node")
        return {str(key): logical_view(child) for key, child in payload.items()}
    if tag == "@l":
        if not isinstance(payload, list):
            raise ValueError("invalid structural list node")
        return [logical_view(item) for item in payload]
    if tag == "@k":
        if not isinstance(payload, Mapping):
            raise ValueError("invalid keyed structural node")
        order = payload.get("o")
        items = payload.get("i")
        if not isinstance(order, list) or not isinstance(items, Mapping):
            raise ValueError("invalid keyed structural payload")
        result = []
        for raw_token in order:
            token = str(raw_token)
            if token not in items:
                raise ValueError(f"keyed structural item missing: {token!r}")
            result.append(logical_view(items[token]))
        return result
    raise ValueError(f"unknown structural AST tag: {tag!r}")


def _escape(segment: str) -> str:
    return str(segment).replace("~", "~0").replace("/", "~1")


def _equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _diff(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
    if type(left) is not type(right):
        return [{"op": "set", "path": path, "value": deepcopy(right)}]
    if isinstance(right, Mapping):
        operations: list[dict[str, Any]] = []
        for key in sorted(set(left) - set(right), key=str):
            operations.append({"op": "remove", "path": f"{path}/{_escape(key)}"})
        for key in sorted(right, key=str):
            child = f"{path}/{_escape(key)}"
            if key not in left:
                operations.append({"op": "set", "path": child, "value": deepcopy(right[key])})
            else:
                operations.extend(_diff(left[key], right[key], child))
        return operations
    if isinstance(right, list):
        if len(left) != len(right):
            return [{"op": "set", "path": path, "value": deepcopy(right)}]
        operations = []
        for index, (before, after) in enumerate(zip(left, right, strict=True)):
            operations.extend(_diff(before, after, f"{path}/{index}"))
        return operations
    if not _equal(left, right):
        return [{"op": "set", "path": path, "value": deepcopy(right)}]
    return []


class StructuralPathRegistryWriter:
    def __init__(self, handle: TextIO) -> None:
        self.handle = handle
        self._by_key: dict[tuple[str, str], int] = {}
        self._next_id = 1
        self.bytes_written = 0

    def resolve(self, channel: str, path: str) -> int:
        key = (str(channel), str(path))
        existing = self._by_key.get(key)
        if existing is not None:
            return existing
        path_id = self._next_id
        self._next_id += 1
        self._by_key[key] = path_id
        record = {"id": path_id, "c": key[0], "p": key[1]}
        encoded = canonical_json_bytes(record)
        self.handle.write(encoded.decode("utf-8"))
        self.handle.write("\n")
        self.bytes_written += len(encoded) + 1
        return path_id


class StructuralPathRegistryReader:
    def __init__(self, path: str | Path) -> None:
        self._paths: dict[int, tuple[str, str]] = {}
        target = Path(path)
        if not target.is_file():
            return
        with target.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                path_id = int(item["id"])
                if path_id in self._paths:
                    raise ValueError(f"duplicate structural path id at line {line_no}")
                self._paths[path_id] = (str(item["c"]), str(item["p"]))

    def path(self, path_id: int, channel: str) -> str:
        try:
            stored_channel, path = self._paths[int(path_id)]
        except KeyError as exc:
            raise ValueError(f"unknown structural path id: {path_id}") from exc
        if stored_channel != str(channel):
            raise ValueError("structural path channel mismatch")
        return path


class StructuralDeltaWriter:
    def __init__(self, handle: TextIO, registry: StructuralPathRegistryWriter) -> None:
        self.handle = handle
        self.registry = registry
        self._previous: dict[str, Any] = {}
        self.records = 0
        self.bytes_written = 0
        self.operations = 0

    @property
    def schema_changes(self) -> int:
        return 0

    def append(
        self,
        tick: int,
        channel: str,
        value: Any,
    ) -> dict[str, Any] | None:
        channel = str(channel)
        current = structural_view(value)
        previous = self._previous.get(channel, {})
        operations = _diff(previous, current)
        if not operations:
            self._previous[channel] = deepcopy(current)
            return None

        compact: list[list[Any]] = []
        for operation in operations:
            path_id = self.registry.resolve(channel, str(operation["path"]))
            if operation["op"] == "set":
                compact.append([0, path_id, operation["value"]])
            else:
                compact.append([1, path_id])
        record = {"t": int(tick), "c": channel, "p": compact}
        encoded = canonical_json_bytes(record)
        self.handle.write(encoded.decode("utf-8"))
        self.handle.write("\n")
        self._previous[channel] = deepcopy(current)
        self.records += 1
        self.operations += len(compact)
        self.bytes_written += len(encoded) + 1
        return {
            "channel": channel,
            "operations": len(compact),
            "record_sha256": payload_sha256(record),
        }

    def drop(self, channel: str) -> None:
        self._previous.pop(str(channel), None)

    def schema_state(self) -> dict[str, int]:
        return {}


class StructuralDeltaReader:
    def __init__(self, registry: StructuralPathRegistryReader) -> None:
        self.registry = registry
        self._patcher = StatePatcher(object_store=None)
        self._stored: dict[str, Any] = {}
        self.values: dict[str, Any] = {}

    def prime(self, channel: str, logical_value: Any, *, schema_id: int | None = None) -> None:
        del schema_id
        channel = str(channel)
        stored = structural_view(logical_value)
        self._stored[channel] = stored
        self.values[channel] = deepcopy(logical_value)

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel = str(record["c"])
        current = self._stored.get(channel, {})
        expanded = []
        for operation in record.get("p", ()):
            if not isinstance(operation, list) or len(operation) < 2:
                raise ValueError("invalid structural delta operation")
            code = int(operation[0])
            path = self.registry.path(int(operation[1]), channel)
            if code == 0:
                if len(operation) != 3:
                    raise ValueError("invalid structural set operation")
                expanded.append({"op": "set", "path": path, "value": operation[2]})
            elif code == 1:
                expanded.append({"op": "remove", "path": path})
            else:
                raise ValueError(f"unknown structural delta opcode: {code}")
        current = self._patcher.apply(current, expanded)
        logical = logical_view(current)
        self._stored[channel] = current
        self.values[channel] = logical
        return channel, logical

    def drop(self, channel: str) -> None:
        channel = str(channel)
        self._stored.pop(channel, None)
        self.values.pop(channel, None)


# Revision 1/2 reader compatibility.
_LEGACY_ID_CANDIDATES = tuple(candidate for candidate in _ID_CANDIDATES if candidate != "claim_id")


def _legacy_key_tokens_for_list(
    items: list[Any],
) -> tuple[str, list[str]] | None:
    if not items or not all(isinstance(item, Mapping) for item in items):
        return None
    for candidate in _LEGACY_ID_CANDIDATES:
        if all(candidate in item for item in items):
            tokens = [_identity_token(item[candidate]) for item in items]
            if len(tokens) == len(set(tokens)):
                return candidate, tokens
    edge_fields = ("source_id", "target_id", "kind", "delay_ticks")
    if all(all(field in item for field in edge_fields) for item in items):
        tokens = [
            "edge:" + canonical_json_bytes([item[field] for field in edge_fields]).decode("utf-8")
            for item in items
        ]
        if len(tokens) == len(set(tokens)):
            return "edge", tokens
    return None


def _legacy_structural_view(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {"@m": [[str(k), _legacy_structural_view(value[k])] for k in sorted(value, key=str)]}
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        keyed = _legacy_key_tokens_for_list(value)
        if keyed is None:
            return {"@l": [_legacy_structural_view(x) for x in value]}
        label, tokens = keyed
        pairs = [[t, _legacy_structural_view(dict(x))] for x, t in zip(value, tokens, strict=True)]
        pairs.sort(key=lambda pair: pair[0])
        return {f"@k:{label}": {"o": list(tokens), "i": pairs}}
    return {"@v": deepcopy(value)}


def _legacy_logical_view(value: Any) -> Any:
    if not isinstance(value, Mapping) or len(value) != 1:
        raise ValueError("invalid legacy structural AST")
    tag, payload = next(iter(value.items()))
    if tag == "@v":
        return deepcopy(payload)
    if tag == "@m":
        return {str(item[0]): _legacy_logical_view(item[1]) for item in payload}
    if tag == "@l":
        return [_legacy_logical_view(item) for item in payload]
    if isinstance(tag, str) and tag.startswith("@k:"):
        by_token = {str(item[0]): item[1] for item in payload["i"]}
        return [_legacy_logical_view(by_token[str(token)]) for token in payload["o"]]
    raise ValueError(f"unknown legacy structural tag: {tag!r}")


class LegacyStructuralStreamWriter:
    """Test/compatibility writer for v4.1 layout revisions 1 and 2."""

    def __init__(
        self,
        handle: TextIO,
        registry: FrameSchemaRegistryWriter,
    ) -> None:
        self._frames = FrameStreamWriter(
            handle,
            registry,
            stream_name="structural",
        )

    def append(self, tick: int, channel: str, value: Any) -> dict[str, Any]:
        return self._frames.append(
            tick,
            channel,
            _legacy_structural_view(value),
        )

    def drop(self, channel: str) -> None:
        self._frames.drop(channel)

    def schema_state(self) -> dict[str, int]:
        return self._frames.schema_state()


class LegacyStructuralStreamReader:
    def __init__(self, registry: FrameSchemaRegistryReader) -> None:
        self._frames = FrameStreamReader(registry)
        self.values: dict[str, Any] = {}

    def prime(self, channel: str, logical_value: Any, *, schema_id: int | None = None) -> None:
        self._frames.prime(channel, _legacy_structural_view(logical_value), schema_id=schema_id)
        self.values[channel] = deepcopy(logical_value)

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel, stored = self._frames.apply(record)
        logical = _legacy_logical_view(stored)
        self.values[channel] = logical
        return channel, logical

    def drop(self, channel: str) -> None:
        self._frames.drop(channel)
        self.values.pop(str(channel), None)


# Kept for source compatibility with tests/importers.
StructuralStreamWriter = StructuralDeltaWriter
StructuralStreamReader = StructuralDeltaReader

__all__ = [
    "LegacyStructuralStreamReader",
    "LegacyStructuralStreamWriter",
    "StructuralDeltaReader",
    "StructuralDeltaWriter",
    "StructuralPathRegistryReader",
    "StructuralPathRegistryWriter",
    "StructuralStreamReader",
    "StructuralStreamWriter",
    "logical_view",
    "structural_view",
]
