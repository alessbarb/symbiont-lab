from __future__ import annotations

from dataclasses import dataclass

import pytest

from symbiont.host import (
    AccessMode,
    Capability,
    CapabilityKind,
    CapabilityScope,
    HostDiscovery,
    discover_local_host,
)


@dataclass
class FakeProvider:
    provider_id: str
    capabilities: tuple[Capability, ...] = ()
    error: Exception | None = None

    def discover(self) -> tuple[Capability, ...]:
        if self.error is not None:
            raise self.error
        return self.capabilities


def capability(
    capability_id: str,
    *,
    access: AccessMode = AccessMode.READ_ONLY,
    scope: CapabilityScope = CapabilityScope.LOCAL,
) -> Capability:
    return Capability(
        capability_id=capability_id,
        kind=CapabilityKind.COMPUTE,
        source="untrusted-source",
        access=access,
        scope=scope,
    )


def test_discovery_is_provider_and_order_agnostic():
    manifest = HostDiscovery(
        (
            FakeProvider("z-provider", (capability("compute.z"),)),
            FakeProvider("a-provider", (capability("compute.a"),)),
        )
    ).discover()

    assert [item.capability_id for item in manifest.capabilities] == [
        "compute.a",
        "compute.z",
    ]
    assert [item.source for item in manifest.capabilities] == [
        "a-provider",
        "z-provider",
    ]


@pytest.mark.parametrize(
    ("access", "scope"),
    [
        (AccessMode.WRITE, CapabilityScope.LOCAL),
        (AccessMode.EXECUTE, CapabilityScope.LOCAL),
        (AccessMode.READ_ONLY, CapabilityScope.REMOTE),
    ],
)
def test_default_policy_rejects_active_or_remote_discovery(access, scope):
    manifest = HostDiscovery(
        (FakeProvider("unsafe", (capability("unsafe", access=access, scope=scope),)),)
    ).discover()

    assert not manifest.capabilities
    assert len(manifest.failures) == 1
    assert "rejected unsafe capability" in manifest.failures[0].reason


def test_broken_provider_does_not_blind_other_senses():
    manifest = HostDiscovery(
        (
            FakeProvider("broken", error=RuntimeError("secret host detail")),
            FakeProvider("healthy", (capability("compute.logical"),)),
        )
    ).discover()

    assert manifest.supports("compute.logical")
    assert manifest.failures[0].provider_id == "broken"
    assert "secret host detail" not in manifest.failures[0].reason


def test_duplicate_capability_is_deterministic_and_visible():
    manifest = HostDiscovery(
        (
            FakeProvider("first", (capability("compute.logical"),)),
            FakeProvider("second", (capability("compute.logical"),)),
        )
    ).discover()

    assert len(manifest.capabilities) == 1
    assert manifest.capabilities[0].source == "first"
    assert "duplicate capability" in manifest.failures[0].reason


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


def test_capability_rejects_identity_metadata():
    with pytest.raises(ValueError):
        Capability(
            capability_id="runtime.identity",
            kind=CapabilityKind.RUNTIME,
            source="test",
            detail=(("hostname", "secret-host"),),
        )


def test_duplicate_provider_ids_are_rejected():
    with pytest.raises(ValueError):
        HostDiscovery((FakeProvider("same"), FakeProvider("same")))
