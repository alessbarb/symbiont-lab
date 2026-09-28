"""Revision Coherence v1 §3.7: a bundle manifest describes exactly its runtime."""

from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from symbiont_lab.physics3d.persistence import (
    build_symbiont_bundle_manifest,
    read_symbiont_bundle_manifest,
)

RUNTIME = {"organism_id": "org.x", "saved_at_tick": 3785, "embodiment_lifecycle": {"epoch": 3}}


def _bundle(tmp_path, manifest_overrides):
    runtime_bytes = json.dumps(RUNTIME, sort_keys=True).encode("utf-8")
    manifest = build_symbiont_bundle_manifest(
        RUNTIME, runtime_sha256=hashlib.sha256(runtime_bytes).hexdigest()
    )
    manifest.update(manifest_overrides)
    path = tmp_path / "organism.symbiont"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("runtime.json", runtime_bytes)
    return path


def test_export_manifest_and_runtime_are_the_same_checkpoint(tmp_path):
    manifest = read_symbiont_bundle_manifest(_bundle(tmp_path, {}), verify=True)
    assert manifest["saved_at_tick"] == 3785


def test_a_manifest_from_another_checkpoint_is_rejected(tmp_path):
    stale = _bundle(tmp_path, {"saved_at_tick": 753})  # hash still matches runtime.json
    with pytest.raises(ValueError, match="saved_at_tick"):
        read_symbiont_bundle_manifest(stale, verify=True)
