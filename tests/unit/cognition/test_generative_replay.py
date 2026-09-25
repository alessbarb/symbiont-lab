from symbiont.cognition.generative import (
    EpistemicOrigin,
    GeneratedFeature,
    GenerativeMode,
    GenerativeWorkspace,
    ReplayEngine,
    ReplayFragment,
    new_episode,
)


def test_replay_materializes_source_identity_without_new_factual_support():
    episode = new_episode(
        episode_id="replay-e0",
        organism_id="o0",
        root_state_id="root",
        mode=GenerativeMode.OFFLINE,
        symbiont_tick=4,
        generative_tick=9,
        source_episode_ids=("factual-e1",),
    )
    workspace = GenerativeWorkspace(episode=episode)
    state = ReplayEngine(workspace=workspace).materialize(
        ReplayFragment(
            source_episode_id="factual-e1",
            source_state_id="factual-s7",
            features=(GeneratedFeature("remembered", "blue", 0.8, None),),
            uncertainty=0.3,
            coherence=0.7,
        )
    )

    assert state.origin is EpistemicOrigin.REPLAYED
    assert state.source_episode_ids == ("factual-e1",)
    assert state.source_state_ids == ("factual-s7",)
    assert state.source_model_ids == ()
    assert workspace.episode.source_episode_ids == ("factual-e1",)
