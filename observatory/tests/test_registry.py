import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from observatory.registry import (
    classify_liveness,
    derive_instance_id,
    new_run_id,
    read_registry,
    write_heartbeat,
)


class RegistryTests(unittest.TestCase):
    def test_instance_id_is_a_stable_hash_never_the_raw_path(self):
        first = derive_instance_id("/home/alice/.local/state/symbiont/organism.json")
        second = derive_instance_id("/home/alice/.local/state/symbiont/organism.json")
        different = derive_instance_id("/home/bob/.local/state/symbiont/organism.json")
        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertRegex(first, r"^[0-9a-f]{16}$")
        self.assertNotIn("alice", first)

    def test_run_id_changes_every_call(self):
        self.assertNotEqual(new_run_id(), new_run_id())

    def test_write_and_read_heartbeat_round_trips_and_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            write_heartbeat(
                observatory_dir,
                instance_id="a" * 16,
                run_id="run-1",
                pid=123,
                display_id="local-symbiont",
                started_at="2026-09-14T12:00:00+00:00",
                topology_revision=3,
            )
            records = read_registry(observatory_dir)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["instance_id"], "a" * 16)
            self.assertEqual(records[0]["topology_revision"], 3)
            self.assertIn("last_heartbeat", records[0])
            path = observatory_dir / "instances" / f"{'a' * 16}.json"
            self.assertTrue(path.exists())
            temp_files = list((observatory_dir / "instances").glob(".*"))
            self.assertEqual(temp_files, [])

    def test_read_registry_skips_unparseable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            (observatory_dir / "instances").mkdir(parents=True)
            (observatory_dir / "instances" / "broken.json").write_text("not json", encoding="utf-8")
            self.assertEqual(read_registry(observatory_dir), [])

    def test_classify_liveness_alive_stale_expired(self):
        now = datetime(2026, 9, 14, 12, 10, 0, tzinfo=timezone.utc)

        def record(seconds_ago):
            return {"last_heartbeat": (now - timedelta(seconds=seconds_ago)).isoformat()}

        self.assertEqual(
            classify_liveness(record(5), now=now, heartbeat_interval_seconds=15.0), "alive"
        )
        self.assertEqual(
            classify_liveness(record(40), now=now, heartbeat_interval_seconds=15.0), "stale"
        )
        self.assertEqual(
            classify_liveness(record(700), now=now, heartbeat_interval_seconds=15.0), "expired"
        )


if __name__ == "__main__":
    unittest.main()
