from __future__ import annotations

from symbiont.host.providers.interoception import InteroceptionProvider
from symbiont.host.readings import ReadingQuality, Unit


def test_interoception_provider_discovery():
    provider = InteroceptionProvider()
    caps = provider.discover()
    cap_ids = {c.capability_id for c in caps}

    assert "internal.tick_latency" in cap_ids
    assert "internal.memory_rss" in cap_ids
    assert "internal.epistemic_surprise" in cap_ids
    assert "internal.metabolic_reserve" in cap_ids


def test_interoception_provider_sampling_and_update():
    provider = InteroceptionProvider()
    caps = provider.discover()

    provider.update_metrics(
        tick_latency=0.042,
        epistemic_surprise=0.15,
        metabolic_reserve=0.85,
    )

    readings = {r.capability_id: r for r in provider.sample(caps)}

    assert readings["internal.tick_latency"].value == 0.042
    assert readings["internal.tick_latency"].unit == Unit.SECOND
    assert readings["internal.tick_latency"].quality == ReadingQuality.NOMINAL

    assert readings["internal.epistemic_surprise"].value == 0.15
    assert readings["internal.epistemic_surprise"].unit == Unit.RATIO

    assert readings["internal.metabolic_reserve"].value == 0.85
    assert readings["internal.metabolic_reserve"].unit == Unit.RATIO

    # Memory RSS should be positive numeric on Linux/POSIX
    mem_reading = readings["internal.memory_rss"]
    assert mem_reading.unit == Unit.BYTE
    if mem_reading.value is not None:
        assert mem_reading.value > 0
