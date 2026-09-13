from __future__ import annotations

import os
import platform
import shutil
import time

from ..contracts import Capability, CapabilityKind


class StandardLibraryProvider:
    """Minimal cross-platform discovery using read-only Python APIs."""

    provider_id = "stdlib"

    def discover(self) -> tuple[Capability, ...]:
        logical_cpus = os.cpu_count()
        clock = time.get_clock_info("monotonic")
        disk_root = "C:\\" if os.name == "nt" else "/"
        disk_available = _disk_usage_total(disk_root) > 0
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
            Capability(
                capability_id="storage.disk_usage",
                kind=CapabilityKind.STORAGE,
                source=self.provider_id,
                available=disk_available,
            ),
        )


def _disk_usage_total(path: str) -> int:
    try:
        return shutil.disk_usage(path).total
    except OSError:
        return 0
