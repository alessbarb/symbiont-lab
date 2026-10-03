from __future__ import annotations

from symbiont.host.readings import ReadingQuality, Unit
from symbiont.sensory.interoception import InteroceptionProvider, ShamInteroceptionProvider

from .fake_telemetry import FakeTelemetry


def _provider(provider_type=InteroceptionProvider):
    """Interoception with the host telemetry published alongside it."""
    return provider_type(host_telemetry=FakeTelemetry())


def test_interoception_provider_discovery():
    provider = _provider()
    caps = provider.discover()
    cap_ids = {c.capability_id for c in caps}

    assert "internal.tick_latency" in cap_ids
    assert "internal.memory_rss" in cap_ids
    assert "internal.epistemic_surprise" in cap_ids
    assert "internal.metabolic_reserve" in cap_ids
    assert "internal.integrity" in cap_ids
    assert "internal.metabolic_pressure" in cap_ids
    assert "internal.repair_pressure" in cap_ids
    assert "internal.waste_pressure" in cap_ids
    assert InteroceptionProvider.organism_facing("internal.integrity")
    assert not InteroceptionProvider.organism_facing("internal.memory_rss")
    assert not InteroceptionProvider.organism_facing("internal.tick_latency")


def test_interoception_provider_sampling_and_update():
    provider = _provider()
    caps = provider.discover()

    provider.update_metrics(
        tick_latency=0.042,
        epistemic_surprise=0.15,
        metabolic_reserve=0.85,
        integrity=0.8,
        metabolic_pressure=0.33,
        repair_pressure=0.2,
        waste_pressure=0.1,
    )

    readings = {r.capability_id: r for r in provider.sample(caps)}

    assert readings["internal.tick_latency"].value == 0.042
    assert readings["internal.tick_latency"].unit == Unit.SECOND
    assert readings["internal.tick_latency"].quality == ReadingQuality.NOMINAL

    assert readings["internal.epistemic_surprise"].value == 0.15
    assert readings["internal.epistemic_surprise"].unit == Unit.RATIO

    assert readings["internal.metabolic_reserve"].value == 0.85
    assert readings["internal.metabolic_reserve"].unit == Unit.RATIO
    assert readings["internal.integrity"].value == 0.8
    assert readings["internal.metabolic_pressure"].value == 0.33
    assert readings["internal.repair_pressure"].value == 0.2
    assert readings["internal.waste_pressure"].value == 0.1

    # Memory RSS should be positive numeric on Linux/POSIX
    mem_reading = readings["internal.memory_rss"]
    assert mem_reading.unit == Unit.BYTE
    if mem_reading.value is not None:
        assert mem_reading.value > 0


def test_interoception_organism_projection_is_bounded_and_uses_ratio_units():
    provider = _provider()
    provider.update_metrics(
        tick_latency=4.0,
        epistemic_surprise=1.5,
        metabolic_reserve=-1.0,
    )

    projected = {
        reading.capability_id: provider.normalize_for_organism(reading)
        for reading in provider.sample(provider.discover())
    }

    for capability_id, reading in projected.items():
        if InteroceptionProvider.organism_facing(capability_id):
            assert reading.unit == Unit.RATIO
            assert reading.value is not None
            assert 0.0 <= reading.value <= 1.0

    assert projected["internal.tick_latency"].unit == Unit.SECOND
    assert projected["internal.memory_rss"].unit == Unit.BYTE
    assert projected["internal.epistemic_surprise"].value == 1.0
    assert projected["internal.metabolic_reserve"].value == 0.0


def test_sham_interoception_preserves_manifest_but_projects_neutral_values():
    provider = _provider(ShamInteroceptionProvider)
    provider.update_metrics(
        tick_latency=0.2,
        epistemic_surprise=0.9,
        metabolic_reserve=0.1,
        integrity=0.2,
        metabolic_pressure=0.8,
        repair_pressure=0.7,
        waste_pressure=0.6,
    )
    capabilities = provider.discover()
    readings = provider.sample(capabilities)
    projected = tuple(provider.normalize_for_organism(reading) for reading in readings)
    assert len(projected) == len(readings) == len(capabilities)
    assert {reading.capability_id for reading in projected} == {
        capability.capability_id for capability in capabilities
    }
    organism_projected = [
        reading
        for reading in projected
        if InteroceptionProvider.organism_facing(reading.capability_id)
    ]
    apparatus_only = [
        reading
        for reading in projected
        if not InteroceptionProvider.organism_facing(reading.capability_id)
    ]
    assert organism_projected
    assert all(reading.value == 0.5 for reading in organism_projected)
    assert {reading.capability_id for reading in apparatus_only} == {
        "internal.tick_latency",
        "internal.memory_rss",
    }
    assert provider.local_action_pressure() == 0.5


def test_interoception_action_pressure_includes_integrity_and_repair_channels():
    provider = _provider()
    provider.update_metrics(
        tick_latency=0.0,
        epistemic_surprise=0.0,
        metabolic_reserve=1.0,
        integrity=0.0,
        metabolic_pressure=1.0,
        repair_pressure=1.0,
        waste_pressure=1.0,
    )
    assert provider.local_action_pressure() == 0.55


def test_interoception_physiological_refresh_does_not_reset_computational_channels():
    provider = _provider()
    provider.update_metrics(
        tick_latency=0.25,
        epistemic_surprise=0.75,
        metabolic_reserve=0.9,
        integrity=1.0,
        metabolic_pressure=0.0,
        repair_pressure=0.0,
        waste_pressure=0.0,
    )
    provider.update_physiological_state(
        metabolic_reserve=0.2,
        integrity=0.4,
        metabolic_pressure=0.66,
        repair_pressure=0.6,
        waste_pressure=0.3,
    )
    readings = {item.capability_id: item for item in provider.sample(provider.discover())}
    assert readings["internal.tick_latency"].value == 0.25
    assert readings["internal.epistemic_surprise"].value == 0.75
    assert readings["internal.metabolic_reserve"].value == 0.2
    assert readings["internal.integrity"].value == 0.4


def test_an_unavailable_host_measurement_is_published_without_a_value():
    provider = InteroceptionProvider(host_telemetry=FakeTelemetry(memory_rss=None))
    readings = {item.capability_id: item for item in provider.sample(provider.discover())}

    assert readings["internal.memory_rss"].unit == Unit.BYTE
    assert readings["internal.memory_rss"].value is None


def test_without_host_telemetry_only_the_organism_channels_exist():
    provider = InteroceptionProvider()
    provider.update_metrics(tick_latency=9.0, epistemic_surprise=0.4, metabolic_reserve=0.6)
    capabilities = provider.discover()
    assert {capability.capability_id for capability in capabilities} == set(
        InteroceptionProvider.ORGANISM_CAPABILITY_IDS
    )
    readings = {item.capability_id: item.value for item in provider.sample(capabilities)}
    assert set(readings) == set(InteroceptionProvider.ORGANISM_CAPABILITY_IDS)
    assert readings["internal.epistemic_surprise"] == 0.4


def test_host_telemetry_is_published_under_the_persisted_interoception_source():
    provider = _provider()
    capabilities = provider.discover()
    assert {capability.source for capability in capabilities} == {"interoception"}
    assert {reading.source for reading in provider.sample(capabilities)} == {"interoception"}
