from pathlib import Path

import symbiont_lab.experiments.resource_guard as guard
from symbiont_lab.experiments.resource_guard import ResourceRequest, assess_resources


def test_resource_guard_rejects_impossible_disk_request(tmp_path: Path) -> None:
    result = assess_resources(
        ResourceRequest(peak_memory_gb=0.01, disk_gb=10**9, cpu_threads=1),
        disk_path=tmp_path,
    )
    assert not result.allowed
    assert any(reason.startswith("disk:") for reason in result.reasons)


def test_resource_guard_rejects_unknown_memory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_available_memory_gb", lambda: 0.0)
    result = assess_resources(
        ResourceRequest(peak_memory_gb=1.0, disk_gb=0.0, cpu_threads=1),
        disk_path=tmp_path,
    )
    assert not result.allowed
    assert any("could not be measured" in reason for reason in result.reasons)


def test_resource_guard_rejects_cpu_oversubscription(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(guard, "_available_cpu_threads", lambda: 2)
    monkeypatch.setattr(guard, "_available_memory_gb", lambda: 100.0)
    result = assess_resources(
        ResourceRequest(peak_memory_gb=1.0, disk_gb=0.0, cpu_threads=3),
        disk_path=tmp_path,
    )
    assert not result.allowed
    assert any(reason.startswith("cpu:") for reason in result.reasons)


def test_available_cpu_threads_prefers_affinity(monkeypatch) -> None:
    monkeypatch.setattr(guard.os, "sched_getaffinity", lambda _pid: {2, 3}, raising=False)
    monkeypatch.setattr(guard.os, "cpu_count", lambda: 64)
    assert guard._available_cpu_threads() == 2
