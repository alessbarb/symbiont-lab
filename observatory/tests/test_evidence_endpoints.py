import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from observatory.registry import write_heartbeat
from observatory.server import ObservatoryServer


class EvidenceEndpointTests(unittest.TestCase):
    def _start_server(self, observatory_dir: Path) -> ObservatoryServer:
        server = ObservatoryServer(observatory_dir, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        return server

    def test_manifest_endpoint_projects_provenance_without_private_paths_or_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            instance_id = "a" * 16
            manifest_dir = root / "manifests"
            manifest_dir.mkdir(parents=True)
            payload = {
                "manifest_version": 3,
                "organism_id": "organism-1",
                "instance_id": instance_id,
                "run_id": "run-1",
                "last_sequence": 12,
                "tick": 44,
                "topology_revision": 2,
                "schema_version": 3,
                "kernel_version": "0.80.15",
                "checkpoint_file": "secret-state.json",
                "checkpoint_sha256": "a" * 64,
                "topology_file": "topology.json",
                "topology_sha256": "b" * 64,
                "effective_config": {"private": "must-not-leak"},
                "captured_at": "2026-09-16T18:00:00+00:00",
                "git_commit": "deadbeef",
                "consistency": "atomic",
            }
            (manifest_dir / f"{instance_id}.manifest.json").write_text(json.dumps(payload), encoding="utf-8")
            server = self._start_server(root)
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/instance/{instance_id}/manifest", timeout=2) as response:
                result = json.load(response)
            self.assertEqual(result["projection"], "observatory-provenance-v1")
            self.assertEqual(result["checkpoint_sha256"], "a" * 64)
            self.assertNotIn("checkpoint_file", result)
            self.assertNotIn("topology_file", result)
            self.assertNotIn("effective_config", result)

    def test_history_summary_endpoint_follows_current_registry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            instance_id = "b" * 16
            write_heartbeat(
                root,
                instance_id=instance_id,
                run_id="run-2",
                pid=1,
                display_id="resident",
                started_at="2026-09-16T18:00:00+00:00",
                topology_revision=0,
            )
            summaries = root / "summaries"
            summaries.mkdir(parents=True)
            summary = {"summary_version": 1, "run_id": "run-2", "segments": [], "entries": 7, "tick_range": {"min": 1, "max": 7}, "schema_versions": {"3": 7}, "organism_states": {"observing": 7}}
            (summaries / "run-2.summary.json").write_text(json.dumps(summary), encoding="utf-8")
            server = self._start_server(root)
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/instance/{instance_id}/history-summary", timeout=2) as response:
                result = json.load(response)
            self.assertEqual(result["run_id"], "run-2")
            self.assertEqual(result["entries"], 7)

    def test_artifact_endpoints_reject_invalid_instance_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            port = server.server_address[1]
            for suffix in ("manifest", "history-summary"):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/instance/../{suffix}", timeout=2)
                self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
