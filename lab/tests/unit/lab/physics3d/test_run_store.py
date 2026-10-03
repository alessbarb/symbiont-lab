from __future__ import annotations

import json

import pytest

from lab.app.physics3d.runs import Physics3DRunStore
from lab.integration.physics3d.bodies import DEFAULT_BODY_REGISTRY, BodyDescriptor, BodyRegistry


def test_run_store_prepares_new_organism_and_fresh_body(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare(
        {
            "body_kind": "anthropomorphic-v6",
            "organism": {"mode": "new"},
            "body": {"mode": "fresh"},
        }
    )

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
        store.prepare(
            {
                "body_kind": "anthropomorphic-v6",
                "organism": {"mode": "new"},
                "body": {"mode": "resume"},
            }
        )


def test_run_store_catalogs_managed_runs(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare(
        {
            "body_kind": "anthropomorphic-v6",
            "organism": {"mode": "new"},
            "body": {"mode": "fresh"},
        }
    )
    store.mark_running(launch)
    runs = store.runs()
    assert runs[0]["run_id"] == launch.run_id
    assert runs[0]["status"] == "running"
    assert store.bodies()[0]["body_kind"] == "anthropomorphic-v6"


def test_injected_run_store_does_not_import_global_legacy_subject(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    assert store.organisms() == []


def test_catalog_summary_does_not_materialize_private_models(tmp_path, monkeypatch) -> None:
    from lab.physics3d import persistence

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
    from lab.physics3d import persistence

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

    launch = store.prepare(
        {
            "body_kind": "anthropomorphic-v6",
            "organism": {"mode": "existing", "ref": "org-dead"},
            "body": {"mode": "fresh"},
        }
    )
    assert launch.embodiment_mode == "reembodiment"

    with pytest.raises(ValueError, match="previous body is dead"):
        store.prepare(
            {
                "body_kind": "anthropomorphic-v6",
                "organism": {"mode": "existing", "ref": "org-dead"},
                "body": {"mode": "resume"},
            }
        )


def test_changed_contract_is_reembodiment_not_incompatible(tmp_path) -> None:
    from lab.physics3d import persistence

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

    launch = store.prepare(
        {
            "body_kind": "compact-v1",
            "organism": {"mode": "existing", "ref": "org-old"},
            "body": {"mode": "fresh"},
        }
    )
    manifest = json.loads((tmp_path / "runs" / launch.run_id / "manifest.json").read_text())
    assert manifest["compatibility"] == "reembodiment"
    assert launch.fresh_body is True


def _existing_organism(tmp_path, ref="org-x", vital_state="active"):
    from lab.physics3d import persistence

    organism_dir = tmp_path / "organisms" / ref
    organism_dir.mkdir(parents=True)
    runtime = {
        "organism_id": "symbiont:x",
        "saved_at_tick": 5,
        "living_body": {"vital_state": vital_state},
        "embodiment_lifecycle": {
            "schema_version": 1,
            "state": "dormant",
            "epoch": 1,
            "current": {"body_kind": "anthropomorphic-v6", "started_tick": 0},
            "history": [],
        },
    }
    persistence.save_symbiont_bundle(
        runtime, tmp_path / "models", organism_dir / "organism.symbiont"
    )
    body_dir = tmp_path / "bodies" / "body-x"
    body_dir.mkdir(parents=True)
    (body_dir / "body.json").write_text('{"symbiont_ticks":5}', encoding="utf-8")
    (organism_dir / "metadata.json").write_text(
        json.dumps({"ref": ref, "body_kind": "anthropomorphic-v6", "last_body_ref": "body-x"}),
        encoding="utf-8",
    )
    return organism_dir


def _prepare_existing(store, **extra):
    return store.prepare(
        {
            "body_kind": "anthropomorphic-v6",
            "organism": {"mode": "existing", "ref": "org-x"},
            "body": {"mode": "resume"},
            **extra,
        }
    )


def test_payload_without_definition_keeps_open_world_semantics(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare(
        {"body_kind": "anthropomorphic-v6", "organism": {"mode": "new"}, "body": {"mode": "fresh"}}
    )
    manifest = json.loads((tmp_path / "runs" / launch.run_id / "manifest.json").read_text())
    assert manifest["run_kind"] == "world.open"
    assert manifest["definition"]["definition_id"] == "open-world-v1"
    assert manifest["starting_state"] == {"genesis": True}
    assert manifest["seed"] == 42
    assert manifest["rates"]["physics_hz"] == 240


def test_acquisition_definition_fixes_its_protected_environment(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    base = {
        "body_kind": "anthropomorphic-v6",
        "organism": {"mode": "new"},
        "body": {"mode": "fresh"},
    }
    launch = store.prepare({**base, "definition_id": "embodiment-nursery-v1"})
    assert launch.run_kind.value == "acquisition.embodiment"
    assert launch.environment == "flat-v1"
    with pytest.raises(ValueError, match="fixes environment"):
        store.prepare(
            {**base, "definition_id": "embodiment-nursery-v1", "environment": "contact-garden-v1"}
        )


def test_vision_launch_requires_the_vision_body(tmp_path) -> None:
    store = Physics3DRunStore(tmp_path)
    launch = store.prepare(
        {
            "body_kind": "anthropomorphic-v6-vision",
            "organism": {"mode": "new"},
            "body": {"mode": "fresh"},
            "definition_id": "vision-nursery-v1",
        }
    )
    assert launch.run_kind.value == "acquisition.vision"
    assert launch.environment == "vision-nursery-v1"
    with pytest.raises(ValueError, match="requires body anthropomorphic-v6-vision"):
        store.prepare(
            {
                "body_kind": "anthropomorphic-v6",
                "organism": {"mode": "new"},
                "body": {"mode": "fresh"},
                "definition_id": "vision-nursery-v1",
            }
        )


def test_starting_state_x_is_retained_immutably(tmp_path) -> None:
    _existing_organism(tmp_path)
    store = Physics3DRunStore(tmp_path)
    launch = _prepare_existing(store, seed=101)
    manifest = json.loads((tmp_path / "runs" / launch.run_id / "manifest.json").read_text())
    start = manifest["starting_state"]
    assert start["genesis"] is False
    assert start["checkpoint_id"] == "chk-symbiontx-00000005"
    assert start["checkpoint_hash"].startswith("sha256:")
    retained = tmp_path / start["retained_path"]
    assert retained.read_bytes() == launch.symbiont_file.read_bytes()
    assert start["body_checkpoint_hash"].startswith("sha256:")
    assert (tmp_path / start["body_retained_path"]).read_text() == '{"symbiont_ticks":5}'
    assert manifest["seed"] == 101

    # The live slot evolves; the retained X never does.
    before = retained.read_bytes()
    from lab.physics3d import persistence

    persistence.save_symbiont_bundle(
        {
            "organism_id": "symbiont:x",
            "saved_at_tick": 6,
            "body_kind": "anthropomorphic-v6",
            "living_body": {"vital_state": "active"},
            "embodiment_lifecycle": {
                "schema_version": 1,
                "state": "dormant",
                "epoch": 1,
                "current": {"body_kind": "anthropomorphic-v6", "started_tick": 0},
                "history": [],
            },
        },
        tmp_path / "models",
        launch.symbiont_file,
    )
    launch.body_file.write_text('{"symbiont_ticks":6}', encoding="utf-8")
    _prepare_existing(store)
    assert retained.read_bytes() == before


def test_finalize_records_termination_ending_state_and_lifecycle(tmp_path) -> None:
    from lab.physics3d import persistence

    _existing_organism(tmp_path)
    (tmp_path / "bodies" / "body-x" / "body.json").write_text(
        json.dumps({"symbiont_ticks": 5, "lab_world": {"name": "contact-garden-v1"}}),
        encoding="utf-8",
    )
    store = Physics3DRunStore(tmp_path)
    launch = _prepare_existing(store, definition_id="contact-garden-challenge-v1")
    persistence.save_symbiont_bundle(
        {
            "organism_id": "symbiont:x",
            "saved_at_tick": 9,
            "living_body": {"vital_state": "dead"},
            "embodiment_lifecycle": {
                "schema_version": 1,
                "state": "dormant",
                "epoch": 1,
                "current": {"body_kind": "anthropomorphic-v6", "started_tick": 0},
                "history": [],
            },
        },
        tmp_path / "models",
        launch.symbiont_file,
    )
    store.finalize(launch, status="stopped", termination_reason="body_non_viable")
    manifest = json.loads((tmp_path / "runs" / launch.run_id / "manifest.json").read_text())
    assert manifest["run_kind"] == "world.challenge"
    assert manifest["termination_reason"] == "body_non_viable"
    assert manifest["protection_breach"] is False
    assert manifest["ending_state"]["checkpoint_id"] == "chk-symbiontx-00000009"
    assert (tmp_path / manifest["ending_state"]["retained_path"]).is_file()
    assert manifest["lifecycle"]["embodiment_closed"] is True
    assert manifest["lifecycle"]["reembodiment_required"] is True
    assert manifest["lifecycle"]["symbiont_state"] == "dormant"
    # The dead body can no longer be resumed; only fresh re-embodiment remains.
    with pytest.raises(ValueError, match="previous body is dead"):
        _prepare_existing(store)


def test_retention_distinguishes_bundles_sharing_organism_and_tick(tmp_path) -> None:
    from lab.physics3d import persistence

    organism_dir = _existing_organism(tmp_path)
    store = Physics3DRunStore(tmp_path)
    first = store._retain_organism("org-x", organism_dir / "organism.symbiont")
    persistence.save_symbiont_bundle(
        {
            "organism_id": "symbiont:x",
            "saved_at_tick": 5,
            "living_body": {"vital_state": "active"},
            "embodiment_lifecycle": {
                "schema_version": 1,
                "state": "dormant",
                "epoch": 2,
                "current": {"body_kind": "anthropomorphic-v6"},
                "history": [],
            },
        },
        tmp_path / "models",
        organism_dir / "organism.symbiont",
    )
    second = store._retain_organism("org-x", organism_dir / "organism.symbiont")
    assert first["checkpoint_id"] == second["checkpoint_id"]
    assert first["bundle_hash"] != second["bundle_hash"]
    assert first["retained_path"] != second["retained_path"]
    for state in (first, second):
        assert persistence.hashlib.sha256(
            (tmp_path / state["retained_path"]).read_bytes()
        ).hexdigest() == state["bundle_hash"].removeprefix("sha256:")


def test_fixed_environment_definition_rejects_resumed_body_from_other_world(tmp_path) -> None:
    _existing_organism(tmp_path)
    body = tmp_path / "bodies" / "body-x" / "body.json"
    body.write_text(
        json.dumps({"symbiont_ticks": 5, "lab_world": {"name": "contact-garden-v1"}}),
        encoding="utf-8",
    )
    store = Physics3DRunStore(tmp_path)
    runs_before = set((tmp_path / "runs").iterdir())
    with pytest.raises(ValueError, match="requires flat-v1 and therefore a fresh body"):
        _prepare_existing(store, definition_id="embodiment-nursery-v1")
    assert set((tmp_path / "runs").iterdir()) == runs_before  # refused before any run exists
    assert _prepare_existing(store, definition_id="contact-garden-challenge-v1")


def test_acquisition_refuses_resume_at_protected_boundary(tmp_path) -> None:
    _existing_organism(tmp_path, vital_state="agonizing")
    store = Physics3DRunStore(tmp_path)
    with pytest.raises(ValueError, match="protected viability boundary"):
        _prepare_existing(store, definition_id="embodiment-nursery-v1")
    # World accepts the same body: consequences are not the Lab's to prevent.
    assert _prepare_existing(store).run_kind.value == "world.open"


def test_observer_alias_persists_across_runs_and_never_enters_the_organism(tmp_path) -> None:
    from lab.physics3d import persistence

    _existing_organism(tmp_path)
    store = Physics3DRunStore(tmp_path)
    assert store.set_alias("org-x", "  Ada   the  first ") == {
        "ref": "org-x",
        "alias": "Ada the first",
    }
    assert store.organisms()[0]["alias"] == "Ada the first"
    assert store.alias_for("org-x") == "Ada the first"
    assert store.alias_for(None) is None

    launch = _prepare_existing(store)
    assert "Ada" not in repr(launch.runner_kwargs())
    store.finalize(launch, status="stopped", termination_reason="operator_stop")
    assert store.organisms()[0]["alias"] == "Ada the first"

    bundle = tmp_path / "organisms" / "org-x" / "organism.symbiont"
    with persistence.zipfile.ZipFile(bundle) as archive:
        for name in archive.namelist():
            assert b"Ada" not in archive.read(name)

    assert store.set_alias("org-x", "")["alias"] is None
    assert "alias" not in store.organisms()[0]


def test_alias_rejects_unknown_or_unsafe_refs_and_long_names(tmp_path) -> None:
    _existing_organism(tmp_path)
    store = Physics3DRunStore(tmp_path)
    for ref in ("org-missing", "../org-x", "", ".hidden"):
        with pytest.raises(ValueError, match="unknown organism"):
            store.set_alias(ref, "x")
    with pytest.raises(ValueError, match="at most 64"):
        store.set_alias("org-x", "x" * 65)


def test_catalog_marks_stale_body_checkpoint_non_resumable(tmp_path) -> None:
    _existing_organism(tmp_path)
    body = tmp_path / "bodies" / "body-x" / "body.json"
    body.write_text('{"symbiont_ticks":4}', encoding="utf-8")

    store = Physics3DRunStore(tmp_path)
    item = store.organisms()[0]

    assert item["tick"] == 5
    assert item["body_checkpoint_tick"] == 4
    assert item["body_checkpoint_in_sync"] is False
    assert item["resumable_body"] is False
    assert item["runnable"] is True


def test_resume_rejects_stale_body_before_creating_run(tmp_path) -> None:
    _existing_organism(tmp_path)
    body = tmp_path / "bodies" / "body-x" / "body.json"
    body.write_text('{"symbiont_ticks":4}', encoding="utf-8")

    store = Physics3DRunStore(tmp_path)
    runs_before = set((tmp_path / "runs").iterdir())

    with pytest.raises(ValueError, match=r"stale relative to the Symbiont \(4 != 5\)"):
        _prepare_existing(store)

    assert set((tmp_path / "runs").iterdir()) == runs_before
    # The Symbiont remains runnable through explicit fresh re-embodiment.
    launch = store.prepare(
        {
            "body_kind": "anthropomorphic-v6",
            "organism": {"mode": "existing", "ref": "org-x"},
            "body": {"mode": "fresh"},
        }
    )
    assert launch.embodiment_mode == "reembodiment"
    assert launch.fresh_body is True


def test_finalize_only_marks_body_resumable_when_tick_aligned(tmp_path) -> None:
    from lab.physics3d import persistence

    _existing_organism(tmp_path)
    store = Physics3DRunStore(tmp_path)
    launch = _prepare_existing(store)

    persistence.save_symbiont_bundle(
        {
            "organism_id": "symbiont:x",
            "saved_at_tick": 8,
            "living_body": {"vital_state": "active"},
            "embodiment_lifecycle": {
                "schema_version": 1,
                "state": "dormant",
                "epoch": 1,
                "current": {"body_kind": "anthropomorphic-v6", "started_tick": 0},
                "history": [],
            },
        },
        tmp_path / "models",
        launch.symbiont_file,
    )
    # Simulate a crash window: organism persisted at t8, body remained at t5.
    store.finalize(launch, status="failed", error="simulated interruption")

    body_meta = json.loads(
        (tmp_path / "bodies" / "body-x" / "metadata.json").read_text(encoding="utf-8")
    )
    assert body_meta["checkpoint_tick"] == 5
    assert body_meta["checkpoint_in_sync"] is False
    assert body_meta["resumable"] is False
