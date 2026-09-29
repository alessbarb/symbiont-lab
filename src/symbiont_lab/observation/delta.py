"""Revisioned anchor/delta protocol for passive live observation events."""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any, Mapping

DELTA_CONTRACT = "observer-live-delta-v1"
DEFAULT_ANCHOR_INTERVAL = 32
COMPRESSIBLE_TYPES = frozenset({"body", "cognition", "vitals", "mind_snapshot", "observed_frame"})


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def state_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _join(path: str, segment: str) -> str:
    escaped = str(segment).replace("~", "~0").replace("/", "~1")
    return f"{path}/{escaped}" if path else f"/{escaped}"


def _equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        return set(left) == set(right) and all(_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, float):
        if left == 0.0 and right == 0.0:
            return math.copysign(1.0, left) == math.copysign(1.0, right)
        return left == right
    return left == right


def _diff(previous: Any, current: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(previous, Mapping) and isinstance(current, Mapping):
        operations: list[dict[str, Any]] = []
        before = set(previous)
        after = set(current)
        for key in sorted(before - after, key=str):
            operations.append({"op": "remove", "path": _join(path, str(key))})
        for key in sorted(after - before, key=str):
            operations.append(
                {"op": "set", "path": _join(path, str(key)), "value": deepcopy(current[key])}
            )
        for key in sorted(before & after, key=str):
            operations.extend(_diff(previous[key], current[key], _join(path, str(key))))
        return operations

    if isinstance(previous, list) and isinstance(current, list):
        if _equal(previous, current):
            return []
        # Live transport deliberately replaces changed arrays atomically. This
        # keeps the browser patcher small and deterministic.
        return [{"op": "set", "path": path, "value": deepcopy(current)}]

    if _equal(previous, current):
        return []
    return [{"op": "set", "path": path, "value": deepcopy(current)}]


class ObservationDeltaEncoder:
    """Materialize channels server-side and emit periodic anchors plus deltas."""

    def __init__(self, *, anchor_interval: int = DEFAULT_ANCHOR_INTERVAL) -> None:
        if anchor_interval < 1:
            raise ValueError("anchor_interval must be >= 1")
        self.anchor_interval = int(anchor_interval)
        self._states: dict[str, dict[str, Any]] = {}
        self._revisions: dict[str, int] = {}
        self._since_anchor: dict[str, int] = {}

    def encode(self, event: Mapping[str, Any]) -> dict[str, Any]:
        current = deepcopy(dict(event))
        channel = str(current.get("type") or "")
        if channel not in COMPRESSIBLE_TYPES:
            return current

        previous = self._states.get(channel)
        revision = self._revisions.get(channel, 0) + 1
        force_anchor = (
            previous is None
            or self._since_anchor.get(channel, self.anchor_interval) >= self.anchor_interval
        )
        if force_anchor:
            encoded = self._anchor(channel, current, revision)
            self._since_anchor[channel] = 0
        else:
            operations = _diff(previous, current)
            encoded = {
                "type": "observation_delta",
                "contract": DELTA_CONTRACT,
                "channel": channel,
                "kind": "delta",
                "revision": revision,
                "base_revision": revision - 1,
                "patch": operations,
            }
            self._since_anchor[channel] = self._since_anchor.get(channel, 0) + 1

        self._states[channel] = current
        self._revisions[channel] = revision
        return encoded

    def anchor(self, channel: str) -> dict[str, Any] | None:
        state = self._states.get(str(channel))
        if state is None:
            return None
        revision = self._revisions[str(channel)]
        return self._anchor(str(channel), state, revision)

    def anchors(self) -> list[dict[str, Any]]:
        return [
            self._anchor(channel, self._states[channel], self._revisions[channel])
            for channel in sorted(self._states)
        ]

    @staticmethod
    def _anchor(channel: str, state: Mapping[str, Any], revision: int) -> dict[str, Any]:
        materialized = deepcopy(dict(state))
        return {
            "type": "observation_delta",
            "contract": DELTA_CONTRACT,
            "channel": channel,
            "kind": "anchor",
            "revision": int(revision),
            "state": materialized,
            "state_sha256": state_hash(materialized),
        }


def _split(path: str) -> list[str]:
    if path == "":
        return []
    if not path.startswith("/"):
        raise ValueError(f"invalid observation delta pointer: {path!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _apply(state: Any, operations: list[Mapping[str, Any]]) -> Any:
    result = deepcopy(state)
    for raw in operations:
        operation = dict(raw)
        op = operation.get("op")
        path = str(operation.get("path", ""))
        if op == "set" and path == "":
            result = deepcopy(operation.get("value"))
            continue
        if op == "remove" and path == "":
            result = None
            continue
        parts = _split(path)
        if not parts:
            raise ValueError("observation delta path has no target")
        parent = result
        for segment in parts[:-1]:
            if isinstance(parent, list):
                parent = parent[int(segment)]
            elif isinstance(parent, dict):
                parent = parent[segment]
            else:
                raise ValueError("observation delta descends through scalar")
        leaf = parts[-1]
        if op == "set":
            value = deepcopy(operation.get("value"))
            if isinstance(parent, list):
                parent[int(leaf)] = value
            elif isinstance(parent, dict):
                parent[leaf] = value
            else:
                raise ValueError("observation delta cannot set child on scalar")
        elif op == "remove":
            if isinstance(parent, list):
                del parent[int(leaf)]
            elif isinstance(parent, dict):
                del parent[leaf]
            else:
                raise ValueError("observation delta cannot remove child from scalar")
        else:
            raise ValueError(f"unsupported observation delta operation: {op!r}")
    return result


class ObservationDeltaDecoder:
    """Reference decoder used by tests and non-browser observer consumers."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}
        self._revisions: dict[str, int] = {}

    def decode(self, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        event = dict(payload)
        if event.get("type") != "observation_delta":
            return event
        if event.get("contract") != DELTA_CONTRACT:
            return None
        channel = str(event.get("channel") or "")
        revision = int(event.get("revision") or 0)
        if event.get("kind") == "anchor":
            state = deepcopy(event.get("state"))
            if not isinstance(state, dict) or state.get("type") != channel:
                return None
            if state_hash(state) != event.get("state_sha256"):
                raise ValueError("observation anchor hash mismatch")
            self._states[channel] = state
            self._revisions[channel] = revision
            return deepcopy(state)
        if event.get("kind") != "delta":
            return None
        if self._revisions.get(channel) != int(event.get("base_revision") or -1):
            return None
        state = _apply(self._states[channel], list(event.get("patch") or ()))
        if not isinstance(state, dict) or state.get("type") != channel:
            raise ValueError("observation delta changed channel identity")
        self._states[channel] = state
        self._revisions[channel] = revision
        return deepcopy(state)


__all__ = [
    "COMPRESSIBLE_TYPES",
    "DEFAULT_ANCHOR_INTERVAL",
    "DELTA_CONTRACT",
    "ObservationDeltaDecoder",
    "ObservationDeltaEncoder",
    "state_hash",
]
