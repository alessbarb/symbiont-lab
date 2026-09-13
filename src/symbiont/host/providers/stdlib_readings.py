from __future__ import annotations

import os
import shutil
import time

from ..contracts import Capability
from ..readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit

_DISK_ROOT = "C:\\" if os.name == "nt" else "/"


class StandardLibraryReadingProvider:
    """Sample real host readings using only stdlib, read-only APIs (roadmap v0.31).

    Reports CPU load and disk usage, the two signals reliably obtainable
    cross-platform without a third-party dependency (this project keeps
    ``dependencies = []``). Memory, thermal and power are not sampled here —
    stdlib has no portable, safe way to read them — so a future provider
    adds those rather than this one guessing at them.
    """

    provider_id = "stdlib"

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        available_ids = {capability.capability_id for capability in capabilities}
        now_ns = time.monotonic_ns()
        readings: list[SensorReading] = []

        if "compute.logical_cpu" in available_ids:
            readings.append(self._cpu_load(now_ns))
        if "storage.disk_usage" in available_ids:
            readings.append(self._disk_usage(now_ns))

        return tuple(readings)

    def _unavailable(self, capability_id: str, now_ns: int) -> SensorReading:
        return SensorReading(
            capability_id=capability_id,
            source=self.provider_id,
            value=None,
            unit=Unit.RATIO,
            monotonic_timestamp_ns=now_ns,
            quality=ReadingQuality.UNAVAILABLE,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    def _cpu_load(self, now_ns: int) -> SensorReading:
        cpu_count = os.cpu_count()
        getloadavg = getattr(os, "getloadavg", None)
        if getloadavg is None or not cpu_count:
            return self._unavailable("compute.logical_cpu", now_ns)
        try:
            load_1min = getloadavg()[0]
        except OSError:
            return self._unavailable("compute.logical_cpu", now_ns)
        return SensorReading(
            capability_id="compute.logical_cpu",
            source=self.provider_id,
            value=load_1min / cpu_count,
            unit=Unit.RATIO,
            monotonic_timestamp_ns=now_ns,
            quality=ReadingQuality.NOMINAL,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )

    def _disk_usage(self, now_ns: int) -> SensorReading:
        try:
            usage = shutil.disk_usage(_DISK_ROOT)
        except OSError:
            usage = None
        if usage is None or usage.total <= 0:
            return SensorReading(
                capability_id="storage.disk_usage",
                source=self.provider_id,
                value=None,
                unit=Unit.PERCENT,
                monotonic_timestamp_ns=now_ns,
                quality=ReadingQuality.UNAVAILABLE,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            )
        return SensorReading(
            capability_id="storage.disk_usage",
            source=self.provider_id,
            value=(usage.used / usage.total) * 100.0,
            unit=Unit.PERCENT,
            monotonic_timestamp_ns=now_ns,
            quality=ReadingQuality.NOMINAL,
            privacy_class=ReadingPrivacyClass.AGGREGATE,
        )
