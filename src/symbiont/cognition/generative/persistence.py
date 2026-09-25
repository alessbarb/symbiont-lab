"""Fail-closed checkpoint encoding for a generative workspace."""

from __future__ import annotations

import json
from typing import Any

from .budget import GenerativeBudget
from .types import (
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeEpisode,
    GenerativeMode,
    GenerativeOperation,
    GenerativeState,
    GenerativeTermination,
    GenerativeTransition,
)
from .workspace import GenerativeWorkspace

GENERATIVE_COGNITION_SCHEMA_VERSION = 1


def dumps(workspace: GenerativeWorkspace) -> str:
    return json.dumps(
        {
            "schema_version": GENERATIVE_COGNITION_SCHEMA_VERSION,
            "workspace": workspace.checkpoint(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def loads(payload: str) -> GenerativeWorkspace:
    try:
        decoded = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid generative checkpoint JSON") from exc
    return restore(decoded)


def restore(payload: object) -> GenerativeWorkspace:
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != GENERATIVE_COGNITION_SCHEMA_VERSION
    ):
        raise ValueError("unsupported or missing generative cognition schema version")
    raw_workspace = payload.get("workspace")
    if not isinstance(raw_workspace, dict):
        raise ValueError("generative checkpoint workspace must be an object")
    episode = _episode(raw_workspace.get("episode"))
    budget = _budget(raw_workspace.get("budget"))
    workspace = GenerativeWorkspace(episode=episode, budget=budget)
    raw_states = raw_workspace.get("states")
    raw_transitions = raw_workspace.get("transitions")
    if not isinstance(raw_states, list) or not isinstance(raw_transitions, list):
        raise ValueError("generative checkpoint collections must be lists")
    for raw_state in raw_states:
        workspace.add_state(_state(raw_state))
    for raw_transition in raw_transitions:
        workspace.add_transition(_transition(raw_transition))
    queries = raw_workspace.get("model_queries", 0)
    if (
        isinstance(queries, bool)
        or not isinstance(queries, int)
        or not 0 <= queries <= budget.max_model_queries
    ):
        raise ValueError("invalid generative model query count")
    for _ in range(queries):
        workspace.consume_model_query()
    closed = raw_workspace.get("closed", False)
    if not isinstance(closed, bool):
        raise ValueError("workspace closed flag must be boolean")
    if closed:
        if episode.termination_reason is None:
            raise ValueError("closed workspace must have a termination reason")
        workspace._closed = True  # checkpoint restore, not a public mutation path
    return workspace


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _budget(value: Any) -> GenerativeBudget:
    raw = _object(value, "budget")
    try:
        return GenerativeBudget(
            **{
                name: raw[name]
                for name in (
                    "max_states",
                    "max_transitions",
                    "max_depth",
                    "max_branches",
                    "max_model_queries",
                )
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid generative budget") from exc


def _episode(value: Any) -> GenerativeEpisode:
    raw = _object(value, "episode")
    try:
        termination = raw.get("termination_reason")
        return GenerativeEpisode(
            episode_id=raw["episode_id"],
            organism_id=raw["organism_id"],
            target_id=raw.get("target_id"),
            root_state_id=raw["root_state_id"],
            mode=GenerativeMode(raw["mode"]),
            started_symbiont_tick=raw["started_symbiont_tick"],
            started_generative_tick=raw["started_generative_tick"],
            source_episode_ids=tuple(raw.get("source_episode_ids", ())),
            state_count=0,
            transition_count=0,
            branch_count=0,
            max_depth_reached=0,
            termination_reason=GenerativeTermination(termination)
            if termination is not None
            else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid generative episode") from exc


def _state(value: Any) -> GenerativeState:
    raw = _object(value, "state")
    try:
        features = tuple(GeneratedFeature(**item) for item in raw.get("features", ()))
        return GenerativeState(
            state_id=raw["state_id"],
            episode_id=raw["episode_id"],
            origin=EpistemicOrigin(raw["origin"]),
            parent_state_id=raw.get("parent_state_id"),
            depth=raw["depth"],
            features=features,
            active_concept_ids=tuple(raw.get("active_concept_ids", ())),
            relation_refs=tuple(raw.get("relation_refs", ())),
            source_episode_ids=tuple(raw.get("source_episode_ids", ())),
            source_model_ids=tuple(raw.get("source_model_ids", ())),
            source_state_ids=tuple(raw.get("source_state_ids", ())),
            uncertainty=raw["uncertainty"],
            coherence=raw["coherence"],
            generative_tick=raw["generative_tick"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid generative state") from exc


def _transition(value: Any) -> GenerativeTransition:
    raw = _object(value, "transition")
    try:
        return GenerativeTransition(
            transition_id=raw["transition_id"],
            episode_id=raw["episode_id"],
            source_state_id=raw["source_state_id"],
            target_state_id=raw["target_state_id"],
            operation=GenerativeOperation(raw["operation"]),
            model_ids=tuple(raw.get("model_ids", ())),
            uncertainty_before=raw["uncertainty_before"],
            uncertainty_after=raw["uncertainty_after"],
            predicted_outcomes=tuple(raw.get("predicted_outcomes", ())),
            generative_tick=raw["generative_tick"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid generative transition") from exc


__all__ = ["GENERATIVE_COGNITION_SCHEMA_VERSION", "dumps", "loads", "restore"]
