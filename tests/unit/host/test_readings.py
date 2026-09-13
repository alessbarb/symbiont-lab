from __future__ import annotations

import pytest

from symbiont.host import (
    AccessMode,
    Capability,
    CapabilityKind,
    CapabilityScope,
    HostManifest,
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
    reading_matches_manifest,
)


def _reading(
    *,
    capability_id: str = "compute.logical_cpu",
    source: str = "stdlib",
    value: float | None = 0.42,
    quality: ReadingQuality = ReadingQuality.NOMINAL,
) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source=source,
        value=value,
        unit=Unit.PERCENT,
        monotonic_timestamp_ns=123_456,
        quality=quality,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


def test_reading_round_trips_through_as_dict():
    reading = _reading()
    payload = reading.as_dict()

    assert payload["capability_id"] == "compute.logical_cpu"
    assert payload["unit"] == "percent"
    assert payload["quality"] == "nominal"
    assert payload["privacy_class"] == "aggregate"
    assert payload["value"] == 0.42


@pytest.mark.parametrize(
    "kwargs",
    [
        {"capability_id": ""},
        {"capability_id": "has space"},
        {"source": ""},
        {"monotonic_timestamp_ns": -1},
    ],
)
def test_reading_rejects_malformed_identity_fields(kwargs):
    base = dict(
        capability_id="compute.logical_cpu",
        source="stdlib",
        value=1.0,
        unit=Unit.PERCENT,
        monotonic_timestamp_ns=1,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        SensorReading(**base)


def test_unavailable_reading_must_not_carry_a_value():
    with pytest.raises(ValueError):
        _reading(value=1.0, quality=ReadingQuality.UNAVAILABLE)


def test_available_reading_must_carry_a_value():
    with pytest.raises(ValueError):
        _reading(value=None, quality=ReadingQuality.NOMINAL)


def test_unavailable_reading_with_no_value_is_valid():
    reading = _reading(value=None, quality=ReadingQuality.UNAVAILABLE)
    assert reading.value is None
    assert reading.quality is ReadingQuality.UNAVAILABLE


def _manifest_with(capability_id: str, source: str) -> HostManifest:
    return HostManifest(
        schema_version=1,
        capabilities=(
            Capability(
                capability_id=capability_id,
                kind=CapabilityKind.COMPUTE,
                source=source,
                access=AccessMode.READ_ONLY,
                scope=CapabilityScope.LOCAL,
            ),
        ),
        failures=(),
    )


def test_reading_matches_a_manifest_that_discovered_its_capability():
    manifest = _manifest_with("compute.logical_cpu", "stdlib")
    reading = _reading(capability_id="compute.logical_cpu", source="stdlib")

    assert reading_matches_manifest(reading, manifest)


def test_reading_does_not_match_an_undiscovered_capability():
    manifest = _manifest_with("compute.logical_cpu", "stdlib")
    reading = _reading(capability_id="memory.utilization", source="stdlib")

    assert not reading_matches_manifest(reading, manifest)


def test_reading_does_not_match_a_different_source_for_the_same_capability():
    manifest = _manifest_with("compute.logical_cpu", "stdlib")
    reading = _reading(capability_id="compute.logical_cpu", source="untrusted-source")

    assert not reading_matches_manifest(reading, manifest)
