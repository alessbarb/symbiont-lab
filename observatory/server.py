"""Local-only, read-only server for Observatory.

The server owns presentation transport only. It never imports cognition internals
or mutates organism/world state. Resident data is read from Observatory artifacts;
an optional World runtime can be attached as a passive snapshot/event provider.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    from .config import (
        DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        DEFAULT_OBSERVATORY_DIR,
        DEFAULT_SERVER_HOST,
        DEFAULT_SERVER_PORT,
    )
except ImportError:
    from config import (
        DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        DEFAULT_OBSERVATORY_DIR,
        DEFAULT_SERVER_HOST,
        DEFAULT_SERVER_PORT,
    )

from symbiont_lab.observation.observatory import (
    ObservatorySource,
    valid_instance_id,
)
from symbiont_lab.observation.observatory import (
    parse_journal_line as _canonical_parse_journal_line,
)
from symbiont_lab.observation.observatory import (
    read_journal as _canonical_read_journal,
)
from symbiont_lab.server.sse import stream_fleet, stream_instance

_STATIC_ROOT = Path(__file__).resolve().parent
_STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def _valid_instance_id(value: str) -> bool:
    """Compatibility alias for the canonical instance-id validator."""
    return valid_instance_id(value)


_CLIENT_DISCONNECT_ERRORS = (ConnectionError, BrokenPipeError, ConnectionResetError)


class _Handler(BaseHTTPRequestHandler):
    server: "ObservatoryServer"

    def log_message(self, format: str, *args) -> None:
        pass

    def handle(self) -> None:
        try:
            super().handle()
        except _CLIENT_DISCONNECT_ERRORS:
            pass

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/world/state":
            if self.server.world_state is None:
                self.send_error(404)
                return
            self._serve_json(self.server.world_state.payload())
        elif path == "/world/events":
            if self.server.world_state is None:
                self.send_error(404)
                return
            query = parse_qs(parsed.query)
            after = query.get("after", [None])[0]
            try:
                limit = int(query.get("limit", ["256"])[0])
                payload = self.server.world_state.events_after(after, limit=limit)
            except (TypeError, ValueError) as exc:
                body = (json.dumps({"error": str(exc)}, separators=(",", ":")) + "\n").encode(
                    "utf-8"
                )
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._serve_json(payload)
        elif path == "/fleet":
            self._stream_fleet()
        elif path.startswith("/instance/") and path.endswith("/stream"):
            instance_id = path.split("/")[2]
            self._stream_instance(instance_id)
        elif path.startswith("/instance/") and path.endswith("/manifest"):
            instance_id = path.split("/")[2]
            self._serve_instance_manifest(instance_id)
        elif path.startswith("/instance/") and path.endswith("/history-summary"):
            instance_id = path.split("/")[2]
            self._serve_instance_history_summary(instance_id)
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

    def _serve_json(self, payload: dict) -> None:
        body = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_instance_manifest(self, instance_id: str) -> None:
        payload = self.server.observatory_source.manifest(instance_id)
        if payload is None:
            self.send_error(404)
            return
        self._serve_json(payload)

    def _serve_instance_history_summary(self, instance_id: str) -> None:
        payload = self.server.observatory_source.history_summary(instance_id)
        if payload is None:
            self.send_error(404)
            return
        self._serve_json(payload)

    def _stream_fleet(self) -> None:
        if not stream_fleet(self, self.server.observatory_source):
            self.send_error(503)

    @staticmethod
    def _parse_journal_line(line: str, run_id: str) -> dict | None:
        """Compatibility adapter to the canonical journal parser."""
        return _canonical_parse_journal_line(line, run_id)

    @classmethod
    def _read_run_entries(
        cls,
        journal_dir: Path,
        run_id: str,
        positions: dict[Path, int],
    ) -> list[dict]:
        """Compatibility adapter to the canonical incremental journal reader."""
        return _canonical_read_journal(journal_dir, run_id, positions)

    def _stream_instance(self, instance_id: str) -> None:
        if not valid_instance_id(instance_id):
            self.send_error(404)
            return
        if not stream_instance(self, self.server.observatory_source, instance_id):
            self.send_error(503)


class ObservatoryServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        observatory_dir: Path,
        *,
        host: str = DEFAULT_SERVER_HOST,
        port: int = DEFAULT_SERVER_PORT,
        heartbeat_interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        world_state: object | None = None,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("ObservatoryServer refuses to bind to anything other than 127.0.0.1")
        self.observatory_dir = Path(observatory_dir)
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.observatory_source = ObservatorySource(
            self.observatory_dir,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.world_state = world_state
        super().__init__((host, port), _Handler)

    def handle_error(self, request: object, client_address: object) -> None:
        exc_val = sys.exc_info()[1]
        if isinstance(exc_val, _CLIENT_DISCONNECT_ERRORS):
            return
        super().handle_error(request, client_address)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-only read-only SSE server for Observatory")
    parser.add_argument(
        "--observatory-dir",
        type=Path,
        default=Path(DEFAULT_OBSERVATORY_DIR).expanduser(),
    )
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT)
    args = parser.parse_args(argv)
    server = ObservatoryServer(args.observatory_dir, port=args.port)
    print(f"Observatory server listening on http://127.0.0.1:{server.server_address[1]}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
