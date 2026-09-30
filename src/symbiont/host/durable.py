from __future__ import annotations

import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkstemp
from typing import Any, Callable, Generator


def sync_directory(directory_path: str | Path, *, required: bool = True) -> None:
    """Flush directory entries to persistent storage (POSIX).

    In POSIX, ``os.replace`` updates directory entries in kernel buffer cache.
    Calling ``os.fsync`` on the directory descriptor guarantees that the new
    filename linkage survives an abrupt power loss or kernel panic.

    On non-POSIX systems (e.g. Windows), NTFS metadata modifications are journaled
    and opening directory file descriptors for ``fsync`` is not supported.

    Parameters
    ----------
    directory_path:
        Directory path whose directory entries are to be flushed.
    required:
        If True (default), raise OSError on POSIX if opening or syncing the directory fails.
        If False, errors are silently ignored (best-effort durability).
    """
    if os.name != "posix":
        return

    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    try:
        dir_fd = os.open(str(directory_path), flags)
    except (OSError, PermissionError):
        if required:
            raise
        return

    try:
        os.fsync(dir_fd)
    except OSError:
        if required:
            raise
    finally:
        try:
            os.close(dir_fd)
        except OSError:
            pass


def ensure_secure_file_permissions(path: str | Path, expected_mode: int = 0o600) -> None:
    """Ensure that on POSIX systems, a sensitive file does not allow group or other access.

    If group or other bits are set (e.g. ``st_mode & 0o077 != 0``), attempts to chmod
    the file to expected_mode. If chmod fails, raises PermissionError.
    """
    if os.name != "posix":
        return
    p = Path(path)
    if not p.is_file():
        return
    mode = stat.S_IMODE(p.stat().st_mode)
    if mode & 0o077 != 0:
        try:
            os.chmod(p, expected_mode)
        except OSError as exc:
            raise PermissionError(
                f"Insecure permissions {oct(mode)} on '{p}': group/other access forbidden: {exc}"
            ) from exc


def durable_atomic_write(
    target_path: str | Path,
    data: bytes | str,
    *,
    encoding: str = "utf-8",
    sync_dir: bool = True,
    permissions: int | None = None,
    _fault_point: Callable[[str], None] | None = None,
) -> Path:
    """Write data to target_path atomically and durably.

    Writes to a temporary file in the same directory, flushes and fsyncs the file
    descriptor, atomically replaces the target via ``os.replace``, and synchronously
    flushes the parent directory metadata to disk.

    Parameters
    ----------
    target_path:
        Destination file path.
    data:
        Bytes or string content to write.
    encoding:
        Text encoding if data is a string. Default is utf-8.
    sync_dir:
        Whether to fsync the parent directory after replacement.
    permissions:
        Optional file mode bits (e.g. 0o600 for cryptographic private keys).
        If omitted, standard umask mode is applied.
    _fault_point:
        Testing hook to inject faults at specific execution stages.
    """
    target = Path(target_path)
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    payload_bytes = data.encode(encoding) if isinstance(data, str) else data

    fd, tmp_name = mkstemp(dir=str(parent), prefix=f".{target.name}.", suffix=".tmp")

    if permissions is not None:
        try:
            os.chmod(tmp_name, permissions)
        except OSError:
            pass
    else:
        try:
            current_umask = os.umask(0)
            os.umask(current_umask)
            os.chmod(tmp_name, 0o666 & ~current_umask)
        except OSError:
            pass

    try:
        with os.fdopen(fd, "wb") as handle:
            if _fault_point:
                _fault_point("before_write")
                split_at = max(1, len(payload_bytes) // 2) if payload_bytes else 0
                if split_at:
                    handle.write(payload_bytes[:split_at])
                    _fault_point("during_write")
                    handle.write(payload_bytes[split_at:])
                else:
                    _fault_point("during_write")
            else:
                handle.write(payload_bytes)
            handle.flush()
            if _fault_point:
                _fault_point("before_file_fsync")
            os.fsync(handle.fileno())
            if _fault_point:
                _fault_point("after_file_fsync")

        if _fault_point:
            _fault_point("before_replace")
        os.replace(tmp_name, target)
        if _fault_point:
            _fault_point("after_replace")

        if sync_dir:
            if _fault_point:
                _fault_point("before_dir_fsync")
            sync_directory(parent, required=True)
            if _fault_point:
                _fault_point("after_dir_fsync")
    except BaseException:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass
        raise

    return target


def durable_atomic_write_json(
    target_path: str | Path,
    payload: Any,
    *,
    sync_dir: bool = True,
    permissions: int | None = None,
    indent: int | None = None,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
    _fault_point: Callable[[str], None] | None = None,
) -> Path:
    """Serialize payload to JSON and write to target_path durably and atomically."""
    separators = (",", ":") if indent is None else None
    encoded = (
        json.dumps(
            payload,
            sort_keys=sort_keys,
            indent=indent,
            ensure_ascii=ensure_ascii,
            allow_nan=False,
            separators=separators,
        )
        + "\n"
    )
    return durable_atomic_write(
        target_path,
        encoded.encode("utf-8"),
        sync_dir=sync_dir,
        permissions=permissions,
        _fault_point=_fault_point,
    )


@contextmanager
def durable_atomic_replacement(
    target_path: str | Path,
    *,
    sync_dir: bool = True,
    permissions: int | None = None,
    suffix: str = ".tmp",
    _fault_point: Callable[[str], None] | None = None,
) -> Generator[Path, None, None]:
    """Context manager providing a temporary path atomically moved to target on exit.

    Yields a Path pointing to a newly created temporary file in the same directory.
    When the context block exits normally:
    1. The temporary file is atomically moved to target_path using ``os.replace``.
    2. The parent directory is fsynced (POSIX).

    If an exception is raised inside the context block:
    1. The temporary file is cleaned up if it still exists.
    2. Any existing file at target_path remains unchanged.
    """
    target = Path(target_path)
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_str = mkstemp(dir=str(parent), prefix=f".{target.name}.", suffix=suffix)
    os.close(fd)
    tmp_path = Path(tmp_str)

    if permissions is not None:
        try:
            os.chmod(tmp_path, permissions)
        except OSError:
            pass

    try:
        yield tmp_path
        if tmp_path.exists():
            if _fault_point:
                _fault_point("before_file_fsync")
            tmp_fd = os.open(str(tmp_path), os.O_RDONLY)
            try:
                os.fsync(tmp_fd)
            finally:
                os.close(tmp_fd)
            if _fault_point:
                _fault_point("after_file_fsync")

        if _fault_point:
            _fault_point("before_replace")
        os.replace(tmp_path, target)
        if _fault_point:
            _fault_point("after_replace")

        if sync_dir:
            if _fault_point:
                _fault_point("before_dir_fsync")
            sync_directory(parent, required=True)
            if _fault_point:
                _fault_point("after_dir_fsync")
    except BaseException:
        try:
            if tmp_path.exists():
                os.unlink(tmp_path)
        except OSError:
            pass
        raise
