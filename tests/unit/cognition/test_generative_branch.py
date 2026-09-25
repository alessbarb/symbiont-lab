from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.generative import (
    BranchEngine,
    EpistemicOrigin,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeMode,
    GenerativeModelRegistry,
    GenerativeOperation,
    GenerativeState,
    GenerativeWorkspace,
    new_episode,
)


@dataclass
class BranchModel:
    model_id: str

    def supports(self, operation, state):
        return operation is GenerativeOperation.BRANCH

    def generate(self, *, state, operation, context):
        return (
            GeneratedProposal(
                (GeneratedFeature(self.model_id, state.depth, 0.8, self.model_id),),
                (self.model_id,),
                0.2,
                0.9,
                self.model_id,
                (state.state_id,),
            ),
        )


def test_branch_creates_deterministic_siblings_within_bound():
    episode = new_episode(
        episode_id="e0",
        organism_id="o0",
        root_state_id="s0",
        mode=GenerativeMode.OFFLINE,
        symbiont_tick=0,
        generative_tick=0,
    )
    workspace = GenerativeWorkspace(episode=episode)
    workspace.add_state(
        GenerativeState(
            "s0", "e0", EpistemicOrigin.INFERRED, None, 0, (), (), (), (), (), (), 0.3, 1.0, 0
        )
    )
    registry = GenerativeModelRegistry()
    registry.register(BranchModel("z-model"))
    registry.register(BranchModel("a-model"))

    result = BranchEngine(registry=registry, workspace=workspace).branch(
        root_state_id="s0", context=GenerativeContext(), max_branches=1
    )

    assert result.termination.value == "completed"
    assert [state.source_model_ids for state in result.states] == [("a-model",)]
    assert result.transitions[0].operation is GenerativeOperation.BRANCH
    assert episode.branch_count == 1
