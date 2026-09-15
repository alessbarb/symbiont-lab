from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from observatory.journal import Journal
from observatory.registry import classify_liveness, read_registry, write_heartbeat
from observatory.schema_validate import validate
from observatory.server import ObservatoryServer

ROOT = Path(__file__).resolve().parent.parent


def _next_sse_payload(response):
    while True:
        line = response.readline().decode("utf-8")
        if not line:
            raise AssertionError("SSE stream closed before the next event")
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])


class ObservatoryAdversarialHardeningTests(unittest.TestCase):
    def test_v2_snapshot_requires_organism_and_cognition(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        with self.assertRaises(AssertionError):
            validate({"schema_version": 2, "tick": 1}, schema, schema_root=ROOT)
        with self.assertRaises(AssertionError):
            validate(
                {"schema_version": 2, "tick": 1, "organism": {"cognition": {}}},
                schema,
                schema_root=ROOT,
            )

    def test_v1_snapshot_rejects_cognition(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        with self.assertRaises(AssertionError):
            validate(
                {
                    "schema_version": 1,
                    "tick": 1,
                    "organism": {
                        "cognition": {
                            "topology_revision": 0,
                            "safety_state": {"consecutive_failures": 0, "frozen": False},
                        }
                    },
                },
                schema,
                schema_root=ROOT,
            )

    def test_registry_ignores_structurally_malformed_json_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "instances"
            directory.mkdir(parents=True)
            (directory / "bad.json").write_text('{"last_heartbeat":123}', encoding="utf-8")
            self.assertEqual(read_registry(Path(tmp)), [])

    def test_naive_heartbeat_timestamp_is_expired_not_exception(self) -> None:
        record = {"last_heartbeat": "2026-09-14T12:00:00"}
        state = classify_liveness(
            record,
            now=datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc),
            heartbeat_interval_seconds=15.0,
        )
        self.assertEqual(state, "expired")

    def test_open_instance_stream_accepts_sequence_zero_after_run_rollover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            observatory_dir = Path(tmp)
            instance_id = "a" * 16
            started_at = datetime.now(timezone.utc).isoformat()

            run1 = "run-one"
            Journal(observatory_dir, run_id=run1).append({"snapshot": {"tick": 1}})
            write_heartbeat(
                observatory_dir,
                instance_id=instance_id,
                run_id=run1,
                pid=1,
                display_id="test",
                started_at=started_at,
                topology_revision=0,
            )

            server = ObservatoryServer(observatory_dir, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            port = server.server_address[1]

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/instance/{instance_id}/stream",
                timeout=5,
            ) as response:
                first = _next_sse_payload(response)
                self.assertEqual(first["run_id"], run1)
                self.assertEqual(first["sequence"], 0)

                run2 = "run-two"
                Journal(observatory_dir, run_id=run2).append({"snapshot": {"tick": 2}})
                write_heartbeat(
                    observatory_dir,
                    instance_id=instance_id,
                    run_id=run2,
                    pid=2,
                    display_id="test",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    topology_revision=0,
                )

                second = _next_sse_payload(response)
                self.assertEqual(second["run_id"], run2)
                self.assertEqual(second["sequence"], 0)
                self.assertEqual(second["snapshot"]["tick"], 2)


if __name__ == "__main__":
    unittest.main()
