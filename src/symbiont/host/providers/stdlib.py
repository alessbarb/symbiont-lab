from __future__ import annotations

import os
import platform
import time

from ..contracts import Capability, CapabilityKind


class StandardLibraryProvider:
    """Minimal cross-platform discovery using read-only Python APIs."""

    provider_id = "stdlib"

    def discover(self) -> tuple[Capability, ...]:
        logical_cpus = os.cpu_count()
        clock = time.get_clock_info("monotonic")
        return (
            Capability(
                capability_id="clock.monotonic",
                kind=CapabilityKind.CLOCK,
                source=self.provider_id,
                detail=(
                    ("adjustable", clock.adjustable),
                    ("monotonic", clock.monotonic),
                    ("resolution_seconds", clock.resolution),
                ),
            ),
            Capability(
                capability_id="compute.logical_cpu",
                kind=CapabilityKind.COMPUTE,
                source=self.provider_id,
                available=logical_cpus is not None,
                detail=(("count", logical_cpus),),
            ),
            Capability(
                capability_id="runtime.python",
                kind=CapabilityKind.RUNTIME,
                source=self.provider_id,
                detail=(
                    ("implementation", platform.python_implementation()),
                    ("major", int(platform.python_version_tuple()[0])),
                    ("minor", int(platform.python_version_tuple()[1])),
                ),
            ),
        )
