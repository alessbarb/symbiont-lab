"""Predictive/controllability views over canonical causal evidence."""
from __future__ import annotations

from dataclasses import dataclass

from .evidence import CausalEvidenceLedger


@dataclass(frozen=True, slots=True)
class ControllabilityEstimate:
    effect_id: str
    competence_id: str
    context_id: str | None
    confidence: float
    reliability: float
    counterfactual_rate: float | None
    causal_advantage: float | None
    action_support: int
    counterfactual_support: int
    last_updated_tick: int


class ControllabilityModel:
    """Infer control only when intervention evidence beats alternatives."""

    def __init__(self) -> None:
        self._estimates: dict[tuple[str, str, str | None], ControllabilityEstimate] = {}

    def update_from_ledger(
        self,
        ledger: CausalEvidenceLedger,
        *,
        effect_id: str,
        competence_id: str,
        context_id: str | None,
        tick: int,
    ) -> ControllabilityEstimate:
        action_n, action_hits, other_n, other_hits = ledger.effect_opportunities(
            effect_id,
            competence_id=competence_id,
            context_ref=context_id,
        )
        reliability = action_hits / action_n if action_n else 0.0
        counterfactual_rate = (other_hits / other_n) if other_n else None
        advantage = (
            reliability - counterfactual_rate
            if counterfactual_rate is not None
            else None
        )
        # No counterfactual evidence -> confidence remains explicitly weak.
        if action_n == 0:
            confidence = 0.0
        elif other_n == 0:
            confidence = min(0.25, action_n / 32.0)
        else:
            support = min(1.0, min(action_n, other_n) / 8.0)
            confidence = max(0.0, min(1.0, (advantage or 0.0) * support))
        estimate = ControllabilityEstimate(
            effect_id=effect_id,
            competence_id=competence_id,
            context_id=context_id,
            confidence=confidence,
            reliability=reliability,
            counterfactual_rate=counterfactual_rate,
            causal_advantage=advantage,
            action_support=action_n,
            counterfactual_support=other_n,
            last_updated_tick=tick,
        )
        self._estimates[(effect_id, competence_id, context_id)] = estimate
        return estimate

    def estimate(
        self,
        effect_id: str,
        competence_id: str,
        context_id: str | None = None,
    ) -> ControllabilityEstimate | None:
        return self._estimates.get((effect_id, competence_id, context_id))

    @property
    def estimates(self) -> tuple[ControllabilityEstimate, ...]:
        return tuple(
            sorted(
                self._estimates.values(),
                key=lambda item: (item.effect_id, item.competence_id, item.context_id or ""),
            )
        )
