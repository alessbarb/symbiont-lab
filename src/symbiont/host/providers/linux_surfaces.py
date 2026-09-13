from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
from typing import Callable

from ..contracts import Capability, CapabilityKind
from ..readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


class LinuxSurfaceProvider:
    """Discover safe, aggregate, read-only Linux signal surfaces.

    This provider deliberately does not tell cognition what a discovered
    signal *means*. It only explores a small, vetted part of procfs/sysfs that
    contains aggregate numeric state, assigns stable opaque ids and exposes
    scalar readings. No filenames, usernames, process command lines, network
    addresses or other identifying/user-content metadata leave this class.

    The discovery surface is bounded by construction. It never walks arbitrary
    filesystem trees and never follows a path outside the explicitly approved
    aggregate virtual files below.
    """

    provider_id = "linux-safe-surfaces"

    _PROC_FILES = (
        Path("/proc/loadavg"),
        Path("/proc/meminfo"),
        Path("/proc/stat"),
    )
    _SYS_PATTERNS = (
        "/sys/class/thermal/thermal_zone*/temp",
        "/sys/class/power_supply/*/capacity",
        "/sys/class/power_supply/*/power_now",
        "/sys/class/power_supply/*/energy_now",
        "/sys/class/power_supply/*/voltage_now",
        "/sys/class/power_supply/*/current_now",
    )

    def __init__(self) -> None:
        self._readers: dict[str, Callable[[], float | None]] = {}

    @staticmethod
    def _opaque_id(locator: str) -> str:
        digest = sha256(f"symbiont-linux-surface:{locator}".encode("utf-8")).hexdigest()[:20]
        return f"signal.{digest}"

    @staticmethod
    def _safe_scalar(value: str) -> float | None:
        try:
            result = float(value)
        except ValueError:
            return None
        return result if math.isfinite(result) else None

    @classmethod
    def _read_token(cls, path: Path, token_index: int) -> float | None:
        try:
            tokens = path.read_text(encoding="utf-8", errors="strict").strip().split()
        except (OSError, UnicodeError):
            return None
        if token_index >= len(tokens):
            return None
        return cls._safe_scalar(tokens[token_index])

    @classmethod
    def _read_keyed_value(cls, path: Path, key: str, value_index: int = 0) -> float | None:
        try:
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        except (OSError, UnicodeError):
            return None
        for line in lines:
            if not line.startswith(key):
                continue
            values = line[len(key):].lstrip(": ").split()
            if value_index >= len(values):
                return None
            return cls._safe_scalar(values[value_index])
        return None

    def _register(self, locator: str, reader: Callable[[], float | None]) -> Capability:
        capability_id = self._opaque_id(locator)
        self._readers[capability_id] = reader
        return Capability(
            capability_id=capability_id,
            kind=CapabilityKind.SIGNAL,
            source=self.provider_id,
            detail=(("opaque", True),),
        )

    def discover(self) -> tuple[Capability, ...]:
        self._readers = {}
        capabilities: list[Capability] = []

        loadavg = Path("/proc/loadavg")
        if loadavg.is_file():
            for index in range(3):
                capabilities.append(
                    self._register(
                        f"proc-loadavg:{index}",
                        lambda path=loadavg, idx=index: self._read_token(path, idx),
                    )
                )

        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            try:
                keys = [line.partition(":")[0] for line in meminfo.read_text(encoding="utf-8").splitlines() if ":" in line]
            except (OSError, UnicodeError):
                keys = []
            for key in keys[:128]:
                locator = f"proc-meminfo:{key}"
                capabilities.append(
                    self._register(locator, lambda path=meminfo, item=key: self._read_keyed_value(path, item))
                )

        stat = Path("/proc/stat")
        if stat.is_file():
            try:
                lines = stat.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                lines = []
            for line in lines[:64]:
                parts = line.split()
                if not parts:
                    continue
                key = parts[0]
                if key.startswith("cpu") and key != "cpu":
                    continue
                numeric = [value for value in parts[1:] if self._safe_scalar(value) is not None]
                for index in range(min(len(numeric), 16)):
                    locator = f"proc-stat:{key}:{index}"
                    capabilities.append(
                        self._register(
                            locator,
                            lambda path=stat, item=key, idx=index: self._read_keyed_value(path, item, idx),
                        )
                    )

        for pattern in self._SYS_PATTERNS:
            base = Path("/")
            relative = pattern.removeprefix("/")
            for path in sorted(base.glob(relative))[:64]:
                if not path.is_file():
                    continue
                locator = f"sys-scalar:{path.as_posix()}"
                capabilities.append(
                    self._register(locator, lambda target=path: self._read_token(target, 0))
                )

        unique = {capability.capability_id: capability for capability in capabilities}
        return tuple(unique[key] for key in sorted(unique))

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        readings: list[SensorReading] = []
        for capability in capabilities:
            if capability.source != self.provider_id:
                continue
            reader = self._readers.get(capability.capability_id)
            if reader is None:
                continue
            value = reader()
            readings.append(
                SensorReading(
                    capability_id=capability.capability_id,
                    source=self.provider_id,
                    value=value,
                    unit=Unit.COUNT,
                    monotonic_timestamp_ns=__import__("time").monotonic_ns(),
                    quality=(ReadingQuality.NOMINAL if value is not None else ReadingQuality.UNAVAILABLE),
                    privacy_class=ReadingPrivacyClass.AGGREGATE,
                )
            )
        return tuple(readings)
