from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any

from .capsule import CapsuleKeyPair, KnowledgeCapsule, create_capsule, verify_capsule


class LocalHabitat:
    """Bounded, atomic local filesystem habitat for resident organisms.

    Enables:
    1. Capsule Mailbox:
       - publish_capsule: atomic write via temporary file + os.replace.
       - poll_capsules: read, parse, verify Ed25519 signatures, filter expired.
       - circular retention: keeps at most max_capsules, evicts expired by TTL.
    2. Incubation & Birth:
       - deposit_embryo: atomic write of germinal child checkpoint to incubator/
       - count_incubated: pending embryo queue size.
    """

    def __init__(
        self,
        base_dir: str | Path,
        *,
        max_capsules: int = 50,
        ttl_seconds: float = 300.0,
    ) -> None:
        self.base_dir = Path(base_dir).expanduser()
        self.capsules_dir = self.base_dir / "capsules"
        self.incubator_dir = self.base_dir / "incubator"
        self.max_capsules = max_capsules
        self.ttl_seconds = ttl_seconds

        self.capsules_dir.mkdir(parents=True, exist_ok=True)
        self.incubator_dir.mkdir(parents=True, exist_ok=True)

    def publish_capsule(self, capsule: KnowledgeCapsule) -> Path | None:
        """Publish a verified capsule to the local mailbox atomically."""
        if not verify_capsule(capsule):
            return None
        self._prune_capsules()
        capsule_id = f"cap_{time.time_ns()}_{capsule.signer_public_key[:8].hex()}"
        target = self.capsules_dir / f"{capsule_id}.json"
        tmp = self.capsules_dir / f"{capsule_id}.tmp"
        try:
            tmp.write_text(json.dumps(capsule.to_dict()), encoding="utf-8")
            os.replace(tmp, target)
            self._prune_capsules()
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return target

    def poll_capsules(
        self,
        *,
        exclude_signer: bytes | None = None,
        max_results: int = 20,
    ) -> list[KnowledgeCapsule]:
        """Retrieve recent verified capsules from other organisms."""
        self._prune_capsules()
        capsules: list[KnowledgeCapsule] = []
        try:
            files = sorted(
                self.capsules_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return []

        for path in files[:max_results]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cap = KnowledgeCapsule.from_dict(data)
                if exclude_signer is not None and cap.signer_public_key == exclude_signer:
                    continue
                if verify_capsule(cap):
                    capsules.append(cap)
            except (OSError, json.JSONDecodeError, KeyError, ValueError):
                continue
        return capsules

    def _prune_capsules(self) -> None:
        """Evict expired capsules and enforce capacity bound."""
        now = time.time()
        try:
            files = sorted(self.capsules_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
            valid: list[Path] = []
            for p in files:
                try:
                    if now - p.stat().st_mtime > self.ttl_seconds:
                        p.unlink(missing_ok=True)
                    else:
                        valid.append(p)
                except OSError:
                    pass

            while len(valid) > self.max_capsules:
                oldest = valid.pop(0)
                try:
                    oldest.unlink(missing_ok=True)
                except OSError:
                    pass
        except OSError:
            pass

    def deposit_embryo(self, embryo_payload: dict[str, Any], child_id: str) -> Path | None:
        """Deposit an authorized child embryo in the incubator."""
        target = self.incubator_dir / f"{child_id}.json"
        tmp = self.incubator_dir / f"{child_id}.tmp"
        try:
            tmp.write_text(json.dumps(embryo_payload, indent=2), encoding="utf-8")
            os.replace(tmp, target)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return target

    def count_incubated(self) -> int:
        """Return the number of pending embryos awaiting launch."""
        try:
            return len(list(self.incubator_dir.glob("*.json")))
        except OSError:
            return 0
