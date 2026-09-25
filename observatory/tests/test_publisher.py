import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from observatory.publisher import JournalSink, ReplayRecorder, SnapshotPublisher, StdoutSink


class PublisherTests(unittest.TestCase):
    def test_stdout_sink_prints_one_json_line(self):
        sink = StdoutSink()
        with patch("builtins.print") as mock_print:
            sink.write({"type": "symbiont-observatory-snapshot", "snapshot": {"tick": 1}})
        mock_print.assert_called_once()
        (line,), kwargs = mock_print.call_args
        self.assertEqual(json.loads(line)["snapshot"]["tick"], 1)
        self.assertTrue(kwargs.get("flush"))

    def test_journal_sink_delegates_to_a_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            sink = JournalSink(Path(directory), run_id="run-1")
            sink.write({"type": "symbiont-observatory-snapshot", "snapshot": {"tick": 1}})
            segments = list((Path(directory) / "journal").glob("run-1-*.ndjson"))
            self.assertEqual(len(segments), 1)

    def test_journal_sink_finalizes_summary_for_partial_segment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sink = JournalSink(root, run_id="run-1")
            sink.write({"snapshot": {"tick": 1}})
            sink.finalize()
            summary = json.loads(
                (root / "summaries" / "run-1.summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["entries"], 1)

    def test_replay_recorder_flushes_all_recorded_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = ReplayRecorder()
            recorder.record({"tick": 1})
            recorder.record({"tick": 2})
            path = Path(directory) / "replay.json"
            recorder.flush(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([snapshot["tick"] for snapshot in payload["snapshots"]], [1, 2])

    def test_publisher_fans_out_identical_payload_to_every_sink(self):
        seen = []

        class RecordingSink:
            def write(self, envelope):
                seen.append(envelope)

        recorder = ReplayRecorder()
        publisher = SnapshotPublisher([RecordingSink(), RecordingSink()], replay_recorder=recorder)
        envelope = {"type": "symbiont-observatory-snapshot", "snapshot": {"tick": 3}}
        publisher.publish(envelope, envelope["snapshot"])
        self.assertEqual(seen, [envelope, envelope])


if __name__ == "__main__":
    unittest.main()
