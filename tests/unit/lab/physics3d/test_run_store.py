from __future__ import annotations

import json

import pytest

from symbiont_lab.app.physics3d_runs import Physics3DRunStore
from symbiont_lab.physics3d.bodies import BodyDescriptor, BodyRegistry, DEFAULT_BODY_REGISTRY


def test_run_store_prepares_new_organism_and_fresh_body(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare({
        "body_kind": "anthropomorphic-v5",
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
            "body_kind": "anthropomorphic-v5",
            "organism": {"mode": "new"},
            "body": {"mode": "resume"},
        })


def test_run_store_catalogs_managed_runs(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare({
        "body_kind": "anthropomorphic-v5",
        "organism": {"mode": "new"},
        "body": {"mode": "fresh"},
    })
    store.mark_running(launch)
    runs = store.runs()
    assert runs[0]["run_id"] == launch.run_id
    assert runs[0]["status"] == "running"
    assert store.bodies()[0]["body_kind"] == "anthropomorphic-v5"


def test_injected_run_store_does_not_import_global_legacy_subject(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    assert store.organisms() == []


def test_catalog_summary_does_not_materialize_private_models(tmp_path, monkeypatch) -> None:
    from symbiont_lab.physics3d import persistence

    organism_dir = tmp_path / "organisms" / "org-test"
    organism_dir.mkdir(parents=True)
    bundle = organism_dir / "organism.symbiont"
    with persistence.zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("runtime.json", '{"organism_id":"symbiont:test","saved_at_tick":7}')
        archive.writestr("models/" + "a" * 64 + ".pt", b"large-model-placeholder")

    store = Physics3DRunStore(tmp_path)
    items = store.organisms()

    assert items[0]["organism_id"] == "symbiont:test"
    assert not (organism_dir / ".catalog-models").exists()


def test_dead_body_leaves_symbiont_runnable_for_fresh_reembodiment(tmp_path) -> None:
    from symbiont_lab.physics3d import persistence

    organism_dir = tmp_path / "organisms" / "org-dead"
    organism_dir.mkdir(parents=True)
    bundle = organism_dir / "organism.symbiont"
    with persistence.zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(
            "runtime.json",
            '{"organism_id":"symbiont:persistent","saved_at_tick":9,'
            '"living_body":{"vital_state":"dead"}}',
        )
    (organism_dir / "metadata.json").write_text(
        '{"ref":"org-dead","body_kind":"anthropomorphic-v4","last_body_ref":"body-old"}',
        encoding="utf-8",
    )

    store = Physics3DRunStore(tmp_path)
    item = store.organisms()[0]
    assert item["runnable"] is True
    assert item["symbiont_state"] == "dormant"
    assert item["vital_state"] == "dead"

    launch = store.prepare({
        "body_kind": "anthropomorphic-v5",
        "organism": {"mode": "existing", "ref": "org-dead"},
        "body": {"mode": "fresh"},
    })
    assert launch.embodiment_mode == "reembodiment"

    with pytest.raises(ValueError, match="previous body is dead"):
        store.prepare({
            "body_kind": "anthropomorphic-v5",
            "organism": {"mode": "existing", "ref": "org-dead"},
            "body": {"mode": "resume"},
        })



def test_changed_contract_is_reembodiment_not_incompatible(tmp_path) -> None:
    from symbiont_lab.physics3d import persistence

    compact = BodyDescriptor(
        body_kind="compact-v1",
        display_name="Compact",
        version=1,
        motor_dof=20,
        receptor_count=84,
        effector_count=40,
        receptor_ids=tuple(f"rec.{i}" for i in range(84)),
        interoceptive_receptor_ids=(),
        effector_ids=tuple(f"eff.{i}" for i in range(40)),
        apparatus_factory=lambda _p, _client_id: None,
        ground_material=None,
    )
    registry = BodyRegistry((*DEFAULT_BODY_REGISTRY.list(), compact))
    store = Physics3DRunStore(tmp_path, body_registry=registry)

    organism_dir = tmp_path / "organisms" / "org-old"
    organism_dir.mkdir(parents=True)
    with persistence.zipfile.ZipFile(organism_dir / "organism.symbiont", "w") as archive:
        archive.writestr(
            "runtime.json",
            '{"organism_id":"symbiont:persistent","saved_at_tick":12,'
            '"living_body":{"vital_state":"active"},'
            '"embodiment_lifecycle":{"schema_version":1,"state":"dormant","epoch":1,'
            '"current":{"body_kind":"anthropomorphic-v4","receptor_count":107,'
            '"effector_count":62,"started_tick":0,"body_vital_state":"active"},'
            '"history":[]}}',
        )
    (organism_dir / "metadata.json").write_text(
        '{"ref":"org-old","body_kind":"anthropomorphic-v4",'
        '"receptor_count":107,"effector_count":62}',
        encoding="utf-8",
    )

    launch = store.prepare({
        "body_kind": "compact-v1",
        "organism": {"mode": "existing", "ref": "org-old"},
        "body": {"mode": "fresh"},
    })
    manifest = json.loads(
        (tmp_path / "runs" / launch.run_id / "manifest.json").read_text()
    )
    assert manifest["compatibility"] == "reembodiment"
    assert launch.fresh_body is True
