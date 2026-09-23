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
REPLAY_LINES = 200
CLIENT_ERRORS = (ConnectionError, BrokenPipeError, ConnectionResetError, OSError)


def _encode_sse(data: dict[str, Any]) -> bytes:
    return ("data: " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n\n").encode()


def start_sse(handler: BaseHTTPRequestHandler) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("X-Accel-Buffering", "no")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.end_headers()


def stream_organism(handler: BaseHTTPRequestHandler, stream: ObservationBus) -> None:
    start_sse(handler)
    consumer = stream.subscribe()
    try:
        while True:
            try:
                data = consumer.get(timeout=SSE_HEARTBEAT_SECONDS)
                handler.wfile.write(("data: " + data + "\n\n").encode())
                handler.wfile.flush()
            except queue.Empty:
                handler.wfile.write(b": heartbeat\n\n")
                handler.wfile.flush()
    except CLIENT_ERRORS:
        pass
    finally:
        stream.unsubscribe(consumer)


def stream_fleet(handler: BaseHTTPRequestHandler, source: ObservatorySource) -> None:
    start_sse(handler)
    try:
        while True:
            handler.wfile.write(_encode_sse({"instances": source.fleet_snapshot()}))
            handler.wfile.flush()
            time.sleep(SSE_POLL_SECONDS)
    except CLIENT_ERRORS:
        pass


def stream_instance(
    handler: BaseHTTPRequestHandler,
    source: ObservatorySource,
    instance_id: str,
) -> bool:
    """Stream one instance; return False when Observatory is unavailable."""
    if not source.available:
        return False

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
                last_sequence = -1
                positions.clear()
                last_revision = None
                initial_replay = True

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
                    handler.wfile.write(_encode_sse(entry))
                    last_sequence = entry["sequence"]

            handler.wfile.flush()
            time.sleep(SSE_POLL_SECONDS)
    except CLIENT_ERRORS:
        pass
    return True
