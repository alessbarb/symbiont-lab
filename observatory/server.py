"""Local-only, read-only SSE server for Observatory. Understands only
Observatory's own contracts (registry/topology/journal file shapes) --
never imports symbiont.core or any cognition module. Reads only files
organisms write; never writes into any --state-file, checkpoint, or
registry entry belonging to an organism."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    from .registry import classify_liveness, read_registry
except ImportError:  # allow bare-script execution, matching this package's other CLI entry points
    from registry import classify_liveness, read_registry

_REPLAY_LINES = 200
_POLL_SECONDS = 1.0
_STATIC_ROOT = Path(__file__).resolve().parent
_STATIC_CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}


def _sse_event(data: dict) -> bytes:
    return f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n".encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    server: "ObservatoryServer"

    def log_message(self, format: str, *args) -> None:  # silence default stderr logging
        pass

    def do_GET(self) -> None:  # noqa: N802 (stdlib-mandated method name)
        path = urlparse(self.path).path
        if path == "/fleet":
            self._stream_fleet()
        elif path.startswith("/instance/") and path.endswith("/stream"):
            instance_id = path.split("/")[2]
            self._stream_instance(instance_id)
        else:
            self._serve_static(path)

    def _serve_static(self, path: str) -> None:
        """Serves index.html/app.js/styles.css from the same origin as the
        SSE routes above, so the browser's EventSource("/fleet") calls are
        same-origin -- opening index.html from a *different* static server
        would make those calls cross-origin and fail. Only a small
        extension allowlist under this directory is ever served; nothing
        outside _STATIC_ROOT (path traversal) and nothing with an
        unlisted extension (this module's own .py sources included)."""
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
                            record, now=now, heartbeat_interval_seconds=self.server.heartbeat_interval_seconds
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

    def _stream_instance(self, instance_id: str) -> None:
        self._start_sse()
        journal_dir = self.server.observatory_dir / "journal"
        last_revision = None
        sent_sequences: set[int] = set()
        try:
            while True:
                records = {record["instance_id"]: record for record in read_registry(self.server.observatory_dir)}
                record = records.get(instance_id)
                if record is not None and record["topology_revision"] != last_revision:
                    last_revision = record["topology_revision"]
                    topology_path = self.server.observatory_dir / "instances" / f"{instance_id}.topology.json"
                    if topology_path.exists():
                        self.wfile.write(_sse_event({"topology": json.loads(topology_path.read_text(encoding="utf-8"))}))
                run_id = record["run_id"] if record else None
                if run_id is not None:
                    entries = []
                    for segment in sorted(journal_dir.glob(f"{run_id}-*.ndjson")):
                        for line in segment.read_text(encoding="utf-8").splitlines():
                            if not line.strip():
                                continue
                            entry = json.loads(line)
                            if entry["sequence"] not in sent_sequences:
                                entries.append(entry)
                    if not sent_sequences:
                        entries = entries[-_REPLAY_LINES:]
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
    parser.add_argument("--observatory-dir", type=Path, default=Path("~/.local/state/symbiont/observatory").expanduser())
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args(argv)
    server = ObservatoryServer(args.observatory_dir, port=args.port)
    print(f"Observatory server listening on http://127.0.0.1:{server.server_address[1]}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
