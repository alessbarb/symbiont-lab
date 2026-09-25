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


def test_mature_signal_projects_only_to_external_structural_contention():
    consolidator = GenerativeConsolidator()
    for episode_id, model_id in (("e0", "m0"), ("e1", "m1")):
        consolidator.tracker.record(
            representation_ref="r0",
            episode_id=episode_id,
            state_id=f"{episode_id}-s0",
            model_ids=(model_id,),
        )
    signal = consolidator.signal(representation_ref="r0", generative_demand=0.8)
    projection = consolidator.project_candidate(
        signal=signal,
        candidate_id="candidate-0",
        eligible_tick=12,
        mutation_payloads=("add-node:concept",),
    )
    calls = []
    assert projection is not None
    assert consolidator.submit_candidate(
        projection,
        register=lambda **kwargs: calls.append(kwargs) or True,
        mutations=(object(),),
    )
    assert calls[0]["producer_id"] == "producer.generative"
    assert calls[0]["family"] == "generative"
