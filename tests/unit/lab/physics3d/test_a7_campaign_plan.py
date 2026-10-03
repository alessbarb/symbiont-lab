from itertools import permutations

from symbiont_lab.studies.physics3d.a7_campaign import (
    CANONICAL_BODIES,
    campaign_index_payload,
    planned_arms,
    planned_runs,
)


def test_a7_plan_covers_all_directed_reembodiment_pairs_and_312_runs():
    arms = planned_arms()
    reembodiment = [arm for arm in arms if arm["condition"] == "re-embodiment"]

    assert len(arms) == 52
    assert len(reembodiment) == 12
    assert {(arm["source_body"], arm["destination_body"]) for arm in reembodiment} == set(
        permutations(CANONICAL_BODIES, 2)
    )
    assert len(planned_runs()) == 312


def test_a7_index_is_explicitly_non_authorizing_and_has_unique_run_keys():
    index = campaign_index_payload()

    assert index["execution_authorized"] is False
    assert index["execution_count"] == 312
    keys = [run["key"] for run in index["runs"]]
    assert len(keys) == len(set(keys))
