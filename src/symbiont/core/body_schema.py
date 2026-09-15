from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import secrets
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
_GLOBAL_STATE_KEYS = {"self_model_confidence_class", "integrity_class"}


def _is_lower_hex(value: str, *, length: int) -> bool:
    return len(value) == length and all(char in "0123456789abcdef" for char in value)


def _part_id(id_salt: str, sense_id: str) -> str:
    """Return an organism-local stable opaque id for one learned sense.

    The private salt is checkpointed but never included in the exported
    BodySchema representation. Consequently equal capability ids in two
    organisms do not become a cross-organism correlation surface.
    """
    digest = sha256(f"symbiont-body:{id_salt}:sense:{sense_id}".encode("utf-8")).hexdigest()[:32]
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


def _existence_confidence_class(maturity_class: int) -> int:
    return round((maturity_class / (_MATURITY_CLASSES - 1)) * (_CONFIDENCE_CLASSES - 1))


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
        return _existence_confidence_class(self.maturity_class)


class BodySchemaEngine:
    """Bounded learned representation of the organism's sensory body.

    PR4 intentionally learns only SENSE parts. Evidence comes exclusively
    from ``SelfModel.export()``: no CognitiveGraph nodes, host manifest,
    provider metadata or runtime object identity are inspected here. That
    preserves the distinction between administrative truth and organism-
    owned self-knowledge.
    """

    def __init__(self, *, id_salt: str | None = None) -> None:
        if id_salt is None:
            id_salt = secrets.token_hex(16)
        if not isinstance(id_salt, str) or not _is_lower_hex(id_salt, length=32):
            raise ValueError("body_schema id_salt must be 32 lowercase hex characters")
        self._id_salt = id_salt
        self._parts: dict[str, _SensoryPartState] = {}

    @property
    def state(self) -> str:
        return "partial" if self._parts else "undeveloped"

    @property
    def part_count(self) -> int:
        return len(self._parts)

    def _enforce_bound(self) -> None:
        if len(self._parts) <= MAX_BODY_PARTS:
            return
        # Longitudinal churn can expose more than MAX_BODY_PARTS across the
        # organism's lifetime even though each SelfModel export is itself
        # bounded. Retain the freshest evidence first, then the parts with
        # stronger persistence/confidence evidence; part_id is a stable final
        # tie-breaker so pruning is deterministic and checkpoint-reproducible.
        retained = sorted(
            self._parts.values(),
            key=lambda part: (
                -part.last_evidence_tick,
                -part.existence_confidence_class,
                -part.confidence_class,
                part.part_id,
            ),
        )[:MAX_BODY_PARTS]
        self._parts = {part.part_id: part for part in retained}

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
            recency_raw = _require_class(entry.get("recency_class"), len(RecencyClass), "recency_class")
            representative_idle = _RECENCY_REPRESENTATIVE_IDLE_TICKS[RecencyClass(recency_raw)]
            part_id = _part_id(self._id_salt, sense_id)
            self._parts[part_id] = _SensoryPartState(
                part_id=part_id,
                health_class=health_class,
                confidence_class=confidence_class,
                cost_class=cost_class,
                maturity_class=maturity_class,
                # Presence in SelfModel.export() is not itself fresh evidence:
                # preserve SelfModel's quantized recency rather than rejuvenating
                # an idle sense simply because the entry remains exportable.
                last_evidence_tick=max(0, tick - representative_idle),
            )
        self._enforce_bound()

    def export(self, *, current_tick: int) -> dict[str, Any]:
        """Export organism-owned self-knowledge safe for a future observer.

        The private id salt and source capability ids are intentionally absent.
        """
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

    def export_checkpoint(self, *, current_tick: int) -> dict[str, Any]:
        payload = self.export(current_tick=current_tick)
        return {**payload, "id_salt": self._id_salt}

    @classmethod
    def restore_checkpoint(cls, payload: dict[str, Any] | None, *, current_tick: int) -> "BodySchemaEngine":
        if payload is None:
            return cls()
        if not isinstance(payload, dict):
            raise ValueError("body_schema payload must be a JSON object")
        if payload.get("schema_version") != BODY_SCHEMA_VERSION:
            raise ValueError(f"unsupported body_schema schema_version: {payload.get('schema_version')!r}")
        id_salt = payload.get("id_salt")
        if not isinstance(id_salt, str) or not _is_lower_hex(id_salt, length=32):
            raise ValueError("body_schema checkpoint is missing a valid private id_salt")
        model = cls(id_salt=id_salt)
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

        global_state = payload.get("global_state")
        if not isinstance(global_state, dict):
            raise ValueError("body_schema global_state must be an object")
        if set(global_state) - _GLOBAL_STATE_KEYS:
            raise ValueError("body_schema global_state contains unknown fields")
        for key, value in global_state.items():
            _require_class(value, _CONFIDENCE_CLASSES, key)

        seen: set[str] = set()
        for entry in raw_parts:
            if not isinstance(entry, dict):
                raise ValueError("body_schema part entries must be JSON objects")
            part_id = entry.get("part_id")
            if not isinstance(part_id, str) or not part_id.startswith("part.sense.") or len(part_id) != 43:
                raise ValueError("body_schema part_id must be an opaque part.sense.<32-hex> id")
            suffix = part_id.removeprefix("part.sense.")
            if not _is_lower_hex(suffix, length=32):
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
            existence_class = _require_class(
                entry.get("existence_confidence_class"), _CONFIDENCE_CLASSES, "existence_confidence_class"
            )
            if existence_class != _existence_confidence_class(maturity_class):
                raise ValueError("body_schema existence_confidence_class contradicts maturity_class")
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
        if not model._parts and global_state:
            raise ValueError("undeveloped body_schema global_state must be empty")
        if model._parts and set(global_state) != _GLOBAL_STATE_KEYS:
            raise ValueError("partial body_schema global_state must contain both derived summaries")
        return model


__all__ = ["BODY_SCHEMA_VERSION", "MAX_BODY_PARTS", "BodySchemaEngine"]
