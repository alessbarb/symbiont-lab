import json
import gzip
import tempfile
import unittest
from pathlib import Path

from observatory.journal import Journal


class JournalTests(unittest.TestCase):
    def test_append_assigns_monotonic_sequence_tagged_with_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-1", max_lines_per_segment=100)
            first_sequence = journal.append({"snapshot": {"tick": 1}})
            second_sequence = journal.append({"snapshot": {"tick": 2}})
            self.assertEqual((first_sequence, second_sequence), (0, 1))
            lines = journal.segments()[0].read_text(encoding="utf-8").strip().splitlines()
            entry = json.loads(lines[0])
            self.assertEqual(entry, {"run_id": "run-1", "sequence": 0, "snapshot": {"tick": 1}})

    def test_rotates_to_a_new_segment_when_the_cap_is_hit(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-1", max_lines_per_segment=2)
            for tick in range(5):
                journal.append({"snapshot": {"tick": tick}})
            segments = journal.segments()
            self.assertEqual(len(segments), 3)
            for segment in segments[:-1]:
                self.assertEqual(len(segment.read_text(encoding="utf-8").strip().splitlines()), 2)

    def test_retains_all_segments_until_explicit_compaction(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-1", max_lines_per_segment=1, max_segments=2)
            for tick in range(5):
                journal.append({"snapshot": {"tick": tick}})
            segments = journal.segments()
            self.assertEqual(len(segments), 5)
            remaining_ticks = [json.loads(segment.read_text(encoding="utf-8"))["snapshot"]["tick"] for segment in segments]
            self.assertEqual(remaining_ticks, [0, 1, 2, 3, 4])

    def test_compaction_is_lossless_and_keeps_active_segment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal = Journal(root, run_id="run-1", max_lines_per_segment=1)
            for tick in range(3):
                journal.append({"snapshot": {"tick": tick, "padding": "x" * 20}})
            self.assertEqual(journal.compact(), 2)
            archives = sorted((root / "journal").glob("*.ndjson.gz"))
            self.assertEqual(len(archives), 2)
            with gzip.open(archives[0], "rt", encoding="utf-8") as handle:
                self.assertEqual(json.loads(handle.readline())["snapshot"]["tick"], 0)

    def test_segment_filenames_are_ordered_by_run_id_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-abc", max_lines_per_segment=1)
            journal.append({"snapshot": {"tick": 0}})
            journal.append({"snapshot": {"tick": 1}})
            names = [segment.name for segment in journal.segments()]
            self.assertEqual(names, ["run-abc-000001.ndjson", "run-abc-000002.ndjson"])

    def test_size_target_never_deletes_segments_across_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Journal(root, run_id="old", max_lines_per_segment=1, max_total_bytes=180).append({"snapshot": {"tick": 1, "padding": "x" * 60}})
            Journal(root, run_id="new", max_lines_per_segment=1, max_total_bytes=180).append({"snapshot": {"tick": 2, "padding": "y" * 60}})
            self.assertEqual(len(list((root / "journal").glob("*.ndjson"))), 2)


if __name__ == "__main__":
    unittest.main()
