from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.generative import (
    CounterfactualEngine,
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
class CounterfactualModel:
    model_id: str = "counterfactual-model"

    def supports(self, operation, state):
        return operation is GenerativeOperation.COUNTERFACTUAL

    def generate(self, *, state, operation, context):
        return (
            GeneratedProposal(
                (GeneratedFeature("hypothetical", "changed", 0.7, self.model_id),),
                ("hypothetical",),
                0.6,
                0.8,
                self.model_id,
                (state.state_id,),
            ),
        )


def test_counterfactual_is_generated_and_never_executes_an_intervention():
    episode = new_episode(
        episode_id="e0",
        organism_id="o0",
        root_state_id="s0",
        mode=GenerativeMode.IDLE,
        symbiont_tick=0,
        generative_tick=0,
    )
    workspace = GenerativeWorkspace(episode=episode)
    workspace.add_state(
        GenerativeState(
            "s0", "e0", EpistemicOrigin.INFERRED, None, 0, (), (), (), (), (), (), 0.2, 1.0, 0
        )
    )
    registry = GenerativeModelRegistry()
    registry.register(CounterfactualModel())

    result = CounterfactualEngine(registry=registry, workspace=workspace).evaluate(
        root_state_id="s0", context=GenerativeContext(tokens=("intervention:open",)), max_depth=1
    )

    assert result.states[0].origin is EpistemicOrigin.COUNTERFACTUAL
    assert result.transitions[0].operation is GenerativeOperation.COUNTERFACTUAL
    assert result.states[0].source_state_ids == ("s0",)
