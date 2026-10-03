"""Host telemetry is not the organism: replacing or removing it changes nothing intrinsic."""

from __future__ import annotations

import pytest

from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.host.sources import HostSenseSources
from symbiont.sensory.interoception import InteroceptionProvider

from .fake_telemetry import EXTREME, FakeTelemetry

TICKS = 40


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
    present = _intrinsic(FakeTelemetry(), mode)
    assert len(present["readings"]) == len(InteroceptionProvider.ORGANISM_CAPABILITY_IDS)
    assert _intrinsic(FakeTelemetry(**EXTREME), mode) == present


@pytest.mark.parametrize("mode", ["enabled", "sham"])
def test_removing_host_telemetry_leaves_intrinsic_state_unchanged(mode: str) -> None:
    assert _intrinsic(None, mode) == _intrinsic(FakeTelemetry(), mode)


@pytest.mark.parametrize("mode", ["enabled", "sham"])
def test_removing_host_telemetry_changes_only_the_energy_spent_observing(mode: str) -> None:
    present, absent = _intrinsic(FakeTelemetry(), mode), _intrinsic(None, mode)
    assert absent["integrity"] == present["integrity"]
    assert absent["body"].structural_integrity == present["body"].structural_integrity
    assert absent["body"].energy_reserve == present["body"].energy_reserve


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
