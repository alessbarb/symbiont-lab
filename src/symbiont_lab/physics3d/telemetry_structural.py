"""Keyed structural normalization for telemetry v4.1."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .telemetry_compaction import canonical_json_bytes
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
        tokens: list[str] = []
        valid = True
        for item in items:
            if candidate not in item:
                valid = False
                break
            tokens.append(_identity_token(item[candidate]))
        if valid and len(tokens) == len(set(tokens)):
            return candidate, tokens

    edge_fields = ("source_id", "target_id", "kind", "delay_ticks")
    if all(all(field in item for field in edge_fields) for item in items):
        tokens = [
            "edge:" + canonical_json_bytes(
                [item[field] for field in edge_fields]
            ).decode("utf-8")
            for item in items
        ]
        if len(tokens) == len(set(tokens)):
            return "edge", tokens
    return None


def structural_view(value: Any) -> Any:
    """Create a collision-free reversible AST with keyed-list normalization."""
    if isinstance(value, Mapping):
        return {
            "@m": [
                [str(key), structural_view(value[key])]
                for key in sorted(value, key=str)
            ]
        }
    if isinstance(value, tuple):
        value = list(value)
    if isinstance(value, list):
        keyed = _key_tokens_for_list(value)
        if keyed is None:
            return {"@l": [structural_view(item) for item in value]}
        key_label, tokens = keyed
        order = list(tokens)
        pairs = [
            [token, structural_view(dict(item))]
            for item, token in zip(value, tokens, strict=True)
        ]
        pairs.sort(key=lambda pair: pair[0])
        return {
            f"@k:{key_label}": {
                "o": order,
                "i": pairs,
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
        if not isinstance(payload, list):
            raise ValueError("invalid structural mapping node")
        result: dict[str, Any] = {}
        for item in payload:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("invalid structural mapping entry")
            result[str(item[0])] = logical_view(item[1])
        return result
    if tag == "@l":
        if not isinstance(payload, list):
            raise ValueError("invalid structural list node")
        return [logical_view(item) for item in payload]
    if isinstance(tag, str) and tag.startswith("@k:"):
        if not isinstance(payload, Mapping):
            raise ValueError("invalid keyed structural node")
        order = payload.get("o")
        items = payload.get("i")
        if not isinstance(order, list) or not isinstance(items, list):
            raise ValueError("invalid keyed structural payload")
        by_token: dict[str, Any] = {}
        for item in items:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("invalid keyed structural item")
            token = str(item[0])
            if token in by_token:
                raise ValueError("duplicate keyed structural token")
            by_token[token] = item[1]
        result = []
        for raw_token in order:
            token = str(raw_token)
            if token not in by_token:
                raise ValueError(
                    f"keyed structural item missing from order: {token!r}"
                )
            result.append(logical_view(by_token[token]))
        return result
    raise ValueError(f"unknown structural AST tag: {tag!r}")


class StructuralStreamWriter:
    def __init__(
        self,
        handle,
        registry: FrameSchemaRegistryWriter,
    ) -> None:
        self._frames = FrameStreamWriter(
            handle,
            registry,
            stream_name="structural",
        )

    @property
    def records(self) -> int:
        return self._frames.records

    @property
    def bytes_written(self) -> int:
        return self._frames.bytes_written

    @property
    def schema_changes(self) -> int:
        return self._frames.schema_changes

    def append(self, tick: int, channel: str, value: Any) -> dict[str, Any]:
        return self._frames.append(tick, channel, structural_view(value))

    def drop(self, channel: str) -> None:
        self._frames.drop(channel)

    def schema_state(self) -> dict[str, int]:
        return self._frames.schema_state()


class StructuralStreamReader:
    def __init__(self, registry: FrameSchemaRegistryReader) -> None:
        self._frames = FrameStreamReader(registry)
        self.values: dict[str, Any] = {}

    def prime(
        self,
        channel: str,
        logical_value: Any,
        *,
        schema_id: int | None = None,
    ) -> None:
        self._frames.prime(
            channel,
            structural_view(logical_value),
            schema_id=schema_id,
        )
        self.values[channel] = deepcopy(logical_value)

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel, stored = self._frames.apply(record)
        logical = logical_view(stored)
        self.values[channel] = logical
        return channel, logical

    def drop(self, channel: str) -> None:
        channel = str(channel)
        self._frames.drop(channel)
        self.values.pop(channel, None)


__all__ = [
    "StructuralStreamReader",
    "StructuralStreamWriter",
    "logical_view",
    "structural_view",
]
