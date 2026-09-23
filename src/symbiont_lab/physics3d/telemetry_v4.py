"""Telemetry v4: lossless temporal compaction for Physics3D.

The writer remains apparatus-side and passive. Runtime code still produces the
full completed-tick observation; this module changes only how that observation
is persisted.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import threading
from typing import Any, Iterator, Mapping
import uuid

from .telemetry_compaction import (
    CompactionPolicy,
    ObjectStore,
    StateDiffer,
    StatePatcher,
    canonical_json_bytes,
    payload_sha256,
)


SCHEMA_VERSION = 4
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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            dict(payload),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


class TelemetryV4Writer:
    """Append-only lossless telemetry using anchors plus exact sparse patches."""

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
        minimum_reference_bytes: int = 512,
    ) -> None:
        if snapshot_interval < 1:
            raise ValueError("snapshot_interval must be >= 1")
        if flush_every < 1:
            raise ValueError("flush_every must be >= 1")
        generated_run_id = (
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid.uuid4().hex[:12]}"
        )
        self.run_id = run_id or generated_run_id
        self.root = Path(root).expanduser() / self.run_id
        self.root.mkdir(parents=True, exist_ok=False)
        self.anchors_dir = self.root / "anchors"
        self.indexes_dir = self.root / "indexes"
        self.objects_dir = self.root / "objects" / "sha256"
        self.anchors_dir.mkdir()
        self.indexes_dir.mkdir()
        self.objects_dir.mkdir(parents=True)

        self.transitions_path = self.root / "transitions.ndjson"
        self.anchor_index_path = self.indexes_dir / "anchors.ndjson"
        self._transitions = self.transitions_path.open(
            "a", encoding="utf-8", buffering=65536
        )
        self._anchor_index = self.anchor_index_path.open(
            "a", encoding="utf-8", buffering=8192
        )
        self._flush_every = int(flush_every)
        self._snapshot_interval = int(snapshot_interval)
        self._pending = 0
        self._sequence = 0
        self._previous_hash = ZERO_HASH
        self._last_tick: int | None = None
        self._previous_state: Any = None
        self._previous_summary: Any = None
        self._anchor_count = 0
        self._state_patch_ops = 0
        self._summary_patch_ops = 0

        self.object_store = ObjectStore(self.objects_dir)
        policy = CompactionPolicy(
            minimum_reference_bytes=minimum_reference_bytes
        )
        self._differ = StateDiffer(
            object_store=self.object_store,
            policy=policy,
        )

        config = dict(effective_configuration or {})
        software = dict(software_identity or {})
        self.manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "envelope_type": ENVELOPE_TYPE,
            "run_id": self.run_id,
            "organism_id": str(organism_id),
            "started_at_utc": _utc_now(),
            "ended_at_utc": None,
            "start_tick": int(start_tick),
            "first_recorded_tick": None,
            "end_tick": None,
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
            "transition_records": 0,
            "anchors": 0,
            "objects": 0,
            "state_patch_operations": 0,
            "summary_patch_operations": 0,
            "final_record_hash": None,
            "integrity": "sha256-chain+content-addressed-objects",
            "storage_model": "anchor+exact-patch",
        }
        _write_json(self.root / "manifest.json", self.manifest)

    def _append_line(self, handle, payload: Mapping[str, Any]) -> None:
        handle.write(canonical_json_bytes(payload).decode("utf-8"))
        handle.write("\n")

    def needs_snapshot(self, tick: int) -> bool:
        return self._sequence == 0 or int(tick) % self._snapshot_interval == 0

    def _write_anchor(
        self,
        *,
        tick: int,
        summary: Mapping[str, Any],
        state: Mapping[str, Any],
        record_hash: str,
        full_snapshot: Mapping[str, Any] | None,
    ) -> None:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "tick": int(tick),
            "record_hash": record_hash,
            "summary": deepcopy(dict(summary)),
            "state": deepcopy(dict(state)),
        }
        if full_snapshot is not None:
            payload["snapshot"] = deepcopy(dict(full_snapshot))
        payload["anchor_sha256"] = payload_sha256(payload)
        filename = f"tick-{tick:012d}.json"
        _write_json(self.anchors_dir / filename, payload)
        self._append_line(
            self._anchor_index,
            {
                "tick": int(tick),
                "path": f"anchors/{filename}",
                "anchor_sha256": payload["anchor_sha256"],
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
            raise ValueError(
                f"rich telemetry tick mismatch: {rich_tick} != {tick}"
            )
        if self._last_tick is not None and tick <= self._last_tick:
            raise ValueError(
                f"telemetry ticks must be strictly increasing: {tick} <= {self._last_tick}"
            )

        is_first = self._sequence == 0
        if is_first:
            state_patch: list[dict[str, Any]] = []
            summary_patch: list[dict[str, Any]] = []
        else:
            state_patch = self._differ.diff(self._previous_state, state)
            summary_patch = self._differ.diff(self._previous_summary, summary)

        should_anchor = self.needs_snapshot(tick)
        envelope_without_hash = {
            "schema_version": SCHEMA_VERSION,
            "envelope_type": ENVELOPE_TYPE,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "tick": tick,
            "previous_record_hash": self._previous_hash,
            "anchor": bool(should_anchor),
            "summary_sha256": payload_sha256(summary),
            "state_sha256": payload_sha256(state),
            "summary_patch": summary_patch,
            "state_patch": state_patch,
        }
        record_hash = payload_sha256(envelope_without_hash)
        envelope = dict(envelope_without_hash)
        envelope["record_hash"] = record_hash
        self._append_line(self._transitions, envelope)

        if should_anchor:
            self._write_anchor(
                tick=tick,
                summary=summary,
                state=state,
                record_hash=record_hash,
                full_snapshot=full_snapshot,
            )

        self._sequence += 1
        self._last_tick = tick
        self._previous_hash = record_hash
        self._previous_state = deepcopy(state)
        self._previous_summary = deepcopy(summary)
        self._state_patch_ops += len(state_patch)
        self._summary_patch_ops += len(summary_patch)
        if self.manifest["first_recorded_tick"] is None:
            self.manifest["first_recorded_tick"] = tick
        self._pending += 1
        if self._pending >= self._flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._transitions.closed:
            self._transitions.flush()
            os.fsync(self._transitions.fileno())
        if not self._anchor_index.closed:
            self._anchor_index.flush()
            os.fsync(self._anchor_index.fileno())
        self._pending = 0

    def close(self) -> None:
        if self._transitions.closed:
            return
        self.flush()
        self._transitions.close()
        self._anchor_index.close()
        object_count = sum(1 for _ in self.objects_dir.glob("*/*.json"))
        self.manifest.update(
            {
                "ended_at_utc": _utc_now(),
                "end_tick": self._last_tick,
                "transition_records": self._sequence,
                "anchors": self._anchor_count,
                "objects": object_count,
                "state_patch_operations": self._state_patch_ops,
                "summary_patch_operations": self._summary_patch_ops,
                "final_record_hash": (
                    self._previous_hash if self._sequence else None
                ),
            }
        )
        _write_json(self.root / "manifest.json", self.manifest)


class AsyncTelemetryV4Writer:
    """Bounded FIFO worker around TelemetryV4Writer."""

    _STOP = object()

    def __init__(self, *args, queue_size: int = 256, **kwargs) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        self._writer = TelemetryV4Writer(*args, **kwargs)
        self._snapshot_interval = self._writer._snapshot_interval
        self._queue: queue.Queue[object] = queue.Queue(maxsize=int(queue_size))
        self._submitted = 0
        self._closed = False
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"telemetry-v4-{self._writer.run_id}",
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
        return (
            self._submitted == 0
            or int(tick) % self._snapshot_interval == 0
        )

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


class TelemetryV4Reader:
    """Verified reader that reconstructs v4 states from anchors and patches."""

    def __init__(self, path: str | Path, *, verify: bool = True) -> None:
        root = Path(path).expanduser()
        if root.is_file():
            root = root.parent
        self.root = root
        self.verify = bool(verify)
        self.transitions_path = self.root / "transitions.ndjson"
        self.manifest_path = self.root / "manifest.json"
        if not self.transitions_path.is_file():
            raise FileNotFoundError(
                f"telemetry v4 transitions not found: {self.transitions_path}"
            )
        self.object_store = ObjectStore(self.root / "objects" / "sha256")
        self._patcher = StatePatcher(object_store=self.object_store)
        self.manifest = json.loads(
            self.manifest_path.read_text(encoding="utf-8")
        )
        if int(self.manifest.get("schema_version", -1)) != SCHEMA_VERSION:
            raise ValueError("not a telemetry v4 run")

    def _anchor_files(self) -> list[tuple[int, Path]]:
        items: list[tuple[int, Path]] = []
        for path in sorted((self.root / "anchors").glob("tick-*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            tick = int(payload.get("tick", -1))
            if self.verify:
                claimed = payload.pop("anchor_sha256", None)
                actual = payload_sha256(payload)
                payload["anchor_sha256"] = claimed
                if claimed != actual:
                    raise ValueError(
                        f"telemetry anchor hash mismatch: {path.name}"
                    )
            items.append((tick, path))
        return items

    def _load_anchor(self, path: Path) -> tuple[int, dict[str, Any], dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if self.verify:
            claimed = payload.pop("anchor_sha256", None)
            actual = payload_sha256(payload)
            if claimed != actual:
                raise ValueError(
                    f"telemetry anchor hash mismatch: {path.name}"
                )
        summary = payload.get("summary")
        state = payload.get("state")
        if not isinstance(summary, dict) or not isinstance(state, dict):
            raise ValueError(f"invalid telemetry anchor: {path.name}")
        return int(payload["tick"]), summary, state

    def iter_transition_records(self) -> Iterator[dict[str, Any]]:
        previous_hash = ZERO_HASH
        expected_sequence = 0
        previous_tick: int | None = None
        with self.transitions_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(
                        f"invalid telemetry transition at line {line_no}"
                    )
                if self.verify:
                    if int(item.get("sequence", -1)) != expected_sequence:
                        raise ValueError(
                            f"telemetry sequence gap at line {line_no}"
                        )
                    if item.get("previous_record_hash") != previous_hash:
                        raise ValueError(
                            f"telemetry hash-chain break at line {line_no}"
                        )
                    claimed = item.get("record_hash")
                    unsigned = dict(item)
                    unsigned.pop("record_hash", None)
                    actual = payload_sha256(unsigned)
                    if claimed != actual:
                        raise ValueError(
                            f"telemetry record hash mismatch at line {line_no}"
                        )
                    tick = int(item.get("tick", -1))
                    if previous_tick is not None and tick <= previous_tick:
                        raise ValueError(
                            f"telemetry tick order violation at line {line_no}"
                        )
                    previous_hash = str(claimed)
                    previous_tick = tick
                    expected_sequence += 1
                yield item

    def transitions(self) -> list[dict[str, Any]]:
        """Compatibility materializer; prefer iter_transition_records()."""
        return list(self.iter_transition_records())

    def _reconstruct_all(
        self,
    ) -> Iterator[tuple[int, dict[str, Any], dict[str, Any], dict[str, Any]]]:
        anchors = self._anchor_files()
        if not anchors:
            return
        first_tick, first_anchor_path = anchors[0]
        anchor_tick, summary, state = self._load_anchor(first_anchor_path)
        if anchor_tick != first_tick:
            raise ValueError("telemetry anchor index mismatch")

        found_anchor = False
        for record in self.iter_transition_records():
            record_tick = int(record["tick"])
            if not found_anchor:
                if record_tick < anchor_tick:
                    continue
                if record_tick > anchor_tick:
                    raise ValueError(
                        "first telemetry anchor has no transition record"
                    )
                if self.verify:
                    if payload_sha256(summary) != record.get("summary_sha256"):
                        raise ValueError(
                            "telemetry summary hash mismatch at first anchor"
                        )
                    if payload_sha256(state) != record.get("state_sha256"):
                        raise ValueError(
                            "telemetry state hash mismatch at first anchor"
                        )
                found_anchor = True
                yield (
                    anchor_tick,
                    deepcopy(summary),
                    deepcopy(state),
                    record,
                )
                continue

            summary = self._patcher.apply(
                summary,
                record.get("summary_patch", ()),
            )
            state = self._patcher.apply(
                state,
                record.get("state_patch", ()),
            )
            if not isinstance(summary, dict) or not isinstance(state, dict):
                raise ValueError("telemetry patch did not reconstruct mappings")
            if self.verify:
                if payload_sha256(summary) != record.get("summary_sha256"):
                    raise ValueError(
                        f"telemetry summary hash mismatch at tick {record_tick}"
                    )
                if payload_sha256(state) != record.get("state_sha256"):
                    raise ValueError(
                        f"telemetry state hash mismatch at tick {record_tick}"
                    )
            yield record_tick, deepcopy(summary), deepcopy(state), record

        if not found_anchor:
            raise ValueError("first telemetry anchor has no transition record")

    def state_at(self, tick: int) -> dict[str, Any]:
        requested = int(tick)
        anchors = [
            item for item in self._anchor_files()
            if item[0] <= requested
        ]
        if not anchors:
            raise KeyError(f"no telemetry state at or before tick {requested}")
        anchor_tick, anchor_path = anchors[-1]
        _tick, summary, state = self._load_anchor(anchor_path)
        if requested == anchor_tick:
            return deepcopy(state)

        for record in self.iter_transition_records():
            record_tick = int(record["tick"])
            if record_tick <= anchor_tick:
                continue
            if record_tick > requested:
                break
            summary = self._patcher.apply(
                summary,
                record.get("summary_patch", ()),
            )
            state = self._patcher.apply(
                state,
                record.get("state_patch", ()),
            )
            if self.verify:
                if payload_sha256(summary) != record.get("summary_sha256"):
                    raise ValueError(
                        f"telemetry summary hash mismatch at tick {record_tick}"
                    )
                if payload_sha256(state) != record.get("state_sha256"):
                    raise ValueError(
                        f"telemetry state hash mismatch at tick {record_tick}"
                    )
            if record_tick == requested:
                if not isinstance(state, dict):
                    raise ValueError("reconstructed telemetry state is not a mapping")
                return deepcopy(state)
        raise KeyError(f"telemetry tick not found: {requested}")

    def iter_records(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
        for tick, summary, state, _record in self._reconstruct_all():
            if start_tick is not None and tick < int(start_tick):
                continue
            if end_tick is not None and tick > int(end_tick):
                break
            yield state, summary

    def iter_states(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        for tick, _summary, state, _record in self._reconstruct_all():
            if start_tick is not None and tick < int(start_tick):
                continue
            if end_tick is not None and tick > int(end_tick):
                break
            yield state

    def iter_summaries(
        self,
        *,
        start_tick: int | None = None,
        end_tick: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        for tick, summary, _state, _record in self._reconstruct_all():
            if start_tick is not None and tick < int(start_tick):
                continue
            if end_tick is not None and tick > int(end_tick):
                break
            yield summary


def load_v4_tick_records(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    return list(TelemetryV4Reader(path, verify=verify).iter_summaries())


def load_v4_transitions(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    return list(TelemetryV4Reader(path, verify=verify).iter_states())


def verify_v4_run(path: str | Path) -> dict[str, Any]:
    reader = TelemetryV4Reader(path, verify=True)
    manifest = reader.manifest
    anchors = reader._anchor_files()

    record_count = 0
    final_hash = None
    for record in reader.iter_transition_records():
        record_count += 1
        final_hash = record.get("record_hash")

    reconstructed_count = 0
    first_tick = None
    last_tick = None
    for tick, _summary, _state, _record in reader._reconstruct_all():
        reconstructed_count += 1
        if first_tick is None:
            first_tick = tick
        last_tick = tick

    closed = manifest.get("ended_at_utc") is not None
    complete = (
        closed
        and int(manifest.get("transition_records", -1)) == record_count
        and manifest.get("final_record_hash") == final_hash
        and bool(anchors) == bool(record_count)
        and reconstructed_count == record_count
    )
    return {
        "run_id": manifest.get("run_id"),
        "records": record_count,
        "first_tick": first_tick,
        "last_tick": last_tick,
        "anchors": len(anchors),
        "objects": sum(
            1 for _ in (reader.root / "objects" / "sha256").glob("*/*.json")
        ),
        "manifest_transition_records": manifest.get("transition_records"),
        "manifest_final_record_hash": manifest.get("final_record_hash"),
        "actual_final_record_hash": final_hash,
        "closed": closed,
        "complete": complete,
    }

__all__ = [
    "AsyncTelemetryV4Writer",
    "ENVELOPE_TYPE",
    "SCHEMA_VERSION",
    "TelemetryV4Reader",
    "TelemetryV4Writer",
    "load_v4_tick_records",
    "load_v4_transitions",
    "verify_v4_run",
]
