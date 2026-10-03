"""Host telemetry is not the organism: replacing or removing it changes nothing intrinsic."""

from __future__ import annotations

import time

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.contracts import Capability, CapabilityKind
from symbiont.host.providers.process_telemetry import HostProcessTelemetry
from symbiont.host.readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit
from symbiont.host.sources import HostSenseSources
from symbiont.sensory.interoception import InteroceptionProvider

TICKS = 40
HOST_IDS = {"internal.tick_latency": Unit.SECOND, "internal.memory_rss": Unit.BYTE}


class ExtremeTelemetry:
    """A host that reports an absurd machine: hour-long ticks, a petabyte of memory."""

    provider_id = "extreme"

    def observe_tick(self, latency: float) -> None:
        pass

    def discover(self) -> tuple[Capability, ...]:
        return tuple(
            Capability(capability_id=capability_id, kind=CapabilityKind.SIGNAL, source="extreme")
            for capability_id in HOST_IDS
        )

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        return tuple(
            SensorReading(
                capability_id=capability.capability_id,
                source="extreme",
                value=3600.0 if capability.capability_id == "internal.tick_latency" else 1e15,
                unit=HOST_IDS[capability.capability_id],
                monotonic_timestamp_ns=time.monotonic_ns(),
                quality=ReadingQuality.NOMINAL,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
            for capability in capabilities
            if capability.capability_id in HOST_IDS
        )


def _intrinsic(telemetry: object | None, mode: str) -> dict[str, object]:
    runtime = OrganismRuntime(
        organism_id="intrinsic-probe",
        bootstrap_semantic_senses=False,
        discover_senses=True,
        interoception_mode=mode,
        host_sense_sources=HostSenseSources(process_telemetry=telemetry, availability="available"),
    )
    for _ in range(TICKS):
        runtime.tick()
    provider = runtime._interoception_provider
    organism_capabilities = tuple(
        capability
        for capability in provider.discover()
        if InteroceptionProvider.organism_facing(capability.capability_id)
    )
    return {
        "body": runtime.living_body_state,
        "metabolism": runtime._metabolism.snapshot(),
        "integrity": runtime._homeostasis.integrity,
        "readings": {
            reading.capability_id: reading.value
            for reading in provider.sample(organism_capabilities)
        },
        "action_pressure": provider.local_action_pressure(),
    }


@pytest.mark.parametrize("mode", ["enabled", "sham"])
def test_replacing_host_telemetry_leaves_intrinsic_state_unchanged(mode: str) -> None:
    present = _intrinsic(HostProcessTelemetry(), mode)
    assert len(present["readings"]) == len(InteroceptionProvider.ORGANISM_CAPABILITY_IDS)
    assert _intrinsic(ExtremeTelemetry(), mode) == present


@pytest.mark.xfail(
    strict=True,
    reason=(
        "EXPOSED-BY-MIGRATION: the organism pays observation cost for each sampled "
        "channel, including the two host telemetry channels it never perceives, so "
        "removing them leaves more energy reserve. Owner decision, "
        "migration/open-issues.md."
    ),
)
@pytest.mark.parametrize("mode", ["enabled", "sham"])
def test_removing_host_telemetry_leaves_intrinsic_state_unchanged(mode: str) -> None:
    assert _intrinsic(None, mode) == _intrinsic(HostProcessTelemetry(), mode)


@pytest.mark.parametrize("mode", ["enabled", "sham"])
def test_removing_host_telemetry_changes_only_the_energy_spent_observing(mode: str) -> None:
    present, absent = _intrinsic(HostProcessTelemetry(), mode), _intrinsic(None, mode)
    assert absent["integrity"] == present["integrity"]
    assert absent["body"].structural_integrity == present["body"].structural_integrity
    assert absent["body"].energy_reserve > present["body"].energy_reserve


def test_without_host_telemetry_the_organism_publishes_only_its_own_channels() -> None:
    runtime = OrganismRuntime(
        bootstrap_semantic_senses=False,
        discover_senses=True,
        interoception_mode="enabled",
        host_sense_sources=HostSenseSources(availability="available"),
    )
    assert {
        capability.capability_id
        for capability in runtime._lifecycle._discovery.discover().capabilities
    } == set(InteroceptionProvider.ORGANISM_CAPABILITY_IDS)
