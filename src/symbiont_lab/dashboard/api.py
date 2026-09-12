from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from typing import Any, Callable

from symbiont_lab.experiments.spec import ExperimentSpec, spec_from_payload
from symbiont_lab.studies.campaigns.comparative import COMPARABLE_PARAMETERS
from .page import HTML
from .state import DashboardState, StudyDashboardState, _parse_seeds


def make_handler(
    experiment_state: DashboardState,
    study_state: StudyDashboardState,
    experiment_starter: Callable[[ExperimentSpec], bool],
    study_starter: Callable[..., bool],
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/state":
                payload = experiment_state.payload()
                payload["study"] = study_state.payload()
                self._send_json(200, payload)
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

        def _payload(self) -> dict[str, Any]:
            length = min(int(self.headers.get("Content-Length", "0")), 32768)
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            return payload

        def do_POST(self) -> None:  # noqa: N802
            try:
                payload = self._payload()
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
                return

            if self.path == "/api/experiments/start":
                spec = spec_from_payload(payload, experiment_state.spec)
                if not experiment_starter(spec):
                    self._send_json(409, {"error": "another experiment or study is already running"})
                    return
                self._send_json(
                    202,
                    {
                        "started": True,
                        "experiment_number": experiment_state.experiment_number,
                        "spec": spec.as_dict(),
                    },
                )
                return

            if self.path == "/api/studies/start":
                try:
                    spec = spec_from_payload(payload, experiment_state.spec)
                    title = str(payload.get("study_title") or "Comparative study")[:160]
                    parameter = str(payload.get("parameter") or "")
                    if parameter not in COMPARABLE_PARAMETERS:
                        raise ValueError("unsupported study parameter")
                    baseline = float(payload.get("baseline"))
                    variant = float(payload.get("variant"))
                    seeds = _parse_seeds(payload.get("seeds"))
                    parent_record_id = str(payload.get("parent_study_id") or "").strip() or None
                    if parent_record_id is not None and len(parent_record_id) > 64:
                        raise ValueError("parent study id is too long")
                except (TypeError, ValueError) as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                if not study_starter(
                    spec,
                    title=title,
                    parameter=parameter,
                    baseline=baseline,
                    variant=variant,
                    seeds=seeds,
                    parent_record_id=parent_record_id,
                ):
                    self._send_json(409, {"error": "another experiment or study is already running"})
                    return
                self._send_json(202, {"started": True, "runs": len(seeds) * 2})
                return

            self._send_json(404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler
