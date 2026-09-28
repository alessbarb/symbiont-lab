"""Revisioned anchor/delta protocol for passive live observation events."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping

DELTA_CONTRACT = "observer-live-delta-v1"
DEFAULT_ANCHOR_INTERVAL = 32
COMPRESSIBLE_TYPES = frozenset(
    {"body", "cognition", "vitals", "mind_snapshot", "observed_frame"}
)


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
    return _canonical_bytes(left) == _canonical_bytes(right)


def _diff(previous: Any, current: Any, path: str = "") -> list[dict[str, Any]]:
    if _equal(previous, current):
        return []
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
    # Live transport deliberately replaces changed arrays atomically. This keeps
    # the browser patcher small and deterministic while still compacting stable
    # object structure aggressively.
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
                "state_sha256": state_hash(current),
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


__all__ = [
    "COMPRESSIBLE_TYPES",
    "DEFAULT_ANCHOR_INTERVAL",
    "DELTA_CONTRACT",
    "ObservationDeltaEncoder",
    "state_hash",
]
