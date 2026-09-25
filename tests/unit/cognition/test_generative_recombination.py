import pytest

from symbiont.cognition.generative import (
    EpistemicOrigin,
    ExperienceRecombiner,
    GeneratedFeature,
    GenerativeMode,
    GenerativeWorkspace,
    RecombinationFragment,
    new_episode,
)


def _fragment(episode_id: str, state_id: str, key: str) -> RecombinationFragment:
    return RecombinationFragment(
        source_episode_id=episode_id,
        source_state_id=state_id,
        features=(GeneratedFeature(key, "value", 0.7),),
        compatibility_keys=(key,),
        uncertainty=0.3,
        coherence=0.8,
    )


def test_recombination_requires_organism_owned_compatibility_and_preserves_sources():
    episode = new_episode(
        episode_id="recombine-e0",
        organism_id="o0",
        root_state_id="root",
        mode=GenerativeMode.IDLE,
        symbiont_tick=0,
        generative_tick=3,
    )
    workspace = GenerativeWorkspace(episode=episode)
    recombiner = ExperienceRecombiner(workspace=workspace)

    with pytest.raises(ValueError, match="compatibility"):
        recombiner.combine(_fragment("a", "a0", "left"), _fragment("b", "b0", "right"))

    state = recombiner.combine(_fragment("a", "a0", "shared"), _fragment("b", "b0", "shared"))
    assert state.origin is EpistemicOrigin.IMAGINED
    assert state.source_episode_ids == ("a", "b")
    assert state.source_state_ids == ("a0", "b0")
    assert state.active_concept_ids == ("shared",)
    assert len(state.features) == 2
