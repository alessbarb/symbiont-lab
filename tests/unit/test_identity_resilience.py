from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from symbiont.core.capsule import CapsuleKeyPair

from symbiont_lab.cli.capsule import _load_or_create_keypair


def test_capsule_keypair_public_key_fingerprint() -> None:
    kp = CapsuleKeyPair.generate()
    fp = kp.public_key_fingerprint
    import hashlib

    expected = hashlib.sha256(kp.public_bytes).hexdigest()
    assert fp == expected
    assert len(fp) == 64


def test_cli_capsule_load_existing_valid_key(tmp_path: Path) -> None:
    key_path = tmp_path / "valid.key"
    original = CapsuleKeyPair.generate()
    payload = json.dumps({"private_key": original.private_bytes.hex()})
    key_path.write_text(payload)

    loaded = _load_or_create_keypair(str(key_path))
    assert loaded.private_bytes == original.private_bytes
    assert loaded.public_bytes == original.public_bytes


def test_cli_capsule_creates_key_with_private_permissions(tmp_path: Path) -> None:
    key_path = tmp_path / "new.key"
    created = _load_or_create_keypair(str(key_path))
    assert key_path.is_file()

    mode = stat.S_IMODE(key_path.stat().st_mode)
    assert mode == 0o600

    data = json.loads(key_path.read_text(encoding="utf-8"))
    assert bytes.fromhex(data["private_key"]) == created.private_bytes


def test_cli_capsule_refuses_to_overwrite_corrupt_key(tmp_path: Path) -> None:
    key_path = tmp_path / "corrupt.key"
    key_path.write_text("corrupted-raw-bytes-not-json")

    with pytest.raises(ValueError, match="corrupt or unreadable"):
        _load_or_create_keypair(str(key_path))

    # Invariant: the corrupt file was NOT overwritten with a new key
    assert key_path.read_text() == "corrupted-raw-bytes-not-json"


def test_cli_capsule_refuses_to_overwrite_truncated_hex_key(tmp_path: Path) -> None:
    key_path = tmp_path / "truncated.key"
    key_path.write_text(json.dumps({"private_key": "1234deadbeef"}))  # Ed25519 requires 32 bytes

    with pytest.raises(ValueError, match="corrupt or unreadable"):
        _load_or_create_keypair(str(key_path))

    # Invariant: still truncated, never replaced
    assert json.loads(key_path.read_text())["private_key"] == "1234deadbeef"
