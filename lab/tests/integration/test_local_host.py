"""The organism's host machinery run over this machine's built-in channels."""

from __future__ import annotations

import pytest

from lab.integration.organism.local_host import (
    acclimate_local_host,
    discover_local_host,
    learn_local_host_rhythms,
    monitor_local_host,
    perceive_local_host,
    sample_local_host,
)
from symbiont.host import CyclePhase, ReadingPrivacyClass, reading_matches_manifest


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


def test_learn_local_host_rhythms_seeds_a_real_model():
    model = learn_local_host_rhythms(ticks=5)

    assert model.learned_contexts
    assert model.co_occurring_percepts(CyclePhase.PHASE_0)


def test_learn_local_host_rhythms_rejects_invalid_ticks():
    with pytest.raises(ValueError):
        learn_local_host_rhythms(ticks=0)


def test_perceive_local_host_returns_known_built_in_percepts():
    percepts = perceive_local_host()
    names = {percept.name for percept in percepts}
    assert "system_load" in names
    assert "storage_pressure" in names


def test_builtin_monitor_ticks_without_error():
    lifecycle = monitor_local_host()
    snapshot = lifecycle.tick()
    assert snapshot.tick == 1
    assert len(lifecycle.history) == 1


def test_builtin_discovery_exposes_capabilities_without_identity():
    manifest = discover_local_host()

    assert manifest.schema_version == 1
    assert manifest.supports("runtime.python")
    assert manifest.supports("clock.monotonic")
    assert manifest.supports("storage.disk_usage")
    assert not manifest.failures
    forbidden = {"hostname", "username", "user", "home", "cwd", "ip", "mac"}
    keys = {key.lower() for item in manifest.capabilities for key, _ in item.detail}
    assert not forbidden.intersection(keys)


def test_acclimate_local_host_seeds_a_real_baseline():
    accl, lifecycle = acclimate_local_host(ticks=5)

    assert len(lifecycle.history) == 5
    assert accl.acclimated_capabilities  # at least one built-in capability acclimated


def test_acclimate_local_host_rejects_invalid_ticks():
    with pytest.raises(ValueError):
        acclimate_local_host(ticks=0)
