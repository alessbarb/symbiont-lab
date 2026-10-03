"""Portable host surfaces: the organism senses macOS and Windows hosts too (ADR-0062, rule 8)."""

from __future__ import annotations

import math
import platform

import pytest

from modality.host.portable_surfaces import PortableSurfaceProvider


def test_surfaces_are_opaque_aggregate_and_readable() -> None:
    provider = PortableSurfaceProvider()
    capabilities = provider.discover()
    assert capabilities
    for capability in capabilities:
        assert capability.capability_id.startswith("signal.")
        for word in ("loadavg", "disk", "memory", "sysctl", "cpu", "power"):
            assert word not in capability.capability_id
    readings = provider.sample(capabilities)
    assert len(readings) == len(capabilities)
    assert all(reading.value is not None and math.isfinite(reading.value) for reading in readings)


def test_unsupported_system_calls_are_absent_not_errors() -> None:
    # Windows surfaces on a host without the Windows API: only the stdlib ones.
    other = "Darwin" if platform.system() == "Windows" else "Windows"
    provider = PortableSurfaceProvider(system=other)
    stdlib_only = PortableSurfaceProvider(system="Other").discover()
    assert len(provider.discover()) == len(stdlib_only)


@pytest.mark.skipif(platform.system() not in {"Darwin", "Windows"}, reason="native host only")
def test_native_host_offers_system_surfaces_beyond_the_stdlib_ones() -> None:
    native = PortableSurfaceProvider().discover()
    stdlib_only = PortableSurfaceProvider(system="Other").discover()
    assert len(native) > len(stdlib_only)
