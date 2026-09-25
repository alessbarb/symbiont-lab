from __future__ import annotations

import pytest

from symbiont.host import (
    HostAcclimation,
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
    acclimate_local_host,
)


def _reading(
    capability_id: str, value: float | None, quality: ReadingQuality = ReadingQuality.NOMINAL
) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source="stdlib",
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=1,
        quality=quality,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_not_acclimated_before_min_samples():
    accl = HostAcclimation(min_samples=3)
    accl.observe([_reading("compute.logical_cpu", 0.5), _reading("compute.logical_cpu", 0.6)])

    assert not accl.is_acclimated("compute.logical_cpu")
    assert accl.baseline("compute.logical_cpu") is None
    assert accl.acclimated_capabilities == ()


def test_acclimated_once_min_samples_reached():
    accl = HostAcclimation(min_samples=3)
    for value in (0.4, 0.5, 0.6):
        accl.observe([_reading("compute.logical_cpu", value)])

    assert accl.is_acclimated("compute.logical_cpu")
    baseline = accl.baseline("compute.logical_cpu")
    assert baseline is not None
    assert baseline.count == 3
    assert baseline.mean == pytest.approx(0.5)
    assert baseline.stdev > 0.0
    assert accl.acclimated_capabilities == ("compute.logical_cpu",)


def test_unavailable_readings_are_not_observed():
    accl = HostAcclimation(min_samples=1)
    accl.observe([_reading("compute.logical_cpu", None, quality=ReadingQuality.UNAVAILABLE)])

    assert not accl.is_acclimated("compute.logical_cpu")


def test_capability_count_is_bounded():
    accl = HostAcclimation(max_capabilities=2, min_samples=1)
    accl.observe(
        [
            _reading("a", 1.0),
            _reading("b", 1.0),
            _reading("c", 1.0),  # dropped: capability slots already full
        ]
    )

    assert set(accl.acclimated_capabilities) == {"a", "b"}
    assert accl.baseline("c") is None


def test_constant_readings_have_zero_variance():
    accl = HostAcclimation(min_samples=2)
    accl.observe([_reading("compute.logical_cpu", 0.5), _reading("compute.logical_cpu", 0.5)])

    baseline = accl.baseline("compute.logical_cpu")
    assert baseline.variance == 0.0
    assert baseline.stdev == 0.0


@pytest.mark.parametrize("kwargs", [{"max_capabilities": 0}, {"min_samples": 0}])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        HostAcclimation(**kwargs)


def test_baseline_exposes_no_classification_surface():
    """Acclimation must withhold threat conclusions by construction (roadmap v0.33):
    the public surface can only produce descriptive stats, never a verdict."""
    accl = HostAcclimation(min_samples=1)
    accl.observe([_reading("compute.logical_cpu", 0.5)])
    baseline = accl.baseline("compute.logical_cpu")

    public_attrs = {name for name in dir(baseline) if not name.startswith("_")}
    assert public_attrs <= {"count", "mean", "variance", "stdev"}


def test_acclimate_local_host_seeds_a_real_baseline():
    accl, lifecycle = acclimate_local_host(ticks=5)

    assert len(lifecycle.history) == 5
    assert accl.acclimated_capabilities  # at least one built-in capability acclimated


def test_acclimate_local_host_rejects_invalid_ticks():
    with pytest.raises(ValueError):
        acclimate_local_host(ticks=0)


# --- B02: a full capability table evicts the stalest entry instead of blocking forever ---


def test_a_new_capability_is_learned_after_old_ones_fill_capacity():
    accl = HostAcclimation(max_capabilities=4, min_samples=1)
    for capability_id in ("a", "b", "c", "d"):
        accl.observe([_reading(capability_id, 1.0)])

    for _ in range(3):
        accl.observe([_reading("new", 1.0)])

    assert "new" in accl.known_capabilities
    assert len(accl.known_capabilities) <= 4


def test_eviction_never_removes_something_observed_this_call():
    accl = HostAcclimation(max_capabilities=2, min_samples=1)
    accl.observe([_reading("a", 1.0), _reading("b", 1.0)])
    accl.observe([_reading("c", 1.0), _reading("d", 1.0)])

    assert set(accl.known_capabilities) == {"c", "d"}
