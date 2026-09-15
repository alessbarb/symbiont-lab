from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .selfmodel import RecencyClass

BODY_SCHEMA_VERSION = 1
MAX_BODY_PARTS = 256
_HEALTH_CLASSES = 16
_CONFIDENCE_CLASSES = 16
_COST_CLASSES = 16
_MATURITY_CLASSES = 8
_RECENCY_REPRESENTATIVE_IDLE_TICKS = {
    RecencyClass.CURRENT: 0,
    RecencyClass.SHORT_IDLE: 10,
    RecencyClass.IDLE: 40,
    RecencyClass.LONG_IDLE: 120,
    RecencyClass.DORMANT: 400,
}
_RECENCY_THRESHOLDS = (
    (10, RecencyClass.CURRENT),
    (40, RecencyClass.SHORT_IDLE),
    (120, RecencyClass.IDLE),
    (400, RecencyClass.LONG_IDLE),
)


def _part_id(sense_id: str) -> str:
    """Return a stable opaque body-part id without exposing a capability id."""
    digest = sha256(f"symbiont-body:sense:{sense_id}".encode("utf-8")).hexdigest()[:16]
    return f"part.sense.{digest}"


def _recency_class(idle_ticks: int) -> RecencyClass:
    for threshold, recency in _RECENCY_THRESHOLDS:
        if idle_ticks < threshold:
            return recency
    return RecencyClass.DORMANT


