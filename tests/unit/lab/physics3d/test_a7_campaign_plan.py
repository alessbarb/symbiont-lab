from symbiont_lab.studies.physics3d.a7_campaign import (
    CANONICAL_BODIES,
    REEMBODIMENT_TRANSITIONS,
    campaign_index_payload,
    planned_arms,
    planned_runs,
)


def test_a7_plan_covers_balanced_cycle_reembodiment_and_264_runs():
    arms = planned_arms()
    reembodiment = [arm for arm in arms if arm["condition"] == "re-embodiment"]

    assert len(arms) == 44
    assert len(reembodiment) == 4
    assert {(arm["source_body"], arm["destination_body"]) for arm in reembodiment} == set(
        REEMBODIMENT_TRANSITIONS
    )
    assert {source for source, _ in REEMBODIMENT_TRANSITIONS} == set(CANONICAL_BODIES)
    assert {destination for _, destination in REEMBODIMENT_TRANSITIONS} == set(CANONICAL_BODIES)
    assert len(planned_runs()) == 264


def test_a7_index_is_explicitly_non_authorizing_and_has_unique_run_keys():
    index = campaign_index_payload()

    assert index["execution_authorized"] is False
    assert index["execution_count"] == 264
    keys = [run["key"] for run in index["runs"]]
    assert len(keys) == len(set(keys))
