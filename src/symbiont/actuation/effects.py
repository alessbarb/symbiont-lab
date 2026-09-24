"""Organism-owned sensorimotor effect space.

No body, world, lab or evaluator semantic label is accepted here.  Effects are
identified only from opaque organism-visible feature references and observed
transition structure.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Mapping


_ALLOWED_PREFIXES = ("signal.", "latent.", "part.", "channel.", "internal.", "effect.")


def _valid_feature_ref(value: str) -> bool:
    return bool(value) and value.startswith(_ALLOWED_PREFIXES)


@dataclass(frozen=True, slots=True)
class EffectRepresentation:
    effect_id: str
    feature_refs: tuple[str, ...]
    transition_signature: tuple[tuple[str, int], ...]
    support: int
    confidence: float

    def __post_init__(self) -> None:
        if not self.effect_id.startswith("effect."):
            raise ValueError("effect_id must be opaque and organism-owned")
        if not self.feature_refs or any(not _valid_feature_ref(item) for item in self.feature_refs):
            raise ValueError("effect features must be organism-owned references")
        if self.support < 1 or not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("invalid effect evidence")


@dataclass(frozen=True, slots=True)
class EffectTarget:
    effect_id: str
    desired_change: float | None = None
    tolerance: float | None = None

    def __post_init__(self) -> None:
        if not self.effect_id.startswith("effect."):
            raise ValueError("EffectTarget must reference organism-owned EffectSpace")
        if self.desired_change is not None and not math.isfinite(float(self.desired_change)):
            raise ValueError("desired_change must be finite")
        if self.tolerance is not None and (not math.isfinite(float(self.tolerance)) or self.tolerance < 0):
            raise ValueError("tolerance must be finite and non-negative")


class EffectSpace:
    """Bounded registry of recurring opaque transition signatures."""

    SCHEMA_VERSION = 1

    def __init__(self, *, max_effects: int = 512) -> None:
        if max_effects < 1:
            raise ValueError("max_effects must be positive")
        self._max_effects = int(max_effects)
        self._support: dict[tuple[tuple[str, int], ...], int] = {}
        self._effects: dict[str, EffectRepresentation] = {}

    @staticmethod
    def signature(changes: Mapping[str, float]) -> tuple[tuple[str, int], ...]:
        quantized: list[tuple[str, int]] = []
        for feature, value in sorted(changes.items()):
            if not _valid_feature_ref(str(feature)):
                continue
            number = float(value)
            if not math.isfinite(number) or abs(number) < 1e-9:
                continue
            bucket = max(-7, min(7, round(number * 7.0)))
            if bucket:
                quantized.append((str(feature), bucket))
        return tuple(quantized)

    @staticmethod
    def _id(signature: tuple[tuple[str, int], ...]) -> str:
        material = repr(signature).encode("utf-8")
        return "effect." + hashlib.sha256(material).hexdigest()[:24]

    def observe(self, changes: Mapping[str, float]) -> EffectRepresentation | None:
        signature = self.signature(changes)
        if not signature:
            return None
        support = self._support.get(signature, 0) + 1
        self._support[signature] = support
        effect_id = self._id(signature)
        confidence = min(1.0, support / 8.0)
        representation = EffectRepresentation(
            effect_id=effect_id,
            feature_refs=tuple(feature for feature, _ in signature),
            transition_signature=signature,
            support=support,
            confidence=confidence,
        )
        self._effects[effect_id] = representation
        if len(self._effects) > self._max_effects:
            retained = sorted(
                self._effects.values(),
                key=lambda item: (-item.support, -item.confidence, item.effect_id),
            )[: self._max_effects]
            self._effects = {item.effect_id: item for item in retained}
            retained_signatures = {item.transition_signature for item in retained}
            self._support = {key: value for key, value in self._support.items() if key in retained_signatures}
        return representation

    def get(self, effect_id: str) -> EffectRepresentation | None:
        return self._effects.get(effect_id)

    @property
    def effects(self) -> tuple[EffectRepresentation, ...]:
        return tuple(sorted(self._effects.values(), key=lambda item: item.effect_id))

    def target(self, effect_id: str, *, desired_change: float | None = None, tolerance: float | None = None) -> EffectTarget:
        if effect_id not in self._effects:
            raise KeyError("EffectTarget cannot be constructed from an external/unknown effect")
        return EffectTarget(effect_id, desired_change, tolerance)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "max_effects": self._max_effects,
            "support": [
                {"signature": [[key, value] for key, value in signature], "count": count}
                for signature, count in sorted(self._support.items())
            ],
        }

    @classmethod
    def restore(cls, payload: dict[str, object]) -> "EffectSpace":
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported effect-space checkpoint")
        obj = cls(max_effects=int(payload.get("max_effects", 512)))
        for item in payload.get("support", []):
            if not isinstance(item, dict):
                raise ValueError("invalid effect-space support")
            signature = tuple((str(k), int(v)) for k, v in item["signature"])
            count = int(item["count"])
            if count < 1:
                raise ValueError("invalid effect support count")
            obj._support[signature] = count
            effect_id = obj._id(signature)
            obj._effects[effect_id] = EffectRepresentation(
                effect_id=effect_id,
                feature_refs=tuple(key for key, _ in signature),
                transition_signature=signature,
                support=count,
                confidence=min(1.0, count / 8.0),
            )
        return obj
