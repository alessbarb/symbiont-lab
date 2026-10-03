"""Re-embodiment Functional Transfer v1: mechanical and decision-rule contracts.

Synthetic tables and short mechanics runs only. Nothing here is evidence about
transfer; the scientific campaign is a governed run of the frozen protocol.
"""

from __future__ import annotations

import hashlib

import pytest

from symbiont.actuation.types import Actuation
from symbiont_lab.experiments.loader import load_experiment_file
from symbiont_lab.studies.embodiment import reembodiment_functional_transfer as study
from symbiont_lab.studies.embodiment.reembodiment_functional_transfer import (
    ARMS,
    CONFIRMATION_SEEDS,
    DEVELOPMENT_SEEDS,
    RELATIONS,
    TARGET_MAPPING,
    ArmRun,
    body_family,
    confirmatory_claim,
    level_outcome,
    run_arm,
    seed_contamination,
    shared_pairs,
)
from symbiont_lab.studies.learning.agency_acquisition_body import BodyCondition, CausalBody

pytestmark = pytest.mark.experiment_contract

# Digests of the Body's readings and ground truth before the mapping parameter
# existed (main@6af053aa). Ten recorded agency-acquisition experiments use it.
REFERENCE = {
    "normal": "1001fea44240d85a09438631ccaf9b3bb0949eceb39bd7e082414f55195b7507",
    "permuted": "acf07339ea39c27c51ef3818776225a2b364fd7c59f8101b095372eaa561d4a0",
    "broken_effector": "0736fe2b04d44e3bd5e58f6352f4c5fd3add0b2f8297ffaae68afe39af59d339",
}


@pytest.mark.parametrize("condition", list(BodyCondition))
def test_existing_body_conditions_are_byte_identical(condition: BodyCondition) -> None:
    body = CausalBody(
        actuator_count=4,
        seed=127,
        condition=condition,
        inert_actuator_count=1,
        receptors_per_actuator=2,
        drifting_receptor_count=1,
    )
    digest = hashlib.sha256()
    for step in range(200):
        body.advance(
            [
                Actuation(
                    actuator_id=actuator_id,
                    requested=((step * 7 + index * 3) % 5) / 4,
                    delivered=((step * 7 + index * 3) % 5) / 4,
                )
                for index, actuator_id in enumerate(body.surface.actuator_ids)
                if (step + index) % 3
            ]
        )
        digest.update(repr([round(r.value, 12) for r in body.sample(body.discover())]).encode())
    digest.update(repr(body.ground_truth()).encode())

    assert digest.hexdigest() == REFERENCE[condition.value]


def test_a_mapping_changes_only_which_receptor_an_actuator_drives() -> None:
    plain = CausalBody(actuator_count=4, seed=9)
    identity = CausalBody(actuator_count=4, seed=9, actuator_mapping=(0, 1, 2, 3))
    swapped = CausalBody(actuator_count=4, seed=9, actuator_mapping=(1, 0, 3, 2))

    assert identity.ground_truth() == plain.ground_truth()
    assert swapped.receptor_ids == plain.receptor_ids
    assert swapped.surface.contract_fingerprint == plain.surface.contract_fingerprint
    assert swapped.surface.actuator_ids == plain.surface.actuator_ids
    assert [swapped.driven_receptor(a) for a in swapped.surface.actuator_ids] == [
        plain.receptor_ids[index] for index in (1, 0, 3, 2)
    ]
    with pytest.raises(ValueError, match="permutation"):
        CausalBody(actuator_count=4, seed=9, actuator_mapping=(0, 0, 1, 2))
    with pytest.raises(ValueError, match="PERMUTED"):
        CausalBody(
            actuator_count=4,
            seed=9,
            condition=BodyCondition.PERMUTED,
            actuator_mapping=(0, 1, 2, 3),
        )


@pytest.mark.parametrize(
    ("relation", "expected"), [("same_structure", 4), ("partial", 2), ("unrelated", 0)]
)
def test_the_body_family_realises_the_declared_dose(relation: str, expected: int) -> None:
    for seed_index in (0, 1):
        family = body_family(relation, seed_index=seed_index)
        assert family["target"] == TARGET_MAPPING
        assert shared_pairs(family["source"]) == expected
        # The sham Body never shares a pair with the target.
        assert shared_pairs(family["sham"]) == 0
        assert all(sorted(mapping) == [0, 1, 2, 3] for mapping in family.values())


def test_source_and_sham_are_swapped_on_alternate_seeds_at_the_unrelated_level() -> None:
    even, odd = (body_family("unrelated", seed_index=index) for index in (0, 1))
    assert (even["source"], even["sham"]) == (odd["sham"], odd["source"])
    assert even["source"] != even["sham"]


def test_family_candidates_cover_every_mapping_of_each_dose() -> None:
    assert len(study.PARTIAL_CANDIDATES) == 6 and len(study.UNRELATED_CANDIDATES) == 9
    assert all(shared_pairs(mapping) == 2 for mapping in study.PARTIAL_CANDIDATES)
    assert all(shared_pairs(mapping) == 0 for mapping in study.UNRELATED_CANDIDATES)


