from __future__ import annotations

import json

import pytest

from symbiont_lab.app.physics3d_runs import Physics3DRunStore


def test_run_store_prepares_new_organism_and_fresh_body(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare({
        "body_kind": "anthropomorphic-v4",
        "organism": {"mode": "new"},
        "body": {"mode": "fresh"},
    })

    assert launch.embodiment_mode == "new"
    assert launch.symbiont_file.parent.parent == tmp_path / "organisms"
    assert launch.body_file.parent.parent == tmp_path / "bodies"
    assert launch.telemetry_file.parent.parent == tmp_path / "runs"

    manifest = json.loads((tmp_path / "runs" / launch.run_id / "manifest.json").read_text())
    assert manifest["status"] == "starting"
    assert manifest["contract"]["motor_dof"] == 31
    assert manifest["compatibility"] == "new"


def test_new_organism_cannot_resume_body(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    with pytest.raises(ValueError, match="cannot resume"):
        store.prepare({
            "body_kind": "anthropomorphic-v4",
            "organism": {"mode": "new"},
            "body": {"mode": "resume"},
        })


def test_run_store_catalogs_managed_runs(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare({
        "body_kind": "anthropomorphic-v4",
        "organism": {"mode": "new"},
        "body": {"mode": "fresh"},
    })
    store.mark_running(launch)
    runs = store.runs()
    assert runs[0]["run_id"] == launch.run_id
    assert runs[0]["status"] == "running"
    assert store.bodies()[0]["body_kind"] == "anthropomorphic-v4"


def test_injected_run_store_does_not_import_global_legacy_subject(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    assert store.organisms() == []
