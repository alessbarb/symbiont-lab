from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
import time
from typing import Callable

from ..contracts import Capability, CapabilityKind
from ..readings import ReadingPrivacyClass, ReadingQuality, SensorReading, Unit


class LinuxSurfaceProvider:
    """Discover bounded, aggregate, read-only Linux numeric surfaces.

    Paths/row labels are used only inside the provider to form stable opaque
    hashes; they are never exposed to cognition or persisted as telemetry.
    Discovery is intentionally restricted to aggregate procfs/sysfs surfaces
    and capped, so this can never turn into arbitrary filesystem exploration.
    """

    provider_id = "linux-safe-surfaces"
    MAX_SURFACES = 256

    _SYS_PATTERNS = (
        "/sys/class/thermal/thermal_zone*/temp",
        "/sys/class/power_supply/*/capacity",
        "/sys/class/power_supply/*/power_now",
        "/sys/class/power_supply/*/energy_now",
        "/sys/class/power_supply/*/voltage_now",
        "/sys/class/power_supply/*/current_now",
        "/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq",
        "/sys/class/drm/card[0-9]*/gt_cur_freq_mhz",
        "/sys/class/drm/card[0-9]*/gt_act_freq_mhz",
        "/sys/class/drm/card[0-9]*/device/gpu_busy_percent",
        "/sys/class/drm/card[0-9]*/device/mem_busy_percent",
        "/sys/class/drm/card[0-9]*/device/hwmon/hwmon*/temp*_input",
        "/sys/class/drm/card[0-9]*/device/hwmon/hwmon*/power*_input",
    )
    _TABLE_FILES = (
        Path("/proc/net/dev"),
        Path("/proc/diskstats"),
        Path("/proc/pressure/cpu"),
        Path("/proc/pressure/io"),
        Path("/proc/pressure/memory"),
    )

    def __init__(self) -> None:
        self._readers: dict[str, Callable[[], float | None]] = {}
        # Apparatus-only metadata. It never enters Capability, organism
        # cognition, checkpoints or signal identity.
        self._observer_descriptors: dict[str, dict[str, object]] = {}

    @staticmethod
    def _observer_descriptor(locator: str) -> dict[str, object]:
        lower = locator.lower()
        if "thermal_zone" in lower or "temp" in lower:
            return {"label": "Temperature", "category": "thermal", "unit": "°C", "scale": 0.001}
        if "scaling_cur_freq" in lower or "gt_cur_freq" in lower or "gt_act_freq" in lower:
            return {"label": "CPU/GPU frequency", "category": "compute", "unit": "MHz", "scale": 0.001}
        if "gpu_busy_percent" in lower:
            return {"label": "GPU activity", "category": "compute", "unit": "%", "scale": 1.0}
        if "mem_busy_percent" in lower:
            return {"label": "GPU memory activity", "category": "memory", "unit": "%", "scale": 1.0}
        if "power_supply" in lower and "capacity" in lower:
            return {"label": "Battery capacity", "category": "power", "unit": "%", "scale": 1.0}
        if "power_now" in lower or "power_input" in lower:
            return {"label": "Power", "category": "power", "unit": "W", "scale": 0.000001}
        if "energy_now" in lower:
            return {"label": "Energy", "category": "power", "unit": "Wh", "scale": 0.000001}
        if "voltage_now" in lower:
            return {"label": "Voltage", "category": "power", "unit": "V", "scale": 0.000001}
        if "current_now" in lower:
            return {"label": "Current", "category": "power", "unit": "A", "scale": 0.000001}
        if "proc-loadavg" in lower:
            return {"label": "System load", "category": "compute", "unit": "load", "scale": 1.0}
        if "proc-entropy" in lower:
            return {"label": "Kernel entropy available", "category": "system", "unit": "count", "scale": 1.0}
        if "proc-meminfo" in lower:
            key = locator.rsplit(":", 1)[-1]
            safe = {
                "memtotal": "Memory total", "memfree": "Memory free",
                "memavailable": "Memory available", "cached": "Memory cache",
                "buffers": "Memory buffers", "swaptotal": "Swap total",
                "swapfree": "Swap free",
            }.get(key.lower(), "Memory statistic")
            return {"label": safe, "category": "memory", "unit": "KiB", "scale": 1.0}
        if "/proc/net/dev" in lower:
            return {"label": "Network activity", "category": "network", "unit": "count", "scale": 1.0}
        if "/proc/diskstats" in lower:
            return {"label": "Disk activity", "category": "storage", "unit": "count", "scale": 1.0}
        if "/proc/pressure/cpu" in lower:
            return {"label": "CPU pressure", "category": "compute", "unit": "pressure", "scale": 1.0}
        if "/proc/pressure/io" in lower:
            return {"label": "I/O pressure", "category": "storage", "unit": "pressure", "scale": 1.0}
        if "/proc/pressure/memory" in lower:
            return {"label": "Memory pressure", "category": "memory", "unit": "pressure", "scale": 1.0}
        if "proc-stat:cpu" in lower:
            return {"label": "CPU time", "category": "compute", "unit": "ticks", "scale": 1.0}
        return {"label": "Linux aggregate signal", "category": "system", "unit": "count", "scale": 1.0}

    def observer_descriptor(self, capability_id: str) -> dict[str, object] | None:
        descriptor = self._observer_descriptors.get(capability_id)
        return dict(descriptor) if descriptor is not None else None

    @staticmethod
    def _opaque_id(locator: str) -> str:
        digest = sha256(f"symbiont-linux-surface:{locator}".encode()).hexdigest()[:20]
        return f"signal.{digest}"

    @staticmethod
    def _safe_scalar(value: str) -> float | None:
        value = value.strip().rstrip("%,")
        if "=" in value:
            value = value.rsplit("=", 1)[-1]
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
            stripped = line.strip()
            if not stripped.startswith(key):
                continue
            values = stripped[len(key):].lstrip(": ").split()
            numeric = [value for value in values if cls._safe_scalar(value) is not None]
            if value_index >= len(numeric):
                return None
            return cls._safe_scalar(numeric[value_index])
        return None

    def _register(self, locator: str, reader: Callable[[], float | None]) -> Capability | None:
        if len(self._readers) >= self.MAX_SURFACES:
            return None
        capability_id = self._opaque_id(locator)
        if capability_id in self._readers:
            return None
        self._readers[capability_id] = reader
        self._observer_descriptors[capability_id] = self._observer_descriptor(locator)
        return Capability(
            capability_id=capability_id,
            kind=CapabilityKind.SIGNAL,
            source=self.provider_id,
            detail=(("opaque", True),),
        )

    def _append(self, capabilities: list[Capability], capability: Capability | None) -> None:
        if capability is not None:
            capabilities.append(capability)

    def discover(self) -> tuple[Capability, ...]:
        self._readers = {}
        self._observer_descriptors = {}
        capabilities: list[Capability] = []

        loadavg = Path("/proc/loadavg")
        if loadavg.is_file():
            for index in range(3):
                self._append(capabilities, self._register(
                    f"proc-loadavg:{index}",
                    lambda path=loadavg, idx=index: self._read_token(path, idx),
                ))

        entropy = Path("/proc/sys/kernel/random/entropy_avail")
        if entropy.is_file():
            self._append(capabilities, self._register(
                "proc-entropy",
                lambda path=entropy: self._read_token(path, 0),
            ))

        for pattern in self._SYS_PATTERNS:
            if len(self._readers) >= self.MAX_SURFACES:
                break
            for path in sorted(Path("/").glob(pattern.removeprefix("/")))[:64]:
                if path.is_file():
                    self._append(capabilities, self._register(
                        f"sys-scalar:{path.as_posix()}",
                        lambda target=path: self._read_token(target, 0),
                    ))

        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            try:
                keys = [line.partition(":")[0] for line in meminfo.read_text(encoding="utf-8").splitlines() if ":" in line]
            except (OSError, UnicodeError):
                keys = []
            for key in keys[:128]:
                self._append(capabilities, self._register(
                    f"proc-meminfo:{key}",
                    lambda path=meminfo, item=key: self._read_keyed_value(path, item),
                ))

        stat = Path("/proc/stat")
        if stat.is_file() and len(self._readers) < self.MAX_SURFACES:
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
                numeric_count = sum(self._safe_scalar(value) is not None for value in parts[1:])
                for index in range(min(numeric_count, 16)):
                    self._append(capabilities, self._register(
                        f"proc-stat:{key}:{index}",
                        lambda path=stat, item=key, idx=index: self._read_keyed_value(path, item, idx),
                    ))

        for path in self._TABLE_FILES:
            if len(self._readers) >= self.MAX_SURFACES or not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
            except (OSError, UnicodeError):
                lines = []
            seen_labels: set[str] = set()
            for line in lines[:32]:
                tokens = line.replace(":", " ").split()
                if not tokens:
                    continue
                label = self._row_label(tokens)
                if (
                    label is None
                    or label in seen_labels
                    or label.startswith("loop")
                    or label.startswith("ram")
                ):
                    # No stable non-numeric token to key on, duplicate row,
                    # or virtual loop/ram block device — never guess an identity.
                    continue
                seen_labels.add(label)
                numeric_positions = [i for i, token in enumerate(tokens) if self._safe_scalar(token) is not None]
                for numeric_index in range(min(len(numeric_positions), 16)):
                    locator = f"table:{path.as_posix()}:{label}:{numeric_index}"
                    self._append(capabilities, self._register(
                        locator,
                        lambda target=path, row_label=label, idx=numeric_index: self._read_table_token(target, row_label, idx),
                    ))

        return tuple(sorted(capabilities, key=lambda item: item.capability_id))

    @staticmethod
    def _row_label(tokens: list[str]) -> str | None:
        """The first non-numeric token in a table row — a device/interface
        name or a fixed keyword ("some"/"full") — used as this row's stable
        identity instead of its position, so reordering, removing or adding
        rows can never silently alias one device's history onto another
        (roadmap safety finding A03). Returns ``None`` if every token in the
        row looks numeric, since there is then no stable label to key on."""
        return next((token for token in tokens if LinuxSurfaceProvider._safe_scalar(token) is None), None)

    @classmethod
    def _read_table_token(cls, path: Path, row_label: str, numeric_index: int) -> float | None:
        try:
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        except (OSError, UnicodeError):
            return None
        for line in lines[:32]:
            tokens = line.replace(":", " ").split()
            if not tokens or cls._row_label(tokens) != row_label:
                continue
            numeric_positions = [i for i, token in enumerate(tokens) if cls._safe_scalar(token) is not None]
            if numeric_index >= len(numeric_positions):
                return None
            return cls._safe_scalar(tokens[numeric_positions[numeric_index]])
        return None

    def sample(self, capabilities: tuple[Capability, ...]) -> tuple[SensorReading, ...]:
        now = time.monotonic_ns()
        readings: list[SensorReading] = []
        for capability in capabilities:
            if capability.source != self.provider_id:
                continue
            reader = self._readers.get(capability.capability_id)
            if reader is None:
                continue
            value = reader()
            readings.append(SensorReading(
                capability_id=capability.capability_id,
                source=self.provider_id,
                value=value,
                unit=Unit.COUNT,
                monotonic_timestamp_ns=now,
                quality=ReadingQuality.NOMINAL if value is not None else ReadingQuality.UNAVAILABLE,
                privacy_class=ReadingPrivacyClass.AGGREGATE,
            ))
        return tuple(readings)