def test_family_rule_picks_the_smallest_spread_and_breaks_ties_lexicographically() -> None:
    medians = {mapping: 200.0 for mapping in study.PARTIAL_CANDIDATES + study.UNRELATED_CANDIDATES}
    medians[TARGET_MAPPING] = 100.0
    medians[(0, 1, 3, 2)] = 104.0
    # Three unrelated candidates tie; the lexicographically smallest pair wins.
    for mapping in ((1, 2, 3, 0), (1, 3, 0, 2), (3, 2, 1, 0)):
        medians[mapping] = 101.0
    choice = study.choose_family(medians)
    assert choice["family"] == {
        "target": TARGET_MAPPING,
        "partial": (0, 1, 3, 2),
        "unrelated_1": (1, 2, 3, 0),
        "unrelated_2": (1, 3, 0, 2),
    }
    assert choice["within_limit"] and choice["spread"] == pytest.approx(4 / 101)


def test_family_rule_reports_not_runnable_when_no_family_fits() -> None:
    far = {mapping: 300.0 for mapping in study.PARTIAL_CANDIDATES + study.UNRELATED_CANDIDATES}
    far[TARGET_MAPPING] = 100.0
    assert study.choose_family(far)["within_limit"] is False
    assert study.choose_family({TARGET_MAPPING: None})["family"] is None


def test_the_r6_family_was_outside_the_spread() -> None:
    # The recorded r6 development medians (87/73/73/93) give 0.25 under the rule.
    medians = {
        TARGET_MAPPING: 87.0,
        (0, 1, 3, 2): 73.0,
        (1, 0, 3, 2): 73.0,
        (2, 3, 0, 1): 93.0,
    }
    assert study.choose_family(medians)["spread"] == pytest.approx(0.25)


def test_seed_lists_are_the_frozen_ones_and_disjoint() -> None:
    assert DEVELOPMENT_SEEDS == (101, 103, 107, 109, 113, 131, 137, 139, 149)
    assert len(CONFIRMATION_SEEDS) == 12
    assert not set(DEVELOPMENT_SEEDS) & set(CONFIRMATION_SEEDS)
    # 127 was used for an exploratory look and is excluded from both lists.
    assert 127 not in DEVELOPMENT_SEEDS + CONFIRMATION_SEEDS


def _run(arm: str, m1: int | None, *, seed: int = 1, rate: float = 1.0, **overrides) -> ArmRun:
    values = dict(
        seed=seed,
        relation="same_structure",
        arm=arm,
        m1=m1,
        horizon=400,
        actuations=100,
        activity_rate=rate,
        valid_bindings_at_horizon=1,
        entry_tick=0,
        target_ground_truth_hash="g",
        undriven_response_hash="u",
        observer_schedule=(400,),
        integrity_failures=(),
    )
    values.update(overrides)
    return ArmRun(**values)


def _level(rows: list[tuple[int | None, int | None, int | None]], **kwargs) -> dict:
    return level_outcome(
        {
            seed: {
                "transfer": _run("transfer", t, seed=seed, **kwargs),
                "sham_experience": _run("sham_experience", s, seed=seed),
                "naive": _run("naive", n, seed=seed),
            }
            for seed, (t, s, n) in enumerate(rows)
        }
    )


def test_advantage_needs_the_same_seed_to_beat_both_controls_and_a_large_enough_reduction() -> None:
    assert _level([(100, 200, 200)] * 12)["outcome"] == "advantage"
    # Ten seeds beat sham and ten beat naive, but not the same ten.
    split = [(100, 200, 50)] * 2 + [(100, 50, 200)] * 2 + [(100, 200, 200)] * 8
    assert _level(split)["advantage"] is False
    # Wins on every seed but by less than the preregistered 20%.
    assert _level([(190, 200, 200)] * 12)["advantage"] is False


def test_practical_null_negative_transfer_and_inconclusive_are_distinct() -> None:
    assert _level([(200, 200, 200)] * 12)["outcome"] == "practical_null"
    assert _level([(300, 200, 100)] * 12)["outcome"] == "negative_transfer"
    # Earlier on every seed, but by 15%: too small for an advantage, too large
    # for the practical-null margin.
    assert _level([(170, 200, 200)] * 12)["outcome"] == "inconclusive"
    # Half the seeds much earlier, half much later: the median reduction is 0
    # and neither arm wins ten seeds, which the rule calls practically null.
    split = [(100, 200, 200)] * 6 + [(300, 200, 200)] * 6
    assert _level(split)["outcome"] == "practical_null"


def test_censored_pairs_are_ties_and_a_censored_treatment_loses_to_a_finished_control() -> None:
    assert _level([(None, None, None)] * 12)["seeds_transfer_first_over_both"] == 0
    assert _level([(None, 200, 100)] * 12)["outcome"] == "negative_transfer"


