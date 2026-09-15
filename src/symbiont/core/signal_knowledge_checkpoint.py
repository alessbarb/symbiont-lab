"""Atomic validation boundary for the private signal-knowledge block."""
from __future__ import annotations

import json
from typing import Any

from .signal_knowledge import MAX_KNOWLEDGE_CHECKPOINT_BYTES, SignalKnowledgeEngine


def validate_checkpoint(payload: Any) -> dict[str, Any]:
    """Validate and copy a knowledge checkpoint without mutating its source."""
    if not isinstance(payload, dict):
        raise ValueError("signal knowledge checkpoint must be an object")
    if set(payload) - {"schema_version", "last_tick", "profiles"}:
        raise ValueError("unknown signal knowledge checkpoint fields")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > MAX_KNOWLEDGE_CHECKPOINT_BYTES:
        raise ValueError("signal knowledge checkpoint exceeds 256 KiB")
    # from_checkpoint performs structural and semantic validation into a new
    # engine; re-encoding its result gives callers a normalized safe copy.
    engine = SignalKnowledgeEngine.from_checkpoint(payload)
    return engine.checkpoint()


__all__ = ["validate_checkpoint"]
