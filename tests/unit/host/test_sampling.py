from __future__ import annotations

from dataclasses import dataclass

import pytest

from symbiont.host import (
    AccessMode,
    Capability,
    CapabilityKind,
    CapabilityScope,
    HostManifest,
    HostSampler,
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
    discover_local_host,
    reading_matches_manifest,
    sample_local_host,
)


def _capability(capability_id: str, source: str = "trusted") -> Capability:
    return Capability(
        capability_id=capability_id,
        kind=CapabilityKind.COMPUTE,
        source=source,
        access=AccessMode.READ_ONLY,
        scope=CapabilityScope.LOCAL,
    )


def _manifest(*capabilities: Capability) -> HostManifest:
    return HostManifest(schema_version=1, capabilities=capabilities, failures=())


def _reading(
    capability_id: str = "compute.logical_cpu",
    source: str = "trusted",
    value: float = 0.5,
) -> SensorReading:
    return SensorReading(
        capability_id=capability_id,
        source=source,
        value=value,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=1,
        quality=ReadingQuality.NOMINAL,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )


@dataclass
class FakeReadingProvider:
    provider_id: str
    readings: tuple[SensorReading, ...] = ()
    error: Exception | None = None

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        if self.error is not None:
            raise self.error
        return self.readings


def test_sampler_returns_readings_matching_the_manifest():
    manifest = _manifest(_capability("compute.logical_cpu"))
    sampler = HostSampler((FakeReadingProvider("a", (_reading(),)),))

    readings, failures = sampler.sample(manifest)

    assert readings == (_reading(),)
    assert not failures


def test_sampler_drops_a_reading_the_manifest_never_discovered():
    manifest = _manifest(_capability("compute.logical_cpu"))
    unmatched = _reading(capability_id="memory.utilization")
    sampler = HostSampler((FakeReadingProvider("a", (unmatched,)),))

    readings, failures = sampler.sample(manifest)

    assert not readings
    assert len(failures) == 1
    assert "rejected unmatched reading" in failures[0].reason


def test_broken_reading_provider_does_not_blind_other_providers():
    manifest = _manifest(_capability("compute.logical_cpu"))
    sampler = HostSampler(
        (
            FakeReadingProvider("broken", error=RuntimeError("secret host detail")),
            FakeReadingProvider("healthy", (_reading(source="healthy"),)),
        )
    )

    readings, failures = sampler.sample(_manifest(_capability("compute.logical_cpu", "healthy")))

    assert readings == (_reading(source="healthy"),)
    assert failures[0].provider_id == "broken"
    assert "secret host detail" not in failures[0].reason


def test_duplicate_provider_ids_are_rejected():
    with pytest.raises(ValueError):
        HostSampler((FakeReadingProvider("same"), FakeReadingProvider("same")))


def test_reading_matches_manifest_requires_same_source():
    manifest = _manifest(_capability("compute.logical_cpu", "a"))
    assert not reading_matches_manifest(_reading(source="b"), manifest)


def test_builtin_sampling_only_reports_discovered_capabilities():
    manifest = discover_local_host()
    readings, failures = sample_local_host(manifest)

    assert not failures
    for reading in readings:
        assert manifest.supports(reading.capability_id)
        assert reading_matches_manifest(reading, manifest)


def test_builtin_sampling_reports_no_identifying_data():
    readings, _ = sample_local_host()
    for reading in readings:
        assert reading.privacy_class in (
            ReadingPrivacyClass.AGGREGATE,
            ReadingPrivacyClass.NON_IDENTIFYING,
        )
        # The reading contract carries no free-text field at all beyond
        # typed tokens, so there is no channel for identity to leak through.
        assert isinstance(reading.value, (float, type(None)))
