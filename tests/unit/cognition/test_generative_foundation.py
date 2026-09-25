from __future__ import annotations

import pytest

from symbiont.cognition.generative import (
    BudgetExceeded,
    EpistemicBoundaryError,
    EpistemicFirewall,
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeBudget,
    GenerativeMode,
    GenerativeOperation,
    GenerativeState,
    GenerativeTransition,
    GenerativeWorkspace,
    dumps,
    loads,
    new_episode,
)


def state(
    episode_id: str, state_id: str, *, parent: str | None = None, depth: int = 0
) -> GenerativeState:
    return GenerativeState(
        state_id=state_id,
        episode_id=episode_id,
        origin=EpistemicOrigin.IMAGINED,
        parent_state_id=parent,
        depth=depth,
        features=(GeneratedFeature("opaque", 1, 0.5, "model-a"),),
        active_concept_ids=(),
        relation_refs=(),
        source_episode_ids=(),
        source_model_ids=("model-a",),
        source_state_ids=(),
        uncertainty=0.5,
        coherence=0.8,
        generative_tick=depth,
    )


def workspace(*, budget: GenerativeBudget | None = None) -> GenerativeWorkspace:
    episode = new_episode(
        episode_id="episode-1",
        organism_id="organism-1",
        root_state_id="s0",
        mode=GenerativeMode.ONLINE,
        symbiont_tick=4,
        generative_tick=0,
    )
    result = GenerativeWorkspace(episode=episode, budget=budget)
    result.add_state(state("episode-1", "s0"))
    return result


def test_state_requires_provenance_and_has_no_physical_fields():
    value = state("episode-1", "s0")
    assert value.origin is EpistemicOrigin.IMAGINED
    assert value.features[0].token == "opaque"

    with pytest.raises(ValueError, match="origin"):
        GenerativeState("s", "e", "imagined", None, 0, (), (), (), (), (), (), 0.5, 0.5, 0)  # type: ignore[arg-type]


def test_workspace_is_bounded_and_rejects_reserved_operations():
    work = workspace(
        budget=GenerativeBudget(
            max_states=2, max_transitions=1, max_depth=1, max_branches=1, max_model_queries=1
        )
    )
    work.add_state(state("episode-1", "s1", parent="s0", depth=1))
    with pytest.raises(BudgetExceeded):
        work.add_state(state("episode-1", "s2", parent="s1", depth=2))
    with pytest.raises(NotImplementedError):
        work.add_transition(
            GenerativeTransition(
                "t1", "episode-1", "s0", "s1", GenerativeOperation.ABSTRACT, (), 0.5, 0.5, (), 1
            )
        )


def test_firewall_rejects_all_factual_and_executive_sinks():
    work = workspace()
    generated = work.states[0]
    for guard in (
        EpistemicFirewall.reject_factual_evidence,
        EpistemicFirewall.reject_execution,
        EpistemicFirewall.reject_factual_learning,
    ):
        with pytest.raises(EpistemicBoundaryError):
            guard(generated)


def test_checkpoint_round_trip_is_deterministic_and_fail_closed():
    work = workspace()
    work.consume_model_query()
    encoded = dumps(work)
    restored = loads(encoded)
    assert dumps(restored) == encoded
    with pytest.raises(ValueError, match="schema"):
        loads('{"schema_version": 99}')
