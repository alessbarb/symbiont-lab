from __future__ import annotations

import json

import pytest

from symbiont.host.acclimation import HostAcclimation
from symbiont.host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointError,
    export_checkpoint,
    import_checkpoint,
    load_checkpoint_file,
    normalize_checkpoint,
    save_checkpoint_atomic,
)
from symbiont.host.drift import DriftAwareBaseline
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from symbiont.host.rhythms import RhythmModel, TimeBucket


def _reading(capability_id: str, value: float) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="test",
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=0,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_export_is_empty_shell_when_nothing_is_learned_yet():
    payload = export_checkpoint()

    assert payload == {"schema_version": CHECKPOINT_SCHEMA_VERSION}


def test_export_omits_capabilities_below_min_samples():
    acclimation = HostAcclimation(min_samples=5)
    acclimation.observe([_reading("cpu", 0.1)])

    payload = export_checkpoint(acclimation=acclimation)

    assert payload["acclimation"] == {}


def test_acclimation_round_trips_through_checkpoint():
    """Restoring seeds a coarse consolidated prior, not the exact original
    aggregate (design docs/design/cognicion-y-plasticidad.md §16):
    the restored count is a small fixed prior weight, and mean/variance are
    an order-of-magnitude anchor, not an exact match."""
    acclimation = HostAcclimation(min_samples=2)
    for value in [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 9.95, 10.05]:
        acclimation.observe([_reading("cpu", value)])

    payload = export_checkpoint(acclimation=acclimation)
    restored, _, _ = import_checkpoint(payload, acclimation=HostAcclimation(min_samples=2))

    assert restored.is_acclimated("cpu")
    baseline = restored.baseline("cpu")
    original = acclimation.baseline("cpu")
    assert baseline.count != original.count
    assert baseline.count <= 8
    assert baseline.mean == pytest.approx(original.mean, rel=0.6)


def test_rhythms_round_trip_through_checkpoint():
    from symbiont.host.percepts import Percept

    model = RhythmModel(min_samples=2)
    percept = Percept(
        name="system_load",
        value=0.5,
        unit=Unit.RATIO,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )
    for _ in range(8):
        model.observe([percept], time_bucket=TimeBucket.NIGHT)

    payload = export_checkpoint(rhythm_model=model)
    _, restored, _ = import_checkpoint(payload, rhythm_model=RhythmModel(min_samples=2))

    assert restored.is_learned("system_load", TimeBucket.NIGHT)
    baseline = restored.baseline("system_load", TimeBucket.NIGHT)
    assert baseline.count <= 8
    assert baseline.mean == pytest.approx(0.5, rel=0.6)


def test_drift_baseline_round_trips_but_not_pending_buffer():
    # import_checkpoint restores drift baselines with the class default
    # min_samples (5) -- match it here so the restored prior weight (a
    # small fixed table, not the real count) has a fair chance to clear it.
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    values = [1.0, 1.05, 0.95, 1.02, 0.98, 1.01, 0.99, 1.0, 1.02, 0.98] * 2
    for v in values:
        baseline.observe(v)

    payload = export_checkpoint(drift_baselines={"system_load": baseline})
    _, _, restored = import_checkpoint(payload)

    restored_baseline = restored["system_load"]
    assert restored_baseline.is_established
    assert restored_baseline.mean == pytest.approx(baseline.mean, abs=0.6)
    assert restored_baseline.count != baseline.count
    assert restored_baseline.observe(1.0).kind != "regime_shift"


def test_drift_baseline_omitted_before_established():
    baseline = DriftAwareBaseline(min_samples=5)
    baseline.observe(1.0)

    payload = export_checkpoint(drift_baselines={"system_load": baseline})

    assert payload["drift"] == {}


def test_import_rejects_missing_schema_version():
    with pytest.raises(CheckpointError):
        import_checkpoint({})


def test_import_rejects_wrong_schema_version():
    with pytest.raises(CheckpointError):
        import_checkpoint({"schema_version": 999})


def test_import_rejects_non_dict_payload():
    with pytest.raises(CheckpointError):
        import_checkpoint([])  # type: ignore[arg-type]


def test_import_rejects_malformed_entries():
    with pytest.raises(CheckpointError):
        import_checkpoint({"schema_version": CHECKPOINT_SCHEMA_VERSION, "acclimation": {"cpu": {"count": 5}}})


def test_import_rejects_unknown_time_bucket():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "rhythms": [
            {"percept_name": "x", "time_bucket": "midnight-ish", "count": 5, "mean": 1.0, "variance": 0.0}
        ],
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_full_round_trip_across_all_three_models():
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cpu", 0.2)])

    payload = export_checkpoint(
        acclimation=acclimation,
        rhythm_model=RhythmModel(),
        drift_baselines={},
    )
    restored_acclimation, restored_rhythms, restored_drift = import_checkpoint(
        payload, acclimation=HostAcclimation(min_samples=1)
    )

    assert restored_acclimation.is_acclimated("cpu")
    assert restored_rhythms.learned_contexts == ()
    assert restored_drift == {}


def test_importing_into_a_stricter_min_samples_config_does_not_mark_it_learned():
    """A restored baseline remains subject to the current sample threshold."""
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cpu", 0.2)])
    payload = export_checkpoint(acclimation=acclimation)

    restored, _, _ = import_checkpoint(payload, acclimation=HostAcclimation(min_samples=5))

    assert not restored.is_acclimated("cpu")


# --- v0.46+: saved_at_tick, schema migration, atomic file persistence ---


def test_saved_at_tick_omitted_when_not_given():
    payload = export_checkpoint()
    assert "saved_at_tick" not in payload


def test_saved_at_tick_round_trips():
    payload = export_checkpoint(saved_at_tick=42)
    assert payload["saved_at_tick"] == 42


def test_v1_payload_migrates_forward_and_imports_cleanly():
    v1_payload = {
        "schema_version": 1,
        "acclimation": {"cpu": {"count": 5, "mean": 1.0, "variance": 0.0}},
    }
    restored, _, _ = import_checkpoint(v1_payload, acclimation=HostAcclimation(min_samples=1))

    assert restored.is_acclimated("cpu")


def test_unknown_old_schema_version_with_no_migration_path_is_rejected():
    with pytest.raises(CheckpointError):
        import_checkpoint({"schema_version": 0})


def test_newer_schema_version_is_rejected_as_unsupported():
    with pytest.raises(CheckpointError):
        import_checkpoint({"schema_version": CHECKPOINT_SCHEMA_VERSION + 1})


def test_save_checkpoint_atomic_then_load_round_trips(tmp_path):
    payload = export_checkpoint(saved_at_tick=3)
    path = tmp_path / "state.json"

    save_checkpoint_atomic(payload, path)
    loaded = load_checkpoint_file(path)

    assert loaded == payload


def test_load_checkpoint_file_returns_none_when_missing(tmp_path):
    assert load_checkpoint_file(tmp_path / "does-not-exist.json") is None


def test_load_checkpoint_file_rejects_invalid_json(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("{not valid json")

    with pytest.raises(CheckpointError):
        load_checkpoint_file(path)


def test_load_checkpoint_file_rejects_non_object_json(tmp_path):
    path = tmp_path / "list.json"
    path.write_text(json.dumps([1, 2, 3]))

    with pytest.raises(CheckpointError):
        load_checkpoint_file(path)


def test_save_checkpoint_atomic_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "state.json"
    save_checkpoint_atomic(export_checkpoint(), path)

    assert path.is_file()


def test_save_checkpoint_atomic_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "state.json"
    save_checkpoint_atomic(export_checkpoint(), path)

    remaining = list(tmp_path.iterdir())
    assert remaining == [path]


def test_save_checkpoint_rejects_over_limit_without_replacing_previous_file(tmp_path):
    path = tmp_path / "state.json"
    save_checkpoint_atomic({"schema_version": CHECKPOINT_SCHEMA_VERSION, "marker": "old"}, path)
    oversized = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "blob": "x" * (2 * 1024 * 1024)}
    with pytest.raises(CheckpointError, match="size limit"):
        save_checkpoint_atomic(oversized, path)
    assert load_checkpoint_file(path)["marker"] == "old"


