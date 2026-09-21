"""Private, semantic-free identity boundary for discovered signals."""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from functools import lru_cache

_DOMAIN = b"signal-knowledge-v1:"


@lru_cache(maxsize=1024)
def _compute_signal_id(key: bytes, capability_id: str) -> str:
    if not isinstance(capability_id, str) or not capability_id or any(c.isspace() for c in capability_id) or len(capability_id) > 512:
        raise ValueError("capability_id must be a non-empty bounded token")
    digest = hmac.new(key, _DOMAIN + capability_id.encode(), hashlib.sha256).hexdigest()
    return f"signal.{digest}"


@dataclass(frozen=True, slots=True)
class SignalIdentity:
    key: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.key, bytes) or len(self.key) != 32:
            raise ValueError("SignalIdentity key must be exactly 32 bytes")

    def signal_id(self, capability_id: str) -> str:
        return _compute_signal_id(self.key, capability_id)


@lru_cache(maxsize=4096)
def _compute_claim_id(subject_id: str, kind: str, object_id: str | None, horizon: int | None) -> str:
    if not isinstance(subject_id, str) or not subject_id.startswith("signal.") or len(subject_id) != 71:
        raise ValueError("subject_id must be an opaque signal token")
    if not isinstance(kind, str) or kind not in {"stability", "change", "synchronous_association", "lead_prediction", "self_relevance"}:
        raise ValueError("unknown claim kind")
    if object_id is not None and (not isinstance(object_id, str) or not object_id.startswith("signal.") or len(object_id) != 71):
        raise ValueError("object_id must be an opaque signal token")
    if horizon is not None and (isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1):
        raise ValueError("horizon must be a positive integer")
    raw = json.dumps([subject_id, kind, object_id, horizon], separators=(",", ":"), ensure_ascii=True).encode()
    return "claim." + hashlib.sha256(raw).hexdigest()


def claim_id(subject_id: str, kind: str, object_id: str | None, horizon: int | None) -> str:
    return _compute_claim_id(subject_id, kind, object_id, horizon)
