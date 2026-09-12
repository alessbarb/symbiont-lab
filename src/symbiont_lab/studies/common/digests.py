from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable


def compute_world_digest(events: Iterable[Any]) -> str:
    """Compute deterministic SHA-256 hash of event stream to verify identical worlds."""
    h = sha256()
    for ev in events:
        if hasattr(ev, "step") and hasattr(ev, "host_index") and hasattr(ev, "truth_label"):
            chunk = f"{ev.step}:{ev.host_index}:{ev.truth_label}:{ev.is_threat}\n".encode("utf-8")
        else:
            chunk = str(ev).encode("utf-8")
        h.update(chunk)
    return h.hexdigest()


def compute_config_digest(config: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of configuration dictionary."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()
