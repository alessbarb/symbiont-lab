"""Bounded deterministic branching over one generated parent state."""

from __future__ import annotations

from .model import GenerativeContext
from .registry import GenerativeModelRegistry
from .rollout import RolloutResult
from .types import (
    EpistemicOrigin,
    GenerativeOperation,
    GenerativeState,
    GenerativeTermination,
    GenerativeTransition,
)
from .workspace import BudgetExceeded, GenerativeWorkspace


class BranchEngine:
    """Creates sibling hypotheses without treating any branch as factual."""

    def __init__(
        self, *, registry: GenerativeModelRegistry, workspace: GenerativeWorkspace
    ) -> None:
        self.registry = registry
        self.workspace = workspace

    def branch(
        self,
        *,
        root_state_id: str,
        context: GenerativeContext,
        max_branches: int | None = None,
    ) -> RolloutResult:
        try:
            parent = next(
                state for state in self.workspace.states if state.state_id == root_state_id
            )
        except StopIteration as exc:
            raise ValueError("branch root state is not present in workspace") from exc
        branch_limit = self.workspace.budget.max_branches if max_branches is None else max_branches
        if (
            isinstance(branch_limit, bool)
            or not isinstance(branch_limit, int)
            or not 0 <= branch_limit <= self.workspace.budget.max_branches
        ):
            raise ValueError("max_branches must be within the workspace budget")
        if branch_limit == 0:
            return self._finish((), (), GenerativeTermination.BUDGET_EXHAUSTED)
        try:
            self.workspace.consume_model_query()
        except BudgetExceeded:
            return self._finish((), (), GenerativeTermination.BUDGET_EXHAUSTED)
        proposals = sorted(
            self.registry.query(
                operation=GenerativeOperation.BRANCH, state=parent, context=context
            ),
            key=lambda item: item.model_id,
        )
        if not proposals:
            return self._finish((), (), GenerativeTermination.MODEL_UNAVAILABLE)
        states: list[GenerativeState] = []
        transitions: list[GenerativeTransition] = []
        for proposal in proposals[:branch_limit]:
            state_id = f"{self.workspace.episode.episode_id}.s{len(self.workspace.states)}"
            next_state = GenerativeState(
                state_id=state_id,
                episode_id=self.workspace.episode.episode_id,
                origin=EpistemicOrigin.INFERRED,
                parent_state_id=parent.state_id,
                depth=parent.depth + 1,
                features=proposal.features,
                active_concept_ids=(),
                relation_refs=proposal.support_refs,
                source_episode_ids=parent.source_episode_ids,
                source_model_ids=(proposal.model_id,),
                source_state_ids=(parent.state_id,),
                uncertainty=max(parent.uncertainty, proposal.uncertainty),
                coherence=min(parent.coherence, proposal.coherence),
                generative_tick=parent.generative_tick + 1,
            )
            transition = GenerativeTransition(
                transition_id=f"{self.workspace.episode.episode_id}.t{len(self.workspace.transitions)}",
                episode_id=self.workspace.episode.episode_id,
                source_state_id=parent.state_id,
                target_state_id=state_id,
                operation=GenerativeOperation.BRANCH,
                model_ids=(proposal.model_id,),
                uncertainty_before=parent.uncertainty,
                uncertainty_after=next_state.uncertainty,
                predicted_outcomes=proposal.predicted_outcomes,
                generative_tick=next_state.generative_tick,
            )
            try:
                self.workspace.add_state(next_state)
                self.workspace.add_transition(transition)
            except BudgetExceeded:
                return self._finish(states, transitions, GenerativeTermination.BUDGET_EXHAUSTED)
            states.append(next_state)
            transitions.append(transition)
        return self._finish(states, transitions, GenerativeTermination.COMPLETED)

    def _finish(self, states, transitions, reason) -> RolloutResult:
        self.workspace.episode.termination_reason = reason
        return RolloutResult(tuple(states), tuple(transitions), reason)


__all__ = ["BranchEngine"]
