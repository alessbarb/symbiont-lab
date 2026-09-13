from __future__ import annotations

import pytest

from symbiont.host.contracts import AccessMode, Capability, CapabilityKind, CapabilityScope, HostManifest
from symbiont.host.readings import (
    HostSampler,
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)
from symbiont.host.second_look import SecondLookSession


class _CountingProvider:
    """A test reading provider that returns an incrementing value each
    sample, so a session's readings can be told apart tick-to-tick."""

    provider_id = "counting"

    def __init__(self) -> None:
        self.calls = 0

    def sample(self, capabilities):
        self.calls += 1
        return tuple(
            SensorReading(
                capability_id=capability.capability_id,
                source=capability.source,
                value=float(self.calls),
                unit=Unit.COUNT,
                monotonic_timestamp_ns=self.calls,
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for capability in capabilities
        )


def _manifest(*capability_ids: str) -> HostManifest:
    return HostManifest(
        schema_version=1,
        capabilities=tuple(
            Capability(
                capability_id=capability_id,
                kind=CapabilityKind.COMPUTE,
                source="counting",
                access=AccessMode.READ_ONLY,
                scope=CapabilityScope.LOCAL,
                available=True,
            )
            for capability_id in capability_ids
        ),
        failures=(),
    )


def _session(capability_id: str = "compute.logical_cpu", **kwargs) -> SecondLookSession:
    manifest = _manifest(capability_id)
    sampler = HostSampler(providers=(_CountingProvider(),))
    return SecondLookSession(manifest=manifest, capability_id=capability_id, sampler=sampler, **kwargs)


def test_rejects_capability_not_in_manifest():
    manifest = _manifest("compute.logical_cpu")
    with pytest.raises(ValueError):
        SecondLookSession(manifest=manifest, capability_id="storage.disk_usage")


def test_rejects_non_positive_max_ticks():
    with pytest.raises(ValueError):
        _session(max_ticks=0)


def test_is_active_until_max_ticks_reached():
    session = _session(max_ticks=2)
    assert session.is_active
    session.tick()
    assert session.is_active
    session.tick()
    assert not session.is_active


def test_tick_returns_none_once_inactive():
    session = _session(max_ticks=1)
    first = session.tick()
    assert first is not None
    assert session.tick() is None


def test_cancel_stops_further_ticks():
    session = _session(max_ticks=5)
    session.tick()
    session.cancel()

    assert not session.is_active
    assert session.tick() is None


def test_run_to_completion_collects_all_readings_and_reports_cancelled_flag():
    session = _session(max_ticks=3)
    result = session.run_to_completion()

    assert len(result.readings) == 3
    assert result.cancelled is False
    assert result.capability_id == "compute.logical_cpu"
    assert [reading.value for reading in result.readings] == [1.0, 2.0, 3.0]


def test_run_to_completion_after_cancel_reports_cancelled_and_partial_readings():
    session = _session(max_ticks=5)
    session.tick()
    session.cancel()
    result = session.run_to_completion()

    assert result.cancelled is True
    assert len(result.readings) == 1


def test_only_readings_for_this_session_capability_are_kept():
    manifest = _manifest("compute.logical_cpu", "storage.disk_usage")
    sampler = HostSampler(providers=(_CountingProvider(),))
    session = SecondLookSession(manifest=manifest, capability_id="compute.logical_cpu", sampler=sampler, max_ticks=1)

    result = session.run_to_completion()

    assert len(result.readings) == 1
    assert result.readings[0].capability_id == "compute.logical_cpu"
