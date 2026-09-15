"""Local-only, read-only SSE server for Observatory. Understands only
Observatory's own contracts (registry/topology/journal file shapes) --
never imports symbiont.core or any cognition module. Reads only files
organisms write; never writes into organism state.
"""

from __future__ import annotations

import argparse
import json
import gzip
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    from .registry import classify_liveness, read_registry
except ImportError:
    from registry import classify_liveness, read_registry

_REPLAY_LINES = 200
_POLL_SECONDS = 1.0
_STATIC_ROOT = Path(__file__).resolve().parent
_STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def _sse_event(data: dict) -> bytes:
    return f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n".encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    server: "ObservatoryServer"

    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/fleet":
            self._stream_fleet()
        elif path.startswith("/instance/") and path.endswith("/stream"):
            instance_id = path.split("/")[2]
            self._stream_instance(instance_id)
        else:
            self._serve_static(path)

    def _serve_static(self, path: str) -> None:
        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (_STATIC_ROOT / relative).resolve()
        content_type = _STATIC_CONTENT_TYPES.get(candidate.suffix)
        if content_type is None or _STATIC_ROOT not in candidate.parents or not candidate.is_file():
            self.send_error(404)
            return
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _start_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _stream_fleet(self) -> None:
        self._start_sse()
        try:
            while True:
                records = read_registry(self.server.observatory_dir)
                now = datetime.now(timezone.utc)
                instances = [
                    {
                        **record,
                        "liveness": classify_liveness(
                            record,
                            now=now,
                            heartbeat_interval_seconds=self.server.heartbeat_interval_seconds,
                        ),
                    }
                    for record in records
                ]
                instances = [item for item in instances if item["liveness"] != "expired"]
                self.wfile.write(_sse_event({"instances": instances}))
                self.wfile.flush()
                time.sleep(_POLL_SECONDS)
        except (BrokenPipeError, ConnectionResetError):
            return

    @staticmethod
    def _parse_journal_line(line: str, run_id: str) -> dict | None:
        if not line.strip():
            return None
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(entry, dict):
            return None
        sequence = entry.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return None
        if entry.get("run_id") != run_id or "snapshot" not in entry:
            return None
        return entry

    @classmethod
    def _read_run_entries(
        cls,
        journal_dir: Path,
        run_id: str,
        positions: dict[Path, int],
    ) -> list[dict]:
        """Read only text appended since the previous poll.

        Journal segments are append-only and whole old segments may be
        deleted, never truncated. TextIO ``tell`` cookies captured after
        ``readline`` are safe to feed back to ``seek`` on the next poll.
        """
        entries: list[dict] = []
        segments = sorted([*journal_dir.glob(f"{run_id}-*.ndjson"), *journal_dir.glob(f"{run_id}-*.ndjson.gz")])
        live_paths = set(segments)
        for stale_path in tuple(positions):
            if stale_path not in live_paths:
                positions.pop(stale_path, None)

        for segment in segments:
            try:
                if segment.suffix == ".gz":
                    # Archives are immutable. Position is a line count rather
                    # than a byte offset, so compacted history is replayed once.
                    previous_position = positions.get(segment, 0)
                    index = -1
                    with gzip.open(segment, "rt", encoding="utf-8") as handle:
                        for index, line in enumerate(handle):
                            if index < previous_position:
                                continue
                            entry = cls._parse_journal_line(line, run_id)
                            if entry is not None:
                                entries.append(entry)
                        positions[segment] = index + 1
                else:
                    with segment.open("r", encoding="utf-8") as handle:
                        previous_position = positions.get(segment, 0)
                        try:
                            handle.seek(previous_position)
                        except (OSError, ValueError):
                            handle.seek(0)
                        while True:
                            line = handle.readline()
                            if not line:
                                break
                            entry = cls._parse_journal_line(line, run_id)
                            if entry is not None:
                                entries.append(entry)
                        positions[segment] = handle.tell()
            except OSError:
                continue
        return entries

    def _stream_instance(self, instance_id: str) -> None:
        self._start_sse()
        journal_dir = self.server.observatory_dir / "journal"
        last_revision: int | None = None
        current_run_id: str | None = None
        sent_sequences: set[int] = set()
        journal_positions: dict[Path, int] = {}
        initial_replay = True
        try:
            while True:
                records = {
                    record["instance_id"]: record for record in read_registry(self.server.observatory_dir)
                }
                record = records.get(instance_id)
                run_id = record["run_id"] if record else None

                if run_id != current_run_id:
                    current_run_id = run_id
                    sent_sequences.clear()
                    journal_positions.clear()
                    last_revision = None
                    initial_replay = True

                if record is not None and record["topology_revision"] != last_revision:
                    last_revision = record["topology_revision"]
                    topology_path = self.server.observatory_dir / "instances" / f"{instance_id}.topology.json"
                    try:
                        topology = json.loads(topology_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        topology = None
                    if isinstance(topology, dict):
                        self.wfile.write(_sse_event({"topology": topology}))

                if run_id is not None:
                    entries = [
                        entry
                        for entry in self._read_run_entries(journal_dir, run_id, journal_positions)
                        if entry["sequence"] not in sent_sequences
                    ]
                    if initial_replay:
                        entries = entries[-_REPLAY_LINES:]
                        initial_replay = False
                    for entry in entries:
                        self.wfile.write(_sse_event(entry))
                        sent_sequences.add(entry["sequence"])
                self.wfile.flush()
                time.sleep(_POLL_SECONDS)
        except (BrokenPipeError, ConnectionResetError):
            return


class ObservatoryServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        observatory_dir: Path,
        *,
        host: str = "127.0.0.1",
        port: int = 8899,
        heartbeat_interval_seconds: float = 15.0,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("ObservatoryServer refuses to bind to anything other than 127.0.0.1")
        self.observatory_dir = Path(observatory_dir)
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        super().__init__((host, port), _Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-only read-only SSE server for Observatory")
    parser.add_argument(
        "--observatory-dir",
        type=Path,
        default=Path("~/.local/state/symbiont/observatory").expanduser(),
    )
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args(argv)
    server = ObservatoryServer(args.observatory_dir, port=args.port)
    print(f"Observatory server listening on http://127.0.0.1:{server.server_address[1]}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