def test_a_level_with_too_many_contaminated_seeds_is_not_assessable() -> None:
    runs = {
        seed: {
            "transfer": _run(
                "transfer",
                100,
                seed=seed,
                integrity_failures=("authority_at_entry",) if seed < 3 else (),
            ),
            "sham_experience": _run("sham_experience", 200, seed=seed),
            "naive": _run("naive", 200, seed=seed),
        }
        for seed in range(12)
    }
    assert level_outcome(runs)["outcome"] == "not_assessable"


def test_cross_arm_integrity_conditions_are_checked() -> None:
    arms = [_run("transfer", 1), _run("sham_experience", 1), _run("naive", 1)]
    assert seed_contamination(arms) == ()
    different_body = [*arms[:2], _run("naive", 1, target_ground_truth_hash="other")]
    assert "target_body_differs_between_arms" in seed_contamination(different_body)
    different_observer = [*arms[:2], _run("naive", 1, observer_schedule=(100, 400))]
    assert "observer_schedule_differs_between_arms" in seed_contamination(different_observer)
    different_response = [*arms[:2], _run("naive", 1, undriven_response_hash="x")]
    assert "undriven_response_differs_between_arms" in seed_contamination(different_response)


ADVANTAGE = [(100, 200, 200)] * 12
PARTIAL = [(160, 200, 200)] * 12
NULL = [(200, 200, 200)] * 12


def _claim(r1, r2, r3, **r1_kwargs) -> str:
    return confirmatory_claim(
        {"same_structure": _level(r1, **r1_kwargs), "partial": _level(r2), "unrelated": _level(r3)}
    )["claim"]


def test_the_single_confirmatory_claim_is_a_conjunction() -> None:
    assert _claim(ADVANTAGE, PARTIAL, NULL) == "functional_transfer_established_within_scope"
    # Advantage with an activity excess is activity, not transfer.
    assert _claim(ADVANTAGE, PARTIAL, NULL, rate=2.0) == "activity_not_transfer"
    # An advantage where source and sham are exchangeable invalidates the study.
    assert _claim(ADVANTAGE, PARTIAL, ADVANTAGE) == "apparatus_asymmetry_study_invalid"
    # Advantage without the dose pattern is not a transfer claim.
    inconclusive_r3 = [(170, 200, 200)] * 12
    assert _claim(ADVANTAGE, PARTIAL, inconclusive_r3) == (
        "advantage_at_same_structure_dose_pattern_not_established"
    )
    # Faster than a newborn but not than an equally old organism: maturity.
    assert _claim([(150, 150, 300)] * 12, NULL, NULL) == "maturity_effect_not_transfer"
    assert _claim([(300, 200, 100)] * 12, NULL, NULL) == "negative_transfer_at_same_structure"
    assert _claim(NULL, NULL, NULL) == "no_transfer"


def test_the_experiment_record_matches_the_frozen_constants() -> None:
    spec = load_experiment_file(
        "experiments/embodiment/reembodiment-functional-transfer-v1/experiment.toml"
    )
    frozen = spec.extra_params["transfer"]

    assert spec.protocol == study.PROTOCOL
    assert tuple(spec.seeds) == CONFIRMATION_SEEDS
    assert tuple(frozen["development_seeds"]) == DEVELOPMENT_SEEDS
    assert tuple(frozen["arms"]) == ARMS and tuple(frozen["relations"]) == RELATIONS
    assert frozen["actuators"] == study.ACTUATORS
    assert frozen["shared_pairs"] == {
        relation: shared_pairs(body_family(relation, seed_index=0)["source"])
        for relation in RELATIONS
    }
    assert frozen["min_seeds_improved"] == study.MIN_SEEDS_IMPROVED
    assert frozen["min_median_paired_reduction"] == study.MIN_MEDIAN_PAIRED_REDUCTION
    assert frozen["practical_null_margin"] == study.PRACTICAL_NULL_MARGIN
    assert frozen["max_activity_rate_ratio"] == study.MAX_ACTIVITY_RATE_RATIO
    assert frozen["max_contaminated_seeds"] == study.MAX_CONTAMINATED_SEEDS
    assert frozen["max_body_difficulty_spread"] == study.MAX_BODY_DIFFICULTY_SPREAD


@pytest.mark.parametrize("arm", ARMS)
def test_mechanics_every_arm_enters_the_target_body_without_authority(arm: str) -> None:
    # A seed outside both frozen lists and horizons far too short to measure
    # anything: this checks the machinery, not the organism.
    run = run_arm(7, "partial", arm, seed_index=0, development_ticks=60, horizon=20)

    assert run.integrity_failures == ()
    assert run.entry_tick == (0 if arm == "naive" else 60)
    assert run.horizon == 20 and run.observer_schedule == (20,)
    assert run.m1 is None or 1 <= run.m1 <= 20


def test_mechanics_the_three_arms_of_a_seed_meet_the_same_target_body() -> None:
    runs = [
        run_arm(7, "unrelated", arm, seed_index=1, development_ticks=40, horizon=15) for arm in ARMS
    ]
    assert seed_contamination(runs) == ()
