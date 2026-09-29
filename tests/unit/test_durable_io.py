from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from symbiont.host.durable import (
    durable_atomic_replacement,
    durable_atomic_write,
    durable_atomic_write_json,
    sync_directory,
)


def test_durable_atomic_write_bytes(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "state.bin"
    data = b"binary-checkpoint-bytes"
    result = durable_atomic_write(target, data, sync_dir=True)
    assert result == target
    assert target.is_file()
    assert target.read_bytes() == data


def test_durable_atomic_write_text(tmp_path: Path) -> None:
    target = tmp_path / "hello.txt"
    text = "hello world\n"
    durable_atomic_write(target, text, sync_dir=True)
    assert target.read_text(encoding="utf-8") == text


def test_durable_atomic_write_json(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    payload = {"organism_id": "org_123", "ticks": 42, "values": [1.0, 2.5]}
    durable_atomic_write_json(target, payload, indent=2, sync_dir=True)
    assert target.is_file()
    import json

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == payload


def test_durable_atomic_write_permissions(tmp_path: Path) -> None:
    target = tmp_path / "private.key"
    durable_atomic_write(target, b"secret-key", permissions=0o600, sync_dir=True)
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o600


def test_durable_atomic_replacement_success(tmp_path: Path) -> None:
    target = tmp_path / "bundle.zip"
    with durable_atomic_replacement(target, sync_dir=True) as tmp:
        assert tmp.exists()
        assert not target.exists()
        tmp.write_bytes(b"zip-content")
    assert target.is_file()
    assert target.read_bytes() == b"zip-content"
    assert not tmp.exists()


def test_durable_atomic_replacement_exception_preserves_target(tmp_path: Path) -> None:
    target = tmp_path / "existing.dat"
    target.write_bytes(b"initial-stable-data")

    with pytest.raises(RuntimeError, match="simulated failure"):
        with durable_atomic_replacement(target, sync_dir=True) as tmp:
            tmp.write_bytes(b"corrupt-data")
            raise RuntimeError("simulated failure")

    assert target.read_bytes() == b"initial-stable-data"
    assert not tmp.exists()


@pytest.mark.parametrize(
    "fault_point",
    [
        "before_file_fsync",
        "after_file_fsync",
        "before_replace",
    ],
)
def test_fault_injection_before_replace_preserves_prior_target(
    tmp_path: Path, fault_point: str
) -> None:
    target = tmp_path / "checkpoint.json"
    target.write_text("prior_checkpoint")

    def fault_hook(point: str) -> None:
        if point == fault_point:
            raise OSError(f"Crash simulated at {point}")

    with pytest.raises(OSError, match=f"Crash simulated at {fault_point}"):
        durable_atomic_write(
            target,
            "new_checkpoint",
            _fault_point=fault_hook,
            sync_dir=True,
        )

    # Invariant: prior checkpoint remains untouched
    assert target.read_text() == "prior_checkpoint"
    # Invariant: no orphaned temporary files in the directory
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".checkpoint.json.")]
    assert len(leftovers) == 0


@pytest.mark.parametrize(
    "fault_point",
    [
        "after_replace",
        "before_dir_fsync",
        "after_dir_fsync",
    ],
)
def test_fault_injection_after_replace_retains_new_target(tmp_path: Path, fault_point: str) -> None:
    target = tmp_path / "checkpoint.json"
    target.write_text("prior_checkpoint")

    def fault_hook(point: str) -> None:
        if point == fault_point:
            raise OSError(f"Crash simulated at {point}")

    with pytest.raises(OSError, match=f"Crash simulated at {fault_point}"):
        durable_atomic_write(
            target,
            "new_checkpoint",
            _fault_point=fault_hook,
            sync_dir=True,
        )

    # Invariant: after rename, target is the new file
    assert target.read_text() == "new_checkpoint"


def test_sync_directory_calls_fsync_on_posix(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("POSIX only")

    fsynced_fds: list[int] = []
    real_fsync = os.fsync

    def tracking_fsync(fd: int) -> None:
        fsynced_fds.append(fd)
        real_fsync(fd)

    with patch("os.fsync", side_effect=tracking_fsync):
        sync_directory(tmp_path)

    assert len(fsynced_fds) == 1
