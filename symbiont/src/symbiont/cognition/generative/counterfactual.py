"""Bounded counterfactual rollouts with explicit generated provenance."""

from __future__ import annotations

from .model import GenerativeContext
from .registry import GenerativeModelRegistry
from .rollout import RolloutEngine, RolloutResult
from .types import GenerativeOperation
from .workspace import GenerativeWorkspace


class CounterfactualEngine:
    """Runs hypothetical trajectories without executing their interventions."""

    def __init__(
        self, *, registry: GenerativeModelRegistry, workspace: GenerativeWorkspace
    ) -> None:
        self._rollout = RolloutEngine(registry=registry, workspace=workspace)

    def evaluate(
        self,
        *,
        root_state_id: str,
        context: GenerativeContext,
        max_depth: int | None = None,
    ) -> RolloutResult:
        return self._rollout.rollout(
            root_state_id=root_state_id,
            context=context,
            operation=GenerativeOperation.COUNTERFACTUAL,
            max_depth=max_depth,
        )


__all__ = ["CounterfactualEngine"]
