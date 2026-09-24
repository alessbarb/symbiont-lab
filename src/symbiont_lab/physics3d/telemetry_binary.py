"""Exact binary codecs for Physics3D telemetry v4.1 layout revision 4."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from pathlib import Path
import struct
from typing import Any, BinaryIO, Iterable, Mapping

from .telemetry_compaction import (
    StateDiffer,
    StatePatcher,
    canonical_json_bytes,
)
from .telemetry_schema import EVENT_RULES, TemporalClass, event_mode
from .telemetry_structural import structural_view, logical_view


# Value tags. The format is intentionally small, deterministic and self-describing.
_NULL = 0
_FALSE = 1
_TRUE = 2
_INT = 3
_FLOAT64 = 4
_STRING = 5
_LIST = 6
_DICT = 7

_MODE_FULL = 0
_MODE_SPARSE = 1
_MODE_COPY = 2

_EVENT_SNAPSHOT = 0
_EVENT_EVENTS = 1
_EVENT_RESET = 2
_EVENT_APPEND_MANY = 3

_OP_SET = 0
_OP_REMOVE = 1


def encode_uvarint(value: int) -> bytes:
    value = int(value)
    if value < 0:
        raise ValueError("uvarint cannot encode a negative value")
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def decode_uvarint(data: bytes | bytearray | memoryview, offset: int = 0) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("truncated uvarint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7
        if shift > 70:
            raise ValueError("uvarint is too large")


def _encode_svarint(value: int) -> bytes:
    value = int(value)
    zigzag = (value << 1) if value >= 0 else ((-value << 1) - 1)
    return encode_uvarint(zigzag)


def _decode_svarint(data: bytes | bytearray | memoryview, offset: int) -> tuple[int, int]:
    raw, offset = decode_uvarint(data, offset)
    value = (raw >> 1) if not (raw & 1) else -((raw >> 1) + 1)
    return value, offset


def _read_uvarint(handle: BinaryIO) -> int | None:
    value = 0
    shift = 0
    first = True
    while True:
        raw = handle.read(1)
        if not raw:
            if first:
                return None
            raise ValueError("truncated record length")
        first = False
        byte = raw[0]
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value
        shift += 7
        if shift > 70:
            raise ValueError("record length varint is too large")


class BinaryStringTableWriter:
    """Append-only global UTF-8 dictionary; string IDs are 1-based positions."""

    def __init__(self, handle: BinaryIO) -> None:
        self.handle = handle
        self._ids: dict[str, int] = {}
        self.bytes_written = 0

    def id(self, value: str) -> int:
        value = str(value)
        existing = self._ids.get(value)
        if existing is not None:
            return existing
        identifier = len(self._ids) + 1
        self._ids[value] = identifier
        encoded = value.encode("utf-8")
        record = encode_uvarint(len(encoded)) + encoded
        self.handle.write(record)
        self.bytes_written += len(record)
        return identifier

    def __len__(self) -> int:
        return len(self._ids)


class BinaryStringTableReader:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._values: list[str] = [""]
        if not self.path.is_file():
            return
        with self.path.open("rb") as handle:
            while True:
                length = _read_uvarint(handle)
                if length is None:
                    break
                raw = handle.read(length)
                if len(raw) != length:
                    raise ValueError("truncated telemetry string table")
                self._values.append(raw.decode("utf-8"))

    def get(self, identifier: int) -> str:
        identifier = int(identifier)
        if identifier <= 0 or identifier >= len(self._values):
            raise ValueError(f"unknown telemetry string id: {identifier}")
        return self._values[identifier]

    def __len__(self) -> int:
        return len(self._values) - 1


class BinaryValueCodec:
    """Lossless JSON-domain value codec using string IDs and IEEE-754 float64."""

    def __init__(
        self,
        strings: BinaryStringTableWriter | BinaryStringTableReader,
    ) -> None:
        self.strings = strings

    def encode(self, value: Any) -> bytes:
        out = bytearray()
        self._encode_into(out, value)
        return bytes(out)

    def _encode_into(self, out: bytearray, value: Any) -> None:
        if value is None:
            out.append(_NULL)
            return
        if value is False:
            out.append(_FALSE)
            return
        if value is True:
            out.append(_TRUE)
            return
        if isinstance(value, int) and not isinstance(value, bool):
            out.append(_INT)
            out.extend(_encode_svarint(value))
            return
        if isinstance(value, float):
            out.append(_FLOAT64)
            out.extend(struct.pack(">d", value))
            return
        if isinstance(value, str):
            out.append(_STRING)
            out.extend(encode_uvarint(self.strings.id(value)))
            return
        if isinstance(value, (list, tuple)):
            out.append(_LIST)
            out.extend(encode_uvarint(len(value)))
            for item in value:
                self._encode_into(out, item)
            return
        if isinstance(value, Mapping):
            out.append(_DICT)
            keys = sorted(value, key=str)
            out.extend(encode_uvarint(len(keys)))
            for key in keys:
                out.extend(encode_uvarint(self.strings.id(str(key))))
                self._encode_into(out, value[key])
            return
        raise TypeError(f"unsupported telemetry value type: {type(value)!r}")

    def decode(
        self,
        data: bytes | bytearray | memoryview,
        offset: int = 0,
    ) -> tuple[Any, int]:
        if offset >= len(data):
            raise ValueError("truncated binary telemetry value")
        tag = data[offset]
        offset += 1
        if tag == _NULL:
            return None, offset
        if tag == _FALSE:
            return False, offset
        if tag == _TRUE:
            return True, offset
        if tag == _INT:
            return _decode_svarint(data, offset)
        if tag == _FLOAT64:
            end = offset + 8
            if end > len(data):
                raise ValueError("truncated float64")
            return struct.unpack(">d", bytes(data[offset:end]))[0], end
        if tag == _STRING:
            identifier, offset = decode_uvarint(data, offset)
            return self.strings.get(identifier), offset
        if tag == _LIST:
            count, offset = decode_uvarint(data, offset)
            result = []
            for _ in range(count):
                value, offset = self.decode(data, offset)
                result.append(value)
            return result, offset
        if tag == _DICT:
            count, offset = decode_uvarint(data, offset)
            result: dict[str, Any] = {}
            for _ in range(count):
                key_id, offset = decode_uvarint(data, offset)
                value, offset = self.decode(data, offset)
                result[self.strings.get(key_id)] = value
            return result, offset
        raise ValueError(f"unknown binary telemetry value tag: {tag}")


class BinaryRecordWriter:
    def __init__(self, handle: BinaryIO) -> None:
        self.handle = handle
        self.records = 0
        self.bytes_written = 0

    def append(self, payload: bytes) -> dict[str, Any]:
        prefix = encode_uvarint(len(payload))
        self.handle.write(prefix)
        self.handle.write(payload)
        self.records += 1
        self.bytes_written += len(prefix) + len(payload)
        return {
            "record_sha256": hashlib.sha256(payload).hexdigest(),
            "record_bytes": len(prefix) + len(payload),
        }


class BinaryRecordIterator:
    def __init__(
        self,
        handle: BinaryIO,
        decoder,
        *,
        start_offset: int = 0,
    ) -> None:
        self.handle = handle
        self.decoder = decoder
        self.handle.seek(int(start_offset))

    def next(self) -> dict[str, Any] | None:
        length = _read_uvarint(self.handle)
        if length is None:
            return None
        payload = self.handle.read(length)
        if len(payload) != length:
            raise ValueError("truncated binary telemetry record")
        item = self.decoder(payload)
        if not isinstance(item, dict):
            raise ValueError("binary telemetry decoder must return a mapping")
        item["__record_sha256"] = hashlib.sha256(payload).hexdigest()
        return item


def binary_record_hash(record: Mapping[str, Any]) -> str:
    digest = record.get("__record_sha256")
    if digest is None:
        raise ValueError("binary telemetry record has no physical hash")
    return str(digest)


def _exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, float):
        return struct.pack(">d", left) == struct.pack(">d", right)
    return left == right


def _template_and_values(value: Any) -> tuple[Any, list[Any]]:
    values: list[Any] = []

    def visit(item: Any) -> Any:
        if isinstance(item, Mapping):
            return (
                "d",
                tuple(
                    (str(key), visit(item[key]))
                    for key in sorted(item, key=str)
                ),
            )
        if isinstance(item, (list, tuple)):
            return ("l", tuple(visit(child) for child in item))
        values.append(deepcopy(item))
        return ("v",)

    return visit(value), values


def _inflate(template: Any, values: list[Any], index: list[int]) -> Any:
    tag = template[0]
    if tag == "v":
        current = index[0]
        index[0] += 1
        return deepcopy(values[current])
    if tag == "l":
        return [_inflate(child, values, index) for child in template[1]]
    if tag == "d":
        return {
            key: _inflate(child, values, index)
            for key, child in template[1]
        }
    raise ValueError(f"unknown binary frame template tag: {tag!r}")


def _encode_template(
    template: Any,
    strings: BinaryStringTableWriter,
) -> bytes:
    out = bytearray()

    def visit(node: Any) -> None:
        tag = node[0]
        if tag == "v":
            out.append(0)
            return
        if tag == "l":
            out.append(1)
            out.extend(encode_uvarint(len(node[1])))
            for child in node[1]:
                visit(child)
            return
        if tag == "d":
            out.append(2)
            out.extend(encode_uvarint(len(node[1])))
            for key, child in node[1]:
                out.extend(encode_uvarint(strings.id(key)))
                visit(child)
            return
        raise ValueError(f"unknown frame template tag: {tag!r}")

    visit(template)
    return bytes(out)


def _decode_template(
    data: bytes,
    strings: BinaryStringTableReader,
    offset: int = 0,
) -> tuple[Any, int]:
    if offset >= len(data):
        raise ValueError("truncated binary frame template")
    tag = data[offset]
    offset += 1
    if tag == 0:
        return ("v",), offset
    count, offset = decode_uvarint(data, offset)
    if tag == 1:
        children = []
        for _ in range(count):
            child, offset = _decode_template(data, strings, offset)
            children.append(child)
        return ("l", tuple(children)), offset
    if tag == 2:
        children = []
        for _ in range(count):
            key_id, offset = decode_uvarint(data, offset)
            child, offset = _decode_template(data, strings, offset)
            children.append((strings.get(key_id), child))
        return ("d", tuple(children)), offset
    raise ValueError(f"unknown binary frame template tag: {tag}")


class BinaryFrameSchemaWriter:
    def __init__(
        self,
        handle: BinaryIO,
        strings: BinaryStringTableWriter,
    ) -> None:
        self.strings = strings
        self._records = BinaryRecordWriter(handle)
        self._schemas: dict[tuple[str, Any], int] = {}

    def resolve(self, channel: str, template: Any) -> tuple[int, bool]:
        key = (str(channel), template)
        existing = self._schemas.get(key)
        if existing is not None:
            return existing, False
        schema_id = len(self._schemas) + 1
        self._schemas[key] = schema_id
        payload = (
            encode_uvarint(schema_id)
            + encode_uvarint(self.strings.id(channel))
            + _encode_template(template, self.strings)
        )
        self._records.append(payload)
        return schema_id, True

    def schema_id_for_value(self, channel: str, value: Any) -> int | None:
        template, _values = _template_and_values(value)
        return self._schemas.get((str(channel), template))


class BinaryFrameSchemaReader:
    def __init__(
        self,
        path: str | Path,
        strings: BinaryStringTableReader,
    ) -> None:
        self.strings = strings
        self.schemas: dict[int, tuple[str, Any]] = {}
        target = Path(path)
        if not target.is_file():
            return
        with target.open("rb") as handle:
            iterator = BinaryRecordIterator(handle, self._decode_record)
            while True:
                item = iterator.next()
                if item is None:
                    break
                schema_id = int(item["id"])
                if schema_id in self.schemas:
                    raise ValueError(f"duplicate binary frame schema: {schema_id}")
                self.schemas[schema_id] = (
                    str(item["channel"]),
                    item["template"],
                )

    def _decode_record(self, payload: bytes) -> dict[str, Any]:
        schema_id, offset = decode_uvarint(payload, 0)
        channel_id, offset = decode_uvarint(payload, offset)
        template, offset = _decode_template(payload, self.strings, offset)
        if offset != len(payload):
            raise ValueError("trailing bytes in frame schema record")
        return {
            "id": schema_id,
            "channel": self.strings.get(channel_id),
            "template": template,
        }

    def schema(self, schema_id: int) -> tuple[str, Any]:
        try:
            return self.schemas[int(schema_id)]
        except KeyError as exc:
            raise ValueError(f"unknown binary frame schema: {schema_id}") from exc

    def schema_id_for_value(self, channel: str, value: Any) -> int | None:
        template, _values = _template_and_values(value)
        for schema_id, (stored_channel, stored_template) in self.schemas.items():
            if stored_channel == channel and stored_template == template:
                return schema_id
        return None


class BinaryDenseWriter:
    def __init__(
        self,
        handle: BinaryIO,
        schemas: BinaryFrameSchemaWriter,
        strings: BinaryStringTableWriter,
    ) -> None:
        self.schemas = schemas
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self._records = BinaryRecordWriter(handle)
        self._previous: dict[str, tuple[int, list[Any], Any]] = {}
        self.schema_changes = 0

    def _header(
        self,
        tick: int,
        channel: str,
        schema_id: int,
        mode: int,
    ) -> bytes:
        return (
            encode_uvarint(tick)
            + encode_uvarint(self.strings.id(channel))
            + encode_uvarint(schema_id)
            + bytes((mode,))
        )

    def append(self, tick: int, channel: str, value: Any) -> dict[str, Any]:
        template, values = _template_and_values(value)
        schema_id, created = self.schemas.resolve(channel, template)
        if created:
            self.schema_changes += 1

        full = bytearray(self._header(tick, channel, schema_id, _MODE_FULL))
        full.extend(encode_uvarint(len(values)))
        for item in values:
            full.extend(self.codec.encode(item))

        payload = bytes(full)
        previous = self._previous.get(channel)
        if previous is not None and previous[0] == schema_id:
            changed = [
                (index, item)
                for index, item in enumerate(values)
                if index >= len(previous[1])
                or not _exact_equal(previous[1][index], item)
            ]
            sparse = bytearray(
                self._header(tick, channel, schema_id, _MODE_SPARSE)
            )
            sparse.extend(encode_uvarint(len(changed)))
            for index, item in changed:
                sparse.extend(encode_uvarint(index))
                sparse.extend(self.codec.encode(item))
            if len(sparse) < len(payload):
                payload = bytes(sparse)

        self._previous[channel] = (
            schema_id,
            deepcopy(values),
            deepcopy(value),
        )
        info = self._records.append(payload)
        return {
            "channel": str(channel),
            "schema_id": schema_id,
            "mode": payload[
                len(encode_uvarint(tick))
                + len(encode_uvarint(self.strings.id(channel)))
                + len(encode_uvarint(schema_id))
            ],
            **info,
        }

    def append_copy(
        self,
        tick: int,
        channel: str,
        value: Any,
        *,
        source_channel: str,
    ) -> dict[str, Any]:
        template, values = _template_and_values(value)
        schema_id, created = self.schemas.resolve(channel, template)
        if created:
            self.schema_changes += 1
        payload = (
            self._header(tick, channel, schema_id, _MODE_COPY)
            + encode_uvarint(self.strings.id(source_channel))
        )
        self._previous[channel] = (
            schema_id,
            deepcopy(values),
            deepcopy(value),
        )
        info = self._records.append(payload)
        return {
            "channel": channel,
            "schema_id": schema_id,
            "mode": _MODE_COPY,
            **info,
        }

    def drop(self, channel: str) -> None:
        self._previous.pop(str(channel), None)

    def schema_state(self) -> dict[str, int]:
        return {
            channel: schema_id
            for channel, (schema_id, _values, _logical) in self._previous.items()
        }

    @property
    def bytes_written(self) -> int:
        return self._records.bytes_written

    @property
    def records(self) -> int:
        return self._records.records


class BinaryDenseReader:
    def __init__(
        self,
        schemas: BinaryFrameSchemaReader,
        strings: BinaryStringTableReader,
    ) -> None:
        self.schemas = schemas
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self._previous: dict[str, tuple[int, list[Any]]] = {}
        self.values: dict[str, Any] = {}

    def decode_record(self, payload: bytes) -> dict[str, Any]:
        tick, offset = decode_uvarint(payload, 0)
        channel_id, offset = decode_uvarint(payload, offset)
        schema_id, offset = decode_uvarint(payload, offset)
        if offset >= len(payload):
            raise ValueError("truncated dense frame")
        mode = payload[offset]
        offset += 1
        record: dict[str, Any] = {
            "t": tick,
            "c": self.strings.get(channel_id),
            "s": schema_id,
            "m": mode,
        }
        if mode == _MODE_COPY:
            source_id, offset = decode_uvarint(payload, offset)
            record["f"] = self.strings.get(source_id)
        else:
            count, offset = decode_uvarint(payload, offset)
            values = []
            if mode == _MODE_FULL:
                for _ in range(count):
                    value, offset = self.codec.decode(payload, offset)
                    values.append(value)
            elif mode == _MODE_SPARSE:
                for _ in range(count):
                    index, offset = decode_uvarint(payload, offset)
                    value, offset = self.codec.decode(payload, offset)
                    values.append([index, value])
            else:
                raise ValueError(f"unknown binary dense mode: {mode}")
            record["v"] = values
        if offset != len(payload):
            raise ValueError("trailing bytes in dense frame")
        return record

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
            resolved = self.schemas.schema_id_for_value(channel, value)
        if resolved is None:
            raise ValueError(f"no binary frame schema for {channel!r}")
        stored_channel, stored_template = self.schemas.schema(resolved)
        if stored_channel != channel or stored_template != template:
            raise ValueError("anchor value does not match binary frame schema")
        self._previous[channel] = (resolved, deepcopy(values))
        self.values[channel] = deepcopy(value)

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel = str(record["c"])
        schema_id = int(record["s"])
        schema_channel, template = self.schemas.schema(schema_id)
        if schema_channel != channel:
            raise ValueError("binary frame schema channel mismatch")
        mode = int(record["m"])

        if mode == _MODE_COPY:
            source = str(record["f"])
            if source not in self.values:
                raise ValueError(f"binary copy source unavailable: {source!r}")
            value = deepcopy(self.values[source])
            source_template, values = _template_and_values(value)
            if source_template != template:
                raise ValueError("binary copy source shape mismatch")
        elif mode == _MODE_FULL:
            values = deepcopy(list(record.get("v", ())))
            value = _inflate(template, values, [0])
        elif mode == _MODE_SPARSE:
            previous = self._previous.get(channel)
            if previous is None or previous[0] != schema_id:
                raise ValueError(f"binary sparse frame has no base: {channel!r}")
            values = deepcopy(previous[1])
            for raw_index, item in record.get("v", ()):
                index = int(raw_index)
                if index < 0 or index >= len(values):
                    raise ValueError("binary sparse frame index out of range")
                values[index] = deepcopy(item)
            value = _inflate(template, values, [0])
        else:
            raise ValueError(f"unknown binary dense mode: {mode}")

        self._previous[channel] = (schema_id, deepcopy(values))
        self.values[channel] = deepcopy(value)
        return channel, value

    def drop(self, channel: str) -> None:
        channel = str(channel)
        self._previous.pop(channel, None)
        self.values.pop(channel, None)


class BinaryPathRegistryWriter:
    def __init__(
        self,
        handle: BinaryIO,
        strings: BinaryStringTableWriter,
    ) -> None:
        self.strings = strings
        self._records = BinaryRecordWriter(handle)
        self._paths: dict[tuple[str, str], int] = {}

    def resolve(self, channel: str, path: str) -> int:
        key = (str(channel), str(path))
        existing = self._paths.get(key)
        if existing is not None:
            return existing
        path_id = len(self._paths) + 1
        self._paths[key] = path_id
        payload = (
            encode_uvarint(path_id)
            + encode_uvarint(self.strings.id(channel))
            + encode_uvarint(self.strings.id(path))
        )
        self._records.append(payload)
        return path_id


class BinaryPathRegistryReader:
    def __init__(
        self,
        path: str | Path,
        strings: BinaryStringTableReader,
    ) -> None:
        self.strings = strings
        self._paths: dict[int, tuple[str, str]] = {}
        target = Path(path)
        if not target.is_file():
            return
        with target.open("rb") as handle:
            iterator = BinaryRecordIterator(handle, self._decode_record)
            while True:
                item = iterator.next()
                if item is None:
                    break
                identifier = int(item["id"])
                if identifier in self._paths:
                    raise ValueError(f"duplicate binary path id: {identifier}")
                self._paths[identifier] = (
                    str(item["channel"]),
                    str(item["path"]),
                )

    def _decode_record(self, payload: bytes) -> dict[str, Any]:
        identifier, offset = decode_uvarint(payload, 0)
        channel_id, offset = decode_uvarint(payload, offset)
        path_id, offset = decode_uvarint(payload, offset)
        if offset != len(payload):
            raise ValueError("trailing bytes in path registry record")
        return {
            "id": identifier,
            "channel": self.strings.get(channel_id),
            "path": self.strings.get(path_id),
        }

    def path(self, identifier: int, channel: str) -> str:
        try:
            stored_channel, path = self._paths[int(identifier)]
        except KeyError as exc:
            raise ValueError(f"unknown binary path id: {identifier}") from exc
        if stored_channel != str(channel):
            raise ValueError("binary path channel mismatch")
        return path


def _escape(segment: str) -> str:
    return str(segment).replace("~", "~0").replace("/", "~1")


def _diff(left: Any, right: Any, path: str = "") -> list[dict[str, Any]]:
    if type(left) is not type(right):
        return [{"op": "set", "path": path, "value": deepcopy(right)}]
    if isinstance(right, Mapping):
        operations: list[dict[str, Any]] = []
        for key in sorted(set(left) - set(right), key=str):
            operations.append(
                {"op": "remove", "path": f"{path}/{_escape(key)}"}
            )
        for key in sorted(right, key=str):
            child = f"{path}/{_escape(key)}"
            if key not in left:
                operations.append(
                    {
                        "op": "set",
                        "path": child,
                        "value": deepcopy(right[key]),
                    }
                )
            else:
                operations.extend(_diff(left[key], right[key], child))
        return operations
    if isinstance(right, list):
        if len(left) != len(right):
            return [{"op": "set", "path": path, "value": deepcopy(right)}]
        operations = []
        for index, (before, after) in enumerate(
            zip(left, right, strict=True)
        ):
            operations.extend(
                _diff(before, after, f"{path}/{index}")
            )
        return operations
    if not _exact_equal(left, right):
        return [{"op": "set", "path": path, "value": deepcopy(right)}]
    return []


class BinaryDeltaWriter:
    """Path-ID delta writer used for structural and fallback streams."""

    def __init__(
        self,
        handle: BinaryIO,
        paths: BinaryPathRegistryWriter,
        strings: BinaryStringTableWriter,
        *,
        transform=lambda value: value,
    ) -> None:
        self.paths = paths
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self._records = BinaryRecordWriter(handle)
        self.transform = transform
        self._previous: dict[str, Any] = {}
        self.operations = 0

    def append(
        self,
        tick: int,
        channel: str,
        value: Any,
    ) -> dict[str, Any] | None:
        channel = str(channel)
        current = self.transform(value)
        previous = self._previous.get(channel, {})
        operations = _diff(previous, current)
        self._previous[channel] = deepcopy(current)
        if not operations:
            return None

        payload = bytearray()
        payload.extend(encode_uvarint(tick))
        payload.extend(encode_uvarint(self.strings.id(channel)))
        payload.extend(encode_uvarint(len(operations)))
        for operation in operations:
            path_id = self.paths.resolve(channel, str(operation["path"]))
            if operation["op"] == "set":
                payload.append(_OP_SET)
                payload.extend(encode_uvarint(path_id))
                payload.extend(self.codec.encode(operation["value"]))
            else:
                payload.append(_OP_REMOVE)
                payload.extend(encode_uvarint(path_id))
        self.operations += len(operations)
        info = self._records.append(bytes(payload))
        return {
            "channel": channel,
            "operations": len(operations),
            **info,
        }

    @property
    def bytes_written(self) -> int:
        return self._records.bytes_written

    @property
    def records(self) -> int:
        return self._records.records

    @property
    def schema_changes(self) -> int:
        return 0

    def drop(self, channel: str) -> None:
        self._previous.pop(str(channel), None)

    def schema_state(self) -> dict[str, int]:
        return {}


class BinaryDeltaReader:
    def __init__(
        self,
        paths: BinaryPathRegistryReader,
        strings: BinaryStringTableReader,
        *,
        transform=lambda value: value,
        inverse=lambda value: value,
    ) -> None:
        self.paths = paths
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self.transform = transform
        self.inverse = inverse
        self._patcher = StatePatcher(object_store=None)
        self._stored: dict[str, Any] = {}
        self.values: dict[str, Any] = {}

    def decode_record(self, payload: bytes) -> dict[str, Any]:
        tick, offset = decode_uvarint(payload, 0)
        channel_id, offset = decode_uvarint(payload, offset)
        channel = self.strings.get(channel_id)
        count, offset = decode_uvarint(payload, offset)
        operations = []
        for _ in range(count):
            if offset >= len(payload):
                raise ValueError("truncated binary delta")
            opcode = payload[offset]
            offset += 1
            path_id, offset = decode_uvarint(payload, offset)
            path = self.paths.path(path_id, channel)
            if opcode == _OP_SET:
                value, offset = self.codec.decode(payload, offset)
                operations.append(
                    {"op": "set", "path": path, "value": value}
                )
            elif opcode == _OP_REMOVE:
                operations.append({"op": "remove", "path": path})
            else:
                raise ValueError(f"unknown binary delta opcode: {opcode}")
        if offset != len(payload):
            raise ValueError("trailing bytes in binary delta")
        return {"t": tick, "c": channel, "p": operations}

    def prime(
        self,
        channel: str,
        logical_value: Any,
        *,
        schema_id: int | None = None,
    ) -> None:
        del schema_id
        channel = str(channel)
        stored = self.transform(logical_value)
        self._stored[channel] = deepcopy(stored)
        self.values[channel] = deepcopy(logical_value)

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel = str(record["c"])
        current = self._stored.get(channel, {})
        current = self._patcher.apply(current, record.get("p", ()))
        logical = self.inverse(current)
        self._stored[channel] = current
        self.values[channel] = logical
        return channel, logical

    def drop(self, channel: str) -> None:
        channel = str(channel)
        self._stored.pop(channel, None)
        self.values.pop(channel, None)


class BinaryEventWriter:
    def __init__(
        self,
        handle: BinaryIO,
        strings: BinaryStringTableWriter,
    ) -> None:
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self._records = BinaryRecordWriter(handle)
        self._previous_cumulative: dict[str, list[Any]] = {}

    def append(self, tick: int, channel: str, value: Any) -> list[str]:
        mode = event_mode(channel)
        if not isinstance(value, (list, tuple)):
            operation = _EVENT_SNAPSHOT
            payload_value = deepcopy(value)
        else:
            current = [deepcopy(item) for item in value]
            if mode is TemporalClass.EVENT_EPHEMERAL:
                if not current:
                    return []
                operation = _EVENT_EVENTS
                payload_value = current
            else:
                previous = self._previous_cumulative.get(channel)
                if previous is None:
                    operation = _EVENT_RESET
                    payload_value = current
                else:
                    prefix = len(previous) <= len(current) and all(
                        canonical_json_bytes(left)
                        == canonical_json_bytes(right)
                        for left, right in zip(previous, current, strict=False)
                    )
                    if prefix:
                        appended = current[len(previous):]
                        if not appended:
                            self._previous_cumulative[channel] = current
                            return []
                        operation = _EVENT_APPEND_MANY
                        payload_value = appended
                    else:
                        operation = _EVENT_RESET
                        payload_value = current
                self._previous_cumulative[channel] = current

        payload = (
            encode_uvarint(tick)
            + encode_uvarint(self.strings.id(channel))
            + bytes((operation,))
            + self.codec.encode(payload_value)
        )
        info = self._records.append(payload)
        return [str(info["record_sha256"])]

    @property
    def bytes_written(self) -> int:
        return self._records.bytes_written

    @property
    def records(self) -> int:
        return self._records.records

    def drop(self, channel: str) -> None:
        self._previous_cumulative.pop(str(channel), None)


class BinaryEventReader:
    def __init__(
        self,
        strings: BinaryStringTableReader,
    ) -> None:
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self.values: dict[str, Any] = {}

    def decode_record(self, payload: bytes) -> dict[str, Any]:
        tick, offset = decode_uvarint(payload, 0)
        channel_id, offset = decode_uvarint(payload, offset)
        if offset >= len(payload):
            raise ValueError("truncated binary event")
        operation = payload[offset]
        offset += 1
        value, offset = self.codec.decode(payload, offset)
        if offset != len(payload):
            raise ValueError("trailing bytes in binary event")
        return {
            "t": tick,
            "c": self.strings.get(channel_id),
            "o": operation,
            "v": value,
        }

    def prime(self, events: Mapping[str, Any]) -> None:
        self.values = deepcopy(dict(events))

    def begin_tick(self, event_rules: Iterable[Any] = EVENT_RULES) -> None:
        for rule in event_rules:
            if (
                rule.temporal_class is TemporalClass.EVENT_EPHEMERAL
                and rule.channel in self.values
            ):
                self.values[rule.channel] = []

    def apply(self, record: Mapping[str, Any]) -> None:
        channel = str(record["c"])
        operation = int(record["o"])
        value = deepcopy(record.get("v"))
        if operation == _EVENT_SNAPSHOT:
            self.values[channel] = value
        elif operation == _EVENT_EVENTS:
            if not isinstance(value, list):
                raise ValueError("binary events payload must be a list")
            self.values[channel] = value
        elif operation == _EVENT_RESET:
            if not isinstance(value, list):
                raise ValueError("binary event reset must be a list")
            self.values[channel] = value
        elif operation == _EVENT_APPEND_MANY:
            if not isinstance(value, list):
                raise ValueError("binary event append must be a list")
            current = self.values.setdefault(channel, [])
            if not isinstance(current, list):
                raise ValueError("binary cumulative event channel is not a list")
            current.extend(value)
        else:
            raise ValueError(f"unknown binary event operation: {operation}")

    def drop(self, channel: str) -> None:
        self.values.pop(str(channel), None)


class BinaryStaticWriter:
    def __init__(
        self,
        handle: BinaryIO,
        strings: BinaryStringTableWriter,
    ) -> None:
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self._records = BinaryRecordWriter(handle)
        self._previous: dict[str, bytes] = {}

    def append(self, tick: int, channel: str, value: Any) -> str | None:
        digest = hashlib.sha256(canonical_json_bytes(value)).digest()
        if self._previous.get(channel) == digest:
            return None
        self._previous[channel] = digest
        payload = (
            encode_uvarint(tick)
            + encode_uvarint(self.strings.id(channel))
            + digest
            + self.codec.encode(value)
        )
        return str(self._records.append(payload)["record_sha256"])

    @property
    def bytes_written(self) -> int:
        return self._records.bytes_written

    @property
    def records(self) -> int:
        return self._records.records

    def drop(self, channel: str) -> None:
        self._previous.pop(str(channel), None)


class BinaryStaticReader:
    def __init__(self, strings: BinaryStringTableReader) -> None:
        self.strings = strings
        self.codec = BinaryValueCodec(strings)
        self.values: dict[str, Any] = {}

    def decode_record(self, payload: bytes) -> dict[str, Any]:
        tick, offset = decode_uvarint(payload, 0)
        channel_id, offset = decode_uvarint(payload, offset)
        end = offset + 32
        if end > len(payload):
            raise ValueError("truncated binary static digest")
        digest = bytes(payload[offset:end])
        value, offset = self.codec.decode(payload, end)
        if offset != len(payload):
            raise ValueError("trailing bytes in binary static record")
        if hashlib.sha256(canonical_json_bytes(value)).digest() != digest:
            raise ValueError("binary static value hash mismatch")
        return {
            "t": tick,
            "c": self.strings.get(channel_id),
            "v": value,
        }

    def prime(self, values: Mapping[str, Any]) -> None:
        self.values = deepcopy(dict(values))

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel = str(record["c"])
        value = deepcopy(record["v"])
        self.values[channel] = value
        return channel, value

    def drop(self, channel: str) -> None:
        self.values.pop(str(channel), None)


class BinaryTickBucket:
    def __init__(
        self,
        handle: BinaryIO,
        decoder,
        *,
        start_offset: int = 0,
    ) -> None:
        self.iterator = BinaryRecordIterator(
            handle,
            decoder,
            start_offset=start_offset,
        )
        self._pending: dict[str, Any] | None = None

    def take(self, tick: int) -> list[dict[str, Any]]:
        result = []
        while True:
            if self._pending is None:
                self._pending = self.iterator.next()
            if self._pending is None:
                break
            record_tick = int(self._pending.get("t", -1))
            if record_tick < tick:
                raise ValueError(
                    f"binary telemetry stream behind commit: {record_tick} < {tick}"
                )
            if record_tick > tick:
                break
            result.append(self._pending)
            self._pending = None
        return result


__all__ = [
    "BinaryDeltaReader",
    "BinaryDeltaWriter",
    "BinaryDenseReader",
    "BinaryDenseWriter",
    "BinaryEventReader",
    "BinaryEventWriter",
    "BinaryFrameSchemaReader",
    "BinaryFrameSchemaWriter",
    "BinaryPathRegistryReader",
    "BinaryPathRegistryWriter",
    "BinaryRecordIterator",
    "BinaryRecordWriter",
    "BinaryStaticReader",
    "BinaryStaticWriter",
    "BinaryStringTableReader",
    "BinaryStringTableWriter",
    "BinaryTickBucket",
    "BinaryValueCodec",
    "binary_record_hash",
    "decode_uvarint",
    "encode_uvarint",
]
