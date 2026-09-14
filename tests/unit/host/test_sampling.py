from __future__ import annotations

from dataclasses import dataclass, field

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
from symbiont.host.readings import SamplingOutcomeKind


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


@dataclass
class RecordingProvider:
    provider_id: str = "trusted"
    seen: list[tuple[str, ...]] = field(default_factory=list)

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        ids = tuple(capability.capability_id for capability in capabilities)
        self.seen.append(ids)
        return tuple(_reading(capability_id=capability_id) for capability_id in ids)


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
        assert isinstance(reading.value, (float, type(None)))


def test_capability_selection_is_applied_before_provider_reads() -> None:
    provider = RecordingProvider()
    manifest = _manifest(
        _capability("sense-a"),
        _capability("sense-b"),
        _capability("sense-c"),
    )

    readings, failures = HostSampler((provider,)).sample(
        manifest,
        capability_ids=("sense-b",),
    )

    assert not failures
    assert provider.seen == [("sense-b",)]
    assert [reading.capability_id for reading in readings] == ["sense-b"]


def test_outcomes_attribute_elapsed_time_evenly_across_attempted_capabilities():
    manifest = _manifest(_capability("sense-a"), _capability("sense-b"))
    clock_values = iter([0.0, 0.010])
    provider = RecordingProvider()
    sampler = HostSampler((provider,))

    _, _, outcomes = sampler.sample_with_outcomes(manifest, clock=lambda: next(clock_values))

    by_id = {o.capability_id: o for o in outcomes}
    assert by_id["sense-a"].attributed_elapsed_s == pytest.approx(0.005)
    assert by_id["sense-b"].attributed_elapsed_s == pytest.approx(0.005)
    assert by_id["sense-a"].kind == SamplingOutcomeKind.SUCCEEDED


def test_missing_capability_gets_missing_outcome_not_zero_cost():
    manifest = _manifest(_capability("sense-a"), _capability("sense-b"))
    clock_values = iter([0.0, 0.010])
    provider = FakeReadingProvider("p", (_reading(capability_id="sense-a"),))
    sampler = HostSampler((provider,))

    _, _, outcomes = sampler.sample_with_outcomes(manifest, clock=lambda: next(clock_values))

    by_id = {o.capability_id: o for o in outcomes}
    assert by_id["sense-b"].kind == SamplingOutcomeKind.MISSING
    assert by_id["sense-b"].attributed_elapsed_s == pytest.approx(0.005)


def test_provider_exception_attributes_provider_failed_to_every_attempted_capability():
    manifest = _manifest(_capability("sense-a"), _capability("sense-b"))
    clock_values = iter([0.0, 0.020])
    provider = FakeReadingProvider("broken", error=RuntimeError("boom"))
    sampler = HostSampler((provider,))

    _, failures, outcomes = sampler.sample_with_outcomes(manifest, clock=lambda: next(clock_values))

    assert len(failures) == 1
    kinds = {o.capability_id: o.kind for o in outcomes}
    assert kinds == {
        "sense-a": SamplingOutcomeKind.PROVIDER_FAILED,
        "sense-b": SamplingOutcomeKind.PROVIDER_FAILED,
    }


def test_unavailable_quality_reading_produces_unavailable_outcome():
    manifest = _manifest(_capability("sense-a", "p"))
    unavailable = SensorReading(
        capability_id="sense-a",
        source="p",
        value=None,
        unit=Unit.RATIO,
        monotonic_timestamp_ns=1,
        quality=ReadingQuality.UNAVAILABLE,
        privacy_class=ReadingPrivacyClass.AGGREGATE,
    )
    provider = FakeReadingProvider("p", (unavailable,))
    sampler = HostSampler((provider,))
    clock_values = iter([0.0, 0.004])

    _, _, outcomes = sampler.sample_with_outcomes(manifest, clock=lambda: next(clock_values))

    assert outcomes[0].kind == SamplingOutcomeKind.UNAVAILABLE
    assert outcomes[0].quality == ReadingQuality.UNAVAILABLE


def test_sample_public_two_tuple_contract_is_unchanged():
    manifest = _manifest(_capability("sense-a"))
    provider = FakeReadingProvider("p", (_reading(capability_id="sense-a"),))
    result = HostSampler((provider,)).sample(manifest)

    assert len(result) == 2
    readings, failures = result
    assert readings == (_reading(capability_id="sense-a"),)


def test_provider_cannot_smuggle_an_unrequested_reading_back_into_runtime() -> None:
    provider = FakeReadingProvider(
        "provider",
        readings=(
            _reading("allowed", source="trusted"),
            _reading("not-requested", source="trusted"),
        ),
    )
    manifest = _manifest(_capability("allowed"), _capability("not-requested"))

    readings, failures = HostSampler((provider,)).sample(
        manifest,
        capability_ids=("allowed",),
    )

    assert [reading.capability_id for reading in readings] == ["allowed"]
    assert any("rejected unrequested reading" in failure.reason for failure in failures)
