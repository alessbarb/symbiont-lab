from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Iterable


def compute_world_digest(events: Iterable[Any]) -> str:
    """Compute a deterministic SHA-256 hash of an exogenous event stream to
    verify two simulated worlds are actually identical.

    Includes the full exogenous event: step, host, truth label, threat flag,
    phase, drift state and the agent's observation vector (roadmap safety
    finding A01). Earlier this hashed only step/host_index/truth_label/
    is_threat — two worlds that differed only in their observations (e.g.
    different drift magnitude) produced the *same* digest despite the
    agent seeing materially different data every step. Never includes
    anything the agent itself decided — this stays evaluator/world-side.
    """
    h = sha256()
    for ev in events:
        if hasattr(ev, "step") and hasattr(ev, "host_index") and hasattr(ev, "truth_label"):
            observation = getattr(ev, "observation", None)
            vector = (
                observation.vector()
                if observation is not None and hasattr(observation, "vector")
                else ()
            )
            values = ",".join(repr(float(value)) for value in vector)
            phase = getattr(ev, "phase", "")
            drift_state = getattr(ev, "drift_state", "")
            chunk = (
                f"{ev.step}:{ev.host_index}:{ev.truth_label}:{ev.is_threat}:{phase}:{drift_state}:{values}\n"
            ).encode("utf-8")
        else:
            chunk = str(ev).encode("utf-8")
        h.update(chunk)
    return h.hexdigest()


def compute_config_digest(config: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of configuration dictionary."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()
