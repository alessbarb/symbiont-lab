from __future__ import annotations

from contextlib import contextmanager
from http.client import HTTPConnection
from threading import Thread
from typing import Iterator

from symbiont_lab.dashboard.state import DashboardState as LegacyDashboardState
from symbiont_lab.server.organism_stream import OrganismStream
from symbiont_lab.server.server import UnifiedLabServer, make_server
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


def request(server: UnifiedLabServer, path: str) -> tuple[int, bytes]:
    host, port = server.server_address[:2]
    conn = HTTPConnection(host, port, timeout=2)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def test_unified_server_is_canonical_state_owner() -> None:
    assert LegacyDashboardState is DashboardState


def test_unified_server_starts_without_synthetic_telemetry() -> None:
    stream = OrganismStream()
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
