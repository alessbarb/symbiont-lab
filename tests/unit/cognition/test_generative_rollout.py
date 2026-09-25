from __future__ import annotations

from dataclasses import dataclass

from symbiont.cognition.generative import (
    EpistemicOrigin,
    GeneratedFeature,
    GeneratedProposal,
    GenerativeContext,
    GenerativeMode,
    GenerativeModelRegistry,
    GenerativeOperation,
    GenerativeState,
    GenerativeWorkspace,
    RolloutEngine,
    new_episode,
)


@dataclass
class Model:
    model_id: str = "model-a"

    def supports(self, operation, state):
        return operation is GenerativeOperation.PREDICT

    def generate(self, *, state, operation, context):
        return (
            GeneratedProposal(
                (GeneratedFeature("next", state.depth, 0.8, self.model_id),),
                ("next",),
                0.2,
                0.9,
                self.model_id,
                (state.state_id,),
            ),
        )


def test_rollout_composes_multiple_steps_and_preserves_uncertainty():
    episode = new_episode(
        episode_id="e0",
        organism_id="o0",
        root_state_id="s0",
        mode=GenerativeMode.ONLINE,
        symbiont_tick=0,
        generative_tick=0,
    )
    workspace = GenerativeWorkspace(episode=episode)
    workspace.add_state(
        GenerativeState(
            "s0", "e0", EpistemicOrigin.INFERRED, None, 0, (), (), (), (), (), (), 0.4, 1.0, 0
        )
    )
    registry = GenerativeModelRegistry()
    registry.register(Model())
    result = RolloutEngine(registry=registry, workspace=workspace).rollout(
        root_state_id="s0", context=GenerativeContext(), max_depth=2
    )
    assert result.termination.value == "completed"
    assert len(result.states) == len(result.transitions) == 2
    assert result.states[-1].uncertainty >= result.states[0].uncertainty
    assert result.states[-1].origin is EpistemicOrigin.INFERRED