def _require_class(value: Any, count: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an int")
    if not 0 <= value < count:
        raise ValueError(f"{field_name} out of range [0, {count})")
    return value


@dataclass(slots=True)
class _SensoryPartState:
    part_id: str
    health_class: int
    confidence_class: int
    cost_class: int
    maturity_class: int
    last_evidence_tick: int

    @property
    def existence_confidence_class(self) -> int:
        # Maturity is evidence that this functional component persistently
        # belongs to the organism. Rescale its 8 classes onto the common
        # 16-class confidence vocabulary without inventing a new signal.
        return round((self.maturity_class / (_MATURITY_CLASSES - 1)) * (_CONFIDENCE_CLASSES - 1))


class BodySchemaEngine:
    """Bounded learned representation of the organism's sensory body.

    PR4 intentionally learns only SENSE parts. Evidence comes exclusively
    from ``SelfModel.export()``: no CognitiveGraph nodes, host manifest,
    provider metadata or runtime object identity are inspected here. That
    preserves the distinction between administrative truth and organism-
    owned self-knowledge.
    """

    def __init__(self) -> None:
        self._parts: dict[str, _SensoryPartState] = {}

    @property
    def state(self) -> str:
        return "partial" if self._parts else "undeveloped"

    @property
    def part_count(self) -> int:
        return len(self._parts)

    def observe_self_model(self, payload: dict[str, Any], *, tick: int) -> None:
        if tick < 0:
            raise ValueError("tick must be non-negative")
        if not isinstance(payload, dict):
            raise ValueError("self-model evidence must be a JSON object")
        if len(payload) > MAX_BODY_PARTS:
            raise ValueError(f"self-model evidence exceeds MAX_BODY_PARTS ({MAX_BODY_PARTS})")

        for sense_id, entry in sorted(payload.items()):
            if not isinstance(sense_id, str) or not sense_id:
                raise ValueError("self-model sense ids must be non-empty strings")
            if not isinstance(entry, dict):
                raise ValueError(f"self-model entry for {sense_id!r} must be a JSON object")
            health_class = _require_class(entry.get("health_class"), _HEALTH_CLASSES, "health_class")
            confidence_class = _require_class(
                entry.get("confidence_class"), _CONFIDENCE_CLASSES, "confidence_class"
            )
            cost_class = _require_class(entry.get("cost_class"), _COST_CLASSES, "cost_class")
            maturity_class = _require_class(entry.get("maturity_class"), _MATURITY_CLASSES, "maturity_class")
            _require_class(entry.get("recency_class"), len(RecencyClass), "recency_class")
            part_id = _part_id(sense_id)
            self._parts[part_id] = _SensoryPartState(
                part_id=part_id,
                health_class=health_class,
                confidence_class=confidence_class,
                cost_class=cost_class,
                maturity_class=maturity_class,
                last_evidence_tick=tick,
            )

    def export(self, *, current_tick: int) -> dict[str, Any]:
        if current_tick < 0:
            raise ValueError("current_tick must be non-negative")
        parts = []
        for part in sorted(self._parts.values(), key=lambda item: item.part_id):
            idle_ticks = max(0, current_tick - part.last_evidence_tick)
            parts.append(
                {
                    "part_id": part.part_id,
                    "kind": "sense",
                    "existence_confidence_class": part.existence_confidence_class,
                    "health_class": part.health_class,
                    "confidence_class": part.confidence_class,
                    "cost_class": part.cost_class,
                    "maturity_class": part.maturity_class,
                    "recency_class": _recency_class(idle_ticks).value,
                }
            )

        global_state: dict[str, int] = {}
        if parts:
            global_state = {
                "self_model_confidence_class": round(
                    sum(part["confidence_class"] for part in parts) / len(parts)
                ),
                "integrity_class": round(sum(part["health_class"] for part in parts) / len(parts)),
            }
        return {
            "schema_version": BODY_SCHEMA_VERSION,
            "state": self.state,
            "parts": parts,
            "dependencies": [],
            "global_state": global_state,
        }

    @classmethod
    def restore(cls, payload: dict[str, Any] | None, *, current_tick: int) -> "BodySchemaEngine":
        model = cls()
        if payload is None:
            return model
        if not isinstance(payload, dict):
            raise ValueError("body_schema payload must be a JSON object")
        if payload.get("schema_version") != BODY_SCHEMA_VERSION:
            raise ValueError(f"unsupported body_schema schema_version: {payload.get('schema_version')!r}")
        state = payload.get("state")
        if state not in ("undeveloped", "partial"):
            raise ValueError("body_schema state must be 'undeveloped' or 'partial' in sensory PR4")
        raw_parts = payload.get("parts")
        if not isinstance(raw_parts, list):
            raise ValueError("body_schema parts must be an array")
        if len(raw_parts) > MAX_BODY_PARTS:
            raise ValueError(f"body_schema parts exceeds MAX_BODY_PARTS ({MAX_BODY_PARTS})")
        if payload.get("dependencies") not in (None, []):
            raise ValueError("sensory PR4 body_schema must not contain dependencies")
        if not isinstance(payload.get("global_state", {}), dict):
            raise ValueError("body_schema global_state must be an object")

        seen: set[str] = set()
        for entry in raw_parts:
            if not isinstance(entry, dict):
                raise ValueError("body_schema part entries must be JSON objects")
            part_id = entry.get("part_id")
            if not isinstance(part_id, str) or not part_id.startswith("part.sense.") or len(part_id) != 27:
                raise ValueError("body_schema part_id must be an opaque part.sense.<16-hex> id")
            suffix = part_id.removeprefix("part.sense.")
            if any(char not in "0123456789abcdef" for char in suffix):
                raise ValueError("body_schema part_id suffix must be lowercase hex")
            if part_id in seen:
                raise ValueError(f"duplicate body_schema part_id: {part_id}")
            seen.add(part_id)
            if entry.get("kind") != "sense":
                raise ValueError("sensory PR4 body_schema supports only kind='sense'")
            health_class = _require_class(entry.get("health_class"), _HEALTH_CLASSES, "health_class")
            confidence_class = _require_class(
                entry.get("confidence_class"), _CONFIDENCE_CLASSES, "confidence_class"
            )
            cost_class = _require_class(entry.get("cost_class"), _COST_CLASSES, "cost_class")
            maturity_class = _require_class(entry.get("maturity_class"), _MATURITY_CLASSES, "maturity_class")
            _require_class(
                entry.get("existence_confidence_class"), _CONFIDENCE_CLASSES, "existence_confidence_class"
            )
            recency_raw = _require_class(entry.get("recency_class"), len(RecencyClass), "recency_class")
            representative_idle = _RECENCY_REPRESENTATIVE_IDLE_TICKS[RecencyClass(recency_raw)]
            model._parts[part_id] = _SensoryPartState(
                part_id=part_id,
                health_class=health_class,
                confidence_class=confidence_class,
                cost_class=cost_class,
                maturity_class=maturity_class,
                last_evidence_tick=max(0, current_tick - representative_idle),
            )

        if state == "undeveloped" and model._parts:
            raise ValueError("undeveloped body_schema cannot contain parts")
        if state == "partial" and not model._parts:
            raise ValueError("partial body_schema must contain at least one part")
        return model


__all__ = ["BODY_SCHEMA_VERSION", "MAX_BODY_PARTS", "BodySchemaEngine"]
