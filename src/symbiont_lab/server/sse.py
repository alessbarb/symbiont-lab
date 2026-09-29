"""Long-lived Server-Sent Events transport for the unified local server."""

from __future__ import annotations

import json
import queue
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.observation.observatory import ObservatorySource

SSE_POLL_SECONDS = 1.0
SSE_HEARTBEAT_SECONDS = 15.0
SSE_BATCH_MESSAGES = 64
SSE_BATCH_BYTES = 256 * 1024
REPLAY_LINES = 200
CLIENT_ERRORS = (ConnectionError, BrokenPipeError, ConnectionResetError)


def _encode_sse(data: dict[str, Any], *, event_id: str | int | None = None) -> bytes:
    prefix = "" if event_id is None else f"id: {event_id}\n"
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return (prefix + "data: " + payload + "\n\n").encode()


def _encode_serialized_sse(data: bytes, *, event_id: str | int | None = None) -> bytes:
    """Frame already-serialized JSON bytes without parsing or re-encoding."""
    prefix = b"" if event_id is None else f"id: {event_id}\n".encode("ascii")
    return prefix + b"data: " + data + b"\n\n"


def _drain_observation_batch(consumer, first) -> bytes:
    chunks = [
        _encode_serialized_sse(first.data, event_id=first.stream_id),
    ]
    total = len(chunks[0])
    count = 1
    while count < SSE_BATCH_MESSAGES and total < SSE_BATCH_BYTES:
        try:
            message = consumer.get_nowait()
        except queue.Empty:
            break
        chunk = _encode_serialized_sse(message.data, event_id=message.stream_id)
        chunks.append(chunk)
        total += len(chunk)
        count += 1
    return b"".join(chunks)


def _last_event_id(handler: BaseHTTPRequestHandler) -> str | None:
    value = handler.headers.get("Last-Event-ID")
    return value.strip() if value and value.strip() else None


def start_sse(handler: BaseHTTPRequestHandler) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("X-Accel-Buffering", "no")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.end_headers()


def stream_organism(handler: BaseHTTPRequestHandler, stream: ObservationBus) -> None:
    resume: int | None = None
    raw_resume = _last_event_id(handler)
    if raw_resume is not None:
        try:
            resume = max(0, int(raw_resume))
        except ValueError:
            resume = None

    start_sse(handler)
    consumer = stream.subscribe(after_sequence=resume)
    try:
        while True:
            try:
                first = consumer.get(timeout=SSE_HEARTBEAT_SECONDS)
                handler.wfile.write(_drain_observation_batch(consumer, first))
                handler.wfile.flush()
            except queue.Empty:
                handler.wfile.write(b": heartbeat\n\n")
                handler.wfile.flush()
    except CLIENT_ERRORS:
        pass
    finally:
        stream.unsubscribe(consumer)


def stream_fleet(handler: BaseHTTPRequestHandler, source: ObservatorySource) -> bool:
    if not source.available:
        return False
    start_sse(handler)
    try:
        while True:
            handler.wfile.write(_encode_sse({"instances": source.fleet_snapshot()}))
            handler.wfile.flush()
            time.sleep(SSE_POLL_SECONDS)
    except CLIENT_ERRORS:
        pass
    return True


def stream_instance(
    handler: BaseHTTPRequestHandler,
    source: ObservatorySource,
    instance_id: str,
) -> bool:
    """Stream one instance; return False when Observatory is unavailable."""
    if not source.available:
        return False

    resume_run: str | None = None
    resume_sequence = -1
    raw_resume = _last_event_id(handler)
    if raw_resume and ":" in raw_resume:
        candidate_run, candidate_sequence = raw_resume.rsplit(":", 1)
        try:
            resume_sequence = int(candidate_sequence)
        except ValueError:
            pass
        else:
            resume_run = candidate_run

    start_sse(handler)
    last_revision: int | None = None
    current_run_id: str | None = None
    last_sequence = -1
    positions: dict[Path, int] = {}
    initial_replay = True

    try:
        while True:
            record = source.instance_record(instance_id)
            run_id = record["run_id"] if record else None

            if run_id != current_run_id:
                current_run_id = run_id
                last_sequence = (
                    resume_sequence if run_id is not None and run_id == resume_run else -1
                )
                positions.clear()
                last_revision = None
                initial_replay = not (run_id is not None and run_id == resume_run)

            if record and record.get("topology_revision") != last_revision:
                last_revision = record["topology_revision"]
                topology = source.topology(instance_id)
                if topology is not None:
                    handler.wfile.write(_encode_sse({"topology": topology}))

            if run_id:
                entries = source.journal_entries(run_id, positions)
                entries.sort(key=lambda entry: entry["sequence"])
                entries = [entry for entry in entries if entry["sequence"] > last_sequence]
                if initial_replay:
                    entries = entries[-REPLAY_LINES:]
                    initial_replay = False
                for entry in entries:
                    sequence = int(entry["sequence"])
                    handler.wfile.write(_encode_sse(entry, event_id=f"{run_id}:{sequence}"))
                    last_sequence = sequence

            handler.wfile.flush()
            time.sleep(SSE_POLL_SECONDS)
    except CLIENT_ERRORS:
        pass
    return True
