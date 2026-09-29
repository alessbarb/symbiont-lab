from pathlib import Path

from symbiont_lab.experiments.resource_guard import ResourceRequest, assess_resources


def test_resource_guard_rejects_impossible_disk_request(tmp_path: Path) -> None:
    result = assess_resources(
        ResourceRequest(peak_memory_gb=0.01, disk_gb=10**9, cpu_threads=1),
        disk_path=tmp_path,
    )
    assert not result.allowed
    assert any(reason.startswith("disk:") for reason in result.reasons)
