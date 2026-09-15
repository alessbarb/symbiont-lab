from __future__ import annotations

from collections.abc import Collection, Mapping
from hashlib import sha256
import math
from typing import Any

COGNITIVE_SELF_OBSERVATION_VERSION = 1
MAX_COGNITIVE_CHANNELS_PER_TICK = 32
_ACTIVITY_THRESHOLD = 0.1
_ACTIVITY_CLASSES = 16


def _channel_id(node_id: str) -> str:
    """Domain-separated opaque token for one internal activation channel.

    This token is an organism-internal evidence handle, not observer identity.
    It never crosses BodySchema.export_representation(). The public region id
    is separately salted per organism by BodySchemaEngine.
    """
    digest = sha256(f"symbiont-cognitive-self:{node_id}".encode("utf-8")).hexdigest()[:32]
    return f"channel.cognition.{digest}"


def _activity_class(value: float) -> int:
    magnitude = min(1.0, abs(float(value)))
    return max(1, min(_ACTIVITY_CLASSES - 1, round(magnitude * (_ACTIVITY_CLASSES - 1))))


def project_cognitive_self_observation(
    activations: Mapping[str, float],
    *,
    sensory_ids: Collection[str],
) -> dict[str, Any]:
    """Project dynamic cognition into bounded opaque evidence for BodySchema.

    The projector deliberately receives activation state rather than graph
    topology. A node that merely exists is not self-evidence. Known sensory
    channels are excluded before hashing so PR6 learns only coarse internal
    cognitive organization.
    """
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
        token = _channel_id(raw_id)
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
    "project_cognitive_self_observation",
]
