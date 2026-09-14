import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from observatory.journal import Journal
from observatory.registry import write_heartbeat
from observatory.server import ObservatoryServer


class ServerTests(unittest.TestCase):
    def _start_server(self, observatory_dir: Path) -> ObservatoryServer:
        server = ObservatoryServer(observatory_dir, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        return server

    def test_binds_only_to_127_0_0_1(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            self.assertEqual(server.server_address[0], "127.0.0.1")

    def test_refuses_to_bind_to_a_non_loopback_host(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                ObservatoryServer(Path(directory), host="0.0.0.0", port=0)

    def test_fleet_endpoint_streams_registry_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            write_heartbeat(
                observatory_dir,
                instance_id="a" * 16,
                run_id="run-1",
                pid=1,
                display_id="local-symbiont",
                started_at="2026-09-14T12:00:00+00:00",
                topology_revision=0,
            )
            server = self._start_server(observatory_dir)
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/fleet", timeout=2) as response:
                self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))
                first_line = response.readline().decode("utf-8")
            self.assertTrue(first_line.startswith("data: "))
            payload = json.loads(first_line[len("data: "):])
            self.assertEqual(payload["instances"][0]["instance_id"], "a" * 16)

    def test_instance_stream_replays_recent_journal_lines_on_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            journal = Journal(observatory_dir, run_id="run-1")
            journal.append({"snapshot": {"tick": 1}})
            journal.append({"snapshot": {"tick": 2}})
            write_heartbeat(
                observatory_dir,
                instance_id="b" * 16,
                run_id="run-1",
                pid=1,
                display_id="x",
                started_at="2026-09-14T12:00:00+00:00",
                topology_revision=0,
            )
            server = self._start_server(observatory_dir)
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/instance/{'b' * 16}/stream", timeout=2) as response:
                first_line = response.readline().decode("utf-8")
            self.assertTrue(first_line.startswith("data: "))
            first_payload = json.loads(first_line[len("data: "):])
            self.assertEqual(first_payload["snapshot"]["tick"], 1)


if __name__ == "__main__":
    unittest.main()
