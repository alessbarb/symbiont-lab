from __future__ import annotations

from symbiont.host.providers.interoception import (
    InteroceptionProvider,
    ShamInteroceptionProvider,
)
from symbiont.host.readings import ReadingQuality, Unit


def test_interoception_provider_discovery():
    provider = InteroceptionProvider()
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


def test_interoception_provider_sampling_and_update():
    provider = InteroceptionProvider()
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
    provider = InteroceptionProvider()
    provider.update_metrics(
        tick_latency=4.0,
        epistemic_surprise=1.5,
        metabolic_reserve=-1.0,
    )

    projected = {
        reading.capability_id: provider.normalize_for_organism(reading)
        for reading in provider.sample(provider.discover())
    }

    for reading in projected.values():
        assert reading.unit == Unit.RATIO
        assert reading.value is not None
        assert 0.0 <= reading.value <= 1.0

    assert projected["internal.tick_latency"].value == 1.0
    assert projected["internal.epistemic_surprise"].value == 1.0
    assert projected["internal.metabolic_reserve"].value == 0.0


def test_sham_interoception_preserves_manifest_but_projects_neutral_values():
    provider = ShamInteroceptionProvider()
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
    assert all(reading.value == 0.5 for reading in projected)
    assert provider.local_action_pressure() == 0.5
