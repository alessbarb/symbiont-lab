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
        if self.tolerance is not None and (
            not math.isfinite(float(self.tolerance)) or self.tolerance < 0
        ):
            raise ValueError("tolerance must be finite and non-negative")


class EffectMatcher:
    """Effect equivalence (§33).

    v1 equivalence is identity: same organism-owned effect -> 1.0, otherwise
    0.0.  All intent/feedback logic compares effects through this class so a
    graded similarity can replace identity without touching its callers.
    """

    def similarity(
        self,
        expected: EffectRepresentation,
        observed: EffectRepresentation,
    ) -> float:
        return 1.0 if expected.effect_id == observed.effect_id else 0.0

    def match(
        self,
        space: "EffectSpace",
        *,
        expected_effect_id: str | None,
        observed_effect_id: str | None,
    ) -> float:
        """Similarity of two effects known to ``space``; unknown/absent -> 0.0."""
        if expected_effect_id is None or observed_effect_id is None:
            return 0.0
        expected = space.get(expected_effect_id)
        observed = space.get(observed_effect_id)
        if expected is None or observed is None:
            return 0.0
        return self.similarity(expected, observed)


# -- Factorized Effect Representation v1 §4.1: atomic effects --------------------
MAX_ATOMS_PER_TRANSITION = 16


def magnitude_class(bucket: int) -> int:
    """Coarse magnitude of a v4 bucket (spec §4.1): exact, fixed mapping."""
    size = abs(int(bucket))
    if not 1 <= size <= 7:
        raise ValueError("a magnitude class needs a non-zero bucket within [-7, 7]")
    return 1 if size <= 2 else (2 if size <= 4 else 3)


@dataclass(frozen=True, slots=True)
class EffectAtom:
    """One organism feature moving in one direction by a coarse amount."""

    feature_ref: str
    direction: int
    magnitude_class: int

    def __post_init__(self) -> None:
        if not _valid_feature_ref(self.feature_ref):
            raise ValueError("atom features must be organism-owned references")
        if self.direction not in (-1, 1):
            raise ValueError("atom direction must be -1 or +1")
        if self.magnitude_class not in (1, 2, 3):
            raise ValueError("atom magnitude class must be 1, 2 or 3")

    @property
    def effect_id(self) -> str:
        material = f"atom|{self.feature_ref}|{self.direction}|{self.magnitude_class}"
        return "effect.atom." + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def from_bucket(cls, feature_ref: str, bucket: int) -> "EffectAtom":
        return cls(str(feature_ref), 1 if bucket > 0 else -1, magnitude_class(bucket))


def atoms_from_signature(
    signature: tuple[tuple[str, int], ...],
) -> tuple[EffectAtom, ...]:
    """Exact decomposition of a v4 whole-state signature (spec §8)."""
    return tuple(
        sorted(
            (EffectAtom.from_bucket(feature, bucket) for feature, bucket in signature if bucket),
            key=lambda atom: atom.feature_ref,
        )
    )


def atoms_from_changes(
    changes: Mapping[str, float],
    *,
    limit: int = MAX_ATOMS_PER_TRANSITION,
) -> tuple[EffectAtom, ...]:
    """The atoms of one transition, bounded: largest magnitudes first."""
    return bounded_atoms(EffectSpace.signature(changes), limit=limit)


def bounded_atoms(
    signature: tuple[tuple[str, int], ...],
    *,
    limit: int = MAX_ATOMS_PER_TRANSITION,
) -> tuple[EffectAtom, ...]:
    """A signature's atoms under the per-transition bound: largest changes first."""
    if limit < 1:
        raise ValueError("limit must be positive")
    kept = sorted(signature, key=lambda item: (-abs(item[1]), item[0]))[:limit]
    return atoms_from_signature(tuple(kept))


class EffectSpace:
    """Bounded registry of recurring opaque transition signatures."""

    SCHEMA_VERSION = 1

    def __init__(self, *, max_effects: int = 512) -> None:
        if max_effects < 1:
            raise ValueError("max_effects must be positive")
        self._max_effects = int(max_effects)
        self._support: dict[tuple[tuple[str, int], ...], int] = {}
        self._effects: dict[str, EffectRepresentation] = {}
        # Factorized Effect Representation v1 §14.1: footprint effects are
        # keyed by entity, registered explicitly and never evicted by the
        # whole-state bound (which saturates in high-dimensional bodies).
        self._footprints: dict[str, tuple[EffectRepresentation, tuple[EffectAtom, ...]]] = {}

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
            self._support = {
                key: value for key, value in self._support.items() if key in retained_signatures
            }
        return representation

    def register_footprint(
        self, effect_id: str, atoms: tuple[EffectAtom, ...], *, support: int
    ) -> EffectRepresentation:
        """(Re)register a footprint entity's effect with its current atoms."""
        if not effect_id.startswith("effect.entity."):
            raise ValueError("footprint effects are keyed by footprint entity")
        ordered = tuple(sorted(set(atoms), key=lambda atom: atom.effect_id))
        if not ordered or support < 1:
            raise ValueError("a footprint effect needs atoms and support")
        representation = EffectRepresentation(
            effect_id=effect_id,
            feature_refs=tuple(sorted({atom.feature_ref for atom in ordered})),
            transition_signature=tuple(
                sorted(
                    (atom.feature_ref, atom.direction * atom.magnitude_class) for atom in ordered
                )
            ),
            support=int(support),
            confidence=min(1.0, support / 8.0),
        )
        self._footprints[effect_id] = (representation, ordered)
        return representation

    def footprint_atoms(self, effect_id: str) -> tuple[str, ...] | None:
        """Atom effect ids of a registered footprint effect."""
        entry = self._footprints.get(effect_id)
        return tuple(atom.effect_id for atom in entry[1]) if entry is not None else None

    def get(self, effect_id: str) -> EffectRepresentation | None:
        found = self._effects.get(effect_id)
        if found is not None:
            return found
        entry = self._footprints.get(effect_id)
        return entry[0] if entry is not None else None

    @property
    def effects(self) -> tuple[EffectRepresentation, ...]:
        return tuple(
            sorted(
                (*self._effects.values(), *(entry[0] for entry in self._footprints.values())),
                key=lambda item: item.effect_id,
            )
        )

    def target(
        self, effect_id: str, *, desired_change: float | None = None, tolerance: float | None = None
    ) -> EffectTarget:
        if self.get(effect_id) is None:
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
            "footprints": [
                {
                    "effect_id": effect_id,
                    "support": representation.support,
                    "atoms": [
                        [atom.feature_ref, atom.direction, atom.magnitude_class] for atom in atoms
                    ],
                }
                for effect_id, (representation, atoms) in sorted(self._footprints.items())
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
        for item in payload.get("footprints", []):
            obj.register_footprint(
                str(item["effect_id"]),
                tuple(EffectAtom(str(f), int(d), int(m)) for f, d, m in item["atoms"]),
                support=int(item["support"]),
            )
        return obj
