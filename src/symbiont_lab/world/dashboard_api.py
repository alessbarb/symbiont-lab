"""HTTP handler for the World dashboard. GET-only, on purpose: there is no
POST endpoint in this module, and none should ever be added that lets a
remote client call WorldAction or otherwise steer the tick (docs/design/
symbiont-world-v2.md §8)."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json

from .dashboard_page import HTML
from .dashboard_state import WorldDashboardState


def make_handler(state: WorldDashboardState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/state":
                self._send_json(200, state.payload())
                return
            if self.path in ("/", "/index.html"):
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._send_json(404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler
