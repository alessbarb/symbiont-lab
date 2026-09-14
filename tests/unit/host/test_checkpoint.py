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
    acclimation = HostAcclimation(min_samples=2)
    acclimation.observe([_reading("cpu", 0.1), _reading("cpu", 0.3)])

    payload = export_checkpoint(acclimation=acclimation)
    restored, _, _ = import_checkpoint(payload, acclimation=HostAcclimation(min_samples=2))

    assert restored.is_acclimated("cpu")
    baseline = restored.baseline("cpu")
    original = acclimation.baseline("cpu")
    assert baseline.count == original.count
    assert baseline.mean == pytest.approx(original.mean)
    assert baseline.variance == pytest.approx(original.variance)


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
    model.observe([percept], time_bucket=TimeBucket.NIGHT)
    model.observe([percept], time_bucket=TimeBucket.NIGHT)

    payload = export_checkpoint(rhythm_model=model)
    _, restored, _ = import_checkpoint(payload, rhythm_model=RhythmModel(min_samples=2))

    assert restored.is_learned("system_load", TimeBucket.NIGHT)
    baseline = restored.baseline("system_load", TimeBucket.NIGHT)
    assert baseline.count == 2
    assert baseline.mean == pytest.approx(0.5)


def test_drift_baseline_round_trips_but_not_pending_buffer():
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    for v in [1.0, 1.05, 0.95, 1.02, 0.98]:
        baseline.observe(v)
    baseline.observe(5.0)  # starts a pending, unconfirmed streak

    payload = export_checkpoint(drift_baselines={"system_load": baseline})
    _, _, restored = import_checkpoint(payload)

    restored_baseline = restored["system_load"]
    assert restored_baseline.is_established
    assert restored_baseline.mean == pytest.approx(baseline.mean)
    assert restored_baseline.count == baseline.count
    # The pending streak/buffer is never exported: a fresh confirmation run
    # is required after restore, it does not resume mid-streak.
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
    """Documented, deliberate behavior: a restored baseline's sample count is
    honest, and a stricter min_samples than the exporting instance used can
    still withhold "learned" until it is met — restoring is not laundering
    past a threshold the current config wants enforced."""
    acclimation = HostAcclimation(min_samples=1)
    acclimation.observe([_reading("cpu", 0.2)])
    payload = export_checkpoint(acclimation=acclimation)

    restored, _, _ = import_checkpoint(payload, acclimation=HostAcclimation(min_samples=5))

    assert not restored.is_acclimated("cpu")


# --- v0.46: saved_at_tick, schema migration, atomic file persistence ---


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


# --- v0.53: self-model checkpoint schema bump 2 -> 3 ---


def test_current_schema_version_is_three():
    assert CHECKPOINT_SCHEMA_VERSION == 3


def test_v2_checkpoint_migrates_to_v3_with_empty_self_model():
    from symbiont.host.checkpoint import _migrate_to_current

    v2_payload = {"schema_version": 2, "saved_at_tick": 5}
    migrated = _migrate_to_current(dict(v2_payload))
    assert migrated["schema_version"] == 3
    assert migrated["self_model"] == {}


def test_v1_checkpoint_migrates_through_v2_to_v3():
    from symbiont.host.checkpoint import _migrate_to_current

    v1_payload = {"schema_version": 1}
    migrated = _migrate_to_current(v1_payload)
    assert migrated["schema_version"] == 3
    assert migrated["saved_at_tick"] is None
    assert migrated["self_model"] == {}


def test_v2_checkpoint_still_imports_cleanly_through_migration():
    payload = {"schema_version": 2, "saved_at_tick": 3, "acclimation": {"x": {"count": 5, "mean": 1.0, "variance": 0.0}}}
    acclimation, _, _ = import_checkpoint(payload)
    assert acclimation.baseline("x") is not None
