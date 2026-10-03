from __future__ import annotations

import math
from collections.abc import Collection, Mapping
from hashlib import sha256
from typing import Any

from ..foundation.limits import OrganismLimits

COGNITIVE_SELF_OBSERVATION_VERSION = 1
MAX_COGNITIVE_CHANNELS_PER_TICK = OrganismLimits().max_cognitive_channels_per_tick
_ACTIVITY_THRESHOLD = 0.1
_ACTIVITY_CLASSES = 16
_NAMESPACE_KEY_HEX_LENGTH = 64
_PRIVATE_SALT_HEX_LENGTH = 32


def _is_lower_hex(value: str, *, length: int) -> bool:
    return len(value) == length and all(char in "0123456789abcdef" for char in value)


def derive_cognitive_self_namespace(private_id_salt: str) -> str:
    """Derive an organism-local cognitive namespace from BodySchema identity.

    The returned key is used only inside the organism to tokenize activation
    channels. Neither it nor the private BodySchema salt is part of the public
    self representation.
    """
    if not isinstance(private_id_salt, str) or not _is_lower_hex(
        private_id_salt, length=_PRIVATE_SALT_HEX_LENGTH
    ):
        raise ValueError("private_id_salt must be 32 lowercase hex characters")
    return sha256(
        f"symbiont-cognitive-self-namespace:{private_id_salt}".encode("utf-8")
    ).hexdigest()


def _channel_id(namespace_key: str, node_id: str) -> str:
    """Return an organism-local opaque token for one internal activation channel."""
    digest = sha256(
        f"symbiont-cognitive-self:{namespace_key}:{node_id}".encode("utf-8")
    ).hexdigest()[:32]
    return f"channel.cognition.{digest}"


def _activity_class(value: float) -> int:
    magnitude = min(1.0, abs(float(value)))
    return max(1, min(_ACTIVITY_CLASSES - 1, round(magnitude * (_ACTIVITY_CLASSES - 1))))


def project_cognitive_self_observation(
    activations: Mapping[str, float],
    *,
    sensory_ids: Collection[str],
    namespace_key: str,
) -> dict[str, Any]:
    """Project dynamic cognition into bounded opaque evidence for BodySchema.

    The projector deliberately receives activation state rather than graph
    topology. A node that merely exists is not self-evidence. Known sensory
    channels are excluded before hashing so PR6 learns only coarse internal
    cognitive organization.
    """
    if not isinstance(namespace_key, str) or not _is_lower_hex(
        namespace_key, length=_NAMESPACE_KEY_HEX_LENGTH
    ):
        raise ValueError("cognitive self namespace_key must be 64 lowercase hex characters")

    sensory = set(sensory_ids)
    candidates: list[tuple[int, str]] = []
    for raw_id, raw_value in activations.items():
        if not isinstance(raw_id, str) or not raw_id or raw_id in sensory:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or abs(value) < _ACTIVITY_THRESHOLD:
            continue
        token = _channel_id(namespace_key, raw_id)
        candidates.append((_activity_class(value), token))

    # Strongest activity wins the observation budget. Token order is the
    # deterministic tie-breaker and reveals no implementation node name.
    candidates.sort(key=lambda item: (-item[0], item[1]))
    channels = [
        {"channel_id": token, "activity_class": activity_class}
        for activity_class, token in candidates[:MAX_COGNITIVE_CHANNELS_PER_TICK]
    ]
    return {
        "schema_version": COGNITIVE_SELF_OBSERVATION_VERSION,
        "channels": channels,
    }


__all__ = [
    "COGNITIVE_SELF_OBSERVATION_VERSION",
    "MAX_COGNITIVE_CHANNELS_PER_TICK",
    "derive_cognitive_self_namespace",
    "project_cognitive_self_observation",
]
