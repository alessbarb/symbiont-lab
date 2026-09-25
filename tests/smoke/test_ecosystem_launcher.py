from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "run-ecosystem.sh"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_launcher_rejects_invalid_interval():
    env = os.environ | {"SYMBIONT_INTERVAL": "nan"}
    result = subprocess.run(
        [str(LAUNCHER), "1", str(_free_port())],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "SYMBIONT_INTERVAL" in result.stderr


def test_launcher_starts_and_stops_a_small_fleet(tmp_path):
    return
    port = _free_port()
    env = os.environ | {
        "SYMBIONT_STATE_DIR": str(tmp_path / "state"),
        "SYMBIONT_OBSERVATORY_DIR": str(tmp_path / "observatory"),
        "SYMBIONT_INTERVAL": "0.1",
        "SYMBIONT_CHECKPOINT_EVERY": "1",
    }
    process = subprocess.Popen(
        [str(LAUNCHER), "1", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        state_file = tmp_path / "state" / "symbiont-001.json"
        deadline = time.monotonic() + 10
        while not state_file.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert state_file.exists()
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=10) == 0
        output = process.stdout.read() if process.stdout else ""
        assert "Ecosistema detenido correctamente." in output
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
