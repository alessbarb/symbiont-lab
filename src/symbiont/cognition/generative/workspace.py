"""Bounded temporary workspace for Generative Cognition v1."""

from __future__ import annotations

from .budget import GenerativeBudget
from .types import GenerativeEpisode, GenerativeOperation, GenerativeState, GenerativeTransition


class GenerativeWorkspace:
    """Owns generated states and transitions, never factual stores or actions."""

    def __init__(
        self, *, episode: GenerativeEpisode, budget: GenerativeBudget | None = None
    ) -> None:
        self.episode = episode
        self.budget = budget or GenerativeBudget()
        self._states: dict[str, GenerativeState] = {}
        self._transitions: dict[str, GenerativeTransition] = {}
        self._model_queries = 0
        self._closed = False

    @property
    def states(self) -> tuple[GenerativeState, ...]:
        return tuple(self._states.values())

    @property
    def transitions(self) -> tuple[GenerativeTransition, ...]:
        return tuple(self._transitions.values())

    @property
    def model_queries(self) -> int:
        return self._model_queries

    def add_state(self, state: GenerativeState) -> None:
        self._ensure_open()
        if state.episode_id != self.episode.episode_id:
            raise ValueError("state belongs to a different generative episode")
        if state.state_id in self._states:
            raise ValueError("duplicate generative state_id")
        if len(self._states) >= self.budget.max_states:
            raise BudgetExceeded("maximum generative states reached")
        if state.depth > self.budget.max_depth:
            raise BudgetExceeded("maximum generative depth reached")
        if state.parent_state_id is not None and state.parent_state_id not in self._states:
            raise ValueError("state parent is not present in workspace")
        self._states[state.state_id] = state
        self.episode.state_count = len(self._states)
        self.episode.max_depth_reached = max(self.episode.max_depth_reached, state.depth)

    def add_transition(self, transition: GenerativeTransition) -> None:
        self._ensure_open()
        if transition.episode_id != self.episode.episode_id:
            raise ValueError("transition belongs to a different generative episode")
        if transition.operation in {
            GenerativeOperation.ABSTRACT,
            GenerativeOperation.ANALOGIZE,
            GenerativeOperation.COMPOSE,
            GenerativeOperation.DECOMPOSE,
        }:
            raise NotImplementedError(f"{transition.operation.value} is reserved in v1")
        if transition.transition_id in self._transitions:
            raise ValueError("duplicate generative transition_id")
        if len(self._transitions) >= self.budget.max_transitions:
            raise BudgetExceeded("maximum generative transitions reached")
        if (
            transition.source_state_id not in self._states
            or transition.target_state_id not in self._states
        ):
            raise ValueError("transition endpoints must be present in workspace")
        if (
            transition.operation is GenerativeOperation.BRANCH
            and self.episode.branch_count >= self.budget.max_branches
        ):
            raise BudgetExceeded("maximum generative branches reached")
        self._transitions[transition.transition_id] = transition
        self.episode.transition_count = len(self._transitions)
        if transition.operation is GenerativeOperation.BRANCH:
            self.episode.branch_count += 1

    def consume_model_query(self) -> None:
        self._ensure_open()
        if self._model_queries >= self.budget.max_model_queries:
            raise BudgetExceeded("maximum generative model queries reached")
        self._model_queries += 1

    def close(self, reason) -> None:
        self._ensure_open()
        self.episode.termination_reason = reason
        self._closed = True

    def checkpoint(self) -> dict[str, object]:
        return {
            "episode": _episode_payload(self.episode),
            "budget": {
                "max_states": self.budget.max_states,
                "max_transitions": self.budget.max_transitions,
                "max_depth": self.budget.max_depth,
                "max_branches": self.budget.max_branches,
                "max_model_queries": self.budget.max_model_queries,
            },
            "states": [_state_payload(state) for state in self.states],
            "transitions": [_transition_payload(item) for item in self.transitions],
            "model_queries": self._model_queries,
            "closed": self._closed,
        }

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("generative workspace is closed")


class BudgetExceeded(RuntimeError):
    """Raised when a workspace reaches an explicit engineering bound."""


def _feature_payload(feature):
    return {
        "token": feature.token,
        "value_class": feature.value_class,
        "confidence": feature.confidence,
        "source_model_id": feature.source_model_id,
    }


def _state_payload(state):
    return {
        "state_id": state.state_id,
        "episode_id": state.episode_id,
        "origin": state.origin.value,
        "parent_state_id": state.parent_state_id,
        "depth": state.depth,
        "features": [_feature_payload(feature) for feature in state.features],
        "active_concept_ids": list(state.active_concept_ids),
        "relation_refs": list(state.relation_refs),
        "source_episode_ids": list(state.source_episode_ids),
        "source_model_ids": list(state.source_model_ids),
        "source_state_ids": list(state.source_state_ids),
        "uncertainty": state.uncertainty,
        "coherence": state.coherence,
        "generative_tick": state.generative_tick,
    }


def _transition_payload(item):
    return {
        "transition_id": item.transition_id,
        "episode_id": item.episode_id,
        "source_state_id": item.source_state_id,
        "target_state_id": item.target_state_id,
        "operation": item.operation.value,
        "model_ids": list(item.model_ids),
        "uncertainty_before": item.uncertainty_before,
        "uncertainty_after": item.uncertainty_after,
        "predicted_outcomes": list(item.predicted_outcomes),
        "generative_tick": item.generative_tick,
    }


def _episode_payload(episode):
    return {
        "episode_id": episode.episode_id,
        "organism_id": episode.organism_id,
        "target_id": episode.target_id,
        "root_state_id": episode.root_state_id,
        "mode": episode.mode.value,
        "started_symbiont_tick": episode.started_symbiont_tick,
        "started_generative_tick": episode.started_generative_tick,
        "source_episode_ids": list(episode.source_episode_ids),
        "state_count": episode.state_count,
        "transition_count": episode.transition_count,
        "branch_count": episode.branch_count,
        "max_depth_reached": episode.max_depth_reached,
        "termination_reason": episode.termination_reason.value
        if episode.termination_reason
        else None,
    }


__all__ = ["BudgetExceeded", "GenerativeWorkspace"]
