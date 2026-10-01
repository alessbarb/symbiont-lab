"""Telemetry v3 for reproducible Physics3D analysis.

The writer is intentionally apparatus-side and passive. It records completed
runtime observations and never feeds data back into the organism.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import threading
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = 3
ENVELOPE_TYPE = "symbiont-physics3d-telemetry"
ZERO_HASH = "0" * 64


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _hash_payload(payload: Any) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


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


def _record_mapping(record: Any) -> dict[str, Any]:
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, Mapping):
        return dict(record)
    raise TypeError("telemetry record must be a dataclass or mapping")


class TelemetryV3Writer:
    """Append-only run-scoped telemetry with integrity chaining."""

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
        generated_run_id = (
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:12]}"
        )
        self.run_id = run_id or generated_run_id
        self.root = Path(root).expanduser() / self.run_id
        self.root.mkdir(parents=True, exist_ok=False)
        self.snapshots_dir = self.root / "snapshots"
        self.snapshots_dir.mkdir()

        self.core_path = self.root / "ticks.ndjson"
        self.delta_path = self.root / "deltas.ndjson"
        self._core = self.core_path.open("a", encoding="utf-8", buffering=65536)
        self._deltas = self.delta_path.open("a", encoding="utf-8", buffering=32768)
        self._flush_every = int(flush_every)
        self._snapshot_interval = int(snapshot_interval)
        self._pending = 0
        self._sequence = 0
        self._previous_hash = ZERO_HASH
        self._last_tick: int | None = None
        self._last_component_hashes: dict[str, str] = {}
        self._delta_count = 0
        self._snapshot_count = 0

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
            "end_tick": None,
            "seed": int(seed),
            "physics_hz": int(physics_hz),
            "cognition_hz": int(cognition_hz),
            "physics_substeps_per_tick": int(physics_hz // cognition_hz),
            "embodiment_mode": str(embodiment_mode),
            "snapshot_interval": self._snapshot_interval,
            "effective_configuration": config,
            "effective_configuration_sha256": _hash_payload(config),
            "software_identity": software,
            "software_identity_sha256": _hash_payload(software),
            "tick_records": 0,
            "delta_records": 0,
            "snapshots": 0,
            "final_record_hash": None,
            "integrity": "sha256-chain",
        }
        _write_json(self.root / "manifest.json", self.manifest)

    def _append_line(self, handle, payload: Mapping[str, Any]) -> None:
        handle.write(_json_bytes(payload).decode("utf-8"))
        handle.write("\n")

    @staticmethod
    def _delta_projection(component: str, rich: Mapping[str, Any]) -> Any:
        current = rich.get(component, {})
        if not isinstance(current, Mapping):
            return current
        if component == "cognition":
            keys = (
                "topology_revision",
                "topology_health",
                "recovering",
                "mutations",
                "recycling_events",
                "stranded_concepts",
                "retiring_predictors",
                "retirement_edges",
                "structural_candidates",
                "structural_producers",
                "oldest_structural_wait_ticks",
                "representation_maturity",
                "max_contention_losses",
                "node_budget",
                "edge_budget",
                "sense_budget",
            )
            return {key: current.get(key) for key in keys}
        if component == "sensorimotor":
            keys = (
                "known_patterns",
                "primitives",
                "hypotheses",
                "cognitive_primitives",
                "investigation_active",
                "investigation_primitive_id",
                "replay_active",
                "active_motor_repertoire",
            )
            return {key: current.get(key) for key in keys}
        return dict(current)

    def _component_deltas(self, tick: int, rich: Mapping[str, Any]) -> None:
        for component in ("cognition", "body_schema", "sensorimotor"):
            current = self._delta_projection(component, rich)
            digest = _hash_payload(current)
            if self._last_component_hashes.get(component) == digest:
                continue
            delta = {
                "schema_version": SCHEMA_VERSION,
                "run_id": self.run_id,
                "tick": int(tick),
                "component": component,
                "state_sha256": digest,
                "state": current,
            }
            self._append_line(self._deltas, delta)
            self._last_component_hashes[component] = digest
            self._delta_count += 1

    def needs_snapshot(self, tick: int) -> bool:
        return self._sequence == 0 or int(tick) % self._snapshot_interval == 0

    def append(
        self,
        record: Any,
        *,
        rich_state: Mapping[str, Any],
        full_snapshot: Mapping[str, Any] | None = None,
    ) -> None:
        summary = _record_mapping(record)
        tick = int(summary["tick"])
        rich_tick = rich_state.get("tick")
        if rich_tick is not None and int(rich_tick) != tick:
            raise ValueError(f"rich telemetry tick mismatch: {rich_tick} != {tick}")
        if self._last_tick is not None and tick <= self._last_tick:
            raise ValueError(
                f"telemetry ticks must be strictly increasing: {tick} <= {self._last_tick}"
            )

        payload = {
            "summary": summary,
            "transition": dict(rich_state),
        }
        envelope_without_hash = {
            "schema_version": SCHEMA_VERSION,
            "envelope_type": ENVELOPE_TYPE,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "tick": tick,
            "previous_record_hash": self._previous_hash,
            "payload": payload,
        }
        record_hash = _hash_payload(envelope_without_hash)
        envelope = dict(envelope_without_hash)
        envelope["record_hash"] = record_hash
        self._append_line(self._core, envelope)

        self._component_deltas(tick, rich_state)

        should_snapshot = full_snapshot is not None and self.needs_snapshot(tick)
        if should_snapshot:
            snapshot = {
                "schema_version": SCHEMA_VERSION,
                "run_id": self.run_id,
                "tick": tick,
                "record_hash": record_hash,
                **dict(full_snapshot),
            }
            snapshot["snapshot_sha256"] = _hash_payload(snapshot)
            _write_json(
                self.snapshots_dir / f"tick-{tick:012d}.json",
                snapshot,
            )
            self._snapshot_count += 1

        self._sequence += 1
        self._last_tick = tick
        self._previous_hash = record_hash
        self._pending += 1
        if self._pending >= self._flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._core.closed:
            self._core.flush()
            os.fsync(self._core.fileno())
        if not self._deltas.closed:
            self._deltas.flush()
            os.fsync(self._deltas.fileno())
        self._pending = 0

    def close(self) -> None:
        if self._core.closed:
            return
        self.flush()
        self._core.close()
        self._deltas.close()
        self.manifest.update(
            {
                "ended_at_utc": _utc_now(),
                "end_tick": self._last_tick,
                "tick_records": self._sequence,
                "delta_records": self._delta_count,
                "snapshots": self._snapshot_count,
                "final_record_hash": self._previous_hash if self._sequence else None,
            }
        )
        _write_json(self.root / "manifest.json", self.manifest)


class AsyncTelemetryV3Writer:
    """Single-worker FIFO wrapper around :class:`TelemetryV3Writer`.

    The completed-tick producer only enqueues already-produced telemetry
    snapshots. All hashing, JSON serialization, delta generation, snapshot
    writes, flushing and fsync stay on one apparatus-side worker thread, so
    ordering and the SHA-256 chain remain identical to the synchronous writer.

    The queue is bounded deliberately: if storage cannot keep up indefinitely,
    the producer eventually back-pressures instead of silently dropping
    scientific evidence or consuming unbounded memory.
    """

    _STOP = object()

    def __init__(self, *args, queue_size: int = 256, **kwargs) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be >= 1")
        self._writer = TelemetryV3Writer(*args, **kwargs)
        self._snapshot_interval = self._writer._snapshot_interval
        self._queue: queue.Queue[object] = queue.Queue(maxsize=int(queue_size))
        self._submitted = 0
        self._closed = False
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"telemetry-v3-{self._writer.run_id}",
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
        # These are completed-tick values produced as fresh mappings by the
        # Physics3D runtime/CLI. The worker never reads live organism state.
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
        """Wait until every telemetry item submitted so far is durable."""
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


def iter_v3_envelopes(
    path: str | Path,
    *,
    verify: bool = True,
):
    root = Path(path).expanduser()
    if root.is_file():
        root = root.parent
    core_path = root / "ticks.ndjson"
    if not core_path.is_file():
        raise FileNotFoundError(f"telemetry v3 ticks not found: {core_path}")

    previous_hash = ZERO_HASH
    expected_sequence = 0
    previous_tick: int | None = None
    with core_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            envelope = json.loads(line)
            if not isinstance(envelope, dict):
                raise ValueError(f"invalid telemetry envelope at line {line_no}")
            if verify:
                if int(envelope.get("sequence", -1)) != expected_sequence:
                    raise ValueError(
                        f"telemetry sequence gap at line {line_no}: "
                        f"{envelope.get('sequence')} != {expected_sequence}"
                    )
                if envelope.get("previous_record_hash") != previous_hash:
                    raise ValueError(f"telemetry hash-chain break at line {line_no}")
                claimed = envelope.get("record_hash")
                unsigned = dict(envelope)
                unsigned.pop("record_hash", None)
                actual = _hash_payload(unsigned)
                if claimed != actual:
                    raise ValueError(f"telemetry record hash mismatch at line {line_no}")
                tick = int(envelope.get("tick", -1))
                if previous_tick is not None and tick <= previous_tick:
                    raise ValueError(f"telemetry tick order violation at line {line_no}")
                previous_tick = tick
                previous_hash = str(claimed)
                expected_sequence += 1
            yield envelope


def load_v3_envelopes(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    """Compatibility materializer; prefer iter_v3_envelopes()."""
    return list(iter_v3_envelopes(path, verify=verify))


def load_v3_tick_records(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for envelope in iter_v3_envelopes(path, verify=verify):
        payload = envelope.get("payload", {})
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        if isinstance(summary, dict):
            records.append(dict(summary))
    return records


def load_v3_transitions(
    path: str | Path,
    *,
    verify: bool = True,
) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for envelope in iter_v3_envelopes(path, verify=verify):
        payload = envelope.get("payload", {})
        transition = payload.get("transition", {}) if isinstance(payload, dict) else {}
        if isinstance(transition, dict):
            transitions.append(dict(transition))
    return transitions


def load_v3_deltas(path: str | Path) -> list[dict[str, Any]]:
    root = Path(path).expanduser()
    if root.is_file():
        root = root.parent
    delta_path = root / "deltas.ndjson"
    if not delta_path.is_file():
        raise FileNotFoundError(f"telemetry v3 deltas not found: {delta_path}")
    deltas: list[dict[str, Any]] = []
    with delta_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"invalid telemetry delta at line {line_no}")
            claimed = item.get("state_sha256")
            if claimed != _hash_payload(item.get("state")):
                raise ValueError(f"telemetry delta hash mismatch at line {line_no}")
            deltas.append(item)
    return deltas


def verify_v3_run(path: str | Path) -> dict[str, Any]:
    root = Path(path).expanduser()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    record_count = 0
    first_tick = None
    last_tick = None
    last_record_hash = None
    for envelope in iter_v3_envelopes(root, verify=True):
        tick = int(envelope.get("tick", -1))
        record_count += 1
        if first_tick is None:
            first_tick = tick
        last_tick = tick
        last_record_hash = envelope.get("record_hash")

    snapshots_valid = True
    snapshot_files = sorted((root / "snapshots").glob("tick-*.json"))
    for snapshot_path in snapshot_files:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        claimed = snapshot.pop("snapshot_sha256", None)
        if claimed != _hash_payload(snapshot):
            snapshots_valid = False
            break

    closed = manifest.get("ended_at_utc") is not None
    complete = (
        closed
        and int(manifest.get("tick_records", -1)) == record_count
        and manifest.get("final_record_hash") == last_record_hash
        and snapshots_valid
    )
    return {
        "run_id": manifest.get("run_id"),
        "records": record_count,
        "first_tick": first_tick,
        "last_tick": last_tick,
        "manifest_tick_records": manifest.get("tick_records"),
        "manifest_final_record_hash": manifest.get("final_record_hash"),
        "actual_final_record_hash": last_record_hash,
        "snapshots_valid": snapshots_valid,
        "closed": closed,
        "complete": complete,
    }


__all__ = [
    "ENVELOPE_TYPE",
    "SCHEMA_VERSION",
    "TelemetryV3Writer",
    "iter_v3_envelopes",
    "load_v3_deltas",
    "load_v3_envelopes",
    "load_v3_tick_records",
    "load_v3_transitions",
    "verify_v3_run",
]
