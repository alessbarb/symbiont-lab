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

import gzip
import json
import queue
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from symbiont_lab.experiments.spec import ExperimentSpec, spec_from_payload
from symbiont_lab.studies.campaigns.comparative import COMPARABLE_PARAMETERS
from .state import DashboardState, StudyDashboardState, _parse_seeds
from .organism_stream import OrganismStream

# Observatory helpers — imported lazily so the server starts even if the
# observatory package isn't importable (e.g. during pure lab runs).
def _obs_imports():
    try:
        from observatory.registry import classify_liveness, read_registry  # type: ignore
        return classify_liveness, read_registry
    except ImportError:
        return None, None


_STATIC_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".js":   "text/javascript; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".ico":  "image/x-icon",
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
}
_SSE_POLL = 1.0          # seconds between observatory journal polls
_SSE_HEARTBEAT = 15.0    # seconds between SSE keepalive comments
_REPLAY_LINES = 200
_CLIENT_ERRORS = (ConnectionError, BrokenPipeError, ConnectionResetError, OSError)


def _sse(data: dict) -> bytes:
    return ("data: " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n\n").encode()


def _valid_instance_id(v: str) -> bool:
    return len(v) == 16 and all(c in "0123456789abcdef" for c in v)


def make_handler(
    experiment_state: DashboardState,
    study_state: StudyDashboardState,
    experiment_starter: Callable[[ExperimentSpec], bool],
    study_starter: Callable[..., bool],
    organism_stream: OrganismStream,
    observatory_dir: Path | None,
    assets_dir: Path,
) -> type[BaseHTTPRequestHandler]:

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
        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
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
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict[str, Any]:
            length = min(int(self.headers.get("Content-Length", "0")), 32768)
            raw = self.rfile.read(length) or b"{}"
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            return payload

        def _start_sse(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

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
                self._static(assets_dir / rel)
                return

            # Observatory static files (render/, ui/, state/, transport/, etc.)
            if path.startswith("/observatory/"):
                rel = path[len("/observatory/"):]
                obs_root = Path(__file__).resolve().parents[4] / "observatory"
                self._static(obs_root / rel)
                return

            # ── API ──────────────────────────────────────────────────────

            if path == "/api/state":
                payload = experiment_state.payload()
                payload["study"] = study_state.payload()
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
                if _valid_instance_id(instance_id):
                    self._stream_instance(instance_id)
                    return

            if path.startswith("/api/instance/") and path.endswith("/manifest"):
                instance_id = path[len("/api/instance/"):-len("/manifest")]
                if observatory_dir and _valid_instance_id(instance_id):
                    self._serve_manifest(instance_id)
                    return

            self._json(404, {"error": "not found"})

        # ----------------------------------------------------------------
        # POST routing
        # ----------------------------------------------------------------
        def do_POST(self) -> None:  # noqa: N802
            try:
                payload = self._body()
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})
                return

            if self.path == "/api/experiments/start":
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

            if self.path == "/api/studies/start":
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
            self._start_sse()
            q = organism_stream.subscribe()
            try:
                while True:
                    try:
                        data: str = q.get(timeout=_SSE_HEARTBEAT)
                        self.wfile.write(("data: " + data + "\n\n").encode())
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except _CLIENT_ERRORS:
                pass
            finally:
                organism_stream.unsubscribe(q)

        # ----------------------------------------------------------------
        # Observatory SSE — fleet
        # ----------------------------------------------------------------
        def _stream_fleet(self) -> None:
            classify_liveness, read_registry = _obs_imports()
            self._start_sse()
            try:
                if read_registry is None or observatory_dir is None:
                    while True:
                        self.wfile.write(_sse({"instances": []}))
                        self.wfile.flush()
                        time.sleep(_SSE_POLL)

                while True:
                    records = read_registry(observatory_dir)
                    now = datetime.now(timezone.utc)
                    instances = [
                        {**r, "liveness": classify_liveness(r, now=now, heartbeat_interval_seconds=30.0)}
                        for r in records
                    ]
                    instances = [i for i in instances if i["liveness"] != "expired"]
                    self.wfile.write(_sse({"instances": instances}))
                    self.wfile.flush()
                    time.sleep(_SSE_POLL)
            except _CLIENT_ERRORS:
                pass

        # ----------------------------------------------------------------
        # Observatory SSE — single instance journal
        # ----------------------------------------------------------------
        def _stream_instance(self, instance_id: str) -> None:
            classify_liveness, read_registry = _obs_imports()
            if read_registry is None or observatory_dir is None:
                self._json(503, {"error": "observatory not configured"})
                return
            self._start_sse()
            journal_dir = observatory_dir / "journal"
            last_revision: int | None = None
            current_run_id: str | None = None
            sent_sequences: set[int] = set()
            positions: dict[Path, int] = {}
            initial_replay = True
            try:
                while True:
                    records = {r["instance_id"]: r for r in read_registry(observatory_dir)}
                    record = records.get(instance_id)
                    run_id = record["run_id"] if record else None

                    if run_id != current_run_id:
                        current_run_id = run_id
                        sent_sequences.clear()
                        positions.clear()
                        last_revision = None
                        initial_replay = True

                    if record and record.get("topology_revision") != last_revision:
                        last_revision = record["topology_revision"]
                        topo_path = observatory_dir / "instances" / f"{instance_id}.topology.json"
                        try:
                            topo = json.loads(topo_path.read_text(encoding="utf-8"))
                            if isinstance(topo, dict):
                                self.wfile.write(_sse({"topology": topo}))
                        except (OSError, json.JSONDecodeError):
                            pass

                    if run_id and journal_dir.exists():
                        entries = self._read_journal(journal_dir, run_id, positions)
                        entries = [e for e in entries if e["sequence"] not in sent_sequences]
                        if initial_replay:
                            entries = entries[-_REPLAY_LINES:]
                            initial_replay = False
                        for entry in entries:
                            self.wfile.write(_sse(entry))
                            sent_sequences.add(entry["sequence"])
                    self.wfile.flush()
                    time.sleep(_SSE_POLL)
            except _CLIENT_ERRORS:
                pass

        @staticmethod
        def _parse_journal_line(line: str, run_id: str) -> dict | None:
            line = line.strip()
            if not line:
                return None
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return None
            if not isinstance(entry, dict):
                return None
            seq = entry.get("sequence")
            if not isinstance(seq, int) or seq < 0 or isinstance(seq, bool):
                return None
            if entry.get("run_id") != run_id or "snapshot" not in entry:
                return None
            return entry

        @classmethod
        def _read_journal(cls, journal_dir: Path, run_id: str, positions: dict[Path, int]) -> list[dict]:
            entries: list[dict] = []
            segments = sorted([
                *journal_dir.glob(f"{run_id}-*.ndjson"),
                *journal_dir.glob(f"{run_id}-*.ndjson.gz"),
            ])
            live = set(segments)
            for stale in list(positions):
                if stale not in live:
                    positions.pop(stale, None)
            for seg in segments:
                try:
                    if seg.suffix == ".gz":
                        prev = positions.get(seg, 0)
                        idx = -1
                        with gzip.open(seg, "rt", encoding="utf-8") as fh:
                            for idx, line in enumerate(fh):
                                if idx < prev:
                                    continue
                                e = cls._parse_journal_line(line, run_id)
                                if e:
                                    entries.append(e)
                        positions[seg] = idx + 1
                    else:
                        prev = positions.get(seg, 0)
                        with seg.open("rb") as fh:
                            fh.seek(prev)
                            data = fh.read()
                        end = data.rfind(b"\n")
                        if end < 0:
                            continue
                        for line in data[: end + 1].decode("utf-8").splitlines():
                            e = cls._parse_journal_line(line, run_id)
                            if e:
                                entries.append(e)
                        positions[seg] = prev + end + 1
                except OSError:
                    continue
            return entries

        def _serve_manifest(self, instance_id: str) -> None:
            assert observatory_dir is not None
            path = observatory_dir / "instances" / f"{instance_id}.json"
            if not path.is_file():
                self._json(404, {"error": "manifest not found"})
                return
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._json(200, data)
            except (OSError, json.JSONDecodeError) as exc:
                self._json(500, {"error": str(exc)})

    return Handler
