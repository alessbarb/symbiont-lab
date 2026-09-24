from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from symbiont.host.adaptive import PairAccumulator

from .types import ActuatorId, _require_nonneg_finite, _require_nonneg_int

ProbingState = Literal["active", "dormant"]
_VALID_PROBING_STATES: frozenset[str] = frozenset({"active", "dormant"})
_MAX_EFFECT_RELATIONS_PER_CANDIDATE = 256


@dataclass(slots=True)
class ActuatorCandidateState:
    """Bounded, per-actuator record of observed activation -> Δpercept effect.

    Tracks effect/controllability evidence only (spec §5): whether
    activating this channel has a measurable, reproducible consequence.
    Whether that consequence is desirable is never decided here.

    ``effect_relations`` is a cumulative, all-time record per percept
    (bounded, bounded-relation-count) — used for ``effect_strength``. Every
    field is exported/restored in ``to_payload``/``from_payload``
    UNCONDITIONALLY, including relations with as few as one sample (spec
    §16.6 rev5): ``run == checkpoint -> restore -> continue`` must hold from
    any tick, and PairAccumulator's own ``correlation`` already returns
    ``None`` below 3 samples (see host/adaptive.py), so an immature relation
    can never influence ``effect_strength`` or promotion regardless of
    whether it round-trips through a checkpoint.
    """

    actuator_id: ActuatorId
    activations: int = 0
    effect_relations: dict[str, PairAccumulator] = field(default_factory=dict)
    cost_evidence: float = 0.0
    probing_state: ProbingState = "dormant"
    last_seen_tick: int = 0
    natural_promotion_samples: int = 0

    def observe_effect(self, percept_id: str, *, activation: float, delta_percept: float) -> None:
        """Record one activation/effect pair for ``percept_id``.

        Contract (spec §6 revisión 4): the caller owns computing
        ``delta_percept`` as ``percept(t+1) - percept(t)`` for the SAME
        actuator activation issued at tick ``t`` — i.e. the percept reading
        taken one tick AFTER the activation, minus the reading taken at (or
        immediately before) the activation. This method does not and
        cannot verify that contract itself; it only accumulates whatever
        pair it is handed.

        Passing a same-tick delta (e.g. ``percept(t) - percept(t)``, which
        is ~0 for any stable percept) defeats the entire purpose of this
        accumulator: it manufactures a constant-zero ``y`` series that can
        never show causal covariance with ``activation``, silently masking
        real effect relations as "no detectable effect" regardless of
        whether the actuator is actually causal. Always derive
        ``delta_percept`` from two chronologically distinct percept
        readings taken across the tick boundary that follows the
        activation being recorded.
        """
        self.activations += 1
        relation = self.effect_relations.get(percept_id)
        if relation is None:
            if len(self.effect_relations) >= _MAX_EFFECT_RELATIONS_PER_CANDIDATE:
                self._evict_weakest_relation()
            relation = PairAccumulator()
            self.effect_relations[percept_id] = relation
        relation.observe(activation, delta_percept)

    def _evict_weakest_relation(self) -> None:
        def strength(item: tuple[str, PairAccumulator]) -> float:
            correlation = item[1].correlation
            return abs(correlation) if correlation is not None else -1.0

        weakest_id, _ = min(self.effect_relations.items(), key=strength)
        del self.effect_relations[weakest_id]

    @property
    def effect_strength(self) -> float:
        strengths = [
            abs(relation.correlation)
            for relation in self.effect_relations.values()
            if relation.correlation is not None
        ]
        return max(strengths, default=0.0)

    def to_payload(self) -> dict[str, Any]:
        # Every field below is exported UNCONDITIONALLY, exactly as it is —
        # this is a checkpoint, not a filtered report to an external
        # observer (see the class docstring / spec §16.6 rev5).
        return {
            "actuator_id": self.actuator_id,
            "activations": self.activations,
            "cost_evidence": self.cost_evidence,
            "probing_state": self.probing_state,
            "last_seen_tick": self.last_seen_tick,
            "natural_promotion_samples": self.natural_promotion_samples,
            "effect_relations": {
                percept_id: relation.to_payload() for percept_id, relation in self.effect_relations.items()
            },
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ActuatorCandidateState":
        required = {
            "actuator_id",
            "activations",
            "cost_evidence",
            "probing_state",
            "last_seen_tick",
            "effect_relations",
        }
        missing = required - set(payload)
        if missing:
            raise ValueError(f"ActuatorCandidateState payload missing fields: {sorted(missing)}")

        actuator_id = payload["actuator_id"]
        if not isinstance(actuator_id, str) or not actuator_id:
            raise ValueError("actuator_id must be a non-empty string")

        probing_state = payload["probing_state"]
        if probing_state not in _VALID_PROBING_STATES:
            raise ValueError(f"probing_state must be one of {sorted(_VALID_PROBING_STATES)}, got {probing_state!r}")
        raw_relations = payload["effect_relations"]
        if not isinstance(raw_relations, dict):
            raise ValueError("effect_relations must be an object")
        effect_relations = {
            percept_id: PairAccumulator.from_payload(dict(raw))
            for percept_id, raw in raw_relations.items()
        }
        if len(effect_relations) > _MAX_EFFECT_RELATIONS_PER_CANDIDATE:
            raise ValueError(
                "effect_relations exceeds max of "
                f"{_MAX_EFFECT_RELATIONS_PER_CANDIDATE}, got {len(effect_relations)}"
            )

        return cls(
            actuator_id=actuator_id,
            activations=_require_nonneg_int(payload["activations"], "activations"),
            effect_relations=effect_relations,
            cost_evidence=_require_nonneg_finite(payload["cost_evidence"], "cost_evidence"),
            probing_state=probing_state,  # type: ignore[arg-type]
            last_seen_tick=_require_nonneg_int(payload["last_seen_tick"], "last_seen_tick"),
            natural_promotion_samples=_require_nonneg_int(
                payload.get("natural_promotion_samples", 0),
                "natural_promotion_samples",
            ),
        )
