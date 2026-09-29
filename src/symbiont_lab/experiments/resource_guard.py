"""Machine resource admission for long scientific runs."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    peak_memory_gb: float
    disk_gb: float
    cpu_threads: int
    safety_memory_gb: float = 1.0


@dataclass(frozen=True, slots=True)
class ResourceAssessment:
    allowed: bool
    available_memory_gb: float
    free_disk_gb: float
    reasons: tuple[str, ...]


def _available_memory_gb() -> float:
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values: dict[str, float] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            try:
                values[key] = float(raw.strip().split()[0]) / (1024 * 1024)
            except (ValueError, IndexError):
                continue
        if "MemAvailable" in values:
            return values["MemAvailable"]
    return 0.0


def assess_resources(request: ResourceRequest, *, disk_path: Path) -> ResourceAssessment:
    available = _available_memory_gb()
    free_disk = shutil.disk_usage(disk_path).free / (1024**3)
    reasons: list[str] = []
    required_memory = request.peak_memory_gb + request.safety_memory_gb
    if available and available < required_memory:
        reasons.append(
            f"memory: {available:.2f} GiB available < {required_memory:.2f} GiB required"
        )
    if free_disk < request.disk_gb:
        reasons.append(f"disk: {free_disk:.2f} GiB free < {request.disk_gb:.2f} GiB required")
    if request.cpu_threads < 1:
        reasons.append("cpu_threads must be >= 1")
    return ResourceAssessment(not reasons, available, free_disk, tuple(reasons))
