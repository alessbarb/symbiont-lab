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



def test_source_diversity_grows_only_from_independent_factual_reconciliation_refs():
    consolidator = GenerativeConsolidator()
    for episode_id in ("e0", "e1", "e2"):
        consolidator.tracker.record(
            representation_ref="r0",
            episode_id=episode_id,
            state_id=f"{episode_id}.s0",
            model_ids=("m0",),
        )

    before = consolidator.signal(representation_ref="r0", generative_demand=0.7)
    assert before.recurrent_activation == 3
    assert before.independent_episode_count == 3
    assert before.source_diversity == 0

    consolidator.tracker.note_factual_sources(
        representation_ref="r0",
        source_refs=("evidence.1",),
    )
    consolidator.tracker.note_factual_sources(
        representation_ref="r0",
        source_refs=("evidence.1",),
    )
    once = consolidator.signal(representation_ref="r0", generative_demand=0.7)
    assert once.source_diversity == 1

    consolidator.tracker.note_factual_sources(
        representation_ref="r0",
        source_refs=("evidence.2",),
    )
    after = consolidator.signal(representation_ref="r0", generative_demand=0.7)
    assert after.source_diversity == 2
    assert consolidator.is_mature(after)


def test_generative_use_checkpoint_round_trip_preserves_bounded_source_diversity():
    from symbiont.cognition.generative.consolidation import GenerativeUseTracker

    tracker = GenerativeUseTracker()
    tracker.record(
        representation_ref="r0",
        episode_id="e0",
        state_id="s0",
        model_ids=("m0",),
        model_disagreement=0.5,
    )
    tracker.note_factual_sources(
        representation_ref="r0",
        source_refs=("evidence.1", "evidence.2"),
    )

    restored = GenerativeUseTracker.from_checkpoint(tracker.checkpoint())
    signal = restored.signal(representation_ref="r0", generative_demand=0.7)

    assert signal.recurrent_activation == 1
    assert signal.independent_episode_count == 1
    assert signal.source_diversity == 2
    assert signal.model_disagreement == 0.5



def test_generative_retention_demand_decays_with_age_without_erasing_history():
    consolidator = GenerativeConsolidator(retention_decay_ticks=8)
    for tick, episode_id, evidence_ref in (
        (0, "e0", "evidence.0"),
        (1, "e1", "evidence.1"),
    ):
        consolidator.tracker.record(
            representation_ref="r0",
            episode_id=episode_id,
            state_id=f"{episode_id}.s0",
            model_ids=("m0",),
            tick=tick,
        )
        consolidator.tracker.note_factual_sources(
            representation_ref="r0",
            source_refs=(evidence_ref,),
        )

    fresh = consolidator.signal(
        representation_ref="r0",
        generative_demand=consolidator.demand_for_age(0),
    )
    old = consolidator.signal(
        representation_ref="r0",
        generative_demand=consolidator.demand_for_age(16),
    )

    assert consolidator.is_mature(fresh)
    assert not consolidator.is_mature(old)
    assert old.source_diversity == fresh.source_diversity == 2
    assert old.cross_episode_reuse == fresh.cross_episode_reuse == 1


def test_last_generative_use_tick_survives_checkpoint():
    from symbiont.cognition.generative.consolidation import GenerativeUseTracker

    tracker = GenerativeUseTracker()
    tracker.record(
        representation_ref="r0",
        episode_id="e0",
        state_id="s0",
        tick=41,
    )

    restored = GenerativeUseTracker.from_checkpoint(tracker.checkpoint())

    assert restored.last_use_tick("r0") == 41
