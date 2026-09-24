"""Bounded predictive and controllability views over canonical evidence."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ControllabilityEstimate:
    effect_id: str
    context_id: str | None
    confidence: float
    reliability: float
    expected_latency: float | None
    effect_variance: float | None
    action_support: int
    counterfactual_support: int
    last_updated_tick: int


class ControllabilityModel:
    def __init__(self) -> None:
        self._estimates: dict[tuple[str, str | None], ControllabilityEstimate] = {}

    def update(
        self,
        *,
        effect_id: str,
        context_id: str | None,
        action_support: int,
        counterfactual_support: int,
        successes: int,
        variance: float | None,
        latency: float | None,
        tick: int,
    ) -> ControllabilityEstimate:
        opportunities = max(1, action_support)
        reliability = max(0.0, min(1.0, successes / opportunities))
        causal_support = max(0, action_support - counterfactual_support)
        confidence = max(0.0, min(1.0, causal_support / max(1, action_support)))
        estimate = ControllabilityEstimate(
            effect_id=effect_id,
            context_id=context_id,
            confidence=confidence,
            reliability=reliability,
            expected_latency=latency,
            effect_variance=variance,
            action_support=action_support,
            counterfactual_support=counterfactual_support,
            last_updated_tick=tick,
        )
        self._estimates[(effect_id, context_id)] = estimate
        return estimate

    def estimate(self, effect_id: str, context_id: str | None = None) -> ControllabilityEstimate | None:
        return self._estimates.get((effect_id, context_id))
