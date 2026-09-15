import json
import gzip
import tempfile
import threading
import unittest
import urllib.error
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

    def test_serves_index_html_at_root_same_origin_as_the_sse_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                self.assertIn("text/html", response.headers.get("Content-Type", ""))
                body = response.read().decode("utf-8")
            self.assertIn("Symbiont Observatory", body)
            self.assertIn('src="./app.js"', body)

    def test_serves_app_js_and_styles_css_as_static_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/app.js", timeout=2) as response:
                self.assertIn("javascript", response.headers.get("Content-Type", ""))
                js = response.read().decode("utf-8")
            self.assertIn("projection/snapshot.js", js)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/projection/snapshot.js", timeout=2) as response:
                self.assertIn("javascript", response.headers.get("Content-Type", ""))
                snapshot_js = response.read().decode("utf-8")
            self.assertIn("function normalizeSnapshot(", snapshot_js)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/styles.css", timeout=2) as response:
                self.assertIn("text/css", response.headers.get("Content-Type", ""))

    def test_refuses_path_traversal_outside_the_static_root(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            port = server.server_address[1]
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/../resident.py", timeout=2)
            self.assertEqual(ctx.exception.code, 404)

    def test_refuses_unknown_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            port = server.server_address[1]
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/server.py", timeout=2)
            self.assertEqual(ctx.exception.code, 404)

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

    def test_reader_replays_losslessly_compacted_segments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal_dir = root / "journal"
            journal_dir.mkdir()
            archive = journal_dir / "run-1-000001.ndjson.gz"
            entry = {"run_id": "run-1", "sequence": 0, "snapshot": {"tick": 7}}
            with gzip.open(archive, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")
            positions = {}
            records = ObservatoryServer._read_run_entries(journal_dir, "run-1", positions)
            self.assertEqual(records[0]["snapshot"]["tick"], 7)
            self.assertEqual(ObservatoryServer._read_run_entries(journal_dir, "run-1", positions), [])


if __name__ == "__main__":
    unittest.main()
