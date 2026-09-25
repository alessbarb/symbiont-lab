"""Lossless JSON-tree compaction primitives for Physics3D telemetry v4."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def payload_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _escape_pointer_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _unescape_pointer_segment(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def join_pointer(path: str, segment: str | int) -> str:
    encoded = _escape_pointer_segment(str(segment))
    return f"{path}/{encoded}" if path else f"/{encoded}"


def split_pointer(path: str) -> list[str]:
    if path == "":
        return []
    if not path.startswith("/"):
        raise ValueError(f"invalid JSON pointer: {path!r}")
    return [_unescape_pointer_segment(item) for item in path[1:].split("/")]


def _exact_equal(left: Any, right: Any) -> bool:
    """JSON-level equality, including distinctions such as 0.0 versus -0.0."""
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if set(left) != set(right):
            return False
        return all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, float):
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    return left == right


class ObjectStore:
    """Content-addressed store for immutable JSON subtrees."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid sha256 digest")
        return self.root / digest[:2] / f"{digest}.json"

    def put(self, payload: Any) -> tuple[str, bool]:
        digest = payload_sha256(payload)
        target = self.path_for(digest)
        if target.is_file():
            return digest, False
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=f".{digest}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(canonical_json_bytes(payload))
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temporary, target)
            except FileExistsError:
                pass
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return digest, True

    def get(self, digest: str) -> Any:
        target = self.path_for(digest)
        if not target.is_file():
            raise FileNotFoundError(f"telemetry object not found: {digest}")
        payload = json.loads(target.read_text(encoding="utf-8"))
        actual = payload_sha256(payload)
        if actual != digest:
            raise ValueError(f"telemetry object hash mismatch: {digest} != {actual}")
        return payload

    def verify(self, digest: str) -> bool:
        self.get(digest)
        return True


class CompactionPolicy:
    """Storage-only policy deciding which changed subtrees become CAS objects."""

    DEFAULT_REFERENCE_PATHS = frozenset(
        {
            "/observer_semantics",
            "/cognitive_topology",
            "/body_schema",
            "/self_model",
            "/sensorimotor/motor_primitives",
        }
    )

    def __init__(
        self,
        *,
        reference_paths: Iterable[str] | None = None,
        minimum_reference_bytes: int = 512,
    ) -> None:
        if minimum_reference_bytes < 1:
            raise ValueError("minimum_reference_bytes must be >= 1")
        self.reference_paths = frozenset(
            reference_paths if reference_paths is not None else self.DEFAULT_REFERENCE_PATHS
        )
        self.minimum_reference_bytes = int(minimum_reference_bytes)

    def should_reference(self, path: str, value: Any) -> bool:
        return (
            path in self.reference_paths
            and isinstance(value, (dict, list))
            and len(canonical_json_bytes(value)) >= self.minimum_reference_bytes
        )


class StateDiffer:
    """Produce deterministic exact patches between JSON-compatible trees."""

    def __init__(
        self,
        *,
        object_store: ObjectStore | None = None,
        policy: CompactionPolicy | None = None,
    ) -> None:
        self.object_store = object_store
        self.policy = policy or CompactionPolicy()

    def diff(self, previous: Any, current: Any) -> list[dict[str, Any]]:
        operations: list[dict[str, Any]] = []
        self._diff(previous, current, "", operations)
        return operations

    def _replacement(
        self,
        path: str,
        current: Any,
        operations: list[dict[str, Any]],
    ) -> None:
        if self.object_store is not None and self.policy.should_reference(path, current):
            digest, _created = self.object_store.put(current)
            operations.append({"op": "ref", "path": path, "sha256": digest})
        else:
            operations.append({"op": "set", "path": path, "value": deepcopy(current)})

    def _diff(
        self,
        previous: Any,
        current: Any,
        path: str,
        operations: list[dict[str, Any]],
    ) -> None:
        if _exact_equal(previous, current):
            return

        if self.object_store is not None and self.policy.should_reference(path, current):
            self._replacement(path, current, operations)
            return

        if isinstance(previous, Mapping) and isinstance(current, Mapping):
            previous_keys = set(previous)
            current_keys = set(current)
            for key in sorted(previous_keys - current_keys, key=str):
                operations.append({"op": "remove", "path": join_pointer(path, str(key))})
            for key in sorted(current_keys - previous_keys, key=str):
                child_path = join_pointer(path, str(key))
                self._replacement(child_path, current[key], operations)
            for key in sorted(previous_keys & current_keys, key=str):
                self._diff(
                    previous[key],
                    current[key],
                    join_pointer(path, str(key)),
                    operations,
                )
            return

        if isinstance(previous, list) and isinstance(current, list):
            if len(previous) != len(current):
                self._replacement(path, current, operations)
                return
            for index, (before, after) in enumerate(zip(previous, current)):
                self._diff(before, after, join_pointer(path, index), operations)
            return

        self._replacement(path, current, operations)


