"""All HTTP routes for the unified Symbiont Lab server.

Routes:
  GET  /                      → app.html (SPA shell)
  GET  /assets/*              → static files from server/assets/
  GET  /observatory/*         → static files from observatory/ package
  GET  /api/state             → JSON experiment + study state
  GET  /api/organism          → SSE: live organism body/cognition/vitals
  GET  /fleet                 → SSE: observatory fleet (if observatory_dir set)
  GET  /instances/<id>        → SSE: single organism journal stream
  GET  /api/instance/<id>/manifest → JSON: instance manifest
  POST /api/experiments/start → start an experiment run
  POST /api/studies/start     → start a comparative study
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from symbiont_lab.experiments.spec import ExperimentSpec, spec_from_payload
from symbiont_lab.observation.observatory import (
    ObservatorySource,
    observatory_package_root,
    valid_instance_id,
)
from symbiont_lab.studies.campaigns.comparative import COMPARABLE_PARAMETERS
from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.workbench.runs import ExperimentRunState, StudyRunState, _parse_seeds
from .sse import CLIENT_ERRORS as _CLIENT_ERRORS
from .sse import stream_fleet, stream_instance, stream_organism

_STATIC_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".js":   "text/javascript; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".ico":  "image/x-icon",
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
}
_MAX_BODY_BYTES = 32768


def make_handler(
    experiment_state: ExperimentRunState,
    study_state: StudyRunState,
    experiment_starter: Callable[[ExperimentSpec], bool],
    study_starter: Callable[..., bool],
    observation_bus: ObservationBus,
    observatory_dir: Path | None,
    assets_dir: Path,
    *,
    source_status: Callable[[], dict[str, Any]] | None = None,
) -> type[BaseHTTPRequestHandler]:
    observatory_source = ObservatorySource(observatory_dir)

    class Handler(BaseHTTPRequestHandler):
        # ----------------------------------------------------------------
        # Error suppression
        # ----------------------------------------------------------------
        def handle(self) -> None:
            try:
                super().handle()
            except _CLIENT_ERRORS:
                pass

        def log_message(self, fmt: str, *args: object) -> None:
            pass  # silence per-request logs

        # ----------------------------------------------------------------
        # Helpers
        # ----------------------------------------------------------------
        def _security_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _static(self, path: Path) -> None:
            if not path.is_file():
                self._json(404, {"error": "not found"})
                return
            suffix = path.suffix.lower()
            ctype = _STATIC_TYPES.get(suffix, "application/octet-stream")
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _static_under(self, root: Path, relative: str) -> None:
            """Serve a file only when its resolved path remains under root."""
            resolved_root = root.resolve()
            candidate = (resolved_root / relative).resolve()
            if not candidate.is_relative_to(resolved_root):
                self._json(404, {"error": "not found"})
                return
            self._static(candidate)

        def _body(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 0:
                raise ValueError("invalid Content-Length")
            if length > _MAX_BODY_BYTES:
                raise OverflowError("request body exceeds 32768 bytes")
            raw = self.rfile.read(length) or b"{}"
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            return payload

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"}:
                return False
            if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                return False
            return parsed.netloc == (self.headers.get("Host") or "")

        # ----------------------------------------------------------------
        # GET routing
        # ----------------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            # SPA shell
            if path in ("/", "/index.html"):
                self._static(assets_dir / "app.html")
                return

            # Static assets
            if path.startswith("/assets/"):
                rel = path[len("/assets/"):]
                self._static_under(assets_dir, rel)
                return

            # Observatory static files (render/, ui/, state/, transport/, etc.)
            if path.startswith("/observatory/"):
                rel = path[len("/observatory/"):]
                obs_root = observatory_package_root()
                if obs_root is None:
                    self._json(404, {"error": "not found"})
                    return
                self._static_under(obs_root, rel)
                return

            # ── API ──────────────────────────────────────────────────────

            if path == "/api/state":
                payload = experiment_state.payload()
                payload["study"] = study_state.payload()
                if source_status is not None:
                    payload["sources"] = source_status()
                self._json(200, payload)
                return

            if path == "/api/organism":
                self._stream_organism()
                return

            # ── Observatory SSE (optional) ───────────────────────────────

            if path == "/fleet":
                self._stream_fleet()
                return

            if path.startswith("/instances/"):
                instance_id = path[len("/instances/"):]
                if valid_instance_id(instance_id):
                    self._stream_instance(instance_id)
                    return
                self._json(404, {"error": "not found"})
                return

            if path.startswith("/api/instance/") and path.endswith("/manifest"):
                instance_id = path[len("/api/instance/"):-len("/manifest")]
                if observatory_dir and valid_instance_id(instance_id):
                    self._serve_manifest(instance_id)
                    return
                self._json(404, {"error": "not found"})
                return

            self._json(404, {"error": "not found"})

        # ----------------------------------------------------------------
        # POST routing
        # ----------------------------------------------------------------
        def do_POST(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self._json(403, {"error": "untrusted origin"})
                return
            try:
                payload = self._body()
            except OverflowError as exc:
                self._json(413, {"error": str(exc)})
                return
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})
                return

            path = urlparse(self.path).path
            if path == "/api/experiments/start":
                spec = spec_from_payload(payload, experiment_state.spec)
                if not experiment_starter(spec):
                    self._json(409, {"error": "another run is already active"})
                    return
                self._json(202, {
                    "started": True,
                    "experiment_number": experiment_state.experiment_number,
                    "spec": spec.as_dict(),
                })
                return

            if path == "/api/studies/start":
                try:
                    spec = spec_from_payload(payload, experiment_state.spec)
                    title = str(payload.get("study_title") or "Comparative study")[:160]
                    parameter = str(payload.get("parameter") or "")
                    if parameter not in COMPARABLE_PARAMETERS:
                        raise ValueError("unsupported study parameter")
                    baseline = float(payload["baseline"])
                    variant = float(payload["variant"])
                    seeds = _parse_seeds(payload.get("seeds"))
                    parent_id = str(payload.get("parent_study_id") or "").strip() or None
                    if parent_id and len(parent_id) > 64:
                        raise ValueError("parent study id too long")
                except (TypeError, ValueError, KeyError) as exc:
                    self._json(400, {"error": str(exc)})
                    return
                if not study_starter(
                    spec,
                    title=title,
                    parameter=parameter,
                    baseline=baseline,
                    variant=variant,
                    seeds=seeds,
                    parent_record_id=parent_id,
                ):
                    self._json(409, {"error": "another run is already active"})
                    return
                self._json(202, {"started": True, "runs": len(seeds) * 2})
                return

            self._json(404, {"error": "not found"})

        # ----------------------------------------------------------------
        # Organism SSE
        # ----------------------------------------------------------------
        def _stream_organism(self) -> None:
            stream_organism(self, observation_bus)

        def _stream_fleet(self) -> None:
            stream_fleet(self, observatory_source)

        def _stream_instance(self, instance_id: str) -> None:
            if not stream_instance(self, observatory_source, instance_id):
                self._json(503, {"error": "observatory not configured"})

        def _serve_manifest(self, instance_id: str) -> None:
            payload = observatory_source.manifest(instance_id)
            if payload is None:
                self._json(404, {"error": "manifest not found"})
                return
            self._json(200, payload)

    return Handler
