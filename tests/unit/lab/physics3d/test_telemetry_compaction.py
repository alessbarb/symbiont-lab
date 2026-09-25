from __future__ import annotations

import json

import pytest

from symbiont_lab.physics3d.telemetry_compaction import (
    CompactionPolicy,
    ObjectStore,
    StateDiffer,
    StatePatcher,
    canonical_json_bytes,
)


def test_sparse_patch_round_trip_preserves_exact_tree(tmp_path):
    before = {
        "a": {"x": 1.0, "keep": True, "remove": "gone"},
        "arr": [{"v": 1}, {"v": 2}],
        "empty": {},
        "none": None,
    }
    after = {
        "a": {"x": -0.0, "keep": True, "new": "value"},
        "arr": [{"v": 1}, {"v": 3}],
        "empty": [],
        "none": None,
    }
    store = ObjectStore(tmp_path / "objects")
    differ = StateDiffer(object_store=store)
    patcher = StatePatcher(object_store=store)

    patch = differ.diff(before, after)
    reconstructed = patcher.apply(before, patch)

    assert canonical_json_bytes(reconstructed) == canonical_json_bytes(after)
    assert any(item["op"] == "remove" for item in patch)
    assert len(patch) < 8


def test_json_pointer_escaping_is_lossless(tmp_path):
    before = {"a/b": {"x~y": 1}}
    after = {"a/b": {"x~y": 2}}

    differ = StateDiffer(object_store=ObjectStore(tmp_path / "objects"))
    patch = differ.diff(before, after)
    reconstructed = StatePatcher(object_store=ObjectStore(tmp_path / "objects")).apply(
        before, patch
    )

    assert reconstructed == after
    assert patch[0]["path"] == "/a~1b/x~0y"


def test_preferred_large_subtree_uses_content_addressed_reference(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    policy = CompactionPolicy(minimum_reference_bytes=32)
    differ = StateDiffer(object_store=store, policy=policy)
    before = {"cognitive_topology": {"nodes": [{"id": "a"}]}}
    after = {"cognitive_topology": {"nodes": [{"id": "b", "payload": "x" * 128}]}}

    patch = differ.diff(before, after)

    assert len(patch) == 1
    assert patch[0]["op"] == "ref"
    digest = patch[0]["sha256"]
    assert store.verify(digest)
    reconstructed = StatePatcher(object_store=store).apply(before, patch)
    assert reconstructed == after


def test_missing_or_tampered_object_fails_closed(tmp_path):
    store = ObjectStore(tmp_path / "objects")
    digest, _ = store.put({"value": "x" * 64})
    path = store.path_for(digest)
    path.write_text(json.dumps({"value": "tampered"}), encoding="utf-8")

    with pytest.raises(ValueError, match="object hash mismatch"):
        store.get(digest)


def test_signed_zero_is_not_compacted_away(tmp_path):
    before = {"value": 0.0}
    after = {"value": -0.0}
    store = ObjectStore(tmp_path / "objects")
    patch = StateDiffer(object_store=store).diff(before, after)

    assert patch == [{"op": "set", "path": "/value", "value": -0.0}]
    reconstructed = StatePatcher(object_store=store).apply(before, patch)
    assert canonical_json_bytes(reconstructed) == canonical_json_bytes(after)
