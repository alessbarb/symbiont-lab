"""Telemetry v4.1: typed temporal streams with exact reconstruction."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import threading
from typing import Any, Iterator, Mapping, TextIO
import uuid

from .telemetry_compaction import (
    ObjectStore,
    StateDiffer,
    StatePatcher,
    canonical_json_bytes,
    payload_sha256,
)
from .telemetry_events import EventStreamReader, EventStreamWriter
from .telemetry_numeric import (
    FrameSchemaRegistryReader,
    FrameSchemaRegistryWriter,
    FrameStreamReader,
    FrameStreamWriter,
)
from .telemetry_schema import (
    EVENT_RULES,
    TemporalClass,
    partition_state,
    reassemble_state,
)
from .telemetry_structural import StructuralStreamReader, StructuralStreamWriter


SCHEMA_VERSION = "4.1"
ENVELOPE_TYPE = "symbiont-physics3d-telemetry"
ZERO_HASH = "0" * 64


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_mapping(record: Any) -> dict[str, Any]:
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, Mapping):
        return dict(record)
    raise TypeError("telemetry record must be a dataclass or mapping")


def _write_json(path: Path, payload: Mapping[str, Any], *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        encoded = canonical_json_bytes(dict(payload)).decode("utf-8") + "\n"
    else:
        encoded = json.dumps(
            dict(payload),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)


def _append_line(handle: TextIO, payload: Mapping[str, Any]) -> int:
    encoded = canonical_json_bytes(payload).decode("utf-8")
    handle.write(encoded)
    handle.write("\n")
    return len(encoded.encode("utf-8")) + 1


def _stream_offsets(handles: Mapping[str, TextIO]) -> dict[str, int]:
    return {name: int(handle.tell()) for name, handle in handles.items()}


def _exact_equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


class _StaticStreamWriter:
    def __init__(self, handle: TextIO, object_store: ObjectStore) -> None:
        self.handle = handle
        self.object_store = object_store
        self._previous_hash: dict[str, str] = {}
        self.records = 0
        self.bytes_written = 0

    def append(self, tick: int, channel: str, value: Any) -> str | None:
        digest, _created = self.object_store.put(value)
        if self._previous_hash.get(channel) == digest:
            return None
        record = {"t": int(tick), "c": str(channel), "h": digest}
        self.bytes_written += _append_line(self.handle, record)
        self.records += 1
        self._previous_hash[channel] = digest
        return payload_sha256(record)

    def drop(self, channel: str) -> None:
        self._previous_hash.pop(str(channel), None)

    def prime_hashes(self) -> dict[str, str]:
        return dict(self._previous_hash)


class _StaticStreamReader:
    def __init__(self, object_store: ObjectStore) -> None:
        self.object_store = object_store
        self.values: dict[str, Any] = {}

    def prime(self, values: Mapping[str, Any]) -> None:
        self.values = deepcopy(dict(values))

    def apply(self, record: Mapping[str, Any]) -> tuple[str, Any]:
        channel = str(record["c"])
        value = self.object_store.get(str(record["h"]))
        self.values[channel] = value
        return channel, value

    def drop(self, channel: str) -> None:
        self.values.pop(str(channel), None)


class _FallbackWriter:
    def __init__(self, handle: TextIO) -> None:
        self.handle = handle
        self._differ = StateDiffer(object_store=None)
        self._previous: dict[str, Any] = {}
        self.records = 0
        self.bytes_written = 0
        self.operations = 0

    def append(self, tick: int, value: Mapping[str, Any]) -> dict[str, Any] | None:
        current = dict(value)
        patch = self._differ.diff(self._previous, current)
        self._previous = deepcopy(current)
        if not patch:
            return None
        record = {"t": int(tick), "p": patch}
        self.bytes_written += _append_line(self.handle, record)
        self.records += 1
        self.operations += len(patch)
        return {
            "record_sha256": payload_sha256(record),
            "operations": len(patch),
        }


class _TickBucket:
    """Consume a sorted NDJSON stream one tick at a time with constant memory."""

    def __init__(self, handle: TextIO, *, start_offset: int = 0) -> None:
        self.handle = handle
        self.handle.seek(int(start_offset))
        self._pending: dict[str, Any] | None = None

    def _next(self) -> dict[str, Any] | None:
        while True:
            line = self.handle.readline()
            if not line:
                return None
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("telemetry stream record must be an object")
            return item

    def take(self, tick: int) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        while True:
            if self._pending is None:
                self._pending = self._next()
            if self._pending is None:
                break
            record_tick = int(self._pending.get("t", -1))
            if record_tick < tick:
                raise ValueError(
                    f"telemetry stream advanced behind committed tick: {record_tick} < {tick}"
                )
            if record_tick > tick:
                break
            result.append(self._pending)
            self._pending = None
        return result


class TelemetryV41Writer:
    """Lossless typed-stream writer. It never feeds observer data back to Symbiont."""

    def __init__(
        self,
        root: str | Path,
        *,
        organism_id: str,
        start_tick: int,
        seed: int,
        physics_hz: int,
        cognition_hz: int,
        embodiment_mode: str,
        effective_configuration: Mapping[str, Any] | None = None,
        software_identity: Mapping[str, Any] | None = None,
        snapshot_interval: int = 1024,
        flush_every: int = 64,
        run_id: str | None = None,
    ) -> None:
        if snapshot_interval < 1:
            raise ValueError("snapshot_interval must be >= 1")
        if flush_every < 1:
            raise ValueError("flush_every must be >= 1")
        generated = (
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid.uuid4().hex[:12]}"
        )
        self.run_id = run_id or generated
        self.root = Path(root).expanduser() / self.run_id
        self.root.mkdir(parents=True, exist_ok=False)

        for directory in (
            "schemas",
            "frames",
            "structures",
            "events",
            "anchors",
            "checkpoints",
            "objects/sha256",
            "indexes",
        ):
            (self.root / directory).mkdir(parents=True, exist_ok=True)

        self._handles: dict[str, TextIO] = {
            "schemas": (self.root / "schemas" / "frames.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "dense": (self.root / "frames" / "dense.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "summary": (self.root / "frames" / "summary.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "structural": (self.root / "structures" / "state.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "events": (self.root / "events" / "events.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "static": (self.root / "structures" / "static.ndjson").open(
                "a", encoding="utf-8", buffering=32768, newline="\n"
            ),
            "fallback": (self.root / "frames" / "fallback.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "ticks": (self.root / "ticks.ndjson").open(
                "a", encoding="utf-8", buffering=65536, newline="\n"
            ),
            "anchor_index": (self.root / "indexes" / "anchors.ndjson").open(
                "a", encoding="utf-8", buffering=8192, newline="\n"
            ),
        }

        self._registry = FrameSchemaRegistryWriter(self._handles["schemas"])
        self._dense = FrameStreamWriter(
            self._handles["dense"], self._registry, stream_name="dense"
        )
        self._summary = FrameStreamWriter(
            self._handles["summary"], self._registry, stream_name="summary"
        )
        self._structural = StructuralStreamWriter(
            self._handles["structural"], self._registry
        )
        self._events = EventStreamWriter(self._handles["events"])
        self._objects = ObjectStore(self.root / "objects" / "sha256")
        self._static = _StaticStreamWriter(self._handles["static"], self._objects)
        self._fallback = _FallbackWriter(self._handles["fallback"])

        self._snapshot_interval = int(snapshot_interval)
        self._flush_every = int(flush_every)
        self._pending = 0
        self._sequence = 0
        self._previous_commit_hash = ZERO_HASH
        self._last_tick: int | None = None
        self._anchor_count = 0
        self._checkpoint_count = 0
        self._previous_presence = {
            "dense": set(),
            "structural": set(),
            "events": set(),
            "static": set(),
        }
        config = dict(effective_configuration or {})
        software = dict(software_identity or {})
        self.manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "envelope_type": ENVELOPE_TYPE,
            "run_id": self.run_id,
            "organism_id": str(organism_id),
            "status": "open",
            "started_at_utc": _utc_now(),
            "ended_at_utc": None,
            "start_tick": int(start_tick),
            "first_recorded_tick": None,
            "end_tick": None,
            "last_committed_tick": None,
            "seed": int(seed),
            "physics_hz": int(physics_hz),
            "cognition_hz": int(cognition_hz),
            "physics_substeps_per_tick": int(physics_hz // cognition_hz),
            "embodiment_mode": str(embodiment_mode),
            "anchor_interval": self._snapshot_interval,
            "effective_configuration": config,
            "effective_configuration_sha256": payload_sha256(config),
            "software_identity": software,
            "software_identity_sha256": payload_sha256(software),
            "storage_model": "typed-temporal-streams",
            "integrity": "tick-commit-sha256+state-sha256",
            "tick_records": 0,
            "anchors": 0,
            "checkpoints": 0,
            "final_commit_hash": None,
            "compaction": {},
        }
        _write_json(self.root / "manifest.json", self.manifest)

    def needs_snapshot(self, tick: int) -> bool:
        return self._sequence == 0 or int(tick) % self._snapshot_interval == 0

    def _write_checkpoint(
        self,
        tick: int,
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "tick": int(tick),
            "snapshot": deepcopy(dict(snapshot)),
        }
        digest = payload_sha256(payload)
        payload["checkpoint_sha256"] = digest
        filename = f"tick-{tick:012d}.json"
        _write_json(
            self.root / "checkpoints" / filename,
            payload,
            compact=True,
        )
        self._checkpoint_count += 1
        return {
            "path": f"checkpoints/{filename}",
            "sha256": digest,
        }

    def _write_anchor(
        self,
        *,
        tick: int,
        state: Mapping[str, Any],
        summary: Mapping[str, Any],
        stream_offsets: Mapping[str, int],
        tick_offset: int,
        commit_hash: str,
    ) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "tick": int(tick),
            "state": deepcopy(dict(state)),
            "summary": deepcopy(dict(summary)),
            "schemas": {
                "dense": self._dense.schema_state(),
                "structural": self._structural.schema_state(),
                "summary": self._summary.schema_state().get("summary"),
            },
            "stream_offsets": {
                key: int(value)
                for key, value in stream_offsets.items()
                if key not in ("ticks", "schemas", "anchor_index")
            },
            "ticks_offset": int(tick_offset),
            "commit_hash": str(commit_hash),
        }
        digest = payload_sha256(payload)
        payload["anchor_sha256"] = digest
        filename = f"tick-{tick:012d}.json"
        _write_json(self.root / "anchors" / filename, payload, compact=True)
        _append_line(
            self._handles["anchor_index"],
            {
                "tick": int(tick),
                "path": f"anchors/{filename}",
                "sha256": digest,
            },
        )
        self._anchor_count += 1

    def append(
        self,
        record: Any,
        *,
        rich_state: Mapping[str, Any],
        full_snapshot: Mapping[str, Any] | None = None,
    ) -> None:
        summary = _record_mapping(record)
        state = dict(rich_state)
        tick = int(summary["tick"])
        rich_tick = state.get("tick")
        if rich_tick is not None and int(rich_tick) != tick:
            raise ValueError(f"rich telemetry tick mismatch: {rich_tick} != {tick}")
        if self._last_tick is not None and tick <= self._last_tick:
            raise ValueError(
                f"telemetry ticks must be strictly increasing: {tick} <= {self._last_tick}"
            )

        partition = partition_state(state)
        emitted_hashes: dict[str, list[str]] = {
            "dense": [],
            "summary": [],
            "structural": [],
            "events": [],
            "static": [],
            "fallback": [],
        }

        for channel, value in partition.dense.items():
            info = self._dense.append(tick, channel, value)
            emitted_hashes["dense"].append(str(info["record_sha256"]))

        for channel, value in partition.structural.items():
            info = self._structural.append(tick, channel, value)
            emitted_hashes["structural"].append(str(info["record_sha256"]))

        for channel, value in partition.events.items():
            emitted_hashes["events"].extend(
                self._events.append(tick, channel, value)
            )

        for channel, value in partition.static.items():
            digest = self._static.append(tick, channel, value)
            if digest is not None:
                emitted_hashes["static"].append(digest)

        fallback_info = self._fallback.append(tick, partition.fallback)
        if fallback_info is not None:
            emitted_hashes["fallback"].append(
                str(fallback_info["record_sha256"])
            )

        summary_info = self._summary.append(tick, "summary", summary)
        emitted_hashes["summary"].append(
            str(summary_info["record_sha256"])
        )

        removed = {
            "dense": sorted(
                self._previous_presence["dense"] - set(partition.dense)
            ),
            "structural": sorted(
                self._previous_presence["structural"] - set(partition.structural)
            ),
            "events": sorted(
                self._previous_presence["events"] - set(partition.events)
            ),
            "static": sorted(
                self._previous_presence["static"] - set(partition.static)
            ),
        }
        for channel in removed["dense"]:
            self._dense.drop(channel)
        for channel in removed["structural"]:
            self._structural.drop(channel)
        for channel in removed["events"]:
            self._events.drop(channel)
        for channel in removed["static"]:
            self._static.drop(channel)

        self._previous_presence = {
            "dense": set(partition.dense),
            "structural": set(partition.structural),
            "events": set(partition.events),
            "static": set(partition.static),
        }

        checkpoint_ref = None
        if full_snapshot is not None:
            checkpoint_ref = self._write_checkpoint(tick, full_snapshot)

        for name, handle in self._handles.items():
            if name not in ("ticks", "anchor_index"):
                handle.flush()

        offsets = _stream_offsets(self._handles)
        tick_offset = int(self._handles["ticks"].tell())
        should_anchor = self.needs_snapshot(tick)

        commit_without_hash = {
            "schema_version": SCHEMA_VERSION,
            "envelope_type": ENVELOPE_TYPE,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "tick": tick,
            "previous_commit_hash": self._previous_commit_hash,
            "state_sha256": payload_sha256(state),
            "summary_sha256": payload_sha256(summary),
            "anchor": bool(should_anchor),
            "checkpoint": checkpoint_ref,
            "removed_channels": removed,
            "present_channels": {
                "dense": sorted(partition.dense),
                "structural": sorted(partition.structural),
                "events": sorted(partition.events),
                "static": sorted(partition.static),
            },
            "stream_offsets": {
                key: int(value)
                for key, value in offsets.items()
                if key not in ("ticks", "anchor_index")
            },
            "stream_records": emitted_hashes,
        }
        commit_hash = payload_sha256(commit_without_hash)
        commit = dict(commit_without_hash)
        commit["commit_hash"] = commit_hash

        if should_anchor:
            self._write_anchor(
                tick=tick,
                state=state,
                summary=summary,
                stream_offsets=offsets,
                tick_offset=tick_offset,
                commit_hash=commit_hash,
            )

        # Commit record is deliberately last: bytes after the previous commit
        # are not evidence until this append succeeds.
        _append_line(self._handles["ticks"], commit)

        self._sequence += 1
        self._last_tick = tick
        self._previous_commit_hash = commit_hash
        if self.manifest["first_recorded_tick"] is None:
            self.manifest["first_recorded_tick"] = tick
        self.manifest["last_committed_tick"] = tick
        self._pending += 1
        if self._pending >= self._flush_every:
            self.flush()

    def flush(self) -> None:
        for handle in self._handles.values():
            if not handle.closed:
                handle.flush()
                os.fsync(handle.fileno())
        self._pending = 0

    def close(self) -> None:
        if self._handles["ticks"].closed:
            return
        self.flush()
        sizes = {
            "schemas": self._handles["schemas"].tell(),
            "dense": self._handles["dense"].tell(),
            "summary": self._handles["summary"].tell(),
            "structural": self._handles["structural"].tell(),
            "events": self._handles["events"].tell(),
            "static": self._handles["static"].tell(),
            "fallback": self._handles["fallback"].tell(),
            "ticks": self._handles["ticks"].tell(),
        }
        for handle in self._handles.values():
            handle.close()
        self.manifest.update(
            {
                "status": "closed",
                "ended_at_utc": _utc_now(),
                "end_tick": self._last_tick,
                "tick_records": self._sequence,
                "anchors": self._anchor_count,
                "checkpoints": self._checkpoint_count,
                "final_commit_hash": (
                    self._previous_commit_hash if self._sequence else None
                ),
                "compaction": {
                    "stream_bytes": sizes,
                    "dense_records": self._dense.records,
                    "dense_schema_changes": self._dense.schema_changes,
                    "structural_records": self._structural.records,
                    "structural_schema_changes": self._structural.schema_changes,
                    "event_records": self._events.records,
                    "static_records": self._static.records,
                    "fallback_records": self._fallback.records,
                    "fallback_operations": self._fallback.operations,
                    "fallback_bytes": self._fallback.bytes_written,
                },
            }
        )
        _write_json(self.root / "manifest.json", self.manifest)


class AsyncTelemetryV41Writer:
    _STOP = object()

    def __init__(self, *args, queue_size: int = 256, **kwargs) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        self._writer = TelemetryV41Writer(*args, **kwargs)
        self._snapshot_interval = self._writer._snapshot_interval
        self._queue: queue.Queue[object] = queue.Queue(maxsize=int(queue_size))
        self._submitted = 0
        self._closed = False
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"telemetry-v41-{self._writer.run_id}",
            daemon=False,
        )
        self._thread.start()

    @property
    def run_id(self) -> str:
        return self._writer.run_id

    @property
    def root(self) -> Path:
        return self._writer.root

    @property
    def manifest(self) -> dict[str, Any]:
        return self._writer.manifest

    def _raise_worker_error(self) -> None:
        if self._error is not None:
            raise RuntimeError("async telemetry worker failed") from self._error

    def needs_snapshot(self, tick: int) -> bool:
        self._raise_worker_error()
        return self._submitted == 0 or int(tick) % self._snapshot_interval == 0

    def append(
        self,
        record: Any,
        *,
        rich_state: Mapping[str, Any],
        full_snapshot: Mapping[str, Any] | None = None,
    ) -> None:
        if self._closed:
            raise RuntimeError("async telemetry writer is closed")
        self._raise_worker_error()
        self._queue.put((record, rich_state, full_snapshot))
        self._submitted += 1
        self._raise_worker_error()

    def _run(self) -> None:
        try:
            while True:
                item = self._queue.get()
                try:
                    if item is self._STOP:
                        return
                    if self._error is not None:
                        continue
                    record, rich_state, full_snapshot = item
                    self._writer.append(
                        record,
                        rich_state=rich_state,
                        full_snapshot=full_snapshot,
                    )
                except BaseException as exc:
                    self._error = exc
                finally:
                    self._queue.task_done()
        finally:
            try:
                self._writer.close()
            except BaseException as exc:
                if self._error is None:
                    self._error = exc

    def flush(self) -> None:
        if self._closed:
            self._raise_worker_error()
            return
        self._queue.join()
        self._raise_worker_error()

    def close(self) -> None:
        if self._closed:
            self._raise_worker_error()
            return
        self._closed = True
        self._queue.put(self._STOP)
        self._queue.join()
        self._thread.join()
        self._raise_worker_error()


class TelemetryV41Reader:
    """Streaming verified reader for telemetry v4.1."""

    _STREAM_PATHS = {
        "dense": ("frames", "dense.ndjson"),
        "summary": ("frames", "summary.ndjson"),
        "structural": ("structures", "state.ndjson"),
        "events": ("events", "events.ndjson"),
        "static": ("structures", "static.ndjson"),
        "fallback": ("frames", "fallback.ndjson"),
    }

    def __init__(self, path: str | Path, *, verify: bool = True) -> None:
        root = Path(path).expanduser()
        if root.is_file():
            root = root.parent
        self.root = root
        self.verify = bool(verify)
        self.manifest = json.loads(
            (self.root / "manifest.json").read_text(encoding="utf-8")
        )
        if str(self.manifest.get("schema_version")) != SCHEMA_VERSION:
            raise ValueError("not a telemetry v4.1 run")
        self.ticks_path = self.root / "ticks.ndjson"
        if not self.ticks_path.is_file():
            raise FileNotFoundError(f"telemetry tick commits not found: {self.ticks_path}")
        self.registry = FrameSchemaRegistryReader(
            self.root / "schemas" / "frames.ndjson"
        )
        self.object_store = ObjectStore(self.root / "objects" / "sha256")
        self._patcher = StatePatcher(object_store=None)

    def _stream_path(self, name: str) -> Path:
        parts = self._STREAM_PATHS[name]
        return self.root.joinpath(*parts)

    def _anchor_files(self) -> list[tuple[int, Path]]:
        result: list[tuple[int, Path]] = []
        for path in sorted((self.root / "anchors").glob("tick-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            claimed = payload.pop("anchor_sha256", None)
            if self.verify and payload_sha256(payload) != claimed:
                raise ValueError(f"telemetry anchor hash mismatch: {path.name}")
            result.append((int(payload["tick"]), path))
        return result

    def _load_anchor(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        claimed = payload.pop("anchor_sha256", None)
        if self.verify and payload_sha256(payload) != claimed:
            raise ValueError(f"telemetry anchor hash mismatch: {path.name}")
        return payload

    def _iter_commits(
        self,
        *,
        start_offset: int = 0,
    ) -> Iterator[dict[str, Any]]:
        previous_hash: str | None = None
        previous_sequence: int | None = None
        previous_tick: int | None = None
        with self.ticks_path.open("r", encoding="utf-8", newline="\n") as handle:
            handle.seek(int(start_offset))
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"invalid tick commit at line {line_no}")
                if self.verify:
                    claimed = item.get("commit_hash")
                    unsigned = dict(item)
                    unsigned.pop("commit_hash", None)
                    if payload_sha256(unsigned) != claimed:
                        raise ValueError(
                            f"telemetry commit hash mismatch at line {line_no}"
                        )
                    sequence = int(item.get("sequence", -1))
                    tick = int(item.get("tick", -1))
                    if previous_sequence is not None and sequence != previous_sequence + 1:
                        raise ValueError("telemetry commit sequence gap")
                    if previous_tick is not None and tick <= previous_tick:
                        raise ValueError("telemetry commit tick order violation")
                    if previous_hash is not None and item.get(
                        "previous_commit_hash"
                    ) != previous_hash:
                        raise ValueError("telemetry commit hash-chain break")
                    previous_hash = str(claimed)
                    previous_sequence = sequence
                    previous_tick = tick
                yield item

    def _prime_decoders(self, anchor: Mapping[str, Any]):
        state = anchor["state"]
        summary = anchor["summary"]
        partition = partition_state(state)

        dense = FrameStreamReader(self.registry)
        dense_schemas = dict(anchor.get("schemas", {}).get("dense", {}))
        for channel, value in partition.dense.items():
            dense.prime(
                channel,
                value,
                schema_id=dense_schemas.get(channel),
            )

        structural = StructuralStreamReader(self.registry)
        structural_schemas = dict(
            anchor.get("schemas", {}).get("structural", {})
        )
        for channel, value in partition.structural.items():
            structural.prime(
                channel,
                value,
                schema_id=structural_schemas.get(channel),
            )

        summary_reader = FrameStreamReader(self.registry)
        summary_reader.prime(
            "summary",
            summary,
            schema_id=anchor.get("schemas", {}).get("summary"),
        )

        events = EventStreamReader()
        events.prime(partition.events)

        static = _StaticStreamReader(self.object_store)
        static.prime(partition.static)

        fallback = deepcopy(partition.fallback)
        return dense, structural, summary_reader, events, static, fallback

    @staticmethod
    def _apply_removed(
        removed: Mapping[str, Any],
        dense: FrameStreamReader,
        structural: StructuralStreamReader,
        events: EventStreamReader,
        static: _StaticStreamReader,
    ) -> None:
        for channel in removed.get("dense", ()):
            dense.drop(str(channel))
        for channel in removed.get("structural", ()):
            structural.drop(str(channel))
        for channel in removed.get("events", ()):
            events.drop(str(channel))
        for channel in removed.get("static", ()):
            static.drop(str(channel))

    def _anchor_commit(self, anchor: Mapping[str, Any]) -> dict[str, Any]:
        try:
            commit = next(
                self._iter_commits(
                    start_offset=int(anchor.get("ticks_offset", 0))
                )
            )
        except StopIteration as exc:
            raise ValueError("telemetry anchor has no committed tick") from exc
        anchor_tick = int(anchor["tick"])
        if int(commit.get("tick", -1)) != anchor_tick:
            raise ValueError("anchor/tick commit position mismatch")
        if self.verify:
            if commit.get("commit_hash") != anchor.get("commit_hash"):
                raise ValueError("anchor/commit hash mismatch")
            if payload_sha256(anchor["state"]) != commit.get("state_sha256"):
                raise ValueError("anchor state commitment mismatch")
            if payload_sha256(anchor["summary"]) != commit.get("summary_sha256"):
                raise ValueError("anchor summary commitment mismatch")
        return commit

    def _reconstruct_from_anchor(
        self,
        anchor: Mapping[str, Any],
        *,
        end_tick: int | None = None,
    ) -> Iterator[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]]:
        anchor_commit = self._anchor_commit(anchor)
        dense, structural, summary_reader, events, static, fallback = (
            self._prime_decoders(anchor)
        )
        anchor_tick = int(anchor["tick"])
        anchor_state = deepcopy(dict(anchor["state"]))
        anchor_summary = deepcopy(dict(anchor["summary"]))
        yield anchor_tick, anchor_summary, anchor_state, anchor_commit
        if end_tick is not None and anchor_tick >= int(end_tick):
            return

        offsets = dict(anchor.get("stream_offsets", {}))
        handles = {
            name: self._stream_path(name).open(
                "r", encoding="utf-8", newline="\n"
            )
            for name in self._STREAM_PATHS
        }
        buckets = {
            name: _TickBucket(handle, start_offset=int(offsets.get(name, 0)))
            for name, handle in handles.items()
        }
        try:
            for commit in self._iter_commits(
                start_offset=int(anchor.get("ticks_offset", 0))
            ):
                tick = int(commit["tick"])
                if tick < anchor_tick:
                    continue
                if tick == anchor_tick:
                    continue
                if end_tick is not None and tick > int(end_tick):
                    break

                events.begin_tick()
                self._apply_removed(
                    commit.get("removed_channels", {}),
                    dense,
                    structural,
                    events,
                    static,
                )
                for channel in commit.get("present_channels", {}).get("events", ()):
                    events.values.setdefault(str(channel), [])

                expected_records = commit.get("stream_records", {})
                for stream_name, decoder in (
                    ("dense", dense),
                    ("structural", structural),
                ):
                    records = buckets[stream_name].take(tick)
                    if self.verify:
                        actual_hashes = [payload_sha256(item) for item in records]
                        if actual_hashes != list(expected_records.get(stream_name, ())):
                            raise ValueError(
                                f"telemetry {stream_name} record commitment mismatch "
                                f"at tick {tick}"
                            )
                    for item in records:
                        decoder.apply(item)

                event_records = buckets["events"].take(tick)
                if self.verify:
                    actual_hashes = [payload_sha256(item) for item in event_records]
                    if actual_hashes != list(expected_records.get("events", ())):
                        raise ValueError(
                            f"telemetry event record commitment mismatch at tick {tick}"
                        )
                for item in event_records:
                    events.apply(item)

                static_records = buckets["static"].take(tick)
                if self.verify:
                    actual_hashes = [payload_sha256(item) for item in static_records]
                    if actual_hashes != list(expected_records.get("static", ())):
                        raise ValueError(
                            f"telemetry static record commitment mismatch at tick {tick}"
                        )
                for item in static_records:
                    static.apply(item)

                fallback_records = buckets["fallback"].take(tick)
                if self.verify:
                    actual_hashes = [payload_sha256(item) for item in fallback_records]
                    if actual_hashes != list(expected_records.get("fallback", ())):
                        raise ValueError(
                            f"telemetry fallback record commitment mismatch at tick {tick}"
                        )
                for item in fallback_records:
                    fallback = self._patcher.apply(
                        fallback,
                        item.get("p", ()),
                    )
                    if not isinstance(fallback, dict):
                        raise ValueError("fallback patch did not reconstruct a mapping")

                summary_records = buckets["summary"].take(tick)
                if len(summary_records) != 1:
                    raise ValueError(
                        f"expected one summary frame for tick {tick}, got {len(summary_records)}"
                    )
                if self.verify:
                    actual_hashes = [payload_sha256(item) for item in summary_records]
                    if actual_hashes != list(expected_records.get("summary", ())):
                        raise ValueError(
                            f"telemetry summary record commitment mismatch at tick {tick}"
                        )
                _summary_channel, summary = summary_reader.apply(summary_records[0])
                state = reassemble_state(
                    dense=dense.values,
                    structural=structural.values,
                    events=events.values,
                    static=static.values,
                    fallback=fallback,
                )
                if self.verify:
                    if payload_sha256(state) != commit.get("state_sha256"):
                        raise ValueError(
                            f"telemetry state hash mismatch at tick {tick}"
                        )
                    if payload_sha256(summary) != commit.get("summary_sha256"):
                        raise ValueError(
                            f"telemetry summary hash mismatch at tick {tick}"
                        )
                yield tick, deepcopy(summary), state, commit
        finally:
            for handle in handles.values():
                handle.close()

    def state_at(self, tick: int) -> dict[str, Any]:
        requested = int(tick)
        candidates = [
            item for item in self._anchor_files()
            if item[0] <= requested
        ]
        if not candidates:
            raise KeyError(f"no telemetry state at or before tick {requested}")
        _anchor_tick, path = candidates[-1]
        anchor = self._load_anchor(path)
        for current_tick, _summary, state, _commit in self._reconstruct_from_anchor(
            anchor,
            end_tick=requested,
        ):
            if current_tick == requested:
                return state
        raise KeyError(f"telemetry tick not found: {requested}")

    def summary_at(self, tick: int) -> dict[str, Any]:
        requested = int(tick)
        candidates = [
            item for item in self._anchor_files()
            if item[0] <= requested
        ]
        if not candidates:
            raise KeyError(f"no telemetry summary at or before tick {requested}")
        anchor = self._load_anchor(candidates[-1][1])
        for current_tick, summary, _state, _commit in self._reconstruct_from_anchor(
            anchor,
            end_tick=requested,
        ):
            if current_tick == requested:
                return summary
        raise KeyError(f"telemetry tick not found: {requested}")

    def iter_states(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        anchors = self._anchor_files()
        if not anchors:
            return
        anchor = self._load_anchor(anchors[0][1])
        for tick, _summary, state, _commit in self._reconstruct_from_anchor(
            anchor,
            end_tick=end_tick,
        ):
            if start_tick is not None and tick < int(start_tick):
                continue
            yield state

    def iter_summaries(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        anchors = self._anchor_files()
        if not anchors:
            return
        anchor = self._load_anchor(anchors[0][1])
        for tick, summary, _state, _commit in self._reconstruct_from_anchor(
            anchor,
            end_tick=end_tick,
        ):
            if start_tick is not None and tick < int(start_tick):
                continue
            yield summary

    def iter_events(
        self,
        *,
        event_type: str | None = None,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        path = self._stream_path("events")
        if not path.is_file():
            return
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                tick = int(item["t"])
                channel = str(item["c"])
                if start_tick is not None and tick < int(start_tick):
                    continue
                if end_tick is not None and tick > int(end_tick):
                    break
                if event_type is not None and channel != event_type:
                    continue
                yield {
                    "tick": tick,
                    "type": channel,
                    "operation": item.get("o"),
                    "payload": deepcopy(item.get("v")),
                }


def load_v41_tick_records(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    return list(TelemetryV41Reader(path, verify=verify).iter_summaries())


def load_v41_transitions(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    return list(TelemetryV41Reader(path, verify=verify).iter_states())


def _verify_checkpoint_reference(
    root: Path,
    commit: Mapping[str, Any],
) -> None:
    reference = commit.get("checkpoint")
    if reference is None:
        return
    if not isinstance(reference, Mapping):
        raise ValueError("invalid telemetry checkpoint reference")
    relative = Path(str(reference.get("path", "")))
    if (
        not relative.parts
        or relative.is_absolute()
        or ".." in relative.parts
    ):
        raise ValueError("unsafe telemetry checkpoint path")
    path = root / relative
    if not path.is_file():
        raise ValueError(f"telemetry checkpoint missing: {relative}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid telemetry checkpoint: {relative}")
    claimed = payload.pop("checkpoint_sha256", None)
    actual = payload_sha256(payload)
    if claimed != actual or reference.get("sha256") != actual:
        raise ValueError(f"telemetry checkpoint hash mismatch: {relative}")
    if int(payload.get("tick", -1)) != int(commit.get("tick", -2)):
        raise ValueError(f"telemetry checkpoint tick mismatch: {relative}")
    if payload.get("run_id") != commit.get("run_id"):
        raise ValueError(f"telemetry checkpoint run mismatch: {relative}")


def verify_v41_run(path: str | Path) -> dict[str, Any]:
    reader = TelemetryV41Reader(path, verify=True)
    anchors = reader._anchor_files()
    if not anchors:
        raise ValueError("telemetry v4.1 run has no anchor")

    commits = list(reader._iter_commits())
    for commit in commits:
        _verify_checkpoint_reference(reader.root, commit)

    records = 0
    first_tick = None
    last_tick = None
    for tick, _summary, _state, _commit in reader._reconstruct_from_anchor(
        reader._load_anchor(anchors[0][1])
    ):
        records += 1
        if first_tick is None:
            first_tick = tick
        last_tick = tick

    last_hash = commits[-1].get("commit_hash") if commits else None
    if len(commits) != records:
        raise ValueError(
            "telemetry committed tick count differs from reconstructed tick count"
        )

    manifest = reader.manifest
    complete = (
        manifest.get("status") == "closed"
        and int(manifest.get("tick_records", -1)) == records
        and manifest.get("final_commit_hash") == last_hash
        and manifest.get("last_committed_tick") == last_tick
    )
    return {
        "run_id": manifest.get("run_id"),
        "records": records,
        "first_tick": first_tick,
        "last_tick": last_tick,
        "anchors": len(anchors),
        "checkpoints": sum(
            1 for item in commits if item.get("checkpoint") is not None
        ),
        "manifest_tick_records": manifest.get("tick_records"),
        "manifest_final_commit_hash": manifest.get("final_commit_hash"),
        "actual_final_commit_hash": last_hash,
        "status": manifest.get("status"),
        "complete": complete,
    }


__all__ = [
    "AsyncTelemetryV41Writer",
    "ENVELOPE_TYPE",
    "SCHEMA_VERSION",
    "TelemetryV41Reader",
    "TelemetryV41Writer",
    "load_v41_tick_records",
    "load_v41_transitions",
    "verify_v41_run",
]
