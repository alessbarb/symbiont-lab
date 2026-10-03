"""Consent-bound in-memory communication channel (v0.75)."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from .exchange import ExchangeEnvelope


@dataclass(frozen=True, slots=True)
class SignedMessage:
    sender: str
    recipient: str
    sequence: int
    payload: dict[str, str]
    signature: str


class ConsentBoundChannel:
    """Local transport; no sockets, discovery or implicit authorization."""

    def __init__(self, habitat_id: str, key: bytes) -> None:
        if not habitat_id or not key:
            raise ValueError("habitat and key are required")
        self.habitat_id = habitat_id
        self._key = bytes(key)
        self._consent: set[tuple[str, str]] = set()
        self._revoked = False

    def authorize(self, sender: str, recipient: str) -> None:
        if self._revoked or not sender or not recipient or sender == recipient:
            raise PermissionError("communication is not authorized")
        self._consent.add((sender, recipient))

    def revoke(self) -> None:
        self._revoked = True
        self._consent.clear()

    def send(self, envelope: ExchangeEnvelope, recipient: str) -> SignedMessage:
        if self._revoked or (envelope.sender, recipient) not in self._consent:
            raise PermissionError("communication consent is absent")
        encoded = envelope.encode()
        body = self.habitat_id.encode() + b"\0" + recipient.encode() + b"\0" + encoded
        signature = hmac.new(self._key, body, hashlib.sha256).hexdigest()
        return SignedMessage(
            envelope.sender, recipient, envelope.sequence, envelope.payload, signature
        )

    def verify(self, message: SignedMessage) -> bool:
        if self._revoked or (message.sender, message.recipient) not in self._consent:
            return False
        envelope = ExchangeEnvelope(message.sender, message.sequence, message.payload)
        body = (
            self.habitat_id.encode()
            + b"\0"
            + message.recipient.encode()
            + b"\0"
            + envelope.encode()
        )
        expected = hmac.new(self._key, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, message.signature)


__all__ = ["ConsentBoundChannel", "SignedMessage"]
