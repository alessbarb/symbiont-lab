from __future__ import annotations

import builtins
from contextlib import contextmanager
from http.client import HTTPConnection
from threading import Thread
from typing import Iterator

from symbiont_lab.observation.bus import ObservationBus
from symbiont_lab.server.server import UnifiedLabServer, _default_observatory_dir, make_server
from symbiont_lab.server.state import DashboardState


@contextmanager
def running_server(**kwargs) -> Iterator[UnifiedLabServer]:
    server = make_server(host="127.0.0.1", port=0, **kwargs)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def request(
    server: UnifiedLabServer,
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    host, port = server.server_address[:2]
    conn = HTTPConnection(host, port, timeout=2)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def test_unified_server_starts_without_synthetic_telemetry() -> None:
    stream = ObservationBus()
    server = make_server(host="127.0.0.1", port=0, organism_stream=stream)
    try:
        assert server.demo_telemetry is None
        assert not stream.has_data
    finally:
        server.server_close()


def test_demo_telemetry_requires_explicit_opt_in() -> None:
    server = make_server(host="127.0.0.1", port=0, demo=True)
    try:
        assert server.demo_telemetry is not None
    finally:
        server.server_close()
    assert server.demo_telemetry is None


def test_spa_and_api_state_are_served_by_unified_server() -> None:
    with running_server() as server:
        status, body = request(server, "/")
        assert status == 200
        assert b"Symbiont" in body

        status, body = request(server, "/api/state")
        assert status == 200
        assert b'"study"' in body


def test_static_traversal_is_rejected() -> None:
    with running_server() as server:
        status, _ = request(server, "/assets/../server.py")
        assert status == 404

        status, _ = request(server, "/observatory/../pyproject.toml")
        assert status == 404


def test_instance_stream_route_is_plural_and_fail_closed_without_observatory() -> None:
    with running_server() as server:
        status, _ = request(server, "/instances/0123456789abcdef")
        assert status == 503

        status, _ = request(server, "/instance/0123456789abcdef/stream")
        assert status == 404



def test_request_body_limits_fail_closed() -> None:
    with running_server() as server:
        status, _ = request(
            server,
            "/api/experiments/start",
            method="POST",
            body=b"{}",
            headers={"Content-Length": "not-a-number"},
        )
        assert status == 400

        oversized = b"{" + b" " * 32768 + b"}"
        status, _ = request(
            server,
            "/api/experiments/start",
            method="POST",
            body=oversized,
        )
        assert status == 413


def test_demo_and_physics3d_modes_are_mutually_exclusive() -> None:
    try:
        make_server(host="127.0.0.1", port=0, demo=True, physics3d=True)
    except ValueError as exc:
        assert "mutually exclusive" in str(exc)
    else:
        raise AssertionError("expected mutually exclusive telemetry modes to fail")



def test_cross_origin_mutation_is_rejected() -> None:
    with running_server() as server:
        status, body = request(
            server,
            "/api/experiments/start",
            method="POST",
            body=b"{}",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://example.invalid",
            },
        )
        assert status == 403
        assert b"untrusted origin" in body



def test_unified_server_refuses_non_loopback_binding() -> None:
    try:
        make_server(host="0.0.0.0", port=0)
    except ValueError as exc:
        assert "127.0.0.1" in str(exc)
    else:
        raise AssertionError("expected non-loopback binding to be rejected")


def test_observatory_default_is_optional(monkeypatch) -> None:
    real_import = builtins.__import__

    def without_observatory(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "observatory.config":
            raise ImportError("observatory intentionally unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", without_observatory)
    assert _default_observatory_dir() is None
