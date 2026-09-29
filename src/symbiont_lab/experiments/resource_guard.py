"""Machine resource admission for long scientific runs."""

from __future__ import annotations

import os
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
    available_cpu_threads: int
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

    try:
        pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, ValueError):
        return 0.0
    if pages <= 0 or page_size <= 0:
        return 0.0
    return pages * page_size / (1024**3)


def assess_resources(request: ResourceRequest, *, disk_path: Path) -> ResourceAssessment:
    available = _available_memory_gb()
    free_disk = shutil.disk_usage(disk_path).free / (1024**3)
    available_cpu = int(os.cpu_count() or 0)
    reasons: list[str] = []

    if request.peak_memory_gb <= 0:
        reasons.append("peak_memory_gb must be > 0")
    if request.safety_memory_gb < 0:
        reasons.append("safety_memory_gb must be >= 0")
    required_memory = request.peak_memory_gb + request.safety_memory_gb
    if available <= 0:
        reasons.append("memory: available memory could not be measured")
    elif available < required_memory:
        reasons.append(
            f"memory: {available:.2f} GiB available < {required_memory:.2f} GiB required"
        )

    if request.disk_gb < 0:
        reasons.append("disk_gb must be >= 0")
    elif free_disk < request.disk_gb:
        reasons.append(f"disk: {free_disk:.2f} GiB free < {request.disk_gb:.2f} GiB required")

    if request.cpu_threads < 1:
        reasons.append("cpu_threads must be >= 1")
    elif available_cpu and request.cpu_threads > available_cpu:
        reasons.append(
            f"cpu: {request.cpu_threads} requested > {available_cpu} available logical CPUs"
        )

    return ResourceAssessment(
        allowed=not reasons,
        available_memory_gb=available,
        free_disk_gb=free_disk,
        available_cpu_threads=available_cpu,
        reasons=tuple(reasons),
    )
