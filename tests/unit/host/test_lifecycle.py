from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from symbiont.host import (
    AccessMode,
    Capability,
    CapabilityKind,
    CapabilityScope,
    DiscoveryPolicy,
    HostDiscovery,
    HostLifecycle,
    SensorReading,
    ReadingPrivacyClass,
    ReadingQuality,
    Unit,
    monitor_local_host,
)


def _capability(capability_id: str, *, available: bool = True) -> Capability:
    return Capability(
        capability_id=capability_id,
        kind=CapabilityKind.COMPUTE,
        source="fake",
        access=AccessMode.READ_ONLY,
        scope=CapabilityScope.LOCAL,
        available=available,
    )


@dataclass
class FakeDiscoveryProvider:
    provider_id: str
    capabilities: tuple[Capability, ...] = ()

    def discover(self) -> tuple[Capability, ...]:
        return self.capabilities


@dataclass
class FlakyReadingProvider:
    provider_id: str
    fail: bool = False
    calls: int = field(default=0)

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        selected = next((cap for cap in capabilities if cap.capability_id == "compute.fake"), None)
        if selected is None:
            return ()
        return (
            SensorReading(
                capability_id="compute.fake",
                source=self.provider_id,
                value=1.0,
                unit=Unit.RATIO,
                monotonic_timestamp_ns=self.calls,
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            ),
        )


def _lifecycle(reading_provider: FlakyReadingProvider, **kwargs) -> HostLifecycle:
    discovery = HostDiscovery(
        (FakeDiscoveryProvider(reading_provider.provider_id, (_capability("compute.fake"),)),),
        DiscoveryPolicy(),
    )
    return HostLifecycle(discovery=discovery, reading_providers=(reading_provider,), **kwargs)


def test_history_is_bounded():
    provider = FlakyReadingProvider("p")
    lifecycle = _lifecycle(provider, history_limit=2)
    for _ in range(5):
        lifecycle.tick()
    assert len(lifecycle.history) == 2
    assert lifecycle.history[-1].tick == 5


def test_failing_provider_is_backed_off_then_retried():
    provider = FlakyReadingProvider("p", fail=True)
    lifecycle = _lifecycle(provider, base_backoff_ticks=1, max_backoff_ticks=4)
    snap1 = lifecycle.tick()
    assert snap1.backed_off_providers == ()
    assert provider.calls == 1
    snap2 = lifecycle.tick()
    assert snap2.backed_off_providers == ("p",)
    assert provider.calls == 1
    snap3 = lifecycle.tick()
    assert snap3.backed_off_providers == ()
    assert provider.calls == 2
    snap4 = lifecycle.tick()
    snap5 = lifecycle.tick()
    assert snap4.backed_off_providers == ("p",)
    assert snap5.backed_off_providers == ("p",)
    assert provider.calls == 2


def test_provider_recovering_resets_backoff():
    provider = FlakyReadingProvider("p", fail=True)
    lifecycle = _lifecycle(provider, base_backoff_ticks=1, max_backoff_ticks=4)
    lifecycle.tick()
    lifecycle.tick()
    provider.fail = False
    lifecycle.tick()
    snap = lifecycle.tick()
    assert snap.backed_off_providers == ()
    assert len(snap.readings) == 1


def test_capability_changes_detected_across_ticks():
    provider = FlakyReadingProvider("p")
    discovery_provider = FakeDiscoveryProvider("disc", (_capability("compute.fake"),))
    discovery = HostDiscovery((discovery_provider,), DiscoveryPolicy())
    lifecycle = HostLifecycle(discovery=discovery, reading_providers=(provider,))
    lifecycle.tick()
    assert lifecycle.capability_changes() == ()
    discovery_provider.capabilities = ()
    lifecycle.tick()
    assert lifecycle.capability_changes() == ("compute.fake",)


def test_no_changes_reported_before_two_ticks():
    provider = FlakyReadingProvider("p")
    lifecycle = _lifecycle(provider)
    assert lifecycle.capability_changes() == ()
    lifecycle.tick()
    assert lifecycle.capability_changes() == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"history_limit": 0},
        {"base_backoff_ticks": 0},
        {"base_backoff_ticks": 5, "max_backoff_ticks": 1},
    ],
)
def test_invalid_configuration_is_rejected(kwargs):
    discovery = HostDiscovery((FakeDiscoveryProvider("disc", ()),), DiscoveryPolicy())
    with pytest.raises(ValueError):
        HostLifecycle(discovery=discovery, reading_providers=(), **kwargs)


def test_duplicate_reading_provider_ids_are_rejected():
    discovery = HostDiscovery((FakeDiscoveryProvider("disc", ()),), DiscoveryPolicy())
    with pytest.raises(ValueError):
        HostLifecycle(
            discovery=discovery,
            reading_providers=(FlakyReadingProvider("same"), FlakyReadingProvider("same")),
        )


def test_builtin_monitor_ticks_without_error():
    lifecycle = monitor_local_host()
    snapshot = lifecycle.tick()
    assert snapshot.tick == 1
    assert len(lifecycle.history) == 1


def test_sampling_selector_can_leave_discovery_intact_while_skipping_reads() -> None:
    provider = FlakyReadingProvider("p")
    lifecycle = _lifecycle(provider)

    snapshot = lifecycle.tick(sampling_selector=lambda manifest: ())

    assert snapshot.manifest.supports("compute.fake")
    assert snapshot.readings == ()
    assert snapshot.sampled_capability_ids == ()
    assert provider.calls == 0


def test_sampling_selector_records_only_the_exercised_capabilities() -> None:
    provider = FlakyReadingProvider("p")
    lifecycle = _lifecycle(provider)

    snapshot = lifecycle.tick(
        sampling_selector=lambda manifest: ("compute.fake", "not-discovered"),
    )

    assert provider.calls == 1
    assert snapshot.sampled_capability_ids == ("compute.fake",)
