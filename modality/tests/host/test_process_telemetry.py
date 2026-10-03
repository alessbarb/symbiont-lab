from __future__ import annotations

import modality.host.process_telemetry as telemetry_module
from modality.host.process_telemetry import HostProcessTelemetry
from modality.host.records import ReadingQuality, Unit


def test_reports_the_observed_tick_latency_and_a_memory_footprint():
    telemetry = HostProcessTelemetry()
    telemetry.observe_tick(0.042)
    readings = {item.capability_id: item for item in telemetry.sample(telemetry.discover())}

    assert readings["internal.tick_latency"].value == 0.042
    assert readings["internal.tick_latency"].unit == Unit.SECOND
    assert readings["internal.memory_rss"].unit == Unit.BYTE
    if readings["internal.memory_rss"].value is not None:
        assert readings["internal.memory_rss"].value > 0


def test_a_negative_latency_is_clamped():
    telemetry = HostProcessTelemetry()
    telemetry.observe_tick(-1.0)
    assert telemetry.sample(telemetry.discover())[0].value == 0.0


def test_sampling_without_the_resource_module(monkeypatch):
    monkeypatch.setattr(telemetry_module, "resource", None)
    telemetry = HostProcessTelemetry()
    readings = {item.capability_id: item for item in telemetry.sample(telemetry.discover())}

    assert readings["internal.memory_rss"].value is None
    assert readings["internal.memory_rss"].quality == ReadingQuality.UNAVAILABLE