class StatePatcher:
    """Apply StateDiffer patches without arithmetic or precision loss."""

    def __init__(self, *, object_store: ObjectStore | None = None) -> None:
        self.object_store = object_store

    def apply(self, state: Any, operations: Iterable[Mapping[str, Any]]) -> Any:
        result = deepcopy(state)
        for raw in operations:
            operation = dict(raw)
            op = operation.get("op")
            path = str(operation.get("path", ""))
            if op == "set":
                value = deepcopy(operation.get("value"))
            elif op == "ref":
                if self.object_store is None:
                    raise ValueError("cannot resolve ref without object store")
                digest = operation.get("sha256")
                if not isinstance(digest, str):
                    raise ValueError("ref operation missing sha256")
                value = self.object_store.get(digest)
            elif op == "remove":
                result = self._remove(result, path)
                continue
            else:
                raise ValueError(f"unsupported telemetry patch operation: {op!r}")
            result = self._set(result, path, value)
        return result

    @staticmethod
    def _resolve_parent(state: Any, path: str) -> tuple[Any, str]:
        parts = split_pointer(path)
        if not parts:
            raise ValueError("root pointer has no parent")
        parent = state
        for segment in parts[:-1]:
            if isinstance(parent, list):
                try:
                    index = int(segment)
                except ValueError as exc:
                    raise ValueError(f"list path segment is not an index: {segment!r}") from exc
                parent = parent[index]
            elif isinstance(parent, dict):
                parent = parent[segment]
            else:
                raise ValueError(f"cannot descend through scalar at {path!r}")
        return parent, parts[-1]

    def _set(self, state: Any, path: str, value: Any) -> Any:
        if path == "":
            return deepcopy(value)
        parent, leaf = self._resolve_parent(state, path)
        if isinstance(parent, list):
            try:
                index = int(leaf)
            except ValueError as exc:
                raise ValueError(f"list path segment is not an index: {leaf!r}") from exc
            if index < 0 or index >= len(parent):
                raise IndexError(f"telemetry list patch index out of range: {index}")
            parent[index] = deepcopy(value)
        elif isinstance(parent, dict):
            parent[leaf] = deepcopy(value)
        else:
            raise ValueError(f"cannot set child on scalar at {path!r}")
        return state

    def _remove(self, state: Any, path: str) -> Any:
        if path == "":
            return None
        parent, leaf = self._resolve_parent(state, path)
        if isinstance(parent, list):
            try:
                index = int(leaf)
            except ValueError as exc:
                raise ValueError(f"list path segment is not an index: {leaf!r}") from exc
            del parent[index]
        elif isinstance(parent, dict):
            if leaf not in parent:
                raise KeyError(f"telemetry remove target missing: {path}")
            del parent[leaf]
        else:
            raise ValueError(f"cannot remove child from scalar at {path!r}")
        return state


__all__ = [
    "CompactionPolicy",
    "ObjectStore",
    "StateDiffer",
    "StatePatcher",
    "canonical_json_bytes",
    "join_pointer",
    "payload_sha256",
    "split_pointer",
]
