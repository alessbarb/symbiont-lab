from __future__ import annotations

import ctypes
import math
import os
import platform
import shutil
import time
from hashlib import sha256
from typing import Callable

from .records import (
    Capability,
    CapabilityKind,
    ReadingPrivacyClass,
    ReadingQuality,
    SensorReading,
    Unit,
)

Reader = Callable[[], float | None]


def _finite(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class PortableSurfaceProvider:
    """Discover bounded, aggregate, read-only host surfaces on macOS and Windows.

    The counterpart of ``LinuxSurfaceProvider`` for hosts without procfs/sysfs,
    built only on the standard library (``ctypes`` for the system calls). The same
    rules hold: locators form stable opaque ids inside the provider and never
    reach cognition, every surface is a whole-system aggregate, nothing is
    written, and discovery is capped. A surface is offered only if it can be read
    at discovery time, so an unsupported call is simply absent.
    """

    provider_id = "portable-safe-surfaces"
    MAX_SURFACES = 64

    def __init__(self, *, system: str | None = None) -> None:
        self._system = system if system is not None else platform.system()
        self._readers: dict[str, Reader] = {}

    @staticmethod
    def _opaque_id(locator: str) -> str:
        digest = sha256(f"symbiont-portable-surface:{locator}".encode()).hexdigest()[:20]
        return f"signal.{digest}"

    def _candidates(self) -> list[tuple[str, Reader]]:
        candidates: list[tuple[str, Reader]] = []
        if hasattr(os, "getloadavg"):
            for index in range(3):
                candidates.append(
                    (f"loadavg:{index}", lambda idx=index: _finite(os.getloadavg()[idx]))
                )
        root = os.path.abspath(os.sep)
        for field in ("total", "used", "free"):
            candidates.append(
                (
                    f"disk:{field}",
                    lambda name=field: _finite(getattr(shutil.disk_usage(root), name)),
                )
            )
        if self._system == "Windows":
            candidates.extend(self._windows_candidates())
        elif self._system == "Darwin":
            candidates.extend(self._darwin_candidates())
        return candidates

    @staticmethod
    def _windows_candidates() -> list[tuple[str, Reader]]:
        kernel32 = getattr(getattr(ctypes, "windll", None), "kernel32", None)
        if kernel32 is None:
            return []

        def memory(field: str) -> float | None:
            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            return _finite(getattr(status, field))

        def cpu_times(index: int) -> float | None:
            times = [ctypes.c_ulonglong() for _ in range(3)]  # idle, kernel, user
            if not kernel32.GetSystemTimes(*(ctypes.byref(item) for item in times)):
                return None
            return _finite(times[index].value)

        def power(field: str) -> float | None:
            status = _SystemPowerStatus()
            if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                return None
            value = getattr(status, field)
            return None if value == 255 else _finite(value)  # 255: unknown

        candidates: list[tuple[str, Reader]] = [
            (f"memory:{field}", lambda name=field: memory(name))
            for field in ("dwMemoryLoad", "ullAvailPhys", "ullTotalPhys", "ullAvailPageFile")
        ]
        candidates += [
            (f"cpu-times:{index}", lambda idx=index: cpu_times(idx)) for index in range(3)
        ]
        candidates += [
            (f"power:{field}", lambda name=field: power(name))
            for field in ("ACLineStatus", "BatteryLifePercent")
        ]
        return candidates

    @staticmethod
    def _darwin_candidates() -> list[tuple[str, Reader]]:
        try:
            libc = ctypes.CDLL(None)
            sysctlbyname = libc.sysctlbyname
        except (OSError, AttributeError, TypeError):
            return []

        def sysctl(name: str) -> float | None:
            value = ctypes.c_uint64(0)
            size = ctypes.c_size_t(ctypes.sizeof(value))
            if sysctlbyname(name.encode(), ctypes.byref(value), ctypes.byref(size), None, 0):
                return None
            if size.value == 4:
                return _finite(value.value & 0xFFFFFFFF)
            return _finite(value.value)

        names = (
            "hw.memsize",
            "vm.page_free_count",
            "vm.page_speculative_count",
            "vm.page_purgeable_count",
            "hw.cpufrequency",
        )
        return [(f"sysctl:{name}", lambda item=name: sysctl(item)) for name in names]

    def discover(self) -> tuple[Capability, ...]:
        self._readers = {}
        capabilities: list[Capability] = []
        for locator, reader in self._candidates():
            if len(self._readers) >= self.MAX_SURFACES:
                break
            try:
                readable = reader() is not None
            except (OSError, ValueError, AttributeError, ctypes.ArgumentError):
                readable = False
            if not readable:
                continue
            capability_id = self._opaque_id(locator)
            self._readers[capability_id] = reader
            capabilities.append(
                Capability(
                    capability_id=capability_id,
                    kind=CapabilityKind.SIGNAL,
                    source=self.provider_id,
                    detail=(("opaque", True),),
                )
            )
        return tuple(sorted(capabilities, key=lambda item: item.capability_id))

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        now = time.monotonic_ns()
        readings: list[SensorReading] = []
        for capability in capabilities:
            if capability.source != self.provider_id:
                continue
            reader = self._readers.get(capability.capability_id)
            if reader is None:
                continue
            try:
                value = reader()
            except (OSError, ValueError, AttributeError, ctypes.ArgumentError):
                value = None
            readings.append(
                SensorReading(
                    capability_id=capability.capability_id,
                    source=self.provider_id,
                    value=value,
                    unit=Unit.COUNT,
                    monotonic_timestamp_ns=now,
                    quality=ReadingQuality.NOMINAL
                    if value is not None
                    else ReadingQuality.UNAVAILABLE,
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )
        return tuple(readings)