# --- A07: corrupt numeric data is rejected at the import boundary ---


def test_import_rejects_negative_variance():
    payload = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "acclimation": {"x": {"count": 10, "mean": 0, "variance": -1}}}
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_non_finite_mean():
    payload = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "acclimation": {"x": {"count": 10, "mean": float("nan"), "variance": 1.0}}}
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_infinite_variance():
    payload = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "acclimation": {"x": {"count": 10, "mean": 0.0, "variance": float("inf")}}}
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_negative_count_in_rhythms():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "rhythms": [{"percept_name": "x", "time_bucket": "night", "count": -1, "mean": 0.0, "variance": 0.0}],
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_negative_variance_in_drift():
    payload = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "drift": {"x": {"count": 10, "mean": 0.0, "variance": -5.0}}}
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


# --- B04: a non-integer sample count must not silently truncate ---


def test_import_rejects_a_non_integer_count_in_acclimation():
    payload = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "acclimation": {"x": {"count": 5.5, "mean": 1.0, "variance": 1.0}}}
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_a_non_integer_count_in_drift():
    payload = {"schema_version": CHECKPOINT_SCHEMA_VERSION, "drift": {"x": {"count": 5.5, "mean": 1.0, "variance": 1.0}}}
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


# --- v0.53+: self-model and resident checkpoint migrations ---


def test_v2_checkpoint_migrates_to_current_with_empty_self_model():
    v2_payload = {"schema_version": 2, "saved_at_tick": 5}
    migrated = normalize_checkpoint(dict(v2_payload))
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert migrated["self_model"] == {}


def test_v1_checkpoint_migrates_all_the_way_to_current():
    v1_payload = {"schema_version": 1}
    migrated = normalize_checkpoint(v1_payload)
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert migrated["saved_at_tick"] is None
    assert migrated["self_model"] == {}


def test_v2_checkpoint_still_imports_cleanly_through_migration():
    # count=20 -> maturity_class 5 -> prior weight 6, enough to clear the
    # default HostAcclimation min_samples=5 after consolidated restore
    # (design §16: restore seeds a small fixed prior weight, not the real
    # historical count).
    payload = {"schema_version": 2, "saved_at_tick": 3, "acclimation": {"x": {"count": 20, "mean": 1.0, "variance": 0.0}}}
    acclimation, _, _ = import_checkpoint(payload)
    assert acclimation.baseline("x") is not None


def test_current_schema_version_is_eight():
    assert CHECKPOINT_SCHEMA_VERSION == 8


def test_v6_checkpoint_migrates_through_signal_knowledge_to_current():
    migrated = normalize_checkpoint({"schema_version": 6, "saved_at_tick": 12})
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert migrated["signal_knowledge"] == {
        "schema_version": 1,
        "last_tick": None,
        "profiles": [],
    }
    assert migrated["sensory_system"] is None


def test_v7_checkpoint_migrates_to_v8_without_inventing_sensory_phenotype():
    migrated = normalize_checkpoint({
        "schema_version": 7,
        "saved_at_tick": 12,
        "effective_config": {"discover_senses": True},
    })
    assert migrated["schema_version"] == 8
    assert migrated["sensory_system"] is None
    assert migrated["effective_config"]["sensory_plasticity"] is False


