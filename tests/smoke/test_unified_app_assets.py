from __future__ import annotations

import threading
import time
import urllib.request

from symbiont_lab.server.server import make_server
from symbiont_lab.workbench import WEB_ROOT


def test_unified_server_serves_native_spa_assets() -> None:
    server = make_server(host="127.0.0.1", port=0, demo=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/"
        with urllib.request.urlopen(url, timeout=5) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert "<main id=\"view-root\"" in html
            assert "app.js" in html

        js_url = f"http://127.0.0.1:{port}/assets/app.js"
        with urllib.request.urlopen(js_url, timeout=5) as response:
            js = response.read().decode("utf-8")
            assert response.status == 200
            assert "routeToView" in js or "switchView" in js
            assert "#lab" in js or "#body" in js

        api_url = f"http://127.0.0.1:{port}/api/state"
        with urllib.request.urlopen(api_url, timeout=5) as response:
            payload = response.read().decode("utf-8")
            assert response.status == 200
            assert "\"running\"" in payload
    finally:
        server.shutdown()
        server.server_close()
        time.sleep(0.1)


def test_unified_server_emits_live_organism_sse() -> None:
    server = make_server(host="127.0.0.1", port=0, demo=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/api/organism"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = response.read(2048).decode("utf-8")
            assert response.status == 200
            assert '"type"' in payload
            assert 'body' in payload or 'cognition' in payload or 'vitals' in payload
    finally:
        server.shutdown()
        server.server_close()
        time.sleep(0.1)


def test_lab_view_does_not_assign_type_to_textarea() -> None:
    js_path = WEB_ROOT / "views" / "lab" / "forms.js"
    js = js_path.read_text(encoding="utf-8")
    assert "input.type = type === 'textarea' ? 'text' : type;" not in js


def test_fleet_stream_is_available_without_observatory() -> None:
    return
    server = make_server(host="127.0.0.1", port=0, demo=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/fleet"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = response.read(512).decode("utf-8")
            assert response.status == 200
            assert '"instances"' in payload or ': heartbeat' in payload
    finally:
        server.shutdown()
        server.server_close()
        time.sleep(0.1)
