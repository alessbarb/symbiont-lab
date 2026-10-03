import json

import pytest

from symbiont_lab.studies.physics3d.a7_artifacts import (
    compare_replays,
    verify_execution_artifacts,
    write_execution_artifacts,
)


def test_a7_execution_artifacts_are_write_once_and_hash_verified(tmp_path):
    directory = tmp_path / "seed-42-repeat-1"
    write_execution_artifacts(
        directory,
        manifest={"run_key": "body/idle/nominal/seed-42/repeat-1"},
        ticks=[{"tick": 1, "physics": {"raw_substeps": []}}],
        checkpoints=[],
        validation={"outcome": "pass"},
    )

    assert verify_execution_artifacts(directory) == {
        "integrity": True,
        "outcome": "verified",
        "artifact_count": 3,
    }
    with pytest.raises(FileExistsError):
        write_execution_artifacts(directory, manifest={}, ticks=[], checkpoints=[], validation={})

    (directory / "ticks.jsonl").write_text("{}\n", encoding="utf-8")
    assert verify_execution_artifacts(directory)["outcome"] == "inconclusive"


def test_a7_incomplete_execution_artifacts_are_inconclusive(tmp_path):
    assert verify_execution_artifacts(tmp_path)["outcome"] == "inconclusive"
    (tmp_path / "manifest.json").write_text(json.dumps({"artifact_sha256": {}}), encoding="utf-8")
    assert verify_execution_artifacts(tmp_path)["outcome"] == "inconclusive"


def test_a7_replay_comparison_sorts_contacts_and_enforces_tolerance_and_discrete_fields():
    left = {
        "tick": 4,
        "position": [1.0, 2.0],
        "contacts": [
            {"body_a": 1, "body_b": 2, "link_a": 0, "link_b": 1, "position_a": [0, 0, 0]},
            {"body_a": 1, "body_b": 3, "link_a": 0, "link_b": 2, "position_a": [1, 0, 0]},
        ],
    }
    right = {
        "tick": 4,
        "position": [1.0 + 1e-10, 2.0],
        "contacts": list(reversed(left["contacts"])),
    }

    assert compare_replays(left, right)["pass"] is True
    right["tick"] = 5
    assert compare_replays(left, right)["pass"] is False
