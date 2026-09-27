"""Organism-acquired action dimensions (Agency Acquisition v1 §17-§20, §81).

An ActionDimension is an intervention dimension the organism has discovered
to be repeatable and causally differentiable.  It is never bootstrapped from
the actuator surface: one actuator is not one dimension.  A dimension groups
the provisional intervention families (InterventionSignatures) that drive the
same opaque channel set — one channel, several channels or a coordinated
synergy — once real consequences after those interventions are repeated,
consistent and more frequent than in counterfactual windows.

Historical knowledge ("known") is kept separate from current executability
("available/bound"): after re-embodiment a dimension may remain known while
no longer being bound to the new body.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping

from .evidence import OpportunityView

_DIMENSION_SCHEMA = "symbiont-action-dimension-v2"


def opaque_dimension_id(channel_refs: Iterable[str]) -> str:
    refs = tuple(sorted(set(channel_refs)))
    if not refs:
        raise ValueError("a dimension spans at least one intervention channel")
    material = "|".join(refs)
    digest = sha256(f"{_DIMENSION_SCHEMA}:{material}".encode("utf-8")).hexdigest()[:16]
    return f"action.dimension.{digest}"


@dataclass(frozen=True)
class ActionDimensionDiscoveryPolicy:
    """Experimental gate parameters; deliberately not frozen scientific values."""

    minimum_attempt_support: int = 2
    minimum_effect_support: int = 2
    minimum_consistency: float = 0.25
    minimum_causal_advantage: float = 0.05
    minimum_counterfactual_support: int = 2
    agentic_confidence: float = 0.35

    def __post_init__(self) -> None:
        for name in (
            "minimum_attempt_support",
            "minimum_effect_support",
            "minimum_counterfactual_support",
        ):
            if int(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be positive")
        for name in ("minimum_consistency", "minimum_causal_advantage", "agentic_confidence"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.minimum_effect_support > self.minimum_attempt_support:
            raise ValueError("effect support cannot exceed attempt support")


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    """Causal assessment of one channel-set family of interventions."""

    signature_refs: tuple[str, ...]
    attempt_support: int
    dominant_effect_id: str | None
    effect_support: int
    consistency: float
    reliability: float
    counterfactual_rate: float | None
    causal_advantage: float | None
    counterfactual_support: int
    qualifies: bool


def assess_family(
    ledger: OpportunityView,
    signature_refs: tuple[str, ...],
    policy: ActionDimensionDiscoveryPolicy,
) -> DimensionEvidence:
    """Context-free repeatability, consistency and counterfactual contrast."""
    refs = tuple(sorted(set(signature_refs)))
    effects: dict[str, int] = {}
    attempts = 0
    for ref in refs:
        for effect_id, count in ledger.signature_effects(ref).items():
            attempts += count
            if effect_id is not None:
                effects[effect_id] = effects.get(effect_id, 0) + count
    if not effects:
        return DimensionEvidence(refs, attempts, None, 0, 0.0, 0.0, None, None, 0, False)
    dominant, effect_support = min(effects.items(), key=lambda item: (-item[1], item[0]))
    action_n, action_hits, other_n, other_hits = ledger.signatures_effect_opportunities(
        dominant, intervention_signature_ids=refs
    )
    reliability = action_hits / action_n if action_n else 0.0
    counterfactual_rate = other_hits / other_n if other_n else None
    advantage = reliability - counterfactual_rate if counterfactual_rate is not None else None
    consistency = effect_support / attempts if attempts else 0.0
    qualifies = (
        attempts >= policy.minimum_attempt_support
        and effect_support >= policy.minimum_effect_support
        and consistency >= policy.minimum_consistency
        and other_n >= policy.minimum_counterfactual_support
        and advantage is not None
        and advantage >= policy.minimum_causal_advantage
    )
    return DimensionEvidence(
        signature_refs=refs,
        attempt_support=attempts,
        dominant_effect_id=dominant,
        effect_support=effect_support,
        consistency=consistency,
        reliability=reliability,
        counterfactual_rate=counterfactual_rate,
        causal_advantage=advantage,
        counterfactual_support=other_n,
        qualifies=qualifies,
    )


@dataclass(frozen=True, slots=True)
class ActionDimension:
    dimension_id: str

    intervention_signature_refs: tuple[str, ...]

    availability: bool

    controllability: float
    confidence: float

    usage_count: int

    embodiment_bound: bool

    def __post_init__(self) -> None:
        if not self.dimension_id.startswith("action.dimension."):
            raise ValueError("dimension_id must be opaque and organism-owned")
        if not self.intervention_signature_refs:
            raise ValueError("an action dimension is grounded in intervention families")
        if tuple(sorted(set(self.intervention_signature_refs))) != (
            self.intervention_signature_refs
        ):
            raise ValueError("intervention_signature_refs must be sorted and unique")
        if any(
            not ref.startswith("intervention.signature.")
            for ref in self.intervention_signature_refs
        ):
            raise ValueError("dimension members must be intervention signatures")
        if not 0.0 <= self.controllability <= 1.0:
            raise ValueError("controllability must be in [0,1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        if self.usage_count < 0:
            raise ValueError("usage_count must be non-negative")
        if self.embodiment_bound and not self.availability:
            raise ValueError("an unavailable dimension cannot be bound to the embodiment")


class ActionDimensionRegistry:
    """Bounded registry of dimensions acquired only from causal evidence."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        capacity: int = 512,
        policy: ActionDimensionDiscoveryPolicy | None = None,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self.policy = policy or ActionDimensionDiscoveryPolicy()
        self._items: dict[str, ActionDimension] = {}
        # Private grounding: which opaque output channels each dimension spans
        # and on which actuator surfaces its evidence was actually gathered.
        self._channels: dict[str, tuple[str, ...]] = {}
        self._verified_surfaces: dict[str, frozenset[str]] = {}
        self._available_channels: frozenset[str] | None = None
        self._surface_fingerprint: str | None = None

    def _available(self, channel_refs: tuple[str, ...]) -> bool:
        return self._available_channels is not None and set(channel_refs) <= (
            self._available_channels
        )

    def _bound(self, dimension_id: str) -> bool:
        """Available here *and* grounded by evidence gathered on this surface."""
        return self._available(self._channels[dimension_id]) and (
            self._surface_fingerprint in self._verified_surfaces.get(dimension_id, frozenset())
        )

    def _project(self, existing: ActionDimension) -> ActionDimension:
        available = self._available(self._channels[existing.dimension_id])
        return ActionDimension(
            dimension_id=existing.dimension_id,
            intervention_signature_refs=existing.intervention_signature_refs,
            availability=available,
            controllability=existing.controllability,
            confidence=existing.confidence,
            usage_count=existing.usage_count,
            embodiment_bound=self._bound(existing.dimension_id),
        )

    def evaluate_family(
        self,
        *,
        channel_refs: tuple[str, ...],
        signature_refs: tuple[str, ...],
        ledger: OpportunityView,
        surface_fingerprint: str,
    ) -> tuple[ActionDimension | None, DimensionEvidence]:
        """Create or refresh the dimension for one family if evidence qualifies.

        ``surface_fingerprint`` names the body on which the triggering
        intervention really happened; only such surfaces ground binding.
        """
        dimension_id = opaque_dimension_id(channel_refs)
        existing = self._items.get(dimension_id)
        refs = tuple(
            sorted(
                set(signature_refs)
                | set(existing.intervention_signature_refs if existing is not None else ())
            )
        )
        evidence = assess_family(ledger, refs, self.policy)
        if existing is None and not evidence.qualifies:
            return None, evidence
        confidence = max(
            0.0,
            min(1.0, evidence.consistency * min(1.0, evidence.attempt_support / 8.0)),
        )
        self._channels[dimension_id] = tuple(sorted(set(channel_refs)))
        self._verified_surfaces[dimension_id] = self._verified_surfaces.get(
            dimension_id, frozenset()
        ) | {surface_fingerprint}
        self._items[dimension_id] = self._project(
            ActionDimension(
                dimension_id=dimension_id,
                intervention_signature_refs=refs,
                availability=False,
                controllability=existing.controllability if existing is not None else 0.0,
                confidence=confidence,
                usage_count=evidence.attempt_support,
                embodiment_bound=False,
            )
        )
        self._enforce_bound()
        return self._items.get(dimension_id), evidence

    def record_controllability(self, dimension_id: str, controllability: float) -> ActionDimension:
        existing = self._items.get(dimension_id)
        if existing is None:
            raise KeyError(f"unknown action dimension: {dimension_id}")
        updated = ActionDimension(
            dimension_id=existing.dimension_id,
            intervention_signature_refs=existing.intervention_signature_refs,
            availability=existing.availability,
            controllability=max(0.0, min(1.0, float(controllability))),
            confidence=existing.confidence,
            usage_count=existing.usage_count,
            embodiment_bound=existing.embodiment_bound,
        )
        self._items[dimension_id] = updated
        return updated

    def bind_surface(
        self,
        available_channel_refs: Iterable[str] | None,
        *,
        surface_fingerprint: str | None,
    ) -> None:
        """Re-derive current availability/binding; historical knowledge is untouched."""
        self._available_channels = (
            None if available_channel_refs is None else frozenset(available_channel_refs)
        )
        self._surface_fingerprint = surface_fingerprint if self._available_channels else None
        for dimension_id, existing in tuple(self._items.items()):
            self._items[dimension_id] = self._project(existing)

    def _enforce_bound(self) -> None:
        if len(self._items) <= self.capacity:
            return
        retained = sorted(
            self._items.values(),
            key=lambda item: (-item.usage_count, item.dimension_id),
        )[: self.capacity]
        keep = {item.dimension_id for item in retained}
        self._items = {item.dimension_id: item for item in retained}
        self._channels = {k: v for k, v in self._channels.items() if k in keep}
        self._verified_surfaces = {k: v for k, v in self._verified_surfaces.items() if k in keep}

    def get(self, dimension_id: str) -> ActionDimension | None:
        return self._items.get(dimension_id)

    def channel_refs(self, dimension_id: str) -> tuple[str, ...]:
        return self._channels.get(dimension_id, ())

    def dimension_for_signature(self, signature_id: str) -> str | None:
        for item in self._items.values():
            if signature_id in item.intervention_signature_refs:
                return item.dimension_id
        return None

    @property
    def members(self) -> dict[str, tuple[str, ...]]:
        return {item.dimension_id: item.intervention_signature_refs for item in self.items}

    @property
    def items(self) -> tuple[ActionDimension, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.dimension_id))

    @property
    def available_items(self) -> tuple[ActionDimension, ...]:
        return tuple(item for item in self.items if item.availability)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "items": [
                {
                    "dimension_id": item.dimension_id,
                    "intervention_signature_refs": list(item.intervention_signature_refs),
                    "channel_refs": list(self._channels[item.dimension_id]),
                    "verified_surfaces": sorted(self._verified_surfaces[item.dimension_id]),
                    "controllability": item.controllability,
                    "confidence": item.confidence,
                    "usage_count": item.usage_count,
                }
                for item in self.items
            ],
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
        *,
        policy: ActionDimensionDiscoveryPolicy | None = None,
    ) -> "ActionDimensionRegistry":
        """Restore acquired dimensions; availability is re-derived by bind_surface().

        Schema 1 dimensions were bootstrapped from the actuator surface rather
        than acquired, so they are deliberately discarded (§83): the organism
        starts with no dimensions instead of inheriting fabricated ones.
        """
        if payload is None or payload.get("schema_version") == 1:
            return cls(policy=policy)
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported action dimension checkpoint")
        obj = cls(capacity=int(payload.get("capacity", 512)), policy=policy)
        raw = payload.get("items", [])
        if not isinstance(raw, list) or len(raw) > obj.capacity:
            raise ValueError("invalid or unbounded action dimensions")
        for entry in raw:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid action dimension entry")
            channels = tuple(sorted(str(value) for value in entry.get("channel_refs", [])))
            dimension_id = str(entry["dimension_id"])
            if dimension_id != opaque_dimension_id(channels):
                raise ValueError("action dimension identity does not match its grounding")
            obj._items[dimension_id] = ActionDimension(
                dimension_id=dimension_id,
                intervention_signature_refs=tuple(
                    sorted(str(value) for value in entry.get("intervention_signature_refs", []))
                ),
                availability=False,
                controllability=float(entry.get("controllability", 0.0)),
                confidence=float(entry.get("confidence", 0.0)),
                usage_count=int(entry.get("usage_count", 0)),
                embodiment_bound=False,
            )
            obj._channels[dimension_id] = channels
            surfaces = entry.get("verified_surfaces", [])
            if not isinstance(surfaces, list) or not surfaces:
                raise ValueError("action dimension lacks the surfaces that grounded it")
            obj._verified_surfaces[dimension_id] = frozenset(str(value) for value in surfaces)
        return obj


__all__ = [
    "ActionDimension",
    "ActionDimensionDiscoveryPolicy",
    "ActionDimensionRegistry",
    "DimensionEvidence",
    "assess_family",
    "opaque_dimension_id",
]
