from __future__ import annotations

from lab.server.server import make_server


def test_server_instantiation():
    # Test that HTTP server can bind to ephemeral port (0)
    server = make_server(host="127.0.0.1", port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] > 0
    finally:
        server.server_close()
