from __future__ import annotations

import json

import pytest

from symbiont.host.acclimation import HostAcclimation
from symbiont.host.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    MAX_HOST_CHECKPOINT_BYTES,
    CheckpointError,
    export_checkpoint,
    import_checkpoint,
    load_checkpoint_file,
    save_checkpoint_atomic,
)
from symbiont.host.drift import DriftAwareBaseline
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from symbiont.host.rhythms import CyclePhase, RhythmModel


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


def test_acclimation_round_trips_as_a_coarse_prior_by_default():
    """The default (real-host) export seeds a coarse consolidated prior, not
    the exact aggregate (docs/design/cognicion-y-plasticidad.md §16)."""
    acclimation = HostAcclimation(min_samples=2)
    for value in [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 9.95, 10.05]:
        acclimation.observe([_reading("cpu", value)])

    payload = export_checkpoint(acclimation=acclimation)
    assert "acclimation_replay" not in payload
    restored, _, _ = import_checkpoint(payload, acclimation=HostAcclimation(min_samples=2))

    assert restored.is_acclimated("cpu")
    baseline = restored.baseline("cpu")
    original = acclimation.baseline("cpu")
    assert baseline.count != original.count
    assert baseline.count <= 8
    assert baseline.mean == pytest.approx(original.mean, rel=0.6)


def test_acclimation_replay_restores_exact_accumulators():
    """Deterministic hosts request replay state for exact continuation."""
    acclimation = HostAcclimation(min_samples=2)
    for value in [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 9.95, 10.05]:
        acclimation.observe([_reading("cpu", value)])

    payload = export_checkpoint(acclimation=acclimation, include_replay=True)
    restored, _, _ = import_checkpoint(payload, acclimation=HostAcclimation(min_samples=2))

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
    for _ in range(8):
        model.observe([percept], phase=CyclePhase.PHASE_0)

    payload = export_checkpoint(rhythm_model=model)
    _, restored, _ = import_checkpoint(payload, rhythm_model=RhythmModel(min_samples=2))

    assert restored.is_learned("system_load", CyclePhase.PHASE_0)
    baseline = restored.baseline("system_load", CyclePhase.PHASE_0)
    assert baseline.count <= 8
    assert baseline.mean == pytest.approx(0.5, rel=0.6)


@pytest.mark.parametrize("include_replay", [False, True])
def test_drift_baseline_round_trips(include_replay):
    # Default export: a coarse prior without the raw pending buffer.
    # Replay export (deterministic hosts): exact bounded state.
    baseline = DriftAwareBaseline(decay=0.2, min_samples=5, regime_run=3)
    values = [1.0, 1.05, 0.95, 1.02, 0.98, 1.01, 0.99, 1.0, 1.02, 0.98] * 2
    for v in values:
        baseline.observe(v)

    payload = export_checkpoint(
        drift_baselines={"system_load": baseline}, include_replay=include_replay
    )
    assert ("drift_replay" in payload) is include_replay
    _, _, restored = import_checkpoint(payload)

    restored_baseline = restored["system_load"]
    assert restored_baseline.is_established
    assert restored_baseline.mean == pytest.approx(baseline.mean, abs=0.6)
    assert (restored_baseline.count == baseline.count) is include_replay
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
        import_checkpoint(
            {"schema_version": CHECKPOINT_SCHEMA_VERSION, "acclimation": {"cpu": {"count": 5}}}
        )


def test_import_rejects_unknown_phase():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "rhythms": [
            {
                "percept_name": "x",
                "phase": "midnight-ish",
                "count": 5,
                "mean": 1.0,
                "variance": 0.0,
            }
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


def test_unknown_old_schema_version_with_no_migration_path_is_rejected():
    with pytest.raises(CheckpointError):
        import_checkpoint({"schema_version": 0})


def test_previous_current_schema_is_rejected_without_continuation_condition_migration():
    with pytest.raises(CheckpointError, match="loads only schema 12"):
        import_checkpoint({"schema_version": 11})


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
    oversized = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "blob": "x" * (MAX_HOST_CHECKPOINT_BYTES + 1024),
    }
    with pytest.raises(CheckpointError, match="size limit"):
        save_checkpoint_atomic(oversized, path)
    assert load_checkpoint_file(path)["marker"] == "old"


# --- A07: corrupt numeric data is rejected at the import boundary ---


def test_import_rejects_negative_variance():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "acclimation": {"x": {"count": 10, "mean": 0, "variance": -1}},
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_non_finite_mean():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "acclimation": {"x": {"count": 10, "mean": float("nan"), "variance": 1.0}},
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_infinite_variance():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "acclimation": {"x": {"count": 10, "mean": 0.0, "variance": float("inf")}},
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_negative_count_in_rhythms():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "rhythms": [
            {"percept_name": "x", "phase": "phase.0", "count": -1, "mean": 0.0, "variance": 0.0}
        ],
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_negative_variance_in_drift():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "drift": {"x": {"count": 10, "mean": 0.0, "variance": -5.0}},
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


# --- B04: a non-integer sample count must not silently truncate ---


def test_import_rejects_a_non_integer_count_in_acclimation():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "acclimation": {"x": {"count": 5.5, "mean": 1.0, "variance": 1.0}},
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


def test_import_rejects_a_non_integer_count_in_drift():
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "drift": {"x": {"count": 5.5, "mean": 1.0, "variance": 1.0}},
    }
    with pytest.raises(CheckpointError):
        import_checkpoint(payload)


# --- v0.53+: self-model and resident checkpoint migrations ---


def test_current_schema_version_is_twelve():
    assert CHECKPOINT_SCHEMA_VERSION == 12
