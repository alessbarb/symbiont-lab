import gzip
import json

from observatory.history_summary import build_history_summary


def test_summary_covers_raw_and_compacted_segments_without_replacing_them(tmp_path):
    first = tmp_path / "run-1-000001.ndjson"
    first.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "sequence": 0,
                "snapshot": {"schema_version": 3, "tick": 4, "organism": {"state": "observing"}},
            }
        )
        + "\n"
    )
    second = tmp_path / "run-1-000002.ndjson.gz"
    with gzip.open(second, "wt", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "run_id": "run-1",
                    "sequence": 1,
                    "snapshot": {"schema_version": 3, "tick": 5, "organism": {"state": "resting"}},
                }
            )
            + "\n"
        )
    summary = build_history_summary(tmp_path, run_id="run-1")
    assert summary["entries"] == 2
    assert summary["tick_range"] == {"min": 4, "max": 5}
    assert summary["organism_states"] == {"observing": 1, "resting": 1}
    assert {segment["name"] for segment in summary["segments"]} == {first.name, second.name}
