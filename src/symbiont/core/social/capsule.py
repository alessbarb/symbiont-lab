from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

CAPSULE_SCHEMA_VERSION = 1


class CapsuleKeyPair:
    """A local Ed25519 signing identity for knowledge capsules (roadmap
    v0.42).

    Deliberately **not** derived from anything about the host: the private
    key is freshly generated random bytes, and the public key — the only
    part ever shared — is an opaque, unlinkable token with no relationship
    to hostname, user or any other real identity. It is not authorized
    real-world identity, only a way for a *recipient* to tell "the same
    signer as last time" from "a different signer", and to detect tampering
    — the identity-minimization the roadmap asks for. Rotating identity is
    just generating a new keypair; nothing here persists automatically.
    """

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key

    @classmethod
    def generate(cls) -> "CapsuleKeyPair":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_private_bytes(cls, raw: bytes) -> "CapsuleKeyPair":
        return cls(Ed25519PrivateKey.from_private_bytes(raw))

    @property
    def private_bytes(self) -> bytes:
        return self._private_key.private_bytes_raw()

    @property
    def public_bytes(self) -> bytes:
        return self._private_key.public_key().public_bytes_raw()

    def sign(self, message: bytes) -> bytes:
        return self._private_key.sign(message)


@dataclass(slots=True, frozen=True)
class KnowledgeCapsule:
    """A signed, identity-minimized, offline unit of abstract knowledge
    (roadmap v0.42).

    ``payload`` is expected to already be safe-to-share abstract state —
    e.g. a v0.37 :func:`~symbiont.host.checkpoint.export_checkpoint`
    document — this module does not itself decide what is safe to put in a
    capsule, only that the capsule is tamper-evident and attributable to a
    consistent (if pseudonymous) signer. There is no transport here: a
    capsule is just bytes a human moves between machines by whatever offline
    means they choose (roadmap v0.45 is where transport itself — explicit,
    consent-bound, revocable — becomes in scope, gated on its own decision).
    """

    schema_version: int
    signer_public_key: bytes
    payload: dict[str, Any]
    signature: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "signer_public_key": self.signer_public_key.hex(),
            "payload": self.payload,
            "signature": self.signature.hex(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeCapsule":
        return cls(
            schema_version=data["schema_version"],
            signer_public_key=bytes.fromhex(data["signer_public_key"]),
            payload=data["payload"],
            signature=bytes.fromhex(data["signature"]),
        )


def _canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    """Deterministic byte encoding a signature is computed and verified
    over — sorted keys, no whitespace ambiguity, so the same payload always
    signs identically regardless of dict insertion order."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_capsule(keypair: CapsuleKeyPair, payload: dict[str, Any]) -> KnowledgeCapsule:
    """Sign ``payload`` and wrap it into a :class:`KnowledgeCapsule`."""
    signature = keypair.sign(_canonical_payload_bytes(payload))
    return KnowledgeCapsule(
        schema_version=CAPSULE_SCHEMA_VERSION,
        signer_public_key=keypair.public_bytes,
        payload=payload,
        signature=signature,
    )


def verify_capsule(capsule: KnowledgeCapsule) -> bool:
    """Verify a capsule's signature against its own claimed public key.

    Never raises — a malformed or forged capsule is external, untrusted
    input; the only thing this function ever produces is ``True``/``False``.
    A schema version this code doesn't recognize is treated as unverifiable
    rather than guessed at.
    """
    if capsule.schema_version != CAPSULE_SCHEMA_VERSION:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(capsule.signer_public_key)
        public_key.verify(capsule.signature, _canonical_payload_bytes(capsule.payload))
    except (InvalidSignature, ValueError):
        return False
    return True
