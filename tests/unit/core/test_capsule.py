from __future__ import annotations

import dataclasses

from symbiont.core.capsule import (
    CAPSULE_SCHEMA_VERSION,
    CapsuleKeyPair,
    KnowledgeCapsule,
    create_capsule,
    verify_capsule,
)


def test_keypair_generates_32_byte_ed25519_keys():
    keypair = CapsuleKeyPair.generate()
    assert len(keypair.private_bytes) == 32
    assert len(keypair.public_bytes) == 32


def test_keypair_round_trips_through_private_bytes():
    keypair = CapsuleKeyPair.generate()
    restored = CapsuleKeyPair.from_private_bytes(keypair.private_bytes)
    assert restored.public_bytes == keypair.public_bytes


def test_two_generated_keypairs_are_different():
    a = CapsuleKeyPair.generate()
    b = CapsuleKeyPair.generate()
    assert a.public_bytes != b.public_bytes


def test_create_capsule_is_valid():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"hello": "world", "count": 5})

    assert capsule.schema_version == CAPSULE_SCHEMA_VERSION
    assert capsule.signer_public_key == keypair.public_bytes
    assert verify_capsule(capsule)


def test_capsule_round_trips_through_dict():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"a": 1, "b": [1, 2, 3]})

    restored = KnowledgeCapsule.from_dict(capsule.to_dict())

    assert restored == capsule
    assert verify_capsule(restored)


def test_tampered_payload_fails_verification():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"count": 5})

    tampered = dataclasses.replace(capsule, payload={"count": 999})

    assert not verify_capsule(tampered)


def test_wrong_signer_public_key_fails_verification():
    keypair = CapsuleKeyPair.generate()
    other = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"count": 5})

    wrong_signer = dataclasses.replace(capsule, signer_public_key=other.public_bytes)

    assert not verify_capsule(wrong_signer)


def test_tampered_signature_fails_verification():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"count": 5})

    corrupted = dataclasses.replace(capsule, signature=b"\x00" * len(capsule.signature))

    assert not verify_capsule(corrupted)


def test_unknown_schema_version_is_rejected_without_raising():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"count": 5})

    future_version = dataclasses.replace(capsule, schema_version=CAPSULE_SCHEMA_VERSION + 1)

    assert not verify_capsule(future_version)


def test_malformed_public_key_bytes_do_not_raise():
    keypair = CapsuleKeyPair.generate()
    capsule = create_capsule(keypair, {"count": 5})

    malformed = dataclasses.replace(capsule, signer_public_key=b"too short")

    assert not verify_capsule(malformed)


def test_payload_order_does_not_affect_signature_validity():
    """Deterministic canonical encoding: two dicts with the same content but
    different insertion order must verify identically."""
    keypair = CapsuleKeyPair.generate()
    capsule_a = create_capsule(keypair, {"a": 1, "b": 2})
    capsule_b = create_capsule(keypair, {"b": 2, "a": 1})

    assert capsule_a.signature == capsule_b.signature


def test_public_key_is_not_derived_from_any_host_identity_string():
    """Identity-minimization sanity check: the public key is just random
    bytes, not a hash of hostname/user/etc. Best we can assert here is that
    it is not trivially reproducible/predictable across independent runs."""
    keys = {CapsuleKeyPair.generate().public_bytes for _ in range(5)}
    assert len(keys) == 5
