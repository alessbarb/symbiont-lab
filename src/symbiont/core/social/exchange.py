"""Offline, bounded knowledge exchange envelopes (v0.72)."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


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
        raw = json.dumps({"sender": self.sender, "sequence": self.sequence, "payload": self.payload}, sort_keys=True, separators=(",", ":")).encode()
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


__all__ = ["MAX_EXCHANGE_BYTES", "ExchangeEnvelope", "ExchangeReplayGuard"]
