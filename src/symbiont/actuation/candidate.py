from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from symbiont.host.adaptive import PairAccumulator

from .types import ActuatorId

ProbingState = Literal["active", "probing", "dormant"]
_VALID_PROBING_STATES: frozenset[str] = frozenset({"active", "probing", "dormant"})
_MAX_EFFECT_RELATIONS_PER_CANDIDATE = 16
_MIN_RELATION_SAMPLES_FOR_EXPORT = 6


@dataclass(slots=True)
class ActuatorCandidateState:
    """Bounded, per-actuator record of observed activation -> Δpercept effect.

    Tracks effect/controllability evidence only (spec §5): whether
    activating this channel has a measurable, reproducible consequence.
    Whether that consequence is desirable is never decided here.
    """

    actuator_id: ActuatorId
    activations: int = 0
    effect_relations: dict[str, PairAccumulator] = field(default_factory=dict)
    cost_evidence: float = 0.0
    probing_state: ProbingState = "dormant"
    last_seen_tick: int = 0
    windows_completed: int = 0

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
        exported_relations = {
            percept_id: relation.to_payload()
            for percept_id, relation in self.effect_relations.items()
            if relation.count >= _MIN_RELATION_SAMPLES_FOR_EXPORT
        }
        # If the exported effect_relations end up empty — whether because
        # every observed relation was withheld for having too few samples,
        # or because none were observed at all — windows_completed must not
        # survive the export as-is: a restored candidate would otherwise
        # start from fresh (empty) PairAccumulators while already sitting
        # at/above the promotion threshold, letting it promote on a single
        # post-restore window with no real evidence behind it (spec §6
        # revisión 3 — promotion requires evidence sustained across
        # multiple distinct calendars, not one). Reset the exported
        # windows_completed to 0 in that case so a restored candidate
        # correctly restarts accumulation.
        exported_windows_completed = self.windows_completed if exported_relations else 0
        return {
            "actuator_id": self.actuator_id,
            "activations": self.activations,
            "cost_evidence": self.cost_evidence,
            "probing_state": self.probing_state,
            "last_seen_tick": self.last_seen_tick,
            "windows_completed": exported_windows_completed,
            "effect_relations": exported_relations,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ActuatorCandidateState":
        required = {
            "actuator_id",
            "activations",
            "cost_evidence",
            "probing_state",
            "last_seen_tick",
            "windows_completed",
            "effect_relations",
        }
        missing = required - set(payload)
        if missing:
            raise ValueError(f"ActuatorCandidateState payload missing fields: {sorted(missing)}")

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
            actuator_id=str(payload["actuator_id"]),
            activations=int(payload["activations"]),
            effect_relations=effect_relations,
            cost_evidence=float(payload["cost_evidence"]),
            probing_state=probing_state,  # type: ignore[arg-type]
            last_seen_tick=int(payload["last_seen_tick"]),
            windows_completed=int(payload["windows_completed"]),
        )
