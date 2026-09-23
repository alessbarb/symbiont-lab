from __future__ import annotations

import io

from symbiont_lab.physics3d.telemetry_compaction import canonical_json_bytes
from symbiont_lab.physics3d.telemetry_numeric import (
    FrameSchemaRegistryReader,
    FrameSchemaRegistryWriter,
    FrameStreamReader,
    FrameStreamWriter,
)


def test_frame_stream_uses_sparse_values_without_losing_signed_zero(tmp_path):
    schema_path = tmp_path / "schemas.ndjson"
    frame_path = tmp_path / "frames.ndjson"
    with schema_path.open("w+", encoding="utf-8") as schemas, frame_path.open(
        "w+", encoding="utf-8"
    ) as frames:
        registry = FrameSchemaRegistryWriter(schemas)
        writer = FrameStreamWriter(frames, registry, stream_name="test")
        first = {"a": 0.0, "b": [1, 2, 3], "empty": {}}
        second = {"a": -0.0, "b": [1, 2, 4], "empty": {}}
        writer.append(1, "channel", first)
        writer.append(2, "channel", second)
        schemas.flush()
        frames.flush()

    registry = FrameSchemaRegistryReader(schema_path)
    reader = FrameStreamReader(registry)
    lines = [
        __import__("json").loads(line)
        for line in frame_path.read_text(encoding="utf-8").splitlines()
    ]
    channel, value = reader.apply(lines[0])
    assert channel == "channel"
    channel, value = reader.apply(lines[1])
    assert canonical_json_bytes(value) == canonical_json_bytes(second)
    assert lines[1]["m"] == "s"


def test_frame_schema_revises_only_when_shape_changes(tmp_path):
    schema_path = tmp_path / "schemas.ndjson"
    frame_path = tmp_path / "frames.ndjson"
    with schema_path.open("w+", encoding="utf-8") as schemas, frame_path.open(
        "w+", encoding="utf-8"
    ) as frames:
        registry = FrameSchemaRegistryWriter(schemas)
        writer = FrameStreamWriter(frames, registry, stream_name="test")
        a = writer.append(1, "c", {"x": 1, "items": [1, 2]})
        b = writer.append(2, "c", {"x": 2, "items": [3, 4]})
        c = writer.append(3, "c", {"x": 3, "items": [3, 4, 5]})

    assert a["schema_id"] == b["schema_id"]
    assert c["schema_id"] != b["schema_id"]
