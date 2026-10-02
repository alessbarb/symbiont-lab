"""Offline, bounded knowledge exchange envelopes (v0.72)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..foundation.limits import OrganismLimits

MAX_EXCHANGE_BYTES = OrganismLimits().max_exchange_bytes


@dataclass(frozen=True, slots=True)
class ExchangeEnvelope:
    sender: str
    sequence: int
    payload: dict[str, str]

    def encode(self) -> bytes:
        if not self.sender or self.sequence < 0 or any(not k for k in self.payload):
            raise ValueError("invalid exchange envelope")
        raw = json.dumps(
            {"sender": self.sender, "sequence": self.sequence, "payload": self.payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if len(raw) > MAX_EXCHANGE_BYTES:
            raise ValueError("exchange envelope exceeds bound")
        return raw

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.encode()).hexdigest()


class ExchangeReplayGuard:
    """Accept each sender sequence once; state is local and replayable offline."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def accept(self, envelope: ExchangeEnvelope) -> bool:
        envelope.encode()
        previous = self._seen.get(envelope.sender, -1)
        if envelope.sequence <= previous:
            return False
        self._seen[envelope.sender] = envelope.sequence
        return True

    def checkpoint(self) -> dict[str, int]:
        return dict(self._seen)

    @classmethod
    def restore(cls, payload: object) -> "ExchangeReplayGuard":
        """Rebuild the highest accepted sequence per sender from a checkpoint."""
        if not isinstance(payload, dict):
            raise ValueError("exchange guard checkpoint must be an object")
        guard = cls()
        for sender, sequence in payload.items():
            if not isinstance(sender, str) or not sender:
                raise ValueError("exchange guard sender must be a non-empty string")
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
                raise ValueError("exchange guard sequence must be a non-negative integer")
            guard._seen[sender] = sequence
        return guard


__all__ = ["MAX_EXCHANGE_BYTES", "ExchangeEnvelope", "ExchangeReplayGuard"]
