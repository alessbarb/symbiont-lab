from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping

from symbiont.host.durable import durable_atomic_write, durable_atomic_write_json, sync_directory

FaultHook = Callable[[str], None]


@dataclass(slots=True, frozen=True)
class CommittedGeneration:
    index: int
    path: Path
    files: dict[str, str]


class GenerationStore:
    """Transactional visibility for multi-file scientific state.

    A generation is prepared under a temporary directory, sealed by a COMPLETE
    manifest, atomically published under its immutable generation name, and only
    then made visible by atomically replacing CURRENT.
    """

    COMPLETE = "COMPLETE"
    CURRENT = "CURRENT"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generation_name(index: int) -> str:
        if index < 0:
            raise ValueError("generation index must be non-negative")
        return f"generation-{index:06d}"

    @staticmethod
    def _safe_relative_path(name: str) -> PurePosixPath:
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise ValueError(f"invalid generation payload path: {name!r}")
        if any(part in {GenerationStore.COMPLETE, GenerationStore.CURRENT} for part in path.parts):
            raise ValueError(f"reserved generation payload path: {name!r}")
        return path

    @staticmethod
    def _digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _hit(hook: FaultHook | None, point: str) -> None:
        if hook is not None:
            hook(point)

    def commit(
        self,
        index: int,
        files: Mapping[str, bytes | str],
        *,
        _fault_point: FaultHook | None = None,
    ) -> CommittedGeneration:
        """Commit one immutable generation and atomically advance CURRENT."""
        name = self.generation_name(index)
        final_dir = self.root / name
        if final_dir.exists():
            raise FileExistsError(f"generation already exists: {name}")

        def write(tmp_dir: Path) -> dict[str, str]:
            digests: dict[str, str] = {}
            for raw_name, value in sorted(files.items()):
                relative = self._safe_relative_path(raw_name)
                data = value.encode("utf-8") if isinstance(value, str) else bytes(value)
                target = tmp_dir.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)

                def payload_fault(point: str) -> None:
                    self._hit(_fault_point, f"payload.{relative.as_posix()}.{point}")

                durable_atomic_write(
                    target,
                    data,
                    sync_dir=True,
                    _fault_point=payload_fault if _fault_point is not None else None,
                )
                digests[relative.as_posix()] = self._digest(data)
            return digests

        return self._publish(index, write, _fault_point)

    def commit_directory(
        self,
        index: int,
        source: str | Path,
        *,
        extra_files: Mapping[str, bytes | str] | None = None,
        _fault_point: FaultHook | None = None,
    ) -> CommittedGeneration:
        """Commit every file under ``source`` as one generation.

        Files are copied and hashed in streaming fashion, so a run's outputs do
        not have to fit in memory. ``extra_files`` are added beside them and may
        not collide with a copied path.
        """
        source = Path(source)
        if not source.is_dir():
            raise NotADirectoryError(source)
        name = self.generation_name(index)
        if (self.root / name).exists():
            raise FileExistsError(f"generation already exists: {name}")
        extras = dict(extra_files or {})

        def write(tmp_dir: Path) -> dict[str, str]:
            digests: dict[str, str] = {}
            for path in sorted(item for item in source.rglob("*") if item.is_file()):
                relative = self._safe_relative_path(path.relative_to(source).as_posix())
                target = tmp_dir.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                relative_name = relative.as_posix()

                def payload_fault(point: str) -> None:
                    self._hit(_fault_point, f"payload.{relative_name}.{point}")

                payload_fault("before_write")
                with path.open("rb") as reader, target.open("wb") as writer:
                    injected_during_write = False
                    for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                        digest.update(chunk)
                        if _fault_point is not None and not injected_during_write and chunk:
                            split_at = max(1, len(chunk) // 2)
                            writer.write(chunk[:split_at])
                            payload_fault("during_write")
                            writer.write(chunk[split_at:])
                            injected_during_write = True
                        else:
                            writer.write(chunk)
                    writer.flush()
                    payload_fault("before_file_fsync")
                    os.fsync(writer.fileno())
                    payload_fault("after_file_fsync")
                payload_fault("before_dir_fsync")
                sync_directory(target.parent)
                payload_fault("after_dir_fsync")
                digests[relative_name] = digest.hexdigest()
            for raw_name, value in sorted(extras.items()):
                relative = self._safe_relative_path(raw_name)
                if relative.as_posix() in digests:
                    raise ValueError(f"extra file collides with a copied path: {raw_name!r}")
                data = value.encode("utf-8") if isinstance(value, str) else bytes(value)
                target = tmp_dir.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                durable_atomic_write(target, data, sync_dir=True)
                digests[relative.as_posix()] = self._digest(data)
            return digests

        return self._publish(index, write, _fault_point)

    def _publish(
        self,
        index: int,
        write: Callable[[Path], dict[str, str]],
        _fault_point: FaultHook | None,
    ) -> CommittedGeneration:
        name = self.generation_name(index)
        final_dir = self.root / name
        tmp_dir = Path(tempfile.mkdtemp(dir=self.root, prefix=f".{name}.", suffix=".tmp"))
        published = False
        try:
            digests = write(tmp_dir)

            marker = {
                "schema_version": 1,
                "generation": index,
                "files": digests,
            }
            durable_atomic_write_json(
                tmp_dir / self.COMPLETE,
                marker,
                sync_dir=True,
                indent=2,
            )
            sync_directory(tmp_dir)

            self._hit(_fault_point, "before_generation_publish")
            os.replace(tmp_dir, final_dir)
            sync_directory(self.root)
            published = True
            self._hit(_fault_point, "after_generation_publish")

            def current_fault(point: str) -> None:
                self._hit(_fault_point, f"current.{point}")

            durable_atomic_write(
                self.root / self.CURRENT,
                name + "\n",
                sync_dir=True,
                _fault_point=current_fault if _fault_point is not None else None,
            )
            self._hit(_fault_point, "after_current_publish")
            return self.open_current()
        except BaseException:
            if not published and tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
            raise

    def has_current(self) -> bool:
        return (self.root / self.CURRENT).is_file()

    def open_current(self) -> CommittedGeneration:
        current = self.root / self.CURRENT
        if not current.is_file():
            raise FileNotFoundError("no committed scientific generation")

        name = current.read_text(encoding="utf-8").strip()
        prefix = "generation-"
        if (
            not name.startswith(prefix)
            or len(name) != len(prefix) + 6
            or not name[len(prefix) :].isdigit()
        ):
            raise ValueError(f"invalid CURRENT generation reference: {name!r}")
        index = int(name[len(prefix) :])
        return self.open_generation(index)

    def open_generation(self, index: int) -> CommittedGeneration:
        name = self.generation_name(index)
        path = self.root / name
        marker_path = path / self.COMPLETE
        if not marker_path.is_file():
            raise ValueError(f"generation is not committed: {name}")

        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if marker.get("schema_version") != 1 or marker.get("generation") != index:
            raise ValueError(f"invalid COMPLETE marker for {name}")

        declared = marker.get("files")
        if not isinstance(declared, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in declared.items()
        ):
            raise ValueError(f"invalid file manifest for {name}")

        actual_files = {
            item.relative_to(path).as_posix()
            for item in path.rglob("*")
            if item.is_file() and item.name != self.COMPLETE
        }
        if actual_files != set(declared):
            raise ValueError(f"generation file set mismatch for {name}")

        for relative, expected_digest in declared.items():
            payload = path.joinpath(*PurePosixPath(relative).parts).read_bytes()
            if self._digest(payload) != expected_digest:
                raise ValueError(f"generation digest mismatch for {name}/{relative}")

        return CommittedGeneration(index=index, path=path, files=dict(declared))
