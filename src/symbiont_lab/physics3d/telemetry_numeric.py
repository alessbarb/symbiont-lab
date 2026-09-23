"""Schema-backed lossless frame codec for telemetry v4.1."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping, TextIO

from .telemetry_compaction import canonical_json_bytes, payload_sha256


def _template_and_values(value: Any) -> tuple[Any, list[Any]]:
    values: list[Any] = []

    def visit(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {
                "d": [
                    [str(key), visit(item[key])]
                    for key in sorted(item, key=str)
                ]
            }
        if isinstance(item, list):
            return {"l": [visit(child) for child in item]}
        if isinstance(item, tuple):
            return {"l": [visit(child) for child in item]}
        index = len(values)
        values.append(deepcopy(item))
        return {"v": index}

    return visit(value), values


def _inflate(template: Any, values: list[Any]) -> Any:
    if not isinstance(template, Mapping):
        raise ValueError("invalid frame template")
    if "v" in template:
        index = int(template["v"])
        return deepcopy(values[index])
    if "d" in template:
        raw = template["d"]
        if not isinstance(raw, list):
            raise ValueError("invalid dictionary frame template")
        result: dict[str, Any] = {}
        for item in raw:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("invalid dictionary frame entry")
            result[str(item[0])] = _inflate(item[1], values)
        return result
    if "l" in template:
        raw = template["l"]
        if not isinstance(raw, list):
            raise ValueError("invalid list frame template")
        return [_inflate(child, values) for child in raw]
    raise ValueError("unknown frame template node")


def _exact_equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


class FrameSchemaRegistryWriter:
    """Deduplicate structural templates shared by dense/structural streams."""

    def __init__(self, handle: TextIO) -> None:
        self.handle = handle
        self._next_id = 1
        self._by_key: dict[tuple[str, str], int] = {}

    def resolve(self, channel: str, template: Any) -> tuple[int, bool]:
        digest = payload_sha256(template)
        key = (str(channel), digest)
        existing = self._by_key.get(key)
        if existing is not None:
            return existing, False
        schema_id = self._next_id
        self._next_id += 1
        self._by_key[key] = schema_id
        payload = {
            "id": schema_id,
            "channel": str(channel),
            "sha256": digest,
            "template": template,
        }
        self.handle.write(canonical_json_bytes(payload).decode("utf-8"))
        self.handle.write("\n")
        return schema_id, True

    def schema_id_for_value(self, channel: str, value: Any) -> int | None:
        template, _values = _template_and_values(value)
        return self._by_key.get((str(channel), payload_sha256(template)))


class FrameStreamWriter:
    """Write full or sparse scalar vectors against immutable shape schemas."""

    def __init__(
        self,
        handle: TextIO,
        registry: FrameSchemaRegistryWriter,
        *,
        stream_name: str,
    ) -> None:
        self.handle = handle
        self.registry = registry
        self.stream_name = str(stream_name)
        self._previous: dict[str, tuple[int, list[Any]]] = {}
        self.records = 0
        self.bytes_written = 0
        self.schema_changes = 0

    def append(self, tick: int, channel: str, value: Any) -> dict[str, Any]:
        template, values = _template_and_values(value)
        schema_id, created = self.registry.resolve(channel, template)
        if created:
            self.schema_changes += 1

        previous = self._previous.get(channel)
        full_record = {
            "t": int(tick),
            "c": str(channel),
            "s": schema_id,
            "m": "f",
            "v": values,
        }
        record = full_record
        if previous is not None and previous[0] == schema_id:
            changed = [
                [index, deepcopy(item)]
                for index, item in enumerate(values)
                if index >= len(previous[1])
                or not _exact_equal(previous[1][index], item)
            ]
            sparse_record = {
                "t": int(tick),
                "c": str(channel),
                "s": schema_id,
                "m": "s",
                "v": changed,
            }
            if len(canonical_json_bytes(sparse_record)) < len(
                canonical_json_bytes(full_record)
            ):
                record = sparse_record

        encoded = canonical_json_bytes(record)
        self.handle.write(encoded.decode("utf-8"))
        self.handle.write("\n")
        self._previous[channel] = (schema_id, deepcopy(values))
        self.records += 1
        self.bytes_written += len(encoded) + 1
        return {
            "channel": str(channel),
            "schema_id": schema_id,
            "mode": record["m"],
            "record_sha256": payload_sha256(record),
        }

    def schema_state(self) -> dict[str, int]:
        return {
            channel: schema_id
            for channel, (schema_id, _values) in self._previous.items()
        }


class FrameSchemaRegistryReader:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.schemas: dict[int, tuple[str, Any, str]] = {}
        self.by_key: dict[tuple[str, str], int] = {}
        if not self.path.is_file():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"invalid frame schema at line {line_no}")
                schema_id = int(item["id"])
                channel = str(item["channel"])
                template = item["template"]
                digest = str(item["sha256"])
                if payload_sha256(template) != digest:
                    raise ValueError(
                        f"frame schema hash mismatch at line {line_no}"
                    )
                if schema_id in self.schemas:
                    raise ValueError(f"duplicate frame schema id: {schema_id}")
                self.schemas[schema_id] = (channel, template, digest)
                self.by_key[(channel, digest)] = schema_id

    def schema(self, schema_id: int) -> tuple[str, Any]:
        try:
            channel, template, _digest = self.schemas[int(schema_id)]
            return channel, template
        except KeyError as exc:
            raise ValueError(f"unknown frame schema id: {schema_id}") from exc

    def schema_id_for_value(self, channel: str, value: Any) -> int | None:
        template, _values = _template_and_values(value)
        return self.by_key.get((str(channel), payload_sha256(template)))


class FrameStreamReader:
    """Stateful decoder for one frame stream."""

    def __init__(self, registry: FrameSchemaRegistryReader) -> None:
        self.registry = registry
        self._previous: dict[str, tuple[int, list[Any]]] = {}
        self.values: dict[str, Any] = {}

    def prime(
        self,
        channel: str,
        value: Any,
        *,
        schema_id: int | None = None,
    ) -> None:
        template, values = _template_and_values(value)
        resolved = schema_id
        if resolved is None:
            resolved = self.registry.schema_id_for_value(channel, value)
        if resolved is None:
            raise ValueError(
                f"no frame schema available to prime channel {channel!r}"
            )
        schema_channel, schema_template = self.registry.schema(resolved)
        if schema_channel != channel:
            raise ValueError("frame schema channel mismatch")
        if payload_sha256(template) != payload_sha256(schema_template):
            raise ValueError("anchor value does not match frame schema")
        self._previous[channel] = (resolved, deepcopy(values))
        self.values[channel] = deepcopy(value)

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel = str(record["c"])
        schema_id = int(record["s"])
        schema_channel, template = self.registry.schema(schema_id)
        if schema_channel != channel:
            raise ValueError("frame record/schema channel mismatch")
        mode = str(record["m"])
        raw_values = record.get("v")
        if mode == "f":
            if not isinstance(raw_values, list):
                raise ValueError("full frame values must be a list")
            values = deepcopy(raw_values)
        elif mode == "s":
            previous = self._previous.get(channel)
            if previous is None or previous[0] != schema_id:
                raise ValueError(
                    f"sparse frame has no matching base for {channel!r}"
                )
            values = deepcopy(previous[1])
            if not isinstance(raw_values, list):
                raise ValueError("sparse frame changes must be a list")
            for change in raw_values:
                if not isinstance(change, list) or len(change) != 2:
                    raise ValueError("invalid sparse frame change")
                index = int(change[0])
                if index < 0 or index >= len(values):
                    raise ValueError("sparse frame index out of range")
                values[index] = deepcopy(change[1])
        else:
            raise ValueError(f"unknown frame mode: {mode!r}")
        value = _inflate(template, values)
        self._previous[channel] = (schema_id, deepcopy(values))
        self.values[channel] = deepcopy(value)
        return channel, value


__all__ = [
    "FrameSchemaRegistryReader",
    "FrameSchemaRegistryWriter",
    "FrameStreamReader",
    "FrameStreamWriter",
]