def test_v3_checkpoint_migrates_to_current_backfilling_recency_class():
    v3_payload = {
        "schema_version": 3,
        "saved_at_tick": 42,
        "self_model": {"sense-a": {"cost_class": 0, "health_class": 8, "confidence_class": 8, "maturity_class": 4}},
    }
    migrated = normalize_checkpoint(dict(v3_payload))
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    # v3->v4 backfills last_observed_tick to saved_at_tick (idle=0); v5->v6
    # then converts that into recency_class -- CURRENT, since idle is 0.
    from symbiont.core.selfmodel import RecencyClass

    assert "last_observed_tick" not in migrated["self_model"]["sense-a"]
    assert migrated["self_model"]["sense-a"]["recency_class"] == RecencyClass.CURRENT.value


def test_v4_checkpoint_adds_privacy_safe_resident_continuity_fields():
    v4_payload = {
        "schema_version": 4,
        "saved_at_tick": 38,
        "sensory_development": {
            "states": [
                {
                    "capability_id": "compute.logical_cpu",
                    "percept_name": "sense_example",
                    "samples": 8,
                    "available_samples": 8,
                    "mean": 1.0,
                    "m2": 2.0,
                    "delta_ewma": 0.1,
                }
            ]
        },
        "cognitive_bridge": {"graph": None},
    }

    migrated = normalize_checkpoint(v4_payload)

    assert v4_payload["schema_version"] == 4
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    fingerprints = migrated["sensory_development"]["known_capability_fingerprints"]
    assert len(fingerprints) == 1
    assert len(fingerprints[0]) == 64
    assert migrated["cognitive_bridge"]["previous_frame"] == {}
    assert migrated["cognitive_bridge"]["structural_plasticity"] == {}


def test_v5_self_model_with_exact_last_observed_tick_migrates_without_crashing():
    """Real regression: PR3 changed SelfModel.restore() to require
    recency_class, but no migration step existed for a genuine historical
    v5 checkpoint's exact last_observed_tick -- this crashed with a raw
    KeyError, not even a clean CheckpointError, before this task."""
    from symbiont.core.selfmodel import RecencyClass, SelfModel

    v5_payload = {
        "schema_version": 5,
        "saved_at_tick": 100,
        "self_model": {
            "cpu": {
                "cost_class": 0, "health_class": 8, "confidence_class": 8, "maturity_class": 4,
                "last_observed_tick": 95,
            },
        },
    }
    migrated = normalize_checkpoint(v5_payload)
    assert migrated["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    entry = migrated["self_model"]["cpu"]
    assert "last_observed_tick" not in entry
    assert entry["recency_class"] == RecencyClass.CURRENT.value  # idle 5 ticks, within the CURRENT threshold

    restored = SelfModel.restore(migrated["self_model"], allowed_sense_ids={"cpu"}, current_tick=100)
    assert restored.is_established("cpu")


def test_v5_acclimation_with_exact_stats_migrates_to_consolidated_classes():
    v5_payload = {
        "schema_version": 5,
        "acclimation": {"cpu": {"count": 20, "mean": 10.0, "variance": 0.04}},
        "rhythms": [{"percept_name": "cpu", "time_bucket": "night", "count": 10, "mean": 5.0, "variance": 1.0}],
        "drift": {"cpu": {"count": 30, "mean": 10.0, "variance": 0.04}},
    }
    migrated = normalize_checkpoint(v5_payload)
    assert set(migrated["acclimation"]["cpu"]) == {"center_class", "scale_class", "maturity_class"}
    assert set(migrated["rhythms"][0]) == {"percept_name", "time_bucket", "center_class", "scale_class", "maturity_class"}
    assert set(migrated["drift"]["cpu"]) == {"center_class", "scale_class", "maturity_class"}

    acclimation, rhythm_model, drift_baselines = import_checkpoint(migrated)
    assert acclimation.baseline("cpu") is not None
    assert drift_baselines["cpu"].is_established or drift_baselines["cpu"].count > 0
