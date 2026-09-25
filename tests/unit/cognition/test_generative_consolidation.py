from symbiont.cognition.generative import GenerativeConsolidator


def test_generative_use_tracks_cross_episode_reuse_without_factual_counts():
    consolidator = GenerativeConsolidator()
    consolidator.tracker.record(
        representation_ref="r0",
        episode_id="e0",
        state_id="s0",
        model_ids=("m0",),
        hypothesis_ref="h0",
        model_disagreement=0.2,
    )
    consolidator.tracker.record(
        representation_ref="r0",
        episode_id="e1",
        state_id="s1",
        model_ids=("m1",),
        hypothesis_ref="h0",
        model_disagreement=0.6,
    )

    signal = consolidator.signal(representation_ref="r0", generative_demand=0.7)
    assert signal.recurrent_activation == 2
    assert signal.cross_episode_reuse == 1
    assert signal.independent_episode_count == 2
    assert signal.source_diversity == 2
    assert signal.hypothesis_persistence == 2
    assert signal.model_disagreement == 0.4
