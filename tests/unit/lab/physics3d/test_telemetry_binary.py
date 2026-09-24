from __future__ import annotations

import math

from symbiont_lab.physics3d.telemetry_binary import (
    BinaryDeltaReader,
    BinaryDeltaWriter,
    BinaryDenseReader,
    BinaryDenseWriter,
    BinaryEventReader,
    BinaryEventWriter,
    BinaryFrameSchemaReader,
    BinaryFrameSchemaWriter,
    BinaryPathRegistryReader,
    BinaryPathRegistryWriter,
    BinaryRecordIterator,
    BinaryStringTableReader,
    BinaryStringTableWriter,
    BinaryValueCodec,
    decode_uvarint,
    encode_uvarint,
)
from symbiont_lab.physics3d.telemetry_compaction import canonical_json_bytes
from symbiont_lab.physics3d.telemetry_structural import logical_view, structural_view


def test_uvarint_round_trip_boundaries():
    for value in (0, 1, 127, 128, 255, 16_384, 2**32, 2**63 - 1):
        encoded = encode_uvarint(value)
        decoded, offset = decode_uvarint(encoded)
        assert decoded == value
        assert offset == len(encoded)


def test_binary_value_codec_round_trip_preserves_signed_zero(tmp_path):
    strings_path = tmp_path / "strings.bin"
    with strings_path.open("wb") as handle:
        strings = BinaryStringTableWriter(handle)
        codec = BinaryValueCodec(strings)
        payload = codec.encode(
            {
                "zero": 0.0,
                "negative_zero": -0.0,
                "ids": ["sense.signal.abc", "sense.signal.abc"],
                "nested": [None, True, False, 17, -9],
            }
        )

    reader_strings = BinaryStringTableReader(strings_path)
    decoded, offset = BinaryValueCodec(reader_strings).decode(payload)

    assert offset == len(payload)
    assert canonical_json_bytes(decoded) == canonical_json_bytes(
        {
            "zero": 0.0,
            "negative_zero": -0.0,
            "ids": ["sense.signal.abc", "sense.signal.abc"],
            "nested": [None, True, False, 17, -9],
        }
    )
    assert math.copysign(1.0, decoded["negative_zero"]) < 0


def test_binary_dense_full_sparse_and_copy_round_trip(tmp_path):
    strings_path = tmp_path / "strings.bin"
    schemas_path = tmp_path / "schemas.bin"
    frames_path = tmp_path / "frames.bin"

    with (
        strings_path.open("wb") as strings_handle,
        schemas_path.open("wb") as schema_handle,
        frames_path.open("wb") as frame_handle,
    ):
        strings = BinaryStringTableWriter(strings_handle)
        schemas = BinaryFrameSchemaWriter(schema_handle, strings)
        writer = BinaryDenseWriter(frame_handle, schemas, strings)
        first = {"x": 1.0, "y": [2.0, 3.0]}
        second = {"x": 1.5, "y": [2.0, 3.0]}
        writer.append(1, "post.physical", first)
        writer.append(2, "post.physical", second)
        writer.append_copy(
            3,
            "pre.physical",
            second,
            source_channel="post.physical",
        )

    strings = BinaryStringTableReader(strings_path)
    schemas = BinaryFrameSchemaReader(schemas_path, strings)
    reader = BinaryDenseReader(schemas, strings)

    records = []
    with frames_path.open("rb") as handle:
        iterator = BinaryRecordIterator(handle, reader.decode_record)
        while True:
            item = iterator.next()
            if item is None:
                break
            records.append(item)
            reader.apply(item)

    assert len(records) == 3
    assert records[1]["m"] == 1
    assert records[2]["m"] == 2
    assert reader.values["post.physical"] == second
    assert reader.values["pre.physical"] == second


def test_binary_structural_delta_round_trip_claim_growth(tmp_path):
    strings_path = tmp_path / "strings.bin"
    paths_path = tmp_path / "paths.bin"
    state_path = tmp_path / "state.bin"

    first = [
        {
            "signal_id": "signal.a",
            "claims": [
                {"claim_id": "claim.1", "status": "candidate", "count": 1}
            ],
        }
    ]
    second = [
        {
            "signal_id": "signal.a",
            "claims": [
                {"claim_id": "claim.1", "status": "supported", "count": 2},
                {"claim_id": "claim.2", "status": "candidate", "count": 1},
            ],
        }
    ]

    with (
        strings_path.open("wb") as strings_handle,
        paths_path.open("wb") as paths_handle,
        state_path.open("wb") as state_handle,
    ):
        strings = BinaryStringTableWriter(strings_handle)
        paths = BinaryPathRegistryWriter(paths_handle, strings)
        writer = BinaryDeltaWriter(
            state_handle,
            paths,
            strings,
            transform=structural_view,
        )
        writer.append(1, "runtime.signal_knowledge", first)
        writer.append(2, "runtime.signal_knowledge", second)

    strings = BinaryStringTableReader(strings_path)
    paths = BinaryPathRegistryReader(paths_path, strings)
    reader = BinaryDeltaReader(
        paths,
        strings,
        transform=structural_view,
        inverse=logical_view,
    )

    with state_path.open("rb") as handle:
        iterator = BinaryRecordIterator(handle, reader.decode_record)
        one = iterator.next()
        two = iterator.next()
        assert one is not None and two is not None
        reader.apply(one)
        _channel, restored = reader.apply(two)

    assert restored == second
    assert len(two["p"]) < 10


def test_binary_event_writer_batches_ephemeral_events(tmp_path):
    strings_path = tmp_path / "strings.bin"
    events_path = tmp_path / "events.bin"
    events = [
        {"kind": "one", "event_id": "e1"},
        {"kind": "two", "event_id": "e2"},
        {"kind": "three", "event_id": "e3"},
    ]

    with (
        strings_path.open("wb") as strings_handle,
        events_path.open("wb") as events_handle,
    ):
        strings = BinaryStringTableWriter(strings_handle)
        writer = BinaryEventWriter(events_handle, strings)
        hashes = writer.append(1, "runtime.knowledge_events", events)
        assert len(hashes) == 1

    strings = BinaryStringTableReader(strings_path)
    reader = BinaryEventReader(strings)
    with events_path.open("rb") as handle:
        iterator = BinaryRecordIterator(handle, reader.decode_record)
        record = iterator.next()
        assert record is not None
        assert iterator.next() is None
        reader.apply(record)

    assert reader.values["runtime.knowledge_events"] == events
