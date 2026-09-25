"""Deterministic bounded multi-step rollout over registered models."""

from __future__ import annotations

from dataclasses import dataclass

from .model import GenerativeContext
from .registry import GenerativeModelRegistry
from .types import (
    EpistemicOrigin,
    GenerativeOperation,
    GenerativeState,
    GenerativeTermination,
    GenerativeTransition,
)
from .workspace import BudgetExceeded, GenerativeWorkspace


@dataclass(frozen=True, slots=True)
class RolloutResult:
    states: tuple[GenerativeState, ...]
    transitions: tuple[GenerativeTransition, ...]
    termination: GenerativeTermination


class RolloutEngine:
    """Composes model proposals without making them factual observations."""

    def __init__(
        self, *, registry: GenerativeModelRegistry, workspace: GenerativeWorkspace
    ) -> None:
        self.registry = registry
        self.workspace = workspace

    def rollout(
        self,
        *,
        root_state_id: str,
        context: GenerativeContext,
        operation: GenerativeOperation = GenerativeOperation.PREDICT,
        max_depth: int | None = None,
    ) -> RolloutResult:
        try:
            current = next(
                state for state in self.workspace.states if state.state_id == root_state_id
            )
        except StopIteration as exc:
            raise ValueError("rollout root state is not present in workspace") from exc
        if operation in {GenerativeOperation.BRANCH, GenerativeOperation.RECOMBINE}:
            raise ValueError("branching and recombination require their dedicated engines")
        depth_limit = self.workspace.budget.max_depth if max_depth is None else max_depth
        if (
            isinstance(depth_limit, bool)
            or not isinstance(depth_limit, int)
            or not 0 <= depth_limit <= self.workspace.budget.max_depth
        ):
            raise ValueError("max_depth must be within the workspace budget")
        generated_states: list[GenerativeState] = []
        generated_transitions: list[GenerativeTransition] = []
        for _ in range(depth_limit):
            try:
                self.workspace.consume_model_query()
            except BudgetExceeded:
                return self._finish(
                    generated_states, generated_transitions, GenerativeTermination.BUDGET_EXHAUSTED
                )
            proposals = self.registry.query(operation=operation, state=current, context=context)
            if not proposals:
                return self._finish(
                    generated_states, generated_transitions, GenerativeTermination.MODEL_UNAVAILABLE
                )
            proposal = min(proposals, key=lambda item: item.model_id)
            state_id = f"{self.workspace.episode.episode_id}.s{len(self.workspace.states)}"
            origin = {
                GenerativeOperation.REPLAY: EpistemicOrigin.REPLAYED,
                GenerativeOperation.COUNTERFACTUAL: EpistemicOrigin.COUNTERFACTUAL,
            }.get(operation, EpistemicOrigin.INFERRED)
            next_state = GenerativeState(
                state_id=state_id,
                episode_id=self.workspace.episode.episode_id,
                origin=origin,
                parent_state_id=current.state_id,
                depth=current.depth + 1,
                features=proposal.features,
                active_concept_ids=(),
                relation_refs=proposal.support_refs,
                source_episode_ids=current.source_episode_ids,
                source_model_ids=(proposal.model_id,),
                source_state_ids=(current.state_id,),
                # Uncertainty may remain or increase; it never silently vanishes.
                uncertainty=max(current.uncertainty, proposal.uncertainty),
                coherence=min(current.coherence, proposal.coherence),
                generative_tick=current.generative_tick + 1,
            )
            transition = GenerativeTransition(
                transition_id=f"{self.workspace.episode.episode_id}.t{len(self.workspace.transitions)}",
                episode_id=self.workspace.episode.episode_id,
                source_state_id=current.state_id,
                target_state_id=state_id,
                operation=operation,
                model_ids=(proposal.model_id,),
                uncertainty_before=current.uncertainty,
                uncertainty_after=next_state.uncertainty,
                predicted_outcomes=proposal.predicted_outcomes,
                generative_tick=next_state.generative_tick,
            )
            try:
                self.workspace.add_state(next_state)
                self.workspace.add_transition(transition)
            except BudgetExceeded:
                return self._finish(
                    generated_states, generated_transitions, GenerativeTermination.BUDGET_EXHAUSTED
                )
            generated_states.append(next_state)
            generated_transitions.append(transition)
            current = next_state
        return self._finish(
            generated_states, generated_transitions, GenerativeTermination.COMPLETED
        )

    def _finish(self, states, transitions, reason) -> RolloutResult:
        self.workspace.episode.termination_reason = reason
        return RolloutResult(tuple(states), tuple(transitions), reason)


__all__ = ["RolloutEngine", "RolloutResult"]
