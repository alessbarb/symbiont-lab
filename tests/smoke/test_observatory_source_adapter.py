from __future__ import annotations

import gzip
import json

from symbiont_lab.observation.observatory import (
    ObservatorySource,
    parse_journal_line,
    read_journal,
    valid_instance_id,
)


def test_instance_id_validation_is_observation_owned() -> None:
    assert valid_instance_id("0123456789abcdef")
    assert not valid_instance_id("0123456789abcdeg")
    assert not valid_instance_id("short")


def test_journal_parser_rejects_wrong_run_and_invalid_sequence() -> None:
    assert parse_journal_line("", "run-a") is None
    assert parse_journal_line('{"run_id":"run-b","sequence":1,"snapshot":{}}', "run-a") is None
    assert parse_journal_line('{"run_id":"run-a","sequence":true,"snapshot":{}}', "run-a") is None
    assert parse_journal_line('{"run_id":"run-a","sequence":-1,"snapshot":{}}', "run-a") is None

    entry = parse_journal_line('{"run_id":"run-a","sequence":2,"snapshot":{"tick":4}}', "run-a")
    assert entry is not None
    assert entry["sequence"] == 2


def test_journal_reader_handles_plain_and_gzip_segments(tmp_path) -> None:
    journal = tmp_path / "journal"
    journal.mkdir()
    plain = journal / "run-a-000.ndjson"
    plain.write_text(
        '{"run_id":"run-a","sequence":1,"snapshot":{"tick":1}}\n',
        encoding="utf-8",
    )
    compressed = journal / "run-a-001.ndjson.gz"
    with gzip.open(compressed, "wt", encoding="utf-8") as handle:
        handle.write('{"run_id":"run-a","sequence":2,"snapshot":{"tick":2}}\n')

    positions = {}
    entries = read_journal(journal, "run-a", positions)
    assert [entry["sequence"] for entry in entries] == [1, 2]

    assert read_journal(journal, "run-a", positions) == []


def test_observatory_source_reads_topology_and_manifest_without_mutation(tmp_path) -> None:
    instances = tmp_path / "instances"
    instances.mkdir()
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    instance_id = "0123456789abcdef"
    (instances / f"{instance_id}.json").write_text(
        json.dumps({"instance_id": instance_id, "run_id": "run-a"}),
        encoding="utf-8",
    )
    (manifests / f"{instance_id}.manifest.json").write_text(
        json.dumps(
            {
                "instance_id": instance_id,
                "run_id": "run-a",
                "organism_id": "o-1",
                "host_agent": "a",
                "platform": "linux",
                "run_started": "1970-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (instances / f"{instance_id}.topology.json").write_text(
        json.dumps({"nodes": [{"id": "concept.1"}], "edges": []}),
        encoding="utf-8",
    )

    source = ObservatorySource(tmp_path)
    assert source.manifest(instance_id)["run_id"] == "run-a"
    assert source.topology(instance_id)["nodes"][0]["id"] == "concept.1"
