from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .contracts import (
    Capability,
    DiscoveryFailure,
    DiscoveryPolicy,
    DiscoveryProvider,
    HostManifest,
)


class HostDiscovery:
    """Discover host capabilities without teaching Symbiont about an OS."""

    def __init__(
        self,
        providers: Iterable[DiscoveryProvider],
        policy: DiscoveryPolicy | None = None,
    ) -> None:
        self._providers = tuple(providers)
        self._policy = policy or DiscoveryPolicy()
        provider_ids = [provider.provider_id for provider in self._providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider_id values must be unique")

    def discover(self) -> HostManifest:
        accepted: dict[str, Capability] = {}
        failures: list[DiscoveryFailure] = []

        for provider in sorted(self._providers, key=lambda item: item.provider_id):
            try:
                discovered = provider.discover()
            except Exception as exc:  # Providers are an isolation boundary.
                failures.append(
                    DiscoveryFailure(
                        provider_id=provider.provider_id,
                        reason=f"{type(exc).__name__}: provider failed",
                    )
                )
                continue

            for capability in sorted(
                discovered,
                key=lambda item: (item.capability_id, item.source),
            ):
                normalized = replace(capability, source=provider.provider_id)
                if not self._policy.accepts(normalized):
                    failures.append(
                        DiscoveryFailure(
                            provider_id=provider.provider_id,
                            reason=(
                                f"rejected unsafe capability {normalized.capability_id}: "
                                f"{normalized.scope.value}/{normalized.access.value}"
                            ),
                        )
                    )
                    continue
                if normalized.capability_id in accepted:
                    failures.append(
                        DiscoveryFailure(
                            provider_id=provider.provider_id,
                            reason=f"duplicate capability {normalized.capability_id}",
                        )
                    )
                    continue
                accepted[normalized.capability_id] = normalized

        return HostManifest(
            schema_version=1,
            capabilities=tuple(accepted[key] for key in sorted(accepted)),
            failures=tuple(sorted(failures, key=lambda item: (item.provider_id, item.reason))),
        )
